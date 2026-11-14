"""Tests for edge cases and real sample files using ingestion and chunker services."""

from pathlib import Path
import re
from app.config import settings
from app.services.ingest import (
    process_uploaded_file,
    process_pasted_text,
    validate_source_batch,
    IngestionError,
)
from app.services.chunker import chunk_source

FIXTURES_DIR = Path("tests/fixtures/edge_cases")
SAMPLES_DIR = Path("samples/campus_food_app")


def test_campus_chat_export():
    """chat_export.txt: labels are well-formed; chunk texts cover the file with no gaps/overlaps; line numbers match."""
    path = SAMPLES_DIR / "chat_export.txt"
    norm = process_uploaded_file(path.name, path.read_bytes())
    chunks = chunk_source(norm.content, norm.kind, source_ordinal=1)

    assert len(chunks) > 0
    original_lines = norm.content.split("\n")
    total_original_lines = len(original_lines)

    expected_next_line = 1
    reassembled_lines = []

    for chunk in chunks:
        # Check label well-formedness: S1:Lstart-end
        match = re.match(r"^S1:L(\d+)-(\d+)$", chunk.label)
        assert match is not None, f"Malformed label: {chunk.label}"
        start_line = int(match.group(1))
        end_line = int(match.group(2))

        # Disjoint, gapless check
        assert start_line == expected_next_line
        assert end_line >= start_line

        # Exact line number match with source
        chunk_lines = chunk.text.split("\n")
        assert len(chunk_lines) == (end_line - start_line + 1)
        assert original_lines[start_line - 1 : end_line] == chunk_lines

        reassembled_lines.extend(chunk_lines)
        expected_next_line = end_line + 1

    assert expected_next_line - 1 == total_original_lines
    assert "\n".join(reassembled_lines) == norm.content


def test_campus_meeting_notes_markdown():
    """meeting_notes/03_it_policy_discussion_2026-10-22.md: same checks for markdown."""
    path = SAMPLES_DIR / "meeting_notes/03_it_policy_discussion_2026-10-22.md"
    norm = process_uploaded_file(path.name, path.read_bytes())
    chunks = chunk_source(norm.content, norm.kind, source_ordinal=2)

    assert len(chunks) > 0
    original_lines = norm.content.split("\n")
    total_original_lines = len(original_lines)

    expected_next_line = 1
    reassembled_lines = []

    for chunk in chunks:
        match = re.match(r"^S2:L(\d+)-(\d+)$", chunk.label)
        assert match is not None, f"Malformed label: {chunk.label}"
        start_line = int(match.group(1))
        end_line = int(match.group(2))

        assert start_line == expected_next_line
        assert end_line >= start_line

        chunk_lines = chunk.text.split("\n")
        assert len(chunk_lines) == (end_line - start_line + 1)
        assert original_lines[start_line - 1 : end_line] == chunk_lines

        reassembled_lines.extend(chunk_lines)
        expected_next_line = end_line + 1

    assert expected_next_line - 1 == total_original_lines
    assert "\n".join(reassembled_lines) == norm.content


def test_campus_tasks_csv():
    """tasks.csv: header row repeated in every chunk; all 26 data rows present."""
    path = SAMPLES_DIR / "tasks.csv"
    norm = process_uploaded_file(path.name, path.read_bytes())
    chunks = chunk_source(norm.content, norm.kind, source_ordinal=3)

    assert len(chunks) > 0
    header = "id,task,owner,status,due,notes"
    collected_data_rows = []

    for chunk in chunks:
        lines = chunk.text.split("\n")
        assert lines[0] == header, f"Chunk {chunk.label} does not repeat header row"
        # Collect non-header lines
        for r in lines[1:]:
            if r.strip():
                collected_data_rows.append(r)

    # 26 tasks T01 through T26
    assert len(collected_data_rows) == 26
    assert any("T01,Repo and docker compose skeleton" in r for r in collected_data_rows)
    assert any("T26,Hostel delivery" in r for r in collected_data_rows)


def test_edge_cases_csv_multiline_quotes_and_hindi():
    """csv_edge.csv: quoted comma, doubled quotes, a line break inside a cell, and Hindi text all survive."""
    path = FIXTURES_DIR / "csv_edge.csv"
    norm = process_uploaded_file(path.name, path.read_bytes())
    chunks = chunk_source(norm.content, norm.kind, source_ordinal=4)

    assert len(chunks) > 0
    full_chunk_text = "\n".join(c.text for c in chunks)

    # 1. Quoted comma: "Set up billing, invoices, and receipts"
    assert '"Set up billing, invoices, and receipts"' in full_chunk_text

    # 2. Doubled quotes: ""legacy""
    assert '""legacy""' in full_chunk_text

    # 3. Line break inside cell: "Fix login bug\nreported by two users"
    assert "Fix login bug\nreported by two users" in full_chunk_text

    # 4. Hindi text: हिन्दी and Rupee symbol ₹
    assert "हिन्दी" in full_chunk_text
    assert "₹" in full_chunk_text


