from datetime import datetime, timedelta

from core.database import get_connection


SEED_SETTING_KEY = "ai_bootstrap_seed_v1"


SEED_HISTORY = [
    {
        "title": "Prepare project documentation",
        "priority": 2,
        "planned_duration": 90,
        "actual_duration": 115,
        "days_to_deadline": 3,
        "late": False,
    },
    {
        "title": "Fix urgent application bug",
        "priority": 1,
        "planned_duration": 60,
        "actual_duration": 95,
        "days_to_deadline": 1,
        "late": True,
    },
    {
        "title": "Study technical material",
        "priority": 3,
        "planned_duration": 120,
        "actual_duration": 110,
        "days_to_deadline": 5,
        "late": False,
    },
    {
        "title": "Send important email",
        "priority": 2,
        "planned_duration": 30,
        "actual_duration": 25,
        "days_to_deadline": 1,
        "late": False,
    },
    {
        "title": "Clean database records",
        "priority": 2,
        "planned_duration": 75,
        "actual_duration": 100,
        "days_to_deadline": 2,
        "late": False,
    },
    {
        "title": "Polish user interface",
        "priority": 4,
        "planned_duration": 45,
        "actual_duration": 55,
        "days_to_deadline": 4,
        "late": False,
    },
    {
        "title": "Write longer report section",
        "priority": 3,
        "planned_duration": 150,
        "actual_duration": 185,
        "days_to_deadline": 7,
        "late": False,
    },
    {
        "title": "Quick task review",
        "priority": 5,
        "planned_duration": 20,
        "actual_duration": 15,
        "days_to_deadline": 2,
        "late": False,
    },
    {
        "title": "Finish deadline task",
        "priority": 1,
        "planned_duration": 80,
        "actual_duration": 130,
        "days_to_deadline": 0,
        "late": True,
    },
    {
        "title": "Refactor backend function",
        "priority": 2,
        "planned_duration": 100,
        "actual_duration": 125,
        "days_to_deadline": 3,
        "late": False,
    },
    {
        "title": "Update README file",
        "priority": 4,
        "planned_duration": 40,
        "actual_duration": 35,
        "days_to_deadline": 6,
        "late": False,
    },
    {
        "title": "Test planner feature",
        "priority": 2,
        "planned_duration": 70,
        "actual_duration": 90,
        "days_to_deadline": 1,
        "late": True,
    },
    {
        "title": "Small frontend fix",
        "priority": 5,
        "planned_duration": 25,
        "actual_duration": 20,
        "days_to_deadline": 4,
        "late": False,
    },
    {
        "title": "Prepare presentation notes",
        "priority": 3,
        "planned_duration": 60,
        "actual_duration": 75,
        "days_to_deadline": 2,
        "late": False,
    },
    {
        "title": "Debug model training issue",
        "priority": 1,
        "planned_duration": 90,
        "actual_duration": 140,
        "days_to_deadline": 1,
        "late": True,
    },
    {
        "title": "Organize task list",
        "priority": 4,
        "planned_duration": 35,
        "actual_duration": 30,
        "days_to_deadline": 5,
        "late": False,
    },
    {
        "title": "Review completed work",
        "priority": 3,
        "planned_duration": 50,
        "actual_duration": 45,
        "days_to_deadline": 3,
        "late": False,
    },
    {
        "title": "Implement validation logic",
        "priority": 2,
        "planned_duration": 85,
        "actual_duration": 105,
        "days_to_deadline": 2,
        "late": False,
    },
    {
        "title": "Prepare final corrections",
        "priority": 1,
        "planned_duration": 120,
        "actual_duration": 170,
        "days_to_deadline": 0,
        "late": True,
    },
    {
        "title": "Simple maintenance task",
        "priority": 5,
        "planned_duration": 30,
        "actual_duration": 25,
        "days_to_deadline": 6,
        "late": False,
    },
]


def _table_columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_bootstrap_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    columns = _table_columns(conn, "task_history")

    required_columns = {
        "source_task_id": "INTEGER",
        "days_to_deadline": "INTEGER DEFAULT 0",
        "weekend_deadline": "INTEGER DEFAULT 0",
        "created_at": "TEXT",
        "is_seed": "INTEGER DEFAULT 0",
    }

    for column_name, column_type in required_columns.items():
        if column_name not in columns:
            conn.execute(
                f"ALTER TABLE task_history ADD COLUMN {column_name} {column_type}"
            )


def _get_setting(conn, key):
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (key,),
    ).fetchone()

    if not row:
        return None

    return row["value"]


def _set_setting(conn, key, value):
    conn.execute(
        """
        INSERT INTO app_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, str(value)),
    )


def _build_seed_dates(index, days_to_deadline, late):
    completed_at = datetime.now().replace(
        hour=18,
        minute=0,
        second=0,
        microsecond=0,
    ) - timedelta(days=index + 7)

    if late:
        deadline_at = completed_at - timedelta(days=1)
        deadline_at = deadline_at.replace(hour=12, minute=0)
    else:
        safe_days = max(0, int(days_to_deadline))
        deadline_at = completed_at + timedelta(days=safe_days)
        deadline_at = deadline_at.replace(hour=23, minute=59)

    weekend_deadline = 1 if deadline_at.weekday() >= 5 else 0

    return deadline_at.isoformat(timespec="minutes"), completed_at.isoformat(timespec="minutes"), weekend_deadline


def _retrain_models_after_seed():
    duration_result = None
    risk_result = None

    try:
        from core.ml_model import retrain_duration_model
        duration_result = retrain_duration_model()
    except Exception as e:
        duration_result = {
            "ok": False,
            "error": str(e),
        }

    try:
        from core.risk_model import retrain_risk_models
        risk_result = retrain_risk_models()
    except Exception as e:
        risk_result = {
            "ok": False,
            "error": str(e),
        }

    return {
        "duration_model": duration_result,
        "risk_model": risk_result,
    }


def bootstrap_ai_training_data(force=False):
    """
    Inserts a small seed dataset into task_history.

    Seed rows are used only for model training.
    They are marked with is_seed = 1 so user-facing statistics can ignore them.
    """

    conn = get_connection()

    try:
        _ensure_bootstrap_schema(conn)

        already_done = _get_setting(conn, SEED_SETTING_KEY) == "1"

        if already_done and not force:
            return {
                "ok": True,
                "inserted": 0,
                "already_bootstrapped": True,
                "models": None,
            }

        conn.execute("DELETE FROM task_history WHERE COALESCE(is_seed, 0) = 1")

        for index, item in enumerate(SEED_HISTORY):
            deadline, completed_at, weekend_deadline = _build_seed_dates(
                index=index,
                days_to_deadline=item["days_to_deadline"],
                late=item["late"],
            )

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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    item["title"],
                    int(item["priority"]),
                    int(item["planned_duration"]),
                    int(item["actual_duration"]),
                    deadline,
                    int(item["days_to_deadline"]),
                    int(weekend_deadline),
                    completed_at,
                    completed_at,
                    1,
                ),
            )

        _set_setting(conn, SEED_SETTING_KEY, "1")
        conn.commit()

    finally:
        conn.close()

    models = _retrain_models_after_seed()

    return {
        "ok": True,
        "inserted": len(SEED_HISTORY),
        "already_bootstrapped": False,
        "models": models,
    }


if __name__ == "__main__":
    result = bootstrap_ai_training_data(force=True)
    print(result)