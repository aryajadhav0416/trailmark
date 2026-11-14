"""Unit tests for ingestion and chunking services."""

import json
import pytest
from app.services.ingest import (
    process_uploaded_file,
    process_pasted_text,
    validate_source_batch,
    IngestionError,
    NormalizedSource,
)
from app.services.chunker import (
    chunk_source,
    chunk_csv,
    chunk_json,
    chunk_text_lines,
)


# ---------------------------------------------------------------------------
# Ingestion Service Tests
# ---------------------------------------------------------------------------

def test_ingest_bom_and_line_endings():
    """Test stripping BOM and normalising \r\n and \r to \n."""
    raw = "\ufeffFirst line\r\nSecond line\rThird line\nFourth line"
    norm = process_uploaded_file("doc.txt", raw.encode("utf-8"))
    assert norm.content == "First line\nSecond line\nThird line\nFourth line"
    assert norm.kind == "txt"
    assert norm.warning is None


def test_ingest_unknown_extension_warning():
    """Test unknown extension is treated as plain text with visible warning."""
    raw = b"Log trace data line 1\nLog trace line 2"
    norm = process_uploaded_file("system.log", raw)
    assert norm.kind == "txt"
    assert norm.warning is not None
    assert "unsupported extension '.log'" in norm.warning
    assert "Treated as plain text" in norm.warning


def test_ingest_odd_encodings_fallback():
    """Test non-UTF8 bytes fallback gracefully using replace instead of crashing."""
    # Byte 0x80 or 0xff in pure ASCII/latin-1 sequence
    raw = b"Valid ASCII prefix \xff\xfe\x80 suffix"
    norm = process_uploaded_file("notes.md", raw)
    assert "Valid ASCII prefix" in norm.content
    assert "suffix" in norm.content
    assert "\ufffd" in norm.content  # Unicode replacement character


def test_ingest_oversize_file_rejected():
    """Test that a file larger than MAX_FILE_BYTES is rejected with clear message."""
    oversize = b"A" * 105
    with pytest.raises(IngestionError, match="exceeds maximum allowed size of 100 bytes"):
        process_uploaded_file("big.txt", oversize, max_file_bytes=100)


def test_ingest_batch_limits():
    """Test total characters limit and file count limit validations."""
    sources = [
        NormalizedSource(filename=f"file{i}.txt", kind="txt", content="sample", char_count=6)
        for i in range(11)
    ]
    with pytest.raises(IngestionError, match="Too many sources: received 11 files/items"):
        validate_source_batch(sources, max_files=10)

    small_batch = [
        NormalizedSource(filename="one.txt", kind="txt", content="123456", char_count=6),
        NormalizedSource(filename="two.txt", kind="txt", content="123456", char_count=6),
    ]
    with pytest.raises(IngestionError, match="Total input volume .* exceeds the limit of 10 characters"):
        validate_source_batch(small_batch, max_files=10, max_total_chars=10)


def test_ingest_pasted_text():
    """Test normalising pasted text."""
    pasted = "First item\r\nSecond item\r\n"
    norm = process_pasted_text(pasted)
    assert norm.kind == "paste"
    assert norm.content == "First item\nSecond item\n"


# ---------------------------------------------------------------------------
# Chunker Service Tests
# ---------------------------------------------------------------------------

def test_chunking_line_numbers_accurate():
    """Verify that chunk line numbers accurately track source lines and never overlap."""
    lines = [f"Line {i} content text." for i in range(1, 151)]
    content = "\n".join(lines)
    chunks = chunk_source(content, kind="txt", source_ordinal=1, source_id="src_1")

    assert len(chunks) > 1

    # Verify continuity and disjoint line intervals
    expected_start = 1
    for i, c in enumerate(chunks):
        assert c.source_ordinal == 1
        assert c.source_id == "src_1"
        assert c.label == f"S1:L{c.start_line}-{c.end_line}"
        assert c.start_line == expected_start
        assert c.end_line >= c.start_line
        # Check text lines match count
        chunk_line_count = len(c.text.split("\n"))
        assert chunk_line_count == (c.end_line - c.start_line + 1)
        expected_start = c.end_line + 1

    assert expected_start - 1 == 150


def test_chunk_reassembly_equals_source():
    """Test that chunk texts reassemble exactly back to original source for txt/md."""
    # Generate multi-paragraph markdown text with varied line lengths and blank lines
    paragraphs = []
    for p in range(10):
        para_lines = [f"Paragraph {p} line {l} with some detailed description." for l in range(1, 8)]
        paragraphs.append("\n".join(para_lines))
    original_text = "\n\n".join(paragraphs)

    chunks = chunk_source(original_text, kind="md", source_ordinal=2)
    reassembled_text = "\n".join(c.text for c in chunks)

    assert reassembled_text == original_text


def test_chunk_empty_file():
    """Test chunking an empty file or empty content."""
    chunks = chunk_source("", kind="txt", source_ordinal=1)
    assert len(chunks) == 1
    assert chunks[0].label == "S1:L1-1"
    assert chunks[0].text == ""
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 1


def test_chunk_csv_with_quotes_commas_and_repeated_headers():
    """Test CSV chunking repeats header in every chunk and preserves line intervals."""
    header = 'id,title,description,notes'
    rows = [
        f'{i},"Feature, Item #{i}","Detailed quote: ""essential step""","Note {i}"'
        for i in range(1, 36)
    ]
    csv_content = header + "\n" + "\n".join(rows)

    chunks = chunk_source(csv_content, kind="csv", source_ordinal=3)
    # 35 rows at 15 rows per chunk -> 3 chunks (15, 15, 5 rows)
    assert len(chunks) == 3

    # Check each chunk repeats the header row at the top
    for idx, c in enumerate(chunks):
        lines = c.text.split("\n")
        assert lines[0] == header
        assert c.label == f"S3:L{c.start_line}-{c.end_line}"

    assert chunks[0].start_line == 2
    assert chunks[0].end_line == 16
    assert chunks[1].start_line == 17
    assert chunks[1].end_line == 31
    assert chunks[2].start_line == 32
    assert chunks[2].end_line == 36

    # Verify that stripping repeated header reassembles exactly to the raw data lines
    data_reconstructed = []
    for c in chunks:
        data_reconstructed.extend(c.text.split("\n")[1:])
    assert data_reconstructed == rows


def test_chunk_json_pretty_printed():
    """Test that JSON is parsed and pretty-printed into deterministic lines."""
    raw_json = '{"settings": {"enabled": true, "timeout": 30}, "tags": ["a", "b"]}'
    chunks = chunk_source(raw_json, kind="json", source_ordinal=1)
    assert len(chunks) >= 1
    # Pretty-printed JSON should contain standard indentation
    assert '  "settings": {' in chunks[0].text
    assert '  "tags": [' in chunks[0].text

