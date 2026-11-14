"""Source ingestion and normalization service.

Handles file validation, encoding fallback, sanitization, and normalization
of uploaded files (.txt, .md, .csv, .json) and pasted text according to PROJECT_BRIEF.md.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from app.config import settings

KNOWN_EXTENSIONS = {
    ".txt": "txt",
    ".md": "md",
    ".csv": "csv",
    ".json": "json",
}

MAX_FILES_ALLOWED = 10


class IngestionError(Exception):
    """Raised when uploaded content or file payload fails validation."""
    pass


@dataclass
class NormalizedSource:
    """Represents a validated, normalized source ready for chunking and storage."""
    filename: str
    kind: str  # 'md', 'txt', 'csv', 'json', 'paste'
    content: str
    char_count: int
    warning: Optional[str] = None


def normalize_text_content(raw_text: str) -> str:
    """
    Normalise text by stripping BOM, standardizing line endings to LF (\n),
    while preserving original lines and blank lines.
    """
    # Strip UTF-8 BOM if present
    if raw_text.startswith("\ufeff"):
        raw_text = raw_text[1:]

    # Normalize carriage returns
    return raw_text.replace("\r\n", "\n").replace("\r", "\n")


def decode_bytes(data: bytes) -> str:
    """
    Decode raw bytes to text using UTF-8 with errors='replace' fallback.
    Handles UTF-8 with BOM automatically as well.
    """
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def detect_kind_and_warning(filename: str, default_kind: Optional[str] = None) -> tuple[str, Optional[str]]:
    """Determine the source kind and produce a visible warning for unknown extensions."""
    if default_kind == "paste":
        return "paste", None

    ext = Path(filename).suffix.lower()
    if ext in KNOWN_EXTENSIONS:
        return KNOWN_EXTENSIONS[ext], None

    warning = f"File '{filename}' has an unsupported extension '{ext}'. Treated as plain text."
    return "txt", warning


def process_uploaded_file(
    filename: str,
    raw_bytes: bytes,
    max_file_bytes: Optional[int] = None,
) -> NormalizedSource:
    """
    Validate, decode, and normalize a single uploaded file.

    Raises IngestionError if size exceeds max_file_bytes.
    """
    limit_bytes = max_file_bytes or settings.MAX_FILE_BYTES
    if len(raw_bytes) > limit_bytes:
        raise IngestionError(
            f"File '{filename}' exceeds maximum allowed size of {limit_bytes} bytes "
            f"(received {len(raw_bytes)} bytes)."
        )

    decoded = decode_bytes(raw_bytes)
    normalized = normalize_text_content(decoded)
    kind, warning = detect_kind_and_warning(filename)

    return NormalizedSource(
        filename=filename,
        kind=kind,
        content=normalized,
        char_count=len(normalized),
        warning=warning,
    )


def process_pasted_text(
    content: str,
    title: str = "pasted_text.txt",
) -> NormalizedSource:
    """Validate and normalize pasted text input."""
    normalized = normalize_text_content(content)
    return NormalizedSource(
        filename=title,
        kind="paste",
        content=normalized,
        char_count=len(normalized),
        warning=None,
    )


def validate_source_batch(
    sources: list[NormalizedSource],
    max_files: int = MAX_FILES_ALLOWED,
    max_total_chars: Optional[int] = None,
) -> None:
    """
    Validate an entire batch of ingested sources against file count and total character limits.

    Raises IngestionError with a clear human message if limits are exceeded.
    """
    if len(sources) > max_files:
        raise IngestionError(
            f"Too many sources: received {len(sources)} files/items, but the maximum allowed is {max_files}."
        )

    limit_chars = max_total_chars or settings.MAX_INPUT_CHARS
    total_chars = sum(s.char_count for s in sources)
    if total_chars > limit_chars:
        raise IngestionError(
            f"Total input volume ({total_chars:,} characters) exceeds the limit of {limit_chars:,} characters. "
            "Please remove some files or trim the input before proceeding."
        )
