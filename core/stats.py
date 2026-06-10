from core.database import get_connection
from core.priority import (
    normalize_priority,
    priority_badge,
    priority_label,
)


def _safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _history_has_seed_column(conn):
    try:
        rows = conn.execute("PRAGMA table_info(task_history)").fetchall()
        columns = {row["name"] for row in rows}
        return "is_seed" in columns
    except Exception:
        return False


def _history_seed_filter(conn):
    """
    Seed rows are used for ML training, but not for user-facing statistics.
    This helper keeps stats.py safe even if an older database does not have is_seed yet.
    """
    if _history_has_seed_column(conn):
        return "COALESCE(is_seed, 0) = 0"

    return "1 = 1"


def _empty_priority_distribution():
    return [
        {
            "priority": 1,
            "label": "Critical",
            "badge": "danger",
            "count": 0,
            "percent": 0,
        },
        {
            "priority": 2,
            "label": "High",
            "badge": "warning",
            "count": 0,
            "percent": 0,
        },
        {
            "priority": 3,
            "label": "Normal",
            "badge": "primary",
            "count": 0,
            "percent": 0,
        },
        {
            "priority": 4,
            "label": "Low",
            "badge": "secondary",
            "count": 0,
            "percent": 0,
        },
        {
            "priority": 5,
            "label": "Optional",
            "badge": "light",
            "count": 0,
            "percent": 0,
        },
    ]


def _priority_distribution(raw_counts):
    distribution = _empty_priority_distribution()

    normalized_counts = {}

    for priority_value, count in raw_counts.items():
        priority = normalize_priority(priority_value)
        normalized_counts[priority] = normalized_counts.get(priority, 0) + _safe_int(count)

    total = sum(normalized_counts.values())

    for item in distribution:
        priority = item["priority"]
        count = normalized_counts.get(priority, 0)

        item["label"] = priority_label(priority)
        item["badge"] = priority_badge(priority)
        item["count"] = count
        item["percent"] = round((count / total) * 100, 1) if total else 0

    return distribution


def _productivity_label(score):
    score = _safe_float(score)

    if score >= 85:
        return "Excellent"

    if score >= 70:
        return "Good"

    if score >= 50:
        return "Fair"

    return "Needs improvement"


def _calculate_planning_accuracy(planned_total, actual_total):
    planned_total = _safe_float(planned_total)
    actual_total = _safe_float(actual_total)

    if actual_total <= 0:
        return 0

    error = abs(actual_total - planned_total)
    error_percent = (error / actual_total) * 100

    return round(max(0, 100 - error_percent), 1)


def _calculate_productivity_score(avg_delta, completion_rate, planning_accuracy):
    """
    Simple user-facing productivity score.

    It combines:
    - completion rate
    - planning accuracy
    - average planning difference

    Lower average difference improves the score.
    """
    avg_delta = abs(_safe_float(avg_delta))
    completion_rate = _safe_float(completion_rate)
    planning_accuracy = _safe_float(planning_accuracy)

    delta_penalty = min(avg_delta, 100)

    score = (
        completion_rate * 0.35
        + planning_accuracy * 0.45
        + max(0, 100 - delta_penalty) * 0.20
    )

    return round(max(0, min(100, score)), 1)


def _build_insights(stats):
    insights = []

    history_total = _safe_int(stats.get("history_total"))
    completion_rate = _safe_float(stats.get("completion_rate"))
    planning_accuracy = _safe_float(stats.get("planning_accuracy"))
    avg_delta = _safe_float(stats.get("avg_delta"))
    overtime_rate = _safe_float(stats.get("history_overtime_rate"))
    priority_distribution = stats.get("priority_distribution") or []

    if history_total == 0:
        insights.append(
            "No real completed task history yet. The AI can use bootstrap training data, but your personal statistics will appear after you complete real tasks."
        )
        return insights

    if completion_rate >= 80:
        insights.append("You are completing a strong percentage of your task list.")
    elif completion_rate >= 50:
        insights.append("Your completion rate is moderate. Reducing active task overload may improve focus.")
    else:
        insights.append("Your completion rate is low. Try planning fewer tasks per day.")

    if planning_accuracy >= 80:
        insights.append("Your planned durations are close to your actual work time.")
    elif avg_delta > 0:
        insights.append("Tasks often take longer than planned. Consider adding more buffer time.")
    elif avg_delta < 0:
        insights.append("Tasks often take less time than planned. You may be overestimating some tasks.")
    else:
        insights.append("There is not enough duration difference to identify a clear planning pattern yet.")

    if overtime_rate >= 50:
        insights.append("A high percentage of completed tasks went over the planned duration.")
    elif overtime_rate <= 20 and history_total >= 3:
        insights.append("Most completed tasks stayed within the planned duration.")

    top_priority = None

    if priority_distribution:
        top_priority = max(
            priority_distribution,
            key=lambda item: item.get("count", 0),
        )

    if top_priority and top_priority.get("count", 0) > 0:
        insights.append(
            f"Most completed tasks are in the {top_priority['label']} priority group."
        )

    return insights