def test_campus_github_issues_json():
    """github_issues.json: parsed and chunked; issue 3 text is findable in a chunk."""
    path = SAMPLES_DIR / "github_issues.json"
    norm = process_uploaded_file(path.name, path.read_bytes())
    chunks = chunk_source(norm.content, norm.kind, source_ordinal=5)

    assert len(chunks) > 0

    # Verify Issue 3 text is present and findable in one of the chunks
    issue_3_found = False
    for chunk in chunks:
        if "502 Bad Gateway after every deploy on the campus VM" in chunk.text and "old gunicorn socket" in chunk.text:
            issue_3_found = True
            break

    assert issue_3_found, "Issue 3 text was not found in any generated JSON chunk."


def test_edge_cases_windows_crlf_bom():
    """windows_crlf_bom.txt: no BOM character and no stray carriage returns in chunk text; line numbers correct."""
    path = FIXTURES_DIR / "windows_crlf_bom.txt"
    norm = process_uploaded_file(path.name, path.read_bytes())
    chunks = chunk_source(norm.content, norm.kind, source_ordinal=6)

    assert len(chunks) > 0
    for chunk in chunks:
        assert "\ufeff" not in chunk.text, "BOM character was not stripped"
        assert "\r" not in chunk.text, "Stray carriage return found in chunk text"

    # Line numbers check against normalized lines
    original_lines = norm.content.split("\n")
    first_chunk = chunks[0]
    assert first_chunk.start_line == 1
    assert first_chunk.end_line == len(original_lines)
    assert first_chunk.text == norm.content


def test_edge_cases_unknown_extension():
    """unknown_extension.log: treated as plain text with a warning."""
    path = FIXTURES_DIR / "unknown_extension.log"
    norm = process_uploaded_file(path.name, path.read_bytes())
    assert norm.kind == "txt"
    assert norm.warning is not None
    assert "unsupported extension '.log'" in norm.warning
    assert "Treated as plain text" in norm.warning

    chunks = chunk_source(norm.content, norm.kind, source_ordinal=7)
    assert len(chunks) == 1
    assert "2026-11-10 09:14:02 INFO deploy started by ben" in chunks[0].text


def test_edge_cases_empty_file_rejected_no_exception():
    """empty.txt: rejected with a clear message, no unhandled exception."""
    path = FIXTURES_DIR / "empty.txt"
    result_message = ""
    try:
        process_uploaded_file(path.name, path.read_bytes())
    except IngestionError as e:
        result_message = str(e)

    assert "empty" in result_message.lower(), f"Unexpected message: {result_message}"


def test_edge_cases_too_large_file_rejected_no_exception():
    """too_large.txt: rejected as over MAX_FILE_BYTES, no unhandled exception."""
    path = FIXTURES_DIR / "too_large.txt"
    result_message = ""
    try:
        process_uploaded_file(path.name, path.read_bytes())
    except IngestionError as e:
        result_message = str(e)

    assert "exceeds maximum allowed size" in result_message


def test_edge_cases_paste_snippet():
    """paste_snippet.txt: handled as pasted text with kind 'paste'."""
    path = FIXTURES_DIR / "paste_snippet.txt"
    raw_content = path.read_text(encoding="utf-8")
    norm = process_pasted_text(raw_content)

    assert norm.kind == "paste"
    assert norm.char_count == len(norm.content)

    chunks = chunk_source(norm.content, norm.kind, source_ordinal=8)
    assert len(chunks) > 0
    assert "Quick handover from Leo" in chunks[0].text


def test_all_campus_food_app_under_max_input_chars():
    """All files in samples/campus_food_app/ together stay under MAX_INPUT_CHARS."""
    sources = []
    for file_path in sorted(SAMPLES_DIR.rglob("*")):
        if file_path.is_file():
            norm = process_uploaded_file(file_path.name, file_path.read_bytes())
            sources.append(norm)

    total_chars = sum(s.char_count for s in sources)
    assert total_chars <= settings.MAX_INPUT_CHARS
    # Ensure validate_source_batch passes without raising
    validate_source_batch(sources, max_files=10, max_total_chars=settings.MAX_INPUT_CHARS)
