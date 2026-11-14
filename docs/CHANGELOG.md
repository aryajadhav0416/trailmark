# Changelog

All notable changes to the Trailmark project will be documented in this file.

## [0.5.1] - Gemini Provider and Deterministic Mock Routing
### Added
- Implemented full Google Gemini REST API provider in `app/services/llm.py` (`generateContent` with `systemInstruction`, `responseMimeType="application/json"`, timeout, and backoff retries).
- Sanitized exception reporting preventing leakage of API keys or full prompts on HTTP/API errors.
- Markdown code fence cleaning (`_clean_json_markdown`) for LLM JSON outputs.
- Deterministic mock routing in `MOCK_POSTGRES_RESPONSE` for PostgreSQL test cases while preserving default mock responses.
- Regression tests for mock input routing, cache isolation, and Gemini request/error formatting.

## [0.5.0] - LLM Adapter and Knowledge Extraction Service
### Added
- `app/services/llm.py`: Provider-agnostic LLM adapter with `generate_json(system, user) -> dict`.
  - Supports `openai_compatible` and `mock` (with stubs for `gemini` and `anthropic`).
  - Single-attempt repair instruction on malformed JSON; raises `ExtractionError` if unrecoverable.
  - 60s timeout with exponential backoff on 429 and 5xx (up to 2 retries).
  - SHA-256 disk cache under `DATA_DIR/llm_cache/` reporting `cached=True` on hit.
  - Safe logging ensuring API keys and prompts are never exposed in logs.
- `app/prompts/extract_system.txt`: Master system prompt with prompt injection defenses and untrusted-data boundary rules.
- `app/services/extract.py`: Extraction service grouping chunks into ~6,000 char batches, invoking LLM within `<source_chunk>` boundary tags, Pydantic item validation (`type`, `quote` 12-300, `statement` <= 240), deduplication by normalized statement, and returning items with run statistics.
- `tests/test_extract.py`: Unit tests verifying disk caching, repair retry logic, prompt encapsulation, schema validation drops, and deduplication.

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

