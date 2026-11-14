# Changelog

All notable changes to the Trailmark project will be documented in this file.

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

