# Changelog

All notable changes to the Trailmark project will be documented in this file.

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

