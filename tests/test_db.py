"""Unit tests for SQLite database schema, foreign keys, and repository operations."""

import sqlite3
import pytest
from app.db import init_db, get_db_connection
from app.models import (
    create_case,
    get_case,
    update_case_status,
    add_source,
    list_sources,
    save_chunks,
    list_chunks,
    save_items,
    list_items,
    get_item,
    update_item,
    get_versions,
    delete_case,
)


@pytest.fixture
def db_conn(tmp_path):
    """Fixture providing an isolated SQLite database connection with tables created."""
    db_file = tmp_path / "test_trailmark.db"
    init_db(db_file)
    conn = get_db_connection(db_file)
    yield conn
    conn.close()


def test_create_and_get_case(db_conn: sqlite3.Connection):
    """Test creating a case and reading it back."""
    case = create_case(
        db_conn,
        name="Project Falcon",
        leaver_name="Alex Smith",
        newcomer_role="Senior Backend Engineer",
    )
    assert len(case["id"]) == 12
    assert len(case["share_token"]) == 24
    assert case["name"] == "Project Falcon"
    assert case["leaver_name"] == "Alex Smith"
    assert case["newcomer_role"] == "Senior Backend Engineer"
    assert case["status"] == "empty"
    assert case["error_message"] is None

    fetched = get_case(db_conn, case["id"])
    assert fetched is not None
    assert fetched["id"] == case["id"]


def test_case_status_transition(db_conn: sqlite3.Connection):
    """Test updating case status manually and via adding a source."""
    case = create_case(db_conn, "Test Project", "Alice", "Lead")
    assert case["status"] == "empty"

    # Adding source transitions case from empty -> ready
    source = add_source(
        db_conn,
        case_id=case["id"],
        ordinal=1,
        filename="notes.md",
        kind="md",
        content="# Handover notes\nSome critical details.",
    )
    assert source["char_count"] == len(source["content"])

    updated = get_case(db_conn, case["id"])
    assert updated["status"] == "ready"

    # Update to running then error
    update_case_status(db_conn, case["id"], "running")
    assert get_case(db_conn, case["id"])["status"] == "running"

    update_case_status(db_conn, case["id"], "error", "Rate limit exceeded")
    err_case = get_case(db_conn, case["id"])
    assert err_case["status"] == "error"
    assert err_case["error_message"] == "Rate limit exceeded"


def test_sources_and_chunks(db_conn: sqlite3.Connection):
    """Test saving sources and chunks."""
    case = create_case(db_conn, "P1", "Bob", "Architect")
    source = add_source(db_conn, case["id"], 1, "arch.txt", "txt", "Line 1\nLine 2")

    chunks = [
        {
            "source_id": source["id"],
            "label": "S1:L1-2",
            "start_line": 1,
            "end_line": 2,
            "text": "Line 1\nLine 2",
        }
    ]
    saved_chunks = save_chunks(db_conn, case["id"], chunks)
    assert len(saved_chunks) == 1
    assert saved_chunks[0]["label"] == "S1:L1-2"

    chunk_list = list_chunks(db_conn, case["id"])
    assert len(chunk_list) == 1


