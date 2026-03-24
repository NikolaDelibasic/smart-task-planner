from datetime import datetime

from core.database import get_connection


def add_task(title, priority, deadline, duration, used_recommendation=0):
    created_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tasks (
                title,
                priority,
                deadline,
                duration,
                used_recommendation,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(title).strip(),
                int(priority),
                str(deadline).strip(),
                int(duration),
                int(used_recommendation),
                created_at,
            )
        )
        conn.commit()


def get_all_tasks():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM tasks
            ORDER BY
                CASE WHEN status != 'completed' THEN 0 ELSE 1 END ASC,
                CASE WHEN status != 'completed' THEN datetime(created_at) END DESC,
                CASE WHEN status = 'completed' THEN datetime(completed_at) END DESC,
                id DESC
        """)
        return cur.fetchall()


def delete_task(task_id):
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("SELECT * FROM tasks WHERE id = ?", (int(task_id),))
        task = cur.fetchone()

        if task and task["status"] == "completed" and task["actual_duration"]:
            cur.execute("""
                INSERT INTO task_history (
                    title,
                    priority,
                    planned_duration,
                    actual_duration,
                    deadline,
                    completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task["title"],
                int(task["priority"]),
                int(task["duration"]),
                int(task["actual_duration"]),
                task["deadline"],
                task["completed_at"],
            ))

        cur.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),))
        conn.commit()


def mark_completed(task_id, actual_duration: int):
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("SELECT * FROM tasks WHERE id = ?", (int(task_id),))
        task = cur.fetchone()

        completed_at = datetime.now().isoformat(timespec="seconds")

        cur.execute(
            """
            UPDATE tasks
            SET status = 'completed',
                actual_duration = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (
                int(actual_duration),
                completed_at,
                int(task_id),
            )
        )

        if task:
            cur.execute("""
                INSERT INTO task_history (
                    title,
                    priority,
                    planned_duration,
                    actual_duration,
                    deadline,
                    completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task["title"],
                int(task["priority"]),
                int(task["duration"]),
                int(actual_duration),
                task["deadline"],
                completed_at,
            ))

        conn.commit()


def get_active_tasks():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM tasks
            WHERE status != 'completed'
            ORDER BY datetime(created_at) DESC, id DESC
        """)
        return cur.fetchall()


def get_completed_tasks():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM tasks
            WHERE status = 'completed'
            ORDER BY datetime(completed_at) DESC, id DESC
        """)
        return cur.fetchall()


def get_tasks_by_date_range(start_date: str, end_date: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM tasks
            WHERE substr(deadline, 1, 10) >= ?
              AND substr(deadline, 1, 10) < ?
            ORDER BY
                CASE WHEN status != 'completed' THEN 0 ELSE 1 END ASC,
                priority DESC,
                duration ASC,
                datetime(created_at) DESC,
                id DESC
        """, (start_date, end_date))
        return cur.fetchall()