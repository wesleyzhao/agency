"""SQLite database setup."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path("agentctl.db")


def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                engine TEXT NOT NULL,
                prompt TEXT NOT NULL,
                repo TEXT,
                branch TEXT,
                machine_type TEXT NOT NULL,
                spot INTEGER NOT NULL DEFAULT 0,
                timeout_seconds INTEGER,
                screenshot_interval INTEGER,
                screenshot_retention TEXT,
                gce_instance TEXT,
                external_ip TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                stopped_at TEXT
            );

            CREATE TABLE IF NOT EXISTS instructions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                instruction TEXT NOT NULL,
                delivered INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            );
        """)


@contextmanager
def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
