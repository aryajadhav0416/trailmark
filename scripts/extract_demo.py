#!/usr/bin/env python3
"""CLI tool to run extraction on a file and print the extracted items as JSON.

Usage:
    python scripts/extract_demo.py <path-to-file> [--provider <provider>] [--model <model>]
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ingest import process_uploaded_file, IngestionError
from app.services.chunker import chunk_source
from app.services.extract import extract_case_knowledge


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured handover items from a source file.")
    parser.add_argument("file_path", type=str, help="Path to the source text file")
    parser.add_argument("--provider", type=str, default=None, help="LLM provider (mock, openai_compatible, etc.)")
    parser.add_argument("--model", type=str, default=None, help="LLM model name")
    parser.add_argument("--project", type=str, default="Demo Project", help="Project name")
    parser.add_argument("--leaver", type=str, default="Sample Leaver", help="Leaver name")
    parser.add_argument("--role", type=str, default="Incoming Engineer", help="Newcomer role")
    parser.add_argument("--bypass-cache", action="store_true", help="Bypass LLM disk cache")

    args = parser.parse_args()

    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"Error: File '{file_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        raw_bytes = file_path.read_bytes()
        normalized = process_uploaded_file(file_path.name, raw_bytes)
    except IngestionError as e:
        print(f"Rejection: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    if normalized.warning:
        print(f"Warning: {normalized.warning}", file=sys.stderr)

    chunks = chunk_source(
        content=normalized.content,
        kind=normalized.kind,
        source_ordinal=1,
    )

    try:
        result = extract_case_knowledge(
            project_name=args.project,
            leaver_name=args.leaver,
            newcomer_role=args.role,
            chunks=chunks,
            provider=args.provider,
            model=args.model,
            bypass_cache=args.bypass_cache,
        )
    except Exception as e:
        print(f"Extraction failed: {e}", file=sys.stderr)
        sys.exit(1)

    output = {
        "items": result.items,
        "warnings": result.warnings,
        "stats": {
            "total_batches": result.stats.total_batches,
            "cached_batches": result.stats.cached_batches,
            "raw_items_count": result.stats.raw_items_count,
            "dropped_invalid_count": result.stats.dropped_invalid_count,
            "dropped_duplicate_count": result.stats.dropped_duplicate_count,
            "final_items_count": result.stats.final_items_count,
        },
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
