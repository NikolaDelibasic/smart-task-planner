from datetime import datetime, timedelta

from core.predictor import recommend_duration
from core.scheduler import suggest_order

DEFAULT_START_HOUR = 9
DEFAULT_START_MINUTE = 0
DEFAULT_AVAILABLE_MINUTES = 8 * 60
DEFAULT_BREAK_MINUTES = 10


def _parse_start_time(start_time: str | None) -> tuple[int, int]:
    if not start_time:
        return DEFAULT_START_HOUR, DEFAULT_START_MINUTE

    try:
        hour_str, minute_str = str(start_time).split(":")
        hour = int(hour_str)
        minute = int(minute_str)

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError

        return hour, minute
    except Exception:
        return DEFAULT_START_HOUR, DEFAULT_START_MINUTE


def generate_daily_plan(
    tasks,
    use_predicted: bool = True,
    start_time: str | None = None,
    available_minutes: int | None = None,
    break_minutes: int | None = None,
):
    ordered = suggest_order(tasks)

    start_hour, start_minute = _parse_start_time(start_time)

    if available_minutes is None or int(available_minutes) <= 0:
        available_minutes = DEFAULT_AVAILABLE_MINUTES
    else:
        available_minutes = int(available_minutes)

    if break_minutes is None or int(break_minutes) < 0:
        break_minutes = DEFAULT_BREAK_MINUTES
    else:
        break_minutes = int(break_minutes)

    day_start = datetime.combine(
        datetime.today(),
        datetime.min.time()
    ).replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)

    day_end = day_start + timedelta(minutes=available_minutes)
    current_time = day_start

    schedule = []
    unscheduled = []

    for t in ordered:
        if t["status"] == "completed":
            continue

        planned_duration = int(t["duration"])
        if planned_duration <= 0:
            unscheduled.append(dict(t))
            continue

        used_recommendation = int(t["used_recommendation"]) if "used_recommendation" in t.keys() else 0
        predicted_duration = planned_duration

        if use_predicted and not used_recommendation:
            try:
                rec = recommend_duration(
                    priority=int(t["priority"]),
                    planned=planned_duration,
                    deadline=str(t["deadline"]),
                )
                predicted_duration = int(rec.recommended)
            except Exception:
                predicted_duration = planned_duration

        duration_for_schedule = predicted_duration if (use_predicted and not used_recommendation) else planned_duration
        duration_td = timedelta(minutes=duration_for_schedule)
        task_end = current_time + duration_td

        if task_end > day_end:
            task_copy = dict(t)
            task_copy["planned_duration"] = planned_duration
            task_copy["predicted_duration"] = predicted_duration
            task_copy["used_recommendation"] = used_recommendation
            unscheduled.append(task_copy)
            continue

        slot = {
            "task_id": t["id"],
            "title": t["title"],
            "priority": t["priority"],
            "deadline": t["deadline"],
            "start": current_time.strftime("%H:%M"),
            "end": task_end.strftime("%H:%M"),
            "duration": duration_for_schedule,
            "planned_duration": planned_duration,
            "predicted_duration": predicted_duration,
            "used_recommendation": used_recommendation,
        }

        schedule.append(slot)
        current_time = task_end + timedelta(minutes=break_minutes)

    unscheduled = sorted(
        unscheduled,
        key=lambda t: (-int(t["priority"]), str(t["deadline"]), int(t["duration"]))
    )

    planner_meta = {
        "start_time": day_start.strftime("%H:%M"),
        "end_time": day_end.strftime("%H:%M"),
        "available_minutes": available_minutes,
        "break_minutes": break_minutes,
        "use_predicted": use_predicted,
    }

    return schedule, unscheduled, planner_meta