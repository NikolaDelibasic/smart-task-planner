from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Tuple

from core.database import get_connection
from core.predictor import recommend_duration


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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tasks WHERE status != 'completed'")
    n = cur.fetchone()[0] or 0
    conn.close()
    return int(n)


def _get_active_backlog_predicted_minutes(exclude_deadline: str | None = None) -> int:
    conn = get_connection()
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

    s = cur.fetchone()[0] or 0
    conn.close()
    return int(s)


def _historical_overtime_rate(priority: int) -> float:
    conn = get_connection()
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
        over = cur.fetchone()[0] or 0

        return int(total), (float(over) / float(total)) if total else 0.0

    n_pr, r_pr = rate_for("AND priority = ?", (int(priority),))
    if n_pr >= 8:
        conn.close()
        return r_pr

    n_all, r_all = rate_for("", tuple())
    conn.close()
    return r_all


def _historical_late_rate(priority: int) -> float:
    conn = get_connection()
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

    n_pr, r_pr = rate_for("AND priority = ?", (int(priority),))
    if n_pr >= 8:
        conn.close()
        return r_pr

    n_all, r_all = rate_for("", tuple())
    conn.close()
    return r_all


def assess_risk(priority: int, planned: int, deadline: str) -> RiskResult:
    priority = int(priority)
    planned = int(planned)
    deadline = str(deadline).strip()

    reasons: List[str] = []

    rec = recommend_duration(priority=priority, planned=planned, deadline=deadline)
    predicted = int(rec.recommended)

    overtime_rate = _historical_overtime_rate(priority)
    late_rate = _historical_late_rate(priority)

    days_left = _days_until(deadline)
    weekend = _is_weekend_deadline(deadline)
    backlog_count = _get_active_backlog_count()
    backlog_minutes = _get_active_backlog_predicted_minutes(exclude_deadline=deadline)

    # === OVERTIME ===
    over_ratio = (predicted - planned) / max(1.0, float(planned))
    p_over = 0.6 * overtime_rate + 0.4 * _clamp01(0.3 + over_ratio)

    if weekend:
        p_over = _clamp01(p_over + 0.03)

    # === LATE ===
    daily_capacity = 240
    capacity_before_deadline = max(0, days_left) * daily_capacity
    workload_before_deadline = backlog_minutes + predicted

    pressure = (workload_before_deadline - capacity_before_deadline) / max(1.0, float(daily_capacity))
    p_late = 0.6 * late_rate + 0.4 * _clamp01(0.3 + 0.2 * pressure)

    # === HARD FEASIBILITY CHECK ===
    if days_left >= 0:
        total_available_minutes = max(1, days_left + 1) * daily_capacity

        if predicted > total_available_minutes:
            p_late = 0.95
            reasons.append(
                f"Task requires about {predicted} min, but only about {total_available_minutes} min remain until deadline."
            )
        elif predicted > total_available_minutes * 0.75:
            p_late = max(p_late, 0.7)
            reasons.append("Task is very large relative to the remaining time window.")

    if days_left < 0:
        p_late = 0.95
        reasons.append("Deadline is already in the past.")

    # === EASY / LOW-PRESSURE CASE REDUCTION ===
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

    # === SMART REDUCTION (LOW CASE) ===
    if abs(predicted - planned) < 5 and days_left > 2 and backlog_count < 5:
        p_over *= 0.6
        p_late *= 0.6

    # === REASONS ===
    if predicted > planned:
        reasons.append(f"Predicted duration ({predicted}m) is higher than planned ({planned}m).")

    if overtime_rate > 0.45:
        reasons.append("You often exceed planned time for similar tasks.")

    if days_left <= 1:
        reasons.append("Very little time is left until the deadline.")

    if workload_before_deadline > capacity_before_deadline:
        reasons.append("Workload before the deadline may exceed available capacity.")

    if backlog_count >= 10:
        reasons.append("A large active backlog increases delay risk.")

    return RiskResult(
        overtime_risk=_risk_bucket(p_over),
        late_risk=_risk_bucket(p_late),
        overtime_prob=round(p_over, 2),
        late_prob=round(p_late, 2),
        reasons=reasons[:4],
    )