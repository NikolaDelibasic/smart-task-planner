import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "planner.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(column["name"] == column_name for column in columns)


def _add_column_if_missing(cursor, table_name, column_definition):
    """
    Adds a column only if it does not already exist.

    Example:
    _add_column_if_missing(cursor, "tasks", "created_at TEXT")
    """
    column_name = column_definition.split()[0]

    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_definition}
        """)


def _table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def _get_setting(cursor, key):
    cursor.execute(
        """
        SELECT value
        FROM app_settings
        WHERE key = ?
        """,
        (key,),
    )
    row = cursor.fetchone()

    if not row:
        return None

    return row["value"]


def _set_setting(cursor, key, value):
    cursor.execute(
        """
        INSERT INTO app_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, str(value)),
    )


def _create_core_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 3,
            deadline TEXT NOT NULL,
            duration INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            actual_duration INTEGER,
            completed_at TEXT,
            used_recommendation INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            repeat_type TEXT DEFAULT 'none',
            repeat_interval INTEGER DEFAULT 1,
            recurring_parent_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_task_id INTEGER,
            title TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 3,
            planned_duration INTEGER NOT NULL,
            actual_duration INTEGER NOT NULL,
            deadline TEXT,
            days_to_deadline INTEGER DEFAULT 0,
            weekend_deadline INTEGER DEFAULT 0,
            completed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_seed INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)


