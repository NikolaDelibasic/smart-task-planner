from core.database import get_connection


def _clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def _build_insights(stats: dict) -> list[str]:
    insights = []

    total = stats["total"]
    completed = stats["completed"]
    active = stats["active"]
    avg_delta = stats["avg_delta"]
    planning_accuracy = stats["planning_accuracy"]
    productivity_score = stats["productivity_score"]
    completed_by_priority = stats["completed_by_priority"]
    total_overtime = stats["total_overtime"]
    total_undertime = stats["total_undertime"]

    # 1. Avg delta insight
    if avg_delta is not None:
        if avg_delta > 5:
            insights.append(f"You usually underestimate tasks by about {abs(avg_delta)} minutes.")
        elif avg_delta < -5:
            insights.append(f"You usually finish tasks about {abs(avg_delta)} minutes faster than planned.")
        else:
            insights.append("Your time estimates are generally close to actual task duration.")

    # 2. Planning accuracy insight
    if planning_accuracy is not None:
        if planning_accuracy >= 90:
            insights.append("Your planning accuracy is high.")
        elif planning_accuracy >= 70:
            insights.append("Your planning accuracy is good, but there is still room for improvement.")
        else:
            insights.append("Your planning accuracy is relatively low, which suggests task durations need adjustment.")

    # 3. Productivity score insight
    if productivity_score >= 85:
        insights.append("Your current productivity score indicates very strong execution consistency.")
    elif productivity_score >= 70:
        insights.append("Your current productivity score is solid and stable.")
    else:
        insights.append("Your current productivity score suggests inconsistent execution compared to the plan.")

    # 4. Priority insight
    if completed_by_priority:
        top_priority = max(completed_by_priority, key=completed_by_priority.get)
        if top_priority == 3:
            insights.append("Most of your completed tasks are high-priority tasks.")
        elif top_priority == 2:
            insights.append("Most of your completed tasks are medium-priority tasks.")
        else:
            insights.append("Most of your completed tasks are low-priority tasks.")

    # 5. Workload / backlog insight
    if active >= 8:
        insights.append("You currently have a large active backlog, which may increase scheduling pressure.")
    elif active == 0 and total > 0:
        insights.append("You currently have no active tasks, which means your backlog is fully cleared.")

    # 6. Overtime vs undertime insight
    if total_overtime > total_undertime + 20:
        insights.append("You spend significantly more extra time on tasks than you save.")
    elif total_undertime > total_overtime + 20:
        insights.append("You tend to complete tasks faster than planned more often than you exceed time.")

    # Keep it compact
    return insights[:5]


def get_basic_stats():
    with get_connection() as conn:
        cur = conn.cursor()
        stats = {}

        cur.execute("SELECT COUNT(*) AS count FROM tasks")
        stats["total"] = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) AS count FROM tasks WHERE status = 'completed'")
        stats["completed"] = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) AS count FROM tasks WHERE status != 'completed'")
        stats["active"] = cur.fetchone()["count"]

        cur.execute("SELECT COALESCE(SUM(duration), 0) AS total_time FROM tasks")
        stats["total_time"] = cur.fetchone()["total_time"]

        cur.execute("""
            SELECT COALESCE(SUM(duration), 0) AS completed_time
            FROM tasks
            WHERE status = 'completed'
        """)
        stats["completed_time"] = cur.fetchone()["completed_time"]

        cur.execute("""
            SELECT COALESCE(SUM(actual_duration), 0) AS actual_completed_time
            FROM tasks
            WHERE status = 'completed'
        """)
        stats["actual_completed_time"] = cur.fetchone()["actual_completed_time"]

        cur.execute("""
            SELECT COALESCE(SUM(actual_duration - duration), 0) AS total_delta
            FROM tasks
            WHERE status = 'completed' AND actual_duration IS NOT NULL
        """)
        stats["total_delta"] = cur.fetchone()["total_delta"]

        cur.execute("""
            SELECT AVG(actual_duration - duration) AS avg_delta
            FROM tasks
            WHERE status = 'completed' AND actual_duration IS NOT NULL
        """)
        avg = cur.fetchone()["avg_delta"]
        stats["avg_delta"] = round(avg, 1) if avg is not None else None

        cur.execute("""
            SELECT COALESCE(SUM(
                CASE
                    WHEN (actual_duration - duration) > 0
                    THEN (actual_duration - duration)
                    ELSE 0
                END
            ), 0) AS total_overtime
            FROM tasks
            WHERE status = 'completed' AND actual_duration IS NOT NULL
        """)
        stats["total_overtime"] = cur.fetchone()["total_overtime"]

        cur.execute("""
            SELECT COALESCE(SUM(
                CASE
                    WHEN (actual_duration - duration) < 0
                    THEN -(actual_duration - duration)
                    ELSE 0
                END
            ), 0) AS total_undertime
            FROM tasks
            WHERE status = 'completed' AND actual_duration IS NOT NULL
        """)
        stats["total_undertime"] = cur.fetchone()["total_undertime"]

        cur.execute("""
            SELECT priority, COUNT(*) AS count
            FROM tasks
            WHERE status = 'completed'
            GROUP BY priority
            ORDER BY priority ASC
        """)
        stats["completed_by_priority"] = {
            row["priority"]: row["count"] for row in cur.fetchall()
        }

        total = stats["total"]
        completed = stats["completed"]
        completed_time = stats["completed_time"]
        actual_completed_time = stats["actual_completed_time"]
        avg_delta = stats["avg_delta"]

        stats["completion_rate"] = round((completed / total) * 100, 1) if total > 0 else 0.0

        if actual_completed_time > 0:
            planning_accuracy = (completed_time / actual_completed_time) * 100
            stats["planning_accuracy"] = round(_clamp(planning_accuracy, 0, 100), 1)
        else:
            stats["planning_accuracy"] = None

        if avg_delta is not None:
            productivity_score = round(_clamp(100 - abs(avg_delta), 0, 100), 1)
        else:
            productivity_score = 0.0

        stats["productivity_score"] = productivity_score

        if productivity_score >= 85:
            stats["score_label"] = "Excellent"
            stats["score_color"] = "success"
        elif productivity_score >= 70:
            stats["score_label"] = "Good"
            stats["score_color"] = "primary"
        elif productivity_score >= 50:
            stats["score_label"] = "Fair"
            stats["score_color"] = "warning"
        else:
            stats["score_label"] = "Needs Improvement"
            stats["score_color"] = "danger"

        stats["insights"] = _build_insights(stats)

        return stats