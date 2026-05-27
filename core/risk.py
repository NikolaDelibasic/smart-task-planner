from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Tuple

from core.database import get_connection
from core.predictor import recommend_duration
from core.priority import importance_score, normalize_priority
from core.risk_model import predict_risk_with_model


@dataclass
class RiskResult:
    overtime_risk: str
    late_risk: str
    overtime_prob: float
    late_prob: float
    reasons: List[str]


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _days_until(deadline_str: str) -> int:
    d = date.fromisoformat(str(deadline_str)[:10])
    return (d - date.today()).days


def _is_weekend_deadline(deadline_str: str) -> bool:
    d = date.fromisoformat(str(deadline_str)[:10])
    return d.weekday() >= 5


def _risk_bucket(p: float) -> str:
    if p >= 0.75:
        return "high"

    if p >= 0.45:
        return "medium"

    return "low"


def _get_active_backlog_count() -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tasks WHERE status != 'completed'")
        n = cur.fetchone()[0] or 0

    return int(n)


def _get_active_backlog_predicted_minutes(exclude_deadline: str | None = None) -> int:
    with get_connection() as conn:
        cur = conn.cursor()

        if exclude_deadline:
            cur.execute("""
                SELECT COALESCE(SUM(duration), 0)
                FROM tasks
                WHERE status != 'completed'
                  AND substr(deadline, 1, 10) <= substr(?, 1, 10)
            """, (exclude_deadline,))
        else:
            cur.execute("""
                SELECT COALESCE(SUM(duration), 0)
                FROM tasks
                WHERE status != 'completed'
            """)

        total = cur.fetchone()[0] or 0

    return int(total)


def _historical_overtime_rate(priority: int) -> float:
    priority = normalize_priority(priority)

    with get_connection() as conn:
        cur = conn.cursor()

        def rate_for(where_clause: str, params: Tuple) -> Tuple[int, float]:
            cur.execute(f"""
                SELECT COUNT(*)
                FROM task_history
                WHERE actual_duration IS NOT NULL
                {where_clause}
            """, params)

            total = cur.fetchone()[0] or 0

            cur.execute(f"""
                SELECT COUNT(*)
                FROM task_history
                WHERE actual_duration IS NOT NULL
                  AND actual_duration > planned_duration
                {where_clause}
            """, params)

            overtime = cur.fetchone()[0] or 0

            return int(total), (float(overtime) / float(total)) if total else 0.0

        priority_count, priority_rate = rate_for("AND priority = ?", (priority,))

        if priority_count >= 8:
            return priority_rate

        _, all_rate = rate_for("", tuple())

    return all_rate


def _historical_late_rate(priority: int) -> float:
    priority = normalize_priority(priority)

    with get_connection() as conn:
        cur = conn.cursor()

        def rate_for(where_clause: str, params: Tuple) -> Tuple[int, float]:
            cur.execute(f"""
                SELECT COUNT(*)
                FROM task_history
                WHERE completed_at IS NOT NULL
                  AND deadline IS NOT NULL
                {where_clause}
            """, params)

            total = cur.fetchone()[0] or 0

            cur.execute(f"""
                SELECT COUNT(*)
                FROM task_history
                WHERE completed_at IS NOT NULL
                  AND deadline IS NOT NULL
                  AND date(substr(completed_at, 1, 10)) > date(substr(deadline, 1, 10))
                {where_clause}
            """, params)

            late = cur.fetchone()[0] or 0

            return int(total), (float(late) / float(total)) if total else 0.0

        priority_count, priority_rate = rate_for("AND priority = ?", (priority,))

        if priority_count >= 8:
            return priority_rate

        _, all_rate = rate_for("", tuple())

    return all_rate


def _assess_risk_fallback(priority: int, planned: int, deadline: str) -> RiskResult:
    priority = normalize_priority(priority)
    planned = int(planned)
    deadline = str(deadline).strip()

    reasons: List[str] = []

    recommendation = recommend_duration(
        priority=priority,
        planned=planned,
        deadline=deadline,
    )

    predicted = int(recommendation.recommended)

    overtime_rate = _historical_overtime_rate(priority)
    late_rate = _historical_late_rate(priority)

    days_left = _days_until(deadline)
    weekend = _is_weekend_deadline(deadline)

    backlog_count = _get_active_backlog_count()
    backlog_minutes = _get_active_backlog_predicted_minutes(exclude_deadline=deadline)

    over_ratio = (predicted - planned) / max(1.0, float(planned))
    p_over = 0.6 * overtime_rate + 0.4 * _clamp01(0.3 + over_ratio)

    priority_importance = importance_score(priority)

    if priority_importance >= 4:
        p_over = _clamp01(p_over + 0.04)

    if weekend:
        p_over = _clamp01(p_over + 0.03)

    daily_capacity = 240
    capacity_before_deadline = max(0, days_left) * daily_capacity
    workload_before_deadline = backlog_minutes + predicted

    pressure = (workload_before_deadline - capacity_before_deadline) / max(1.0, float(daily_capacity))
    p_late = 0.6 * late_rate + 0.4 * _clamp01(0.3 + 0.2 * pressure)

    if priority_importance >= 4 and days_left <= 2:
        p_late = _clamp01(p_late + 0.08)

    if days_left >= 0:
        total_available_minutes = max(1, days_left + 1) * daily_capacity

        if predicted > total_available_minutes:
            p_late = 0.95
            reasons.append("This task may be too large for the remaining time before the deadline.")
        elif predicted > total_available_minutes * 0.75:
            p_late = max(p_late, 0.7)
            reasons.append("This task is large compared to the remaining time.")

    if days_left < 0:
        p_late = 0.95
        reasons.append("The deadline has already passed.")

    if (
        days_left >= 1
        and backlog_count == 0
        and backlog_minutes == 0
        and predicted <= 45
    ):
        p_late = min(p_late, 0.20)

    elif (
        days_left >= 1
        and backlog_count <= 2
        and backlog_minutes <= 60
        and predicted <= 30
    ):
        p_late = min(p_late, 0.25)

    if abs(predicted - planned) < 5 and days_left > 2 and backlog_count < 5:
        p_over *= 0.6
        p_late *= 0.6

    if predicted > planned:
        reasons.append("This task may take longer than planned.")

    if overtime_rate > 0.45:
        reasons.append("Similar tasks often take extra time.")

    if days_left <= 1:
        reasons.append("There is very little time left before the deadline.")

    if workload_before_deadline > capacity_before_deadline:
        reasons.append("Your current workload looks tight before this deadline.")

    if backlog_count >= 10:
        reasons.append("A large active backlog increases delay risk.")

    return RiskResult(
        overtime_risk=_risk_bucket(p_over),
        late_risk=_risk_bucket(p_late),
        overtime_prob=round(p_over, 2),
        late_prob=round(p_late, 2),
        reasons=reasons[:4],
    )


def assess_risk(priority: int, planned: int, deadline: str) -> RiskResult:
    priority = normalize_priority(priority)

    fallback = _assess_risk_fallback(
        priority=priority,
        planned=planned,
        deadline=deadline,
    )

    ml_prediction = predict_risk_with_model(
        planned_duration=planned,
        priority=priority,
        deadline=deadline,
    )

    if ml_prediction is None:
        return fallback

    return RiskResult(
        overtime_risk=ml_prediction["overtime_risk"],
        late_risk=ml_prediction["late_risk"],
        overtime_prob=ml_prediction["overtime_prob"],
        late_prob=ml_prediction["late_prob"],
        reasons=fallback.reasons,
    )