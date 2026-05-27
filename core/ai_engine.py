from __future__ import annotations

from datetime import date
from typing import Any

from core.predictor import recommend_duration
from core.risk import assess_risk


def _parse_deadline(deadline: str) -> date | None:
    try:
        return date.fromisoformat(str(deadline)[:10])
    except Exception:
        return None


def _overall_risk(*levels: str) -> str:
    normalized = [str(level).lower() for level in levels]

    if "high" in normalized:
        return "high"

    if "medium" in normalized:
        return "medium"

    return "low"


def _risk_title(level: str) -> str:
    if level == "high":
        return "This task needs attention"

    if level == "medium":
        return "This task may need extra time"

    return "This task looks manageable"


def _risk_suggestion(level: str, deadline_passed: bool) -> str:
    if deadline_passed:
        return "Reschedule this task or split it into smaller steps."

    if level == "high":
        return "Start earlier, split the task, or reduce its scope."

    if level == "medium":
        return "Keep some extra time in your plan."

    return "Your current plan looks reasonable."


def _confidence_message(confidence: str) -> str:
    confidence = str(confidence).lower()

    if confidence == "high":
        return "I have strong historical data for this estimate."

    if confidence == "medium":
        return "This estimate is based on your task history."

    return "This estimate will improve as you complete more tasks."


def _build_user_bullets(
    planned: int,
    recommended: int,
    deadline: str,
    late_risk: str,
    overtime_risk: str,
) -> list[str]:
    bullets: list[str] = []
    deadline_date = _parse_deadline(deadline)
    today = date.today()

    if deadline_date:
        days_left = (deadline_date - today).days

        if days_left < 0:
            bullets.append("The deadline has already passed.")
        elif days_left == 0:
            bullets.append("The deadline is today.")
        elif days_left == 1:
            bullets.append("There is only 1 day left.")
        elif days_left <= 3:
            bullets.append(f"There are only {days_left} days left.")

    if recommended > planned:
        difference = recommended - planned

        if difference >= 10:
            bullets.append("This task may take longer than planned.")

    if late_risk == "high":
        bullets.append("The deadline looks tight.")
    elif late_risk == "medium":
        bullets.append("There is some deadline pressure.")

    if overtime_risk == "high":
        bullets.append("This task has a higher chance of taking extra time.")
    elif overtime_risk == "medium":
        bullets.append("Keep a small time buffer for this task.")

    if not bullets:
        bullets.append("No major issues detected for this task.")

    return bullets[:4]


def get_ai_task_advice(
    priority: int,
    planned: int,
    deadline: str,
) -> dict[str, Any]:
    priority = int(priority)
    planned = int(planned)
    deadline = str(deadline).strip()

    recommendation = recommend_duration(
        priority=priority,
        planned=planned,
        deadline=deadline,
    )

    risk = assess_risk(
        priority=priority,
        planned=planned,
        deadline=deadline,
    )

    recommended = int(recommendation.recommended)
    confidence = str(recommendation.confidence).lower()

    time_risk = str(risk.overtime_risk).lower()
    deadline_risk = str(risk.late_risk).lower()
    risk_level = _overall_risk(time_risk, deadline_risk)

    deadline_date = _parse_deadline(deadline)
    deadline_passed = bool(deadline_date and deadline_date < date.today())

    bullets = _build_user_bullets(
        planned=planned,
        recommended=recommended,
        deadline=deadline,
        late_risk=deadline_risk,
        overtime_risk=time_risk,
    )

    title = _risk_title(risk_level)
    suggestion = _risk_suggestion(risk_level, deadline_passed)

    if risk_level == "high":
        message = (
            f"I suggest planning around {recommended} minutes. "
            "This task needs attention before you add it to your schedule."
        )
    elif risk_level == "medium":
        message = (
            f"I suggest planning around {recommended} minutes. "
            "It looks doable, but you should keep some extra space in your plan."
        )
    else:
        message = (
            f"I suggest planning around {recommended} minutes. "
            "This task looks reasonable based on the current information."
        )

    return {
        "recommended": recommended,
        "confidence": confidence,
        "risk_level": risk_level,
        "time_risk": time_risk,
        "deadline_risk": deadline_risk,
        "assistant": {
            "title": title,
            "message": message,
            "suggestion": suggestion,
            "bullets": bullets,
            "risk_level": risk_level,
            "confidence_message": _confidence_message(confidence),
        },
        "technical": {
            "duration_details": recommendation.details,
            "overtime_prob": risk.overtime_prob,
            "late_prob": risk.late_prob,
            "overtime_risk": risk.overtime_risk,
            "late_risk": risk.late_risk,
            "risk_reasons": risk.reasons,
        },
    }