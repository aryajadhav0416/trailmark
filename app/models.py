"""Data models and repository access layer for Trailmark SQLite database."""

import json
import secrets
import sqlite3
import string
from datetime import datetime, timezone
from typing import Any, Optional


def generate_id(length: int = 12) -> str:
    """Generate a random alphanumeric ID."""
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_share_token(length: int = 24) -> str:
    """Generate a URL-safe random token."""
    return secrets.token_urlsafe(length)[:length]


# ---------------------------------------------------------------------------
# Repository Operations
# ---------------------------------------------------------------------------

def create_case(
    conn: sqlite3.Connection,
    name: str,
    leaver_name: str,
    newcomer_role: str,
    case_id: Optional[str] = None,
    share_token: Optional[str] = None,
) -> dict[str, Any]:
    """Create a new case record."""
    cid = case_id or generate_id(12)
    token = share_token or generate_share_token(24)
    now = datetime.now(timezone.utc).isoformat()

    with conn:
        conn.execute(
            """
            INSERT INTO cases (id, name, leaver_name, newcomer_role, status, error_message, share_token, created_at)
            VALUES (?, ?, ?, ?, 'empty', NULL, ?, ?)
            """,
            (cid, name, leaver_name, newcomer_role, token, now),
        )

    row = conn.execute("SELECT * FROM cases WHERE id = ?", (cid,)).fetchone()
    return dict(row)


def get_case(conn: sqlite3.Connection, case_id: str) -> Optional[dict[str, Any]]:
    """Fetch a case by ID."""
    row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return dict(row) if row else None


def get_case_by_token(conn: sqlite3.Connection, share_token: str) -> Optional[dict[str, Any]]:
    """Fetch a case by share token."""
    row = conn.execute("SELECT * FROM cases WHERE share_token = ?", (share_token,)).fetchone()
    return dict(row) if row else None