def test_items_and_version_history(db_conn: sqlite3.Connection):
    """Test saving items, updating review status/confidentiality, and version tracking."""
    case = create_case(db_conn, "P2", "Charlie", "DevOps")
    source = add_source(db_conn, case["id"], 1, "config.json", "json", '{"key": "val"}')
    chunks = save_chunks(
        db_conn,
        case["id"],
        [{"source_id": source["id"], "label": "S1:L1-1", "start_line": 1, "end_line": 1, "text": '{"key": "val"}'}],
    )
    chunk_id = chunks[0]["id"]

    # 1. Save items
    raw_items = [
        {
            "type": "decision",
            "statement": "We chose SQLite over PostgreSQL for local simplicity.",
            "owner": "Charlie",
            "quote": "chose SQLite",
            "chunk_id": chunk_id,
            "llm_confidence": "high",
            "verification": "verified",
            "verification_note": "Exact match found in chunk",
        }
    ]
    saved_items = save_items(db_conn, case["id"], raw_items)
    item_id = saved_items[0]["id"]

    # Verify initial creation version exists
    versions = get_versions(db_conn, item_id)
    assert len(versions) == 1
    assert versions[0]["action"] == "created"
    assert versions[0]["snapshot"]["review_status"] == "draft"
    assert versions[0]["snapshot"]["confidential"] == 0

    # 2. Update item: edit statement
    edited = update_item(
        db_conn,
        item_id=item_id,
        action="edited",
        updates={"statement": "We chose SQLite for zero-config simplicity."},
    )
    assert edited["statement"] == "We chose SQLite for zero-config simplicity."

    # 3. Update item: approve
    approved = update_item(
        db_conn,
        item_id=item_id,
        action="approved",
        updates={"review_status": "approved"},
    )
    assert approved["review_status"] == "approved"

    # 4. Update item: toggle confidential on
    conf_on = update_item(
        db_conn,
        item_id=item_id,
        action="confidential_on",
        updates={"confidential": 1},
    )
    assert conf_on["confidential"] == 1

    # 5. Check version history sequence
    versions = get_versions(db_conn, item_id)
    assert len(versions) == 4
    # Newest first
    actions = [v["action"] for v in versions]
    assert actions == ["confidential_on", "approved", "edited", "created"]

    # Verify list filtering (exclude confidential)
    all_items = list_items(db_conn, case["id"])
    assert len(all_items) == 1

    public_items = list_items(db_conn, case["id"], exclude_confidential=True)
    assert len(public_items) == 0

    # Toggle confidential off
    update_item(
        db_conn,
        item_id=item_id,
        action="confidential_off",
        updates={"confidential": 0},
    )
    approved_public = list_items(db_conn, case["id"], review_status="approved", exclude_confidential=True)
    assert len(approved_public) == 1


def test_delete_case_cascades_everything(db_conn: sqlite3.Connection):
    """Test delete_case removes case, sources, chunks, items, and versions completely."""
    case = create_case(db_conn, "To Delete", "Dana", "PM")
    cid = case["id"]

    source = add_source(db_conn, cid, 1, "doc.txt", "txt", "Hello world")
    chunks = save_chunks(
        db_conn,
        cid,
        [{"source_id": source["id"], "label": "S1:L1-1", "start_line": 1, "end_line": 1, "text": "Hello world"}],
    )
    items = save_items(
        db_conn,
        cid,
        [
            {
                "type": "risk",
                "statement": "Migration risk is high.",
                "owner": "Dana",
                "quote": "Hello world",
                "chunk_id": chunks[0]["id"],
                "llm_confidence": "high",
                "verification": "verified",
            }
        ],
    )
    item_id = items[0]["id"]
    update_item(db_conn, item_id, "approved", {"review_status": "approved"})

    # Ensure records exist before deletion
    assert get_case(db_conn, cid) is not None
    assert len(list_sources(db_conn, cid)) == 1
    assert len(list_chunks(db_conn, cid)) == 1
    assert len(list_items(db_conn, cid)) == 1
    assert len(get_versions(db_conn, item_id)) == 2

    # Delete case
    deleted = delete_case(db_conn, cid)
    assert deleted is True

    # Assert cascade removed all child rows
    assert get_case(db_conn, cid) is None
    assert len(list_sources(db_conn, cid)) == 0
    assert len(list_chunks(db_conn, cid)) == 0
    assert len(list_items(db_conn, cid)) == 0
    assert len(get_versions(db_conn, item_id)) == 0


def test_invalid_action_rejected(db_conn: sqlite3.Connection):
    """Test that invalid version actions raise ValueError."""
    case = create_case(db_conn, "Check", "Eva", "Tester")
    items = save_items(
        db_conn,
        case["id"],
        [{"type": "decision", "statement": "Stmt", "quote": "Stmt", "llm_confidence": "low", "verification": "unverified"}],
    )
    with pytest.raises(ValueError, match="Invalid item version action"):
        update_item(db_conn, items[0]["id"], "random_action", {"review_status": "approved"})