def _create_model_status_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ml_model_status (
            id INTEGER PRIMARY KEY,
            model_name TEXT DEFAULT 'Ridge Regression',
            trained INTEGER DEFAULT 0,
            samples INTEGER DEFAULT 0,
            samples_used INTEGER DEFAULT 0,
            mae REAL,
            last_trained TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            message TEXT DEFAULT 'Cold start: model will train after more completed tasks.'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_model_status (
            id INTEGER PRIMARY KEY,
            model_name TEXT DEFAULT 'Logistic Regression Risk Model',
            trained INTEGER DEFAULT 0,
            samples INTEGER DEFAULT 0,
            samples_used INTEGER DEFAULT 0,
            overtime_accuracy REAL,
            late_accuracy REAL,
            last_trained TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            message TEXT DEFAULT 'Cold start: risk model will train after more completed tasks.'
        )
    """)


def _migrate_tasks_table(cursor):
    _add_column_if_missing(cursor, "tasks", "actual_duration INTEGER")
    _add_column_if_missing(cursor, "tasks", "completed_at TEXT")
    _add_column_if_missing(cursor, "tasks", "used_recommendation INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "tasks", "created_at TEXT")
    _add_column_if_missing(cursor, "tasks", "repeat_type TEXT DEFAULT 'none'")
    _add_column_if_missing(cursor, "tasks", "repeat_interval INTEGER DEFAULT 1")
    _add_column_if_missing(cursor, "tasks", "recurring_parent_id INTEGER")

    cursor.execute("""
        UPDATE tasks
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL OR created_at = ''
    """)

    cursor.execute("""
        UPDATE tasks
        SET status = 'pending'
        WHERE status IS NULL OR status = ''
    """)

    cursor.execute("""
        UPDATE tasks
        SET priority = 3
        WHERE priority IS NULL
    """)

    cursor.execute("""
        UPDATE tasks
        SET used_recommendation = 0
        WHERE used_recommendation IS NULL
    """)

    cursor.execute("""
        UPDATE tasks
        SET repeat_type = 'none'
        WHERE repeat_type IS NULL OR repeat_type = ''
    """)

    cursor.execute("""
        UPDATE tasks
        SET repeat_interval = 1
        WHERE repeat_interval IS NULL OR repeat_interval < 1
    """)


def _migrate_task_history_table(cursor):
    _add_column_if_missing(cursor, "task_history", "source_task_id INTEGER")
    _add_column_if_missing(cursor, "task_history", "days_to_deadline INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "task_history", "weekend_deadline INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "task_history", "completed_at TEXT")
    _add_column_if_missing(cursor, "task_history", "created_at TEXT")
    _add_column_if_missing(cursor, "task_history", "is_seed INTEGER DEFAULT 0")

    cursor.execute("""
        UPDATE task_history
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL OR created_at = ''
    """)

    cursor.execute("""
        UPDATE task_history
        SET is_seed = 0
        WHERE is_seed IS NULL
    """)

    cursor.execute("""
        UPDATE task_history
        SET days_to_deadline = 0
        WHERE days_to_deadline IS NULL
    """)

    cursor.execute("""
        UPDATE task_history
        SET weekend_deadline = 0
        WHERE weekend_deadline IS NULL
    """)


def _migrate_model_status_tables(cursor):
    _add_column_if_missing(cursor, "ml_model_status", "model_name TEXT DEFAULT 'Ridge Regression'")
    _add_column_if_missing(cursor, "ml_model_status", "trained INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "ml_model_status", "samples INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "ml_model_status", "samples_used INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "ml_model_status", "mae REAL")
    _add_column_if_missing(cursor, "ml_model_status", "last_trained TEXT")
    _add_column_if_missing(cursor, "ml_model_status", "updated_at TEXT")
    _add_column_if_missing(cursor, "ml_model_status", "message TEXT")

    _add_column_if_missing(cursor, "risk_model_status", "model_name TEXT DEFAULT 'Logistic Regression Risk Model'")
    _add_column_if_missing(cursor, "risk_model_status", "trained INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "risk_model_status", "samples INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "risk_model_status", "samples_used INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "risk_model_status", "overtime_accuracy REAL")
    _add_column_if_missing(cursor, "risk_model_status", "late_accuracy REAL")
    _add_column_if_missing(cursor, "risk_model_status", "last_trained TEXT")
    _add_column_if_missing(cursor, "risk_model_status", "updated_at TEXT")
    _add_column_if_missing(cursor, "risk_model_status", "message TEXT")

    cursor.execute("""
        INSERT OR IGNORE INTO ml_model_status (
            id,
            model_name,
            trained,
            samples,
            samples_used,
            mae,
            last_trained,
            updated_at,
            message
        )
        VALUES (
            1,
            'Ridge Regression',
            0,
            0,
            0,
            NULL,
            NULL,
            CURRENT_TIMESTAMP,
            'Cold start: model will train after more completed tasks.'
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO risk_model_status (
            id,
            model_name,
            trained,
            samples,
            samples_used,
            overtime_accuracy,
            late_accuracy,
            last_trained,
            updated_at,
            message
        )
        VALUES (
            1,
            'Logistic Regression Risk Model',
            0,
            0,
            0,
            NULL,
            NULL,
            NULL,
            CURRENT_TIMESTAMP,
            'Cold start: risk model will train after more completed tasks.'
        )
    """)

    cursor.execute("""
        UPDATE ml_model_status
        SET
            samples = COALESCE(samples, samples_used, 0),
            samples_used = COALESCE(samples_used, samples, 0),
            message = CASE
                WHEN message IS NULL OR message = ''
                THEN 'Cold start: model will train after more completed tasks.'
                ELSE message
            END,
            updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)
        WHERE id = 1
    """)

    cursor.execute("""
        UPDATE risk_model_status
        SET
            samples = COALESCE(samples, samples_used, 0),
            samples_used = COALESCE(samples_used, samples, 0),
            message = CASE
                WHEN message IS NULL OR message = ''
                THEN 'Cold start: risk model will train after more completed tasks.'
                ELSE message
            END,
            updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)
        WHERE id = 1
    """)


def _migrate_priority_scale(cursor):
    """
    One-time migration from the old 1-3 priority scale to the new 1-5 scale.

    Old scale:
    1 = low
    2 = medium
    3 = high

    New scale:
    1 = critical
    2 = high
    3 = normal
    4 = low
    5 = optional

    Mapping:
    old 3 -> new 2
    old 2 -> new 3
    old 1 -> new 4
    """
    setting_key = "priority_scale_v2_migrated"

    if _get_setting(cursor, setting_key) == "1":
        return

    if _table_exists(cursor, "tasks"):
        cursor.execute("""
            UPDATE tasks
            SET priority = CASE
                WHEN priority = 1 THEN 4
                WHEN priority = 2 THEN 3
                WHEN priority = 3 THEN 2
                ELSE priority
            END
            WHERE priority IN (1, 2, 3)
        """)

    if _table_exists(cursor, "task_history"):
        cursor.execute("""
            UPDATE task_history
            SET priority = CASE
                WHEN priority = 1 THEN 4
                WHEN priority = 2 THEN 3
                WHEN priority = 3 THEN 2
                ELSE priority
            END
            WHERE priority IN (1, 2, 3)
            AND COALESCE(is_seed, 0) = 0
        """)

    _set_setting(cursor, setting_key, "1")


def _create_indexes(cursor):
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_status
        ON tasks(status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_deadline
        ON tasks(deadline)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_priority
        ON tasks(priority)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_history_completed_at
        ON task_history(completed_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_history_is_seed
        ON task_history(is_seed)
    """)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        _create_core_tables(cursor)
        _create_model_status_tables(cursor)
        _migrate_tasks_table(cursor)
        _migrate_task_history_table(cursor)
        _migrate_model_status_tables(cursor)
        _migrate_priority_scale(cursor)
        _create_indexes(cursor)

        conn.commit()
    finally:
        conn.close()