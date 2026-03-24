import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "planner.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

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

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN actual_duration INTEGER")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN used_recommendation INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT")
        except sqlite3.OperationalError:
            pass

        cursor.execute("""
            UPDATE tasks
            SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)
            WHERE created_at IS NULL OR TRIM(created_at) = ''
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                priority INTEGER,
                planned_duration INTEGER,
                actual_duration INTEGER,
                deadline TEXT,
                completed_at TEXT
            )
        """)

        conn.commit()