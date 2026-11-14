"""Database initialization and session management placeholder."""

import sqlite3
from app.config import settings


def get_db_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    db_file = settings.data_path / "trailmark.db"
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn

