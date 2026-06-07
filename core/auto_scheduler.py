from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple

from core.predictor import recommend_duration
from core.priority import (
    normalize_priority,
    priority_badge,
    priority_label,
    priority_short_label,
    priority_sort_value,
)
from core.scheduler import suggest_order

DEFAULT_BREAK_MINUTES = 10
DEFAULT_MIN_SPLIT_MINUTES = 15


def _row_has_key(row, key: str) -> bool:
    try:
        return key in row.keys()
    except AttributeError:
        return key in row


def _parse_time_value(value: str) -> tuple[int, int]:
    hour_str, minute_str = str(value).strip().split(":")
    hour = int(hour_str)
    minute = int(minute_str)

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError

    return hour, minute


def _build_datetime_for_today(time_str: str) -> datetime:
    hour, minute = _parse_time_value(time_str)

    return datetime.combine(
        datetime.today(),
        datetime.min.time(),
    ).replace(hour=hour, minute=minute, second=0, microsecond=0)


def _normalize_blocks_text(blocks_text: str | None) -> list[str]:
    if not blocks_text:
        return []

    raw = str(blocks_text).replace("\r", "\n")
    pieces: list[str] = []

    for line in raw.split("\n"):
        for part in line.split(","):
            part = part.strip()

            if part:
                pieces.append(part)

    return pieces


def _parse_time_blocks(blocks_text: str | None) -> list[tuple[datetime, datetime]]:
    parsed_blocks: list[tuple[datetime, datetime]] = []

    for chunk in _normalize_blocks_text(blocks_text):
        if "-" not in chunk:
            continue

        left, right = chunk.split("-", 1)

        try:
            start_dt = _build_datetime_for_today(left.strip())
            end_dt = _build_datetime_for_today(right.strip())
        except Exception:
            continue

        if end_dt > start_dt:
            parsed_blocks.append((start_dt, end_dt))

    parsed_blocks.sort(key=lambda x: x[0])

    if not parsed_blocks:
        return []

    merged: list[tuple[datetime, datetime]] = []

    for start_dt, end_dt in parsed_blocks:
        if not merged:
            merged.append((start_dt, end_dt))
            continue

        prev_start, prev_end = merged[-1]

        if start_dt <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end_dt))
        else:
            merged.append((start_dt, end_dt))

    return merged


def _get_task_duration_meta(task, use_predicted: bool) -> tuple[int, int, int]:
    planned_duration = int(task["duration"])
    used_recommendation = (
        int(task["used_recommendation"])
        if _row_has_key(task, "used_recommendation")
        else 0
    )

    predicted_duration = planned_duration

    if use_predicted and not used_recommendation:
        try:
            rec = recommend_duration(
                priority=normalize_priority(task["priority"]),
                planned=planned_duration,
                deadline=str(task["deadline"]),
            )
            predicted_duration = int(rec.recommended)
        except Exception:
            predicted_duration = planned_duration

    duration_for_schedule = (
        predicted_duration
        if use_predicted and not used_recommendation
        else planned_duration
    )

    return planned_duration, predicted_duration, max(1, duration_for_schedule)


