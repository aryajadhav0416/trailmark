"""SQLite Database initialization, connection management, and table schemas."""

import sqlite3
from pathlib import Path
from typing import Optional
from app.config import settings

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    leaver_name TEXT NOT NULL,
    newcomer_role TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('empty', 'ready', 'running', 'done', 'error')),
    error_message TEXT,
    share_token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    filename TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('md', 'txt', 'csv', 'json', 'paste')),
    content TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    label TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('decision', 'ownership', 'risk', 'open_question', 'dependency', 'next_action')),
    statement TEXT NOT NULL,
    owner TEXT,
    quote TEXT NOT NULL,
    chunk_id TEXT,
    llm_confidence TEXT NOT NULL CHECK(llm_confidence IN ('high', 'medium', 'low')),
    verification TEXT NOT NULL CHECK(verification IN ('verified', 'approximate', 'unverified')),
    verification_note TEXT,
    review_status TEXT NOT NULL CHECK(review_status IN ('draft', 'approved', 'rejected')),
    confidential INTEGER NOT NULL DEFAULT 0 CHECK(confidential IN (0, 1)),
    reviewer_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS item_versions (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('created', 'edited', 'approved', 'rejected', 'confidential_on', 'confidential_off')),
    snapshot_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sources_case_id ON sources(case_id);
CREATE INDEX IF NOT EXISTS idx_chunks_case_id ON chunks(case_id);
CREATE INDEX IF NOT EXISTS idx_items_case_id ON items(case_id);
CREATE INDEX IF NOT EXISTS idx_item_versions_item_id ON item_versions(item_id);
"""


def get_db_connection(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    """Return a connection to the SQLite database with PRAGMA foreign_keys enabled."""
    if db_path is None:
        db_file = settings.data_path / "trailmark.db"
    else:
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path | str] = None) -> None:
    """Initialize database tables and schema."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA_SQL)
    finally:
        conn.close()
