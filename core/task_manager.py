from datetime import datetime
from core.database import get_connection


def add_task(title, priority, deadline, duration, used_recommendation=0):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tasks (title, priority, deadline, duration, used_recommendation)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(title).strip(),
                int(priority),
                str(deadline).strip(),
                int(duration),
                int(used_recommendation),
            )
        )
        conn.commit()


def get_all_tasks():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks ORDER BY id DESC")
        return cur.fetchall()


def delete_task(task_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),))
        conn.commit()


def mark_completed(task_id, actual_duration: int):
    with get_connection() as conn:
        cur = conn.cursor()
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
                datetime.now().isoformat(timespec="seconds"),
                int(task_id)
            )
        )
        conn.commit()


def get_active_tasks():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM tasks
            WHERE status != 'completed'
            ORDER BY id DESC
        """)
        return cur.fetchall()


def get_completed_tasks():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM tasks
            WHERE status = 'completed'
            ORDER BY completed_at DESC, id DESC
        """)
        return cur.fetchall()


def get_tasks_by_date_range(start_date: str, end_date: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM tasks
            WHERE substr(deadline, 1, 10) >= ?
              AND substr(deadline, 1, 10) < ?
            ORDER BY substr(deadline, 1, 10) ASC, priority DESC, duration ASC
        """, (start_date, end_date))
        return cur.fetchall()