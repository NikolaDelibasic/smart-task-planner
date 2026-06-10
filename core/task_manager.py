from datetime import datetime

from core.database import get_connection
from core.priority import normalize_priority
from core.recurring import (
    get_next_deadline,
    normalize_repeat_interval,
    normalize_repeat_type,
)


def _safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_calculate_duration_features(priority, planned_duration, deadline, completed_at):
    """
    Keeps task_manager compatible if calculate_duration_features changes slightly.
    """
    try:
        from core.ml_model import calculate_duration_features

        try:
            return calculate_duration_features(
                priority=priority,
                planned_duration=planned_duration,
                deadline=deadline,
                completed_at=completed_at,
            )
        except TypeError:
            try:
                return calculate_duration_features(
                    priority=priority,
                    planned_duration=planned_duration,
                    deadline=deadline,
                )
            except TypeError:
                return calculate_duration_features(
                    planned_duration,
                    priority,
                    deadline,
                )

    except Exception:
        return {
            "days_to_deadline": 0,
            "weekend_deadline": 0,
        }


def _retrain_models_safely():
    try:
        from core.ml_model import retrain_duration_model
        retrain_duration_model()
    except Exception:
        pass

    try:
        from core.risk_model import retrain_risk_models
        retrain_risk_models()
    except Exception:
        pass


def add_task(
    title,
    priority,
    deadline,
    duration,
    used_recommendation=0,
    repeat_type="none",
    repeat_interval=1,
    recurring_parent_id=None,
):
    priority = normalize_priority(priority)
    duration = _safe_int(duration)
    used_recommendation = 1 if _safe_int(used_recommendation) else 0
    repeat_type = normalize_repeat_type(repeat_type)
    repeat_interval = normalize_repeat_interval(repeat_interval)

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO tasks (
                title,
                priority,
                deadline,
                duration,
                status,
                used_recommendation,
                created_at,
                repeat_type,
                repeat_interval,
                recurring_parent_id
            )
            VALUES (?, ?, ?, ?, 'pending', ?, CURRENT_TIMESTAMP, ?, ?, ?)
            """,
            (
                title,
                priority,
                deadline,
                duration,
                used_recommendation,
                repeat_type,
                repeat_interval,
                recurring_parent_id,
            ),
        )

        task_id = cursor.lastrowid

        if recurring_parent_id is None and repeat_type != "none":
            cursor.execute(
                """
                UPDATE tasks
                SET recurring_parent_id = ?
                WHERE id = ?
                """,
                (task_id, task_id),
            )

        conn.commit()
        return task_id

    finally:
        conn.close()


def get_all_tasks():
    conn = get_connection()

    try:
        return conn.execute(
            """
            SELECT *
            FROM tasks
            ORDER BY
                CASE WHEN status = 'completed' THEN 1 ELSE 0 END,
                id DESC
            """
        ).fetchall()

    finally:
        conn.close()


def get_active_tasks():
    conn = get_connection()

    try:
        return conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE status != 'completed'
            ORDER BY id DESC
            """
        ).fetchall()

    finally:
        conn.close()


def get_completed_tasks():
    conn = get_connection()

    try:
        return conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE status = 'completed'
            ORDER BY completed_at DESC, id DESC
            """
        ).fetchall()

    finally:
        conn.close()


def get_tasks_by_date_range(start_date, end_date):
    conn = get_connection()

    try:
        return conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE date(deadline) >= date(?)
              AND date(deadline) < date(?)
            ORDER BY id DESC
            """,
            (start_date, end_date),
        ).fetchall()

    finally:
        conn.close()


def delete_task(task_id):
    conn = get_connection()

    try:
        conn.execute(
            """
            DELETE FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        )

        conn.commit()

    finally:
        conn.close()


def _insert_task_history(conn, task, actual_duration, completed_at):
    priority = normalize_priority(task["priority"])
    planned_duration = _safe_int(task["duration"])
    actual_duration = _safe_int(actual_duration)

    features = _safe_calculate_duration_features(
        priority=priority,
        planned_duration=planned_duration,
        deadline=task["deadline"],
        completed_at=completed_at,
    )

    days_to_deadline = _safe_int(features.get("days_to_deadline"))
    weekend_deadline = _safe_int(features.get("weekend_deadline"))

    existing = conn.execute(
        """
        SELECT id
        FROM task_history
        WHERE source_task_id = ?
          AND COALESCE(is_seed, 0) = 0
        LIMIT 1
        """,
        (task["id"],),
    ).fetchone()

    if existing:
        return

    conn.execute(
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
            created_at,
            is_seed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 0)
        """,
        (
            task["id"],
            task["title"],
            priority,
            planned_duration,
            actual_duration,
            task["deadline"],
            days_to_deadline,
            weekend_deadline,
            completed_at,
        ),
    )


def _create_next_recurring_task(conn, task):
    repeat_type = normalize_repeat_type(task["repeat_type"])
    repeat_interval = normalize_repeat_interval(task["repeat_interval"])

    if repeat_type == "none":
        return None

    next_deadline = get_next_deadline(
        deadline=task["deadline"],
        repeat_type=repeat_type,
        repeat_interval=repeat_interval,
    )

    if not next_deadline:
        return None

    parent_id = task["recurring_parent_id"] or task["id"]

    existing_next = conn.execute(
        """
        SELECT id
        FROM tasks
        WHERE recurring_parent_id = ?
          AND deadline = ?
          AND status != 'completed'
        LIMIT 1
        """,
        (parent_id, next_deadline),
    ).fetchone()

    if existing_next:
        return existing_next["id"]

    cursor = conn.execute(
        """
        INSERT INTO tasks (
            title,
            priority,
            deadline,
            duration,
            status,
            used_recommendation,
            created_at,
            repeat_type,
            repeat_interval,
            recurring_parent_id
        )
        VALUES (?, ?, ?, ?, 'pending', ?, CURRENT_TIMESTAMP, ?, ?, ?)
        """,
        (
            task["title"],
            normalize_priority(task["priority"]),
            next_deadline,
            _safe_int(task["duration"]),
            _safe_int(task["used_recommendation"]),
            repeat_type,
            repeat_interval,
            parent_id,
        ),
    )

    return cursor.lastrowid


def mark_completed(task_id, actual_duration):
    actual_duration = _safe_int(actual_duration)

    if actual_duration <= 0:
        raise ValueError("Actual duration must be greater than 0.")

    conn = get_connection()

    try:
        task = conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

        if not task:
            return None

        if task["status"] == "completed":
            return None

        completed_at = datetime.now().isoformat(timespec="seconds")

        conn.execute(
            """
            UPDATE tasks
            SET status = 'completed',
                actual_duration = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (
                actual_duration,
                completed_at,
                task_id,
            ),
        )

        _insert_task_history(
            conn=conn,
            task=task,
            actual_duration=actual_duration,
            completed_at=completed_at,
        )

        next_task_id = _create_next_recurring_task(
            conn=conn,
            task=task,
        )

        conn.commit()

    finally:
        conn.close()

    _retrain_models_safely()

    return {
        "completed_task_id": task_id,
        "next_task_id": next_task_id,
    }