# Changelog

All notable changes to the Trailmark project will be documented in this file.

## [0.1.0] - Skeleton & Foundation
### Added
- Project folder structure (`app/`, `tests/`, `samples/`, `scripts/`, `docs/`).
- FastAPI application entrypoint with configuration via `pydantic-settings`.
- Jinja2 templates (`base.html`, `index.html`) integrating HTMX from pinned CDN.
- Healthcheck endpoint `GET /healthz`.
- Dockerfile supporting dynamic `$PORT` binding.
- Pytest test suite with smoke tests for `/healthz` and `/`.
