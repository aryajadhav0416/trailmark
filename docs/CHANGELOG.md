# Changelog

All notable changes to the Trailmark project will be documented in this file.

## [0.4.0] - CLI Tool and Real Fixture Validation Suite
### Added
- `scripts/chunk_demo.py`: CLI tool accepting a file path and printing chunk labels, 80-character snippets, warnings (unknown extension, encoding), or clear rejection messages.
- `tests/test_fixtures.py`: Comprehensive test suite validating ingestion and chunker behavior against sample datasets and edge-case fixtures:
  - `samples/campus_food_app/chat_export.txt`
  - `samples/campus_food_app/meeting_notes/03_it_policy_discussion_2026-10-22.md`
  - `samples/campus_food_app/tasks.csv`
  - `tests/fixtures/edge_cases/csv_edge.csv` (proper handling of multi-line cells, quotes, and Hindi/Rupee symbols)
  - `samples/campus_food_app/github_issues.json`
  - `tests/fixtures/edge_cases/windows_crlf_bom.txt`
  - `tests/fixtures/edge_cases/unknown_extension.log`
  - `tests/fixtures/edge_cases/empty.txt`
  - `tests/fixtures/edge_cases/too_large.txt`
  - `tests/fixtures/edge_cases/paste_snippet.txt`
  - Cumulative volume verification of all `samples/campus_food_app/` files within `MAX_INPUT_CHARS`.
- Empty file validation in `process_uploaded_file` with human-readable rejection.
- Line tracking in `chunk_csv` using `csv.reader` to preserve multiline cells and quotes.

## [0.3.0] - Ingestion and Chunker Services
### Added
- `app/services/ingest.py`: Multi-source ingestion pipeline supporting `.txt`, `.md`, `.csv`, `.json`, and pasted text.
  - Strips BOM, normalizes line endings, preserves line numbering.
  - Fallback encoding decoding with `errors="replace"`.
  - Enforces `MAX_FILE_BYTES`, `MAX_FILES_ALLOWED` (10), and `MAX_INPUT_CHARS` (40,000) with descriptive error messages.
  - Warns on unknown file extensions and treats them safely as plain text.
- `app/services/chunker.py`: Deterministic non-overlapping chunker:
  - Generates stable labels `S{ordinal}:L{start}-{end}` and stores exact chunk text.
  - Markdown, text, and paste snapped around 1,200 characters on blank lines without mid-line splitting.
  - CSV repeat-headers (~15 rows per chunk).
  - JSON pretty-printing prior to line-based chunking.
- Comprehensive unit test suite in `tests/test_services.py`.

## [0.2.0] - SQLite Data Layer
### Added
- SQLite database schema with foreign keys enabled (`PRAGMA foreign_keys = ON;`).
- Tables: `cases`, `sources`, `chunks`, `items`, and `item_versions`.
- Repository access layer in `app/models.py` with version tracking for item creation, edits, approvals, rejections, and confidentiality toggling.
- Automatic table creation on startup via FastAPI application lifespan.
- Unit tests covering case creation, updates, version tracking, cascade deletion, and validation.

## [0.1.0] - Skeleton & Foundation
### Added
- Project folder structure (`app/`, `tests/`, `samples/`, `scripts/`, `docs/`).
- FastAPI application entrypoint with configuration via `pydantic-settings`.
- Jinja2 templates (`base.html`, `index.html`) integrating HTMX from pinned CDN.
- Healthcheck endpoint `GET /healthz`.
- Dockerfile supporting dynamic `$PORT` binding.
- Pytest test suite with smoke tests for `/healthz` and `/`.

