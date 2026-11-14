#!/usr/bin/env python3
"""CLI tool to inspect chunking and ingestion results for a file.

Usage:
    python scripts/chunk_demo.py <path-to-file>
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ingest import process_uploaded_file, IngestionError
from app.services.chunker import chunk_source


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/chunk_demo.py <path-to-file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    try:
        raw_bytes = file_path.read_bytes()
        normalized = process_uploaded_file(file_path.name, raw_bytes)
    except IngestionError as e:
        print(f"Rejection: {e}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Print any ingestion warnings
    if normalized.warning:
        print(f"Warning: {normalized.warning}")

    chunks = chunk_source(
        content=normalized.content,
        kind=normalized.kind,
        source_ordinal=1,
    )

    print(f"Processed '{file_path.name}' ({normalized.kind}): {len(chunks)} chunk(s)\n")
    for chunk in chunks:
        # First 80 chars of text representation (escaped newlines for clean printing)
        snippet = chunk.text[:80].replace("\n", "\\n")
        print(f"[{chunk.label}] {snippet}")


if __name__ == "__main__":
    main()

