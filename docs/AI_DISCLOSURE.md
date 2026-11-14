# AI Assistance Disclosure

In compliance with hackathon rules, this document records AI tool usage in the development of Trailmark.

## Development Log

- **Date**: 2026-11-14
- **Tool**: Antigravity (Gemini 3.8 Flash)
- **Scope**: Fully implemented Google Gemini REST API provider in `app/services/llm.py` with sanitized error reporting. Added deterministic input fixture routing in mock provider for PostgreSQL inputs to avoid SQLite response leakage. Added regression tests in `tests/test_extract.py`.

- **Date**: 2026-11-14
- **Tool**: Antigravity (Gemini 3.8 Flash)
- **Scope**: Implemented `app/services/llm.py` (OpenAI-compatible client, SHA-256 caching, backoff retries, JSON auto-repair) and `app/services/extract.py` (chunk batching, prompt injection protection, Pydantic item validation, deduplication). Added master system prompt in `app/prompts/extract_system.txt` and unit tests in `tests/test_extract.py`.

- **Date**: 2026-11-14
- **Tool**: Antigravity (Gemini 3.8 Flash)
- **Scope**: Created `scripts/chunk_demo.py` inspection CLI. Added `tests/test_fixtures.py` running real samples and edge cases. Enhanced CSV chunking to support embedded newlines using Python's `csv.reader`. Added empty file validation.

- **Date**: 2026-11-14
- **Tool**: Antigravity (Gemini 3.8 Flash)
- **Scope**: Implemented `app/services/ingest.py` and `app/services/chunker.py` with zero-LLM deterministic chunking, format normalisation, boundary validation, and unit tests in `tests/test_services.py`.

- **Date**: 2026-11-14
- **Tool**: Antigravity (Gemini 3.8 Flash)
- **Scope**: Implemented SQLite data schema (`cases`, `sources`, `chunks`, `items`, `item_versions`), repository layer with immutable audit version history (`item_versions`), foreign key cascading, startup initialization, and comprehensive unit tests.

- **Date**: 2026-11-14
- **Tool**: Antigravity (Gemini 3.8 Flash)
- **Scope**: Created project skeleton, FastAPI app, HTMX template layout, configuration, Dockerfile, and initial test setup according to `PROJECT_BRIEF.md`.

