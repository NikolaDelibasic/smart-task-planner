from datetime import datetime

from core.database import get_connection
from core.ml_model import calculate_duration_features, retrain_duration_model
from core.risk_model import retrain_risk_models


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
            ),
        )

        conn.commit()


def _safe_datetime_date(value: str | None):
    if not value:
        return datetime.now().date()

    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        return datetime.now().date()


def _history_exists_for_task(cursor, task, actual_duration: int, completed_at: str) -> bool:
    task_id = int(task["id"])

    cursor.execute(
        """
        SELECT id
        FROM task_history
        WHERE source_task_id = ?
        LIMIT 1
        """,
        (task_id,),
    )

    if cursor.fetchone() is not None:
        return True

    cursor.execute(
        """
        SELECT id
        FROM task_history
        WHERE source_task_id IS NULL
          AND title = ?
          AND priority = ?
          AND planned_duration = ?
          AND actual_duration = ?
          AND deadline = ?
          AND completed_at = ?
        LIMIT 1
        """,
        (
            task["title"],
            int(task["priority"]),
            int(task["duration"]),
            int(actual_duration),
            task["deadline"],
            completed_at,
        ),
    )

    return cursor.fetchone() is not None


def _insert_task_history(cursor, task, actual_duration: int, completed_at: str) -> bool:
    if task is None:
        return False

    if _history_exists_for_task(
        cursor=cursor,
        task=task,
        actual_duration=int(actual_duration),
        completed_at=completed_at,
    ):
        return False

    task_id = int(task["id"])

    created_at = task["created_at"] or completed_at
    created_date = _safe_datetime_date(created_at)

    features = calculate_duration_features(
        planned_duration=int(task["duration"]),
        priority=int(task["priority"]),
        deadline=str(task["deadline"]),
        reference_date=created_date,
    )

    cursor.execute(
        """
        INSERT INTO task_history (
            source_task_id,
            title,
            priority,
            planned_duration,
            actual_duration,
            deadline,
            days_to_deadline,
            weekend_deadline,
            completed_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            task["title"],
            int(task["priority"]),
            int(task["duration"]),
            int(actual_duration),
            task["deadline"],
            int(features["days_to_deadline"]),
            int(features["weekend_deadline"]),
            completed_at,
            created_at,
        ),
    )

    return True


def _retrain_ai_models():
    retrain_duration_model()
    retrain_risk_models()


def get_all_tasks():
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM tasks
            ORDER BY
                CASE WHEN status != 'completed' THEN 0 ELSE 1 END ASC,
                CASE WHEN status != 'completed' THEN datetime(created_at) END DESC,
                CASE WHEN status = 'completed' THEN datetime(completed_at) END DESC,
                id DESC
            """
        )

        return cur.fetchall()


def delete_task(task_id):
    should_retrain = False

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (int(task_id),),
        )

        task = cur.fetchone()

        if task and task["status"] == "completed" and task["actual_duration"]:
            completed_at = task["completed_at"] or datetime.now().isoformat(timespec="seconds")

            should_retrain = _insert_task_history(
                cursor=cur,
                task=task,
                actual_duration=int(task["actual_duration"]),
                completed_at=completed_at,
            )

        cur.execute(
            "DELETE FROM tasks WHERE id = ?",
            (int(task_id),),
        )

        conn.commit()

    if should_retrain:
        _retrain_ai_models()


def mark_completed(task_id, actual_duration: int):
    should_retrain = False

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (int(task_id),),
        )

        task = cur.fetchone()

        if task is None:
            return

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
            ),
        )

        should_retrain = _insert_task_history(
            cursor=cur,
            task=task,
            actual_duration=int(actual_duration),
            completed_at=completed_at,
        )

        conn.commit()

    if should_retrain:
        _retrain_ai_models()


def get_active_tasks():
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM tasks
            WHERE status != 'completed'
            ORDER BY datetime(created_at) DESC, id DESC
            """
        )

        return cur.fetchall()


def get_completed_tasks():
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM tasks
            WHERE status = 'completed'
            ORDER BY datetime(completed_at) DESC, id DESC
            """
        )

        return cur.fetchall()


def get_tasks_by_date_range(start_date: str, end_date: str):
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
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
            """,
            (start_date, end_date),
        )

        return cur.fetchall()