def _format_blocks_meta(blocks: list[tuple[datetime, datetime]]) -> list[dict]:
    out = []

    for idx, (start_dt, end_dt) in enumerate(blocks, start=1):
        out.append({
            "index": idx,
            "start": start_dt.strftime("%H:%M"),
            "end": end_dt.strftime("%H:%M"),
            "minutes": int((end_dt - start_dt).total_seconds() // 60),
        })

    return out


def _priority_payload(priority_value) -> dict:
    priority = normalize_priority(priority_value)

    return {
        "priority": priority,
        "priority_label": priority_label(priority),
        "priority_short_label": priority_short_label(priority),
        "priority_badge": priority_badge(priority),
    }


def _base_planner_meta(
    *,
    blocks: list[tuple[datetime, datetime]],
    break_minutes: int,
    use_predicted: bool,
    allow_split: bool,
    min_split_minutes: int,
    time_blocks: str | None,
    scheduled_minutes: int = 0,
    unscheduled_count: int = 0,
    has_valid_blocks: bool = True,
    message: str | None = None,
) -> dict:
    total_available_minutes = sum(
        int((end_dt - start_dt).total_seconds() // 60)
        for start_dt, end_dt in blocks
    )

    return {
        "start_time": blocks[0][0].strftime("%H:%M") if blocks else None,
        "end_time": blocks[-1][1].strftime("%H:%M") if blocks else None,
        "available_minutes": total_available_minutes,
        "break_minutes": break_minutes,
        "use_predicted": use_predicted,
        "allow_split": allow_split,
        "min_split_minutes": min_split_minutes,
        "time_blocks": time_blocks or "",
        "blocks": _format_blocks_meta(blocks),
        "scheduled_minutes": scheduled_minutes,
        "unscheduled_count": unscheduled_count,
        "has_valid_blocks": has_valid_blocks,
        "message": message,
    }


def generate_daily_plan(
    tasks,
    use_predicted: bool = True,
    break_minutes: int | None = None,
    time_blocks: str | None = None,
    allow_split: bool = True,
    min_split_minutes: int | None = None,
    start_time: str | None = None,
    available_minutes: int | None = None,
):
    """
    Generates a daily plan only inside user-defined time blocks.

    start_time and available_minutes are kept only for backward compatibility
    with older calls, but they are no longer used as planner fallback values.
    """
    if break_minutes is None or int(break_minutes) < 0:
        break_minutes = DEFAULT_BREAK_MINUTES
    else:
        break_minutes = int(break_minutes)

    if min_split_minutes is None or int(min_split_minutes) <= 0:
        min_split_minutes = DEFAULT_MIN_SPLIT_MINUTES
    else:
        min_split_minutes = int(min_split_minutes)

    blocks = _parse_time_blocks(time_blocks)

    if not blocks:
        planner_meta = _base_planner_meta(
            blocks=[],
            break_minutes=break_minutes,
            use_predicted=use_predicted,
            allow_split=allow_split,
            min_split_minutes=min_split_minutes,
            time_blocks=time_blocks,
            scheduled_minutes=0,
            unscheduled_count=0,
            has_valid_blocks=False,
            message="Please enter at least one valid time block to generate your plan.",
        )

        return [], [], planner_meta

    ordered = suggest_order(tasks)

    schedule = []
    unscheduled = []

    block_index = 0
    current_time = blocks[0][0]

    def move_to_next_valid_position():
        nonlocal block_index, current_time

        while block_index < len(blocks):
            block_start, block_end = blocks[block_index]

            if current_time is None or current_time < block_start:
                current_time = block_start

            if current_time >= block_end:
                block_index += 1

                if block_index < len(blocks):
                    current_time = blocks[block_index][0]
                else:
                    current_time = None

                continue

            return

        current_time = None

    move_to_next_valid_position()

    for t in ordered:
        if t["status"] == "completed":
            continue

        planned_duration, predicted_duration, total_duration = _get_task_duration_meta(
            t,
            use_predicted,
        )

        if planned_duration <= 0:
            task_copy = dict(t)
            priority_meta = _priority_payload(task_copy["priority"])
            task_copy.update(priority_meta)
            unscheduled.append(task_copy)
            continue

        remaining = total_duration
        scheduled_parts = []

        while remaining > 0:
            move_to_next_valid_position()

            if current_time is None or block_index >= len(blocks):
                break

            block_start, block_end = blocks[block_index]
            available_here = int((block_end - current_time).total_seconds() // 60)

            if available_here <= 0:
                block_index += 1

                if block_index < len(blocks):
                    current_time = blocks[block_index][0]
                else:
                    current_time = None

                continue

            if remaining <= available_here:
                chunk = remaining
            else:
                if not allow_split:
                    break

                if available_here < min_split_minutes:
                    block_index += 1

                    if block_index < len(blocks):
                        current_time = blocks[block_index][0]
                    else:
                        current_time = None

                    continue

                chunk = available_here

            part_start = current_time
            part_end = current_time + timedelta(minutes=chunk)

            priority_meta = _priority_payload(t["priority"])

            slot = {
                "task_id": t["id"],
                "title": t["title"],
                "priority": priority_meta["priority"],
                "priority_label": priority_meta["priority_label"],
                "priority_short_label": priority_meta["priority_short_label"],
                "priority_badge": priority_meta["priority_badge"],
                "deadline": t["deadline"],
                "start": part_start.strftime("%H:%M"),
                "end": part_end.strftime("%H:%M"),
                "duration": chunk,
                "planned_duration": planned_duration,
                "predicted_duration": predicted_duration,
                "used_recommendation": (
                    int(t["used_recommendation"])
                    if _row_has_key(t, "used_recommendation")
                    else 0
                ),
                "is_split": False,
                "part_index": 1,
                "part_total": 1,
                "part_label": "",
                "block_index": block_index + 1,
                "block_start": block_start.strftime("%H:%M"),
                "block_end": block_end.strftime("%H:%M"),
            }

            scheduled_parts.append(slot)

            remaining -= chunk
            current_time = part_end + timedelta(minutes=break_minutes)

        if scheduled_parts:
            if len(scheduled_parts) > 1 or remaining > 0:
                total_parts = len(scheduled_parts) + (1 if remaining > 0 else 0)

                for idx, part in enumerate(scheduled_parts, start=1):
                    part["is_split"] = True
                    part["part_index"] = idx
                    part["part_total"] = total_parts
                    part["part_label"] = f"Part {idx}/{total_parts}"

            schedule.extend(scheduled_parts)

        if remaining > 0:
            task_copy = dict(t)
            priority_meta = _priority_payload(task_copy["priority"])

            task_copy["priority"] = priority_meta["priority"]
            task_copy["priority_label"] = priority_meta["priority_label"]
            task_copy["priority_short_label"] = priority_meta["priority_short_label"]
            task_copy["priority_badge"] = priority_meta["priority_badge"]
            task_copy["planned_duration"] = planned_duration
            task_copy["predicted_duration"] = predicted_duration
            task_copy["used_recommendation"] = (
                int(t["used_recommendation"])
                if _row_has_key(t, "used_recommendation")
                else 0
            )
            task_copy["remaining_duration"] = remaining
            task_copy["scheduled_duration"] = total_duration - remaining
            task_copy["is_partial"] = len(scheduled_parts) > 0

            unscheduled.append(task_copy)

    unscheduled = sorted(
        unscheduled,
        key=lambda task: (
            priority_sort_value(task["priority"]),
            str(task["deadline"]),
            int(
                task["remaining_duration"]
                if "remaining_duration" in task
                else task["duration"]
            ),
        ),
    )

    total_scheduled_minutes = sum(int(item["duration"]) for item in schedule)

    planner_meta = _base_planner_meta(
        blocks=blocks,
        break_minutes=break_minutes,
        use_predicted=use_predicted,
        allow_split=allow_split,
        min_split_minutes=min_split_minutes,
        time_blocks=time_blocks,
        scheduled_minutes=total_scheduled_minutes,
        unscheduled_count=len(unscheduled),
        has_valid_blocks=True,
        message=None,
    )

    return schedule, unscheduled, planner_meta