def get_basic_stats():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        tasks = cursor.execute("""
            SELECT
                id,
                title,
                priority,
                duration,
                actual_duration,
                status,
                deadline,
                completed_at
            FROM tasks
        """).fetchall()

        total = len(tasks)
        completed_tasks = [
            task for task in tasks
            if str(task["status"]).lower() == "completed"
        ]
        active_tasks = [
            task for task in tasks
            if str(task["status"]).lower() != "completed"
        ]

        completed = len(completed_tasks)
        active = len(active_tasks)

        total_time = sum(_safe_int(task["duration"]) for task in tasks)
        active_time = sum(_safe_int(task["duration"]) for task in active_tasks)
        completed_time = sum(_safe_int(task["duration"]) for task in completed_tasks)

        completed_with_actual = [
            task for task in completed_tasks
            if task["actual_duration"] is not None
        ]

        actual_completed_time = sum(
            _safe_int(task["actual_duration"])
            for task in completed_with_actual
        )

        deltas = [
            _safe_int(task["actual_duration"]) - _safe_int(task["duration"])
            for task in completed_with_actual
        ]

        total_delta = sum(deltas)
        avg_delta = round(total_delta / len(deltas), 1) if deltas else 0

        total_overtime = sum(delta for delta in deltas if delta > 0)
        total_undertime = abs(sum(delta for delta in deltas if delta < 0))

        completion_rate = round((completed / total) * 100, 1) if total else 0

        planning_accuracy = _calculate_planning_accuracy(
            completed_time,
            actual_completed_time,
        )

        productivity_score = _calculate_productivity_score(
            avg_delta=avg_delta,
            completion_rate=completion_rate,
            planning_accuracy=planning_accuracy,
        )

        history_filter = _history_seed_filter(conn)

        history_summary = cursor.execute(f"""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(planned_duration), 0) AS planned_total,
                COALESCE(SUM(actual_duration), 0) AS actual_total,
                COALESCE(AVG(actual_duration - planned_duration), 0) AS avg_delta,
                COALESCE(SUM(CASE WHEN actual_duration > planned_duration THEN 1 ELSE 0 END), 0) AS overtime_count,
                COALESCE(SUM(CASE WHEN actual_duration < planned_duration THEN 1 ELSE 0 END), 0) AS undertime_count
            FROM task_history
            WHERE {history_filter}
        """).fetchone()

        history_total = _safe_int(history_summary["total"])
        history_planned_time = _safe_int(history_summary["planned_total"])
        history_actual_time = _safe_int(history_summary["actual_total"])
        history_avg_delta = round(_safe_float(history_summary["avg_delta"]), 1)

        history_overtime_count = _safe_int(history_summary["overtime_count"])
        history_undertime_count = _safe_int(history_summary["undertime_count"])

        history_overtime_rate = (
            round((history_overtime_count / history_total) * 100, 1)
            if history_total
            else 0
        )

        history_undertime_rate = (
            round((history_undertime_count / history_total) * 100, 1)
            if history_total
            else 0
        )

        priority_rows = cursor.execute(f"""
            SELECT
                priority,
                COUNT(*) AS count
            FROM task_history
            WHERE {history_filter}
            GROUP BY priority
        """).fetchall()

        raw_priority_counts = {
            normalize_priority(row["priority"]): _safe_int(row["count"])
            for row in priority_rows
        }

        # If the user has no real task_history yet, fall back to completed tasks
        # from the current board. Seed rows are never shown as user statistics.
        if not raw_priority_counts and completed_tasks:
            for task in completed_tasks:
                priority = normalize_priority(task["priority"])
                raw_priority_counts[priority] = raw_priority_counts.get(priority, 0) + 1

        priority_distribution = _priority_distribution(raw_priority_counts)

        completed_by_priority = {
            item["label"]: item["count"]
            for item in priority_distribution
        }

        stats = {
            "total": total,
            "completed": completed,
            "active": active,
            "total_time": total_time,
            "active_time": active_time,
            "completed_time": completed_time,
            "actual_completed_time": actual_completed_time,
            "total_delta": total_delta,
            "avg_delta": avg_delta,
            "total_overtime": total_overtime,
            "total_undertime": total_undertime,
            "completion_rate": completion_rate,
            "planning_accuracy": planning_accuracy,
            "productivity_score": productivity_score,
            "productivity_label": _productivity_label(productivity_score),

            # Long-term real user history.
            # Seed/bootstrap rows are excluded here.
            "history_total": history_total,
            "history_planned_time": history_planned_time,
            "history_actual_time": history_actual_time,
            "history_avg_delta": history_avg_delta,
            "history_overtime_count": history_overtime_count,
            "history_undertime_count": history_undertime_count,
            "history_overtime_rate": history_overtime_rate,
            "history_undertime_rate": history_undertime_rate,

            # Priority data.
            "completed_by_priority": completed_by_priority,
            "priority_distribution": priority_distribution,
        }

        stats["insights"] = _build_insights(stats)

        return stats

    finally:
        conn.close()