import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "planner.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row["name"] == column_name for row in cursor.fetchall())


def _add_column_if_missing(cursor, table_name: str, column_definition: str):
    column_name = column_definition.split()[0]

    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")


def _get_setting(cursor, key: str):
    cursor.execute(
        """
        SELECT value
        FROM app_settings
        WHERE key = ?
        """,
        (key,),
    )

    row = cursor.fetchone()

    if row is None:
        return None

    return row["value"]


def _set_setting(cursor, key: str, value: str):
    cursor.execute(
        """
        INSERT INTO app_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value
        """,
        (key, value),
    )


def _migrate_priority_scale(cursor):
    """
    One-time migration from old 1-3 priority scale to new P1-P5 scale.

    Old scale:
    1 = low
    2 = medium
    3 = high

    New scale:
    1 = P1 Critical
    2 = P2 High
    3 = P3 Normal
    4 = P4 Low
    5 = P5 Optional

    Mapping:
    old 3 high   -> new 2 high
    old 2 medium -> new 3 normal
    old 1 low    -> new 4 low
    """
    migration_key = "priority_scale_v2_migrated"

    if _get_setting(cursor, migration_key) == "1":
        return

    cursor.execute("""
        UPDATE tasks
        SET priority = CASE priority
            WHEN 1 THEN 4
            WHEN 2 THEN 3
            WHEN 3 THEN 2
            ELSE priority
        END
        WHERE priority IN (1, 2, 3)
    """)

    cursor.execute("""
        UPDATE task_history
        SET priority = CASE priority
            WHEN 1 THEN 4
            WHEN 2 THEN 3
            WHEN 3 THEN 2
            ELSE priority
        END
        WHERE priority IN (1, 2, 3)
    """)

    _set_setting(cursor, migration_key, "1")


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                priority INTEGER NOT NULL,
                deadline TEXT NOT NULL,
                duration INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                actual_duration INTEGER,
                completed_at TEXT,
                used_recommendation INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        _add_column_if_missing(cursor, "tasks", "actual_duration INTEGER")
        _add_column_if_missing(cursor, "tasks", "completed_at TEXT")
        _add_column_if_missing(cursor, "tasks", "used_recommendation INTEGER DEFAULT 0")
        _add_column_if_missing(cursor, "tasks", "created_at TEXT DEFAULT CURRENT_TIMESTAMP")

        cursor.execute("""
            UPDATE tasks
            SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)
            WHERE created_at IS NULL OR TRIM(created_at) = ''
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_task_id INTEGER,
                title TEXT,
                priority INTEGER,
                planned_duration INTEGER,
                actual_duration INTEGER,
                deadline TEXT,
                days_to_deadline INTEGER,
                weekend_deadline INTEGER,
                completed_at TEXT,
                created_at TEXT
            )
        """)

        _add_column_if_missing(cursor, "task_history", "source_task_id INTEGER")
        _add_column_if_missing(cursor, "task_history", "days_to_deadline INTEGER")
        _add_column_if_missing(cursor, "task_history", "weekend_deadline INTEGER")
        _add_column_if_missing(cursor, "task_history", "completed_at TEXT")
        _add_column_if_missing(cursor, "task_history", "created_at TEXT")

        cursor.execute("""
            UPDATE task_history
            SET created_at = COALESCE(created_at, completed_at, CURRENT_TIMESTAMP)
            WHERE created_at IS NULL OR TRIM(created_at) = ''
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_model_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                model_name TEXT NOT NULL,
                trained INTEGER NOT NULL DEFAULT 0,
                samples INTEGER NOT NULL DEFAULT 0,
                mae REAL,
                updated_at TEXT,
                message TEXT
            )
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO ml_model_status (
                id,
                model_name,
                trained,
                samples,
                mae,
                updated_at,
                message
            )
            VALUES (
                1,
                'Ridge Regression',
                0,
                0,
                NULL,
                NULL,
                'Model is not trained yet.'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_model_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                model_name TEXT NOT NULL,
                trained INTEGER NOT NULL DEFAULT 0,
                samples INTEGER NOT NULL DEFAULT 0,
                overtime_accuracy REAL,
                late_accuracy REAL,
                updated_at TEXT,
                message TEXT
            )
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO risk_model_status (
                id,
                model_name,
                trained,
                samples,
                overtime_accuracy,
                late_accuracy,
                updated_at,
                message
            )
            VALUES (
                1,
                'Logistic Regression Risk Model',
                0,
                0,
                NULL,
                NULL,
                NULL,
                'Risk model is not trained yet.'
            )
        """)

        _migrate_priority_scale(cursor)

        conn.commit()