def update_case_status(
    conn: sqlite3.Connection,
    case_id: str,
    status: str,
    error_message: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Update case status and optional error message."""
    with conn:
        conn.execute(
            "UPDATE cases SET status = ?, error_message = ? WHERE id = ?",
            (status, error_message, case_id),
        )
    return get_case(conn, case_id)


def add_source(
    conn: sqlite3.Connection,
    case_id: str,
    ordinal: int,
    filename: str,
    kind: str,
    content: str,
    source_id: Optional[str] = None,
) -> dict[str, Any]:
    """Add a source to a case and update case status to 'ready' if previously 'empty'."""
    sid = source_id or generate_id(12)
    char_count = len(content)

    with conn:
        conn.execute(
            """
            INSERT INTO sources (id, case_id, ordinal, filename, kind, content, char_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (sid, case_id, ordinal, filename, kind, content, char_count),
        )
        # Transition empty case to ready
        conn.execute(
            "UPDATE cases SET status = 'ready' WHERE id = ? AND status = 'empty'",
            (case_id,),
        )

    row = conn.execute("SELECT * FROM sources WHERE id = ?", (sid,)).fetchone()
    return dict(row)


def list_sources(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """List all sources for a given case, ordered by ordinal."""
    rows = conn.execute(
        "SELECT * FROM sources WHERE case_id = ? ORDER BY ordinal ASC",
        (case_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_chunks(
    conn: sqlite3.Connection,
    case_id: str,
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Bulk save source chunks for a case."""
    saved = []
    with conn:
        for chunk in chunks:
            cid = chunk.get("id") or generate_id(12)
            conn.execute(
                """
                INSERT INTO chunks (id, case_id, source_id, label, start_line, end_line, text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    case_id,
                    chunk["source_id"],
                    chunk["label"],
                    chunk["start_line"],
                    chunk["end_line"],
                    chunk["text"],
                ),
            )
            saved.append({**chunk, "id": cid, "case_id": case_id})
    return saved


def list_chunks(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """List all chunks for a case."""
    rows = conn.execute(
        "SELECT * FROM chunks WHERE case_id = ? ORDER BY label ASC",
        (case_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_chunk(conn: sqlite3.Connection, chunk_id: str) -> Optional[dict[str, Any]]:
    """Fetch a single chunk by ID."""
    row = conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
    return dict(row) if row else None


def save_items(
    conn: sqlite3.Connection,
    case_id: str,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Save extracted items for a case, logging an initial 'created' version for each."""
    now = datetime.now(timezone.utc).isoformat()
    saved = []

    with conn:
        for item in items:
            item_id = item.get("id") or generate_id(12)
            row_data = {
                "id": item_id,
                "case_id": case_id,
                "type": item["type"],
                "statement": item["statement"],
                "owner": item.get("owner"),
                "quote": item["quote"],
                "chunk_id": item.get("chunk_id"),
                "llm_confidence": item.get("llm_confidence", "medium"),
                "verification": item.get("verification", "unverified"),
                "verification_note": item.get("verification_note"),
                "review_status": item.get("review_status", "draft"),
                "confidential": int(bool(item.get("confidential", 0))),
                "reviewer_note": item.get("reviewer_note"),
                "created_at": now,
                "updated_at": now,
            }

            conn.execute(
                """
                INSERT INTO items (
                    id, case_id, type, statement, owner, quote, chunk_id,
                    llm_confidence, verification, verification_note,
                    review_status, confidential, reviewer_note,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_data["id"],
                    row_data["case_id"],
                    row_data["type"],
                    row_data["statement"],
                    row_data["owner"],
                    row_data["quote"],
                    row_data["chunk_id"],
                    row_data["llm_confidence"],
                    row_data["verification"],
                    row_data["verification_note"],
                    row_data["review_status"],
                    row_data["confidential"],
                    row_data["reviewer_note"],
                    row_data["created_at"],
                    row_data["updated_at"],
                ),
            )

            # Write initial version
            v_id = generate_id(12)
            conn.execute(
                """
                INSERT INTO item_versions (id, item_id, action, snapshot_json, created_at)
                VALUES (?, ?, 'created', ?, ?)
                """,
                (v_id, item_id, json.dumps(row_data), now),
            )
            saved.append(row_data)

    return saved


def list_items(
    conn: sqlite3.Connection,
    case_id: str,
    review_status: Optional[str] = None,
    exclude_confidential: bool = False,
) -> list[dict[str, Any]]:
    """List items for a case with optional review_status and confidentiality filtering."""
    query = "SELECT * FROM items WHERE case_id = ?"
    params: list[Any] = [case_id]

    if review_status:
        query += " AND review_status = ?"
        params.append(review_status)

    if exclude_confidential:
        query += " AND confidential = 0"

    query += " ORDER BY created_at ASC"

    rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def get_item(conn: sqlite3.Connection, item_id: str) -> Optional[dict[str, Any]]:
    """Fetch an item by ID."""
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def update_item(
    conn: sqlite3.Connection,
    item_id: str,
    action: str,
    updates: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Update an item and record an item_versions snapshot.

    Permitted actions: 'edited', 'approved', 'rejected', 'confidential_on', 'confidential_off'.
    """
    valid_actions = {"edited", "approved", "rejected", "confidential_on", "confidential_off"}
    if action not in valid_actions:
        raise ValueError(f"Invalid item version action '{action}'. Permitted: {valid_actions}")

    current = get_item(conn, item_id)
    if not current:
        return None

    now = datetime.now(timezone.utc).isoformat()
    fields_to_update = dict(updates)
    fields_to_update["updated_at"] = now

    set_clauses = []
    values = []
    for k, v in fields_to_update.items():
        set_clauses.append(f"{k} = ?")
        values.append(v)
    values.append(item_id)

    with conn:
        conn.execute(
            f"UPDATE items SET {', '.join(set_clauses)} WHERE id = ?",
            tuple(values),
        )

        updated_row = dict(conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone())

        # Record version snapshot
        v_id = generate_id(12)
        conn.execute(
            """
            INSERT INTO item_versions (id, item_id, action, snapshot_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (v_id, item_id, action, json.dumps(updated_row), now),
        )

    return updated_row


def get_versions(conn: sqlite3.Connection, item_id: str) -> list[dict[str, Any]]:
    """Return version history for an item, newest first."""
    rows = conn.execute(
        "SELECT * FROM item_versions WHERE item_id = ? ORDER BY created_at DESC",
        (item_id,),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["snapshot"] = json.loads(d["snapshot_json"])
        result.append(d)
    return result


def delete_case(conn: sqlite3.Connection, case_id: str) -> bool:
    """Delete a case and all associated sources, chunks, items, and versions via cascade."""
    with conn:
        cursor = conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        return cursor.rowcount > 0
