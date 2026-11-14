"""Deterministic text chunking service.

Splits normalized source documents into non-overlapping chunks with line-accurate labels.
Rules from PROJECT_BRIEF.md:
- Deterministic, zero LLM, never splits mid-line.
- md, txt, paste: ~1,200 chars, snapping to blank lines when possible.
  Disjoint (no overlap) so every quote maps to exactly one chunk.
- csv: repeat the header row inside each chunk's text; ~15 rows per chunk.
- json: pretty-print, then treat like txt.
- Labels: 'S{source_ordinal}:L{start}-{end}'.
"""

import csv
import io
import json
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ChunkRecord:
    """Represents an extracted chunk ready for persistence."""
    label: str
    start_line: int
    end_line: int
    text: str
    source_ordinal: int
    source_id: Optional[str] = None


TARGET_CHUNK_CHARS = 1200
CSV_ROWS_PER_CHUNK = 15


def chunk_text_lines(
    lines: list[str],
    source_ordinal: int,
    base_line_offset: int = 1,
    target_chars: int = TARGET_CHUNK_CHARS,
) -> list[ChunkRecord]:
    """
    Chunk lines of text (~1,200 chars), never splitting mid-line,
    snapping to blank lines when possible, with strictly non-overlapping boundaries.

    Lines are assumed to not have trailing newline characters.
    `base_line_offset` is the 1-based line number of lines[0].
    """
    if not lines:
        return []

    # If all lines are empty or just one empty string
    if len(lines) == 1 and lines[0] == "":
        return [
            ChunkRecord(
                label=f"S{source_ordinal}:L{base_line_offset}-{base_line_offset}",
                start_line=base_line_offset,
                end_line=base_line_offset,
                text="",
                source_ordinal=source_ordinal,
            )
        ]

    chunks: list[ChunkRecord] = []
    num_lines = len(lines)
    idx = 0

    while idx < num_lines:
        start_idx = idx
        current_len = 0
        best_blank_idx = -1  # track candidate blank line split points

        while idx < num_lines:
            line_str = lines[idx]
            line_cost = len(line_str) + (1 if current_len > 0 else 0)

            # Check if this line is blank (useful for clean section snapping)
            if not line_str.strip() and idx > start_idx:
                best_blank_idx = idx

            # If we already have content and adding this line pushes us past target
            if current_len > 0 and (current_len + line_cost > target_chars):
                # If we found a blank line recently (at least 50% through target), snap there
                if best_blank_idx != -1 and best_blank_idx > start_idx:
                    split_idx = best_blank_idx
                else:
                    split_idx = idx

                chunk_lines = lines[start_idx:split_idx]
                chunk_text = "\n".join(chunk_lines)
                start_line = base_line_offset + start_idx
                end_line = base_line_offset + split_idx - 1
                chunks.append(
                    ChunkRecord(
                        label=f"S{source_ordinal}:L{start_line}-{end_line}",
                        start_line=start_line,
                        end_line=end_line,
                        text=chunk_text,
                        source_ordinal=source_ordinal,
                    )
                )
                idx = split_idx
                break

            current_len += line_cost
            idx += 1
        else:
            # Reached end of lines
            chunk_lines = lines[start_idx:idx]
            chunk_text = "\n".join(chunk_lines)
            start_line = base_line_offset + start_idx
            end_line = base_line_offset + idx - 1
            chunks.append(
                ChunkRecord(
                    label=f"S{source_ordinal}:L{start_line}-{end_line}",
                    start_line=start_line,
                    end_line=end_line,
                    text=chunk_text,
                    source_ordinal=source_ordinal,
                )
            )

    return chunks


def chunk_csv(
    content: str,
    source_ordinal: int,
    rows_per_chunk: int = CSV_ROWS_PER_CHUNK,
) -> list[ChunkRecord]:
    """
    Chunk CSV documents:
    - Parse using standard csv.reader to properly handle multi-line cells, quotes, and commas.
    - Keep track of actual line numbers in the original raw source.
    - Each chunk repeats the header row inside its text.
    - Chunks span ~15 data rows.
    """
    if not content.strip():
        return [
            ChunkRecord(
                label=f"S{source_ordinal}:L1-1",
                start_line=1,
                end_line=1,
                text="",
                source_ordinal=source_ordinal,
            )
        ]

    lines = content.split("\n")
    sio = io.StringIO(content)
    try:
        reader = csv.reader(sio)
        records: list[tuple[int, int, str]] = []  # (start_line, end_line, raw_text)
        prev_line = 0
        for _ in reader:
            curr_line = reader.line_num
            raw_slice = lines[prev_line:curr_line]
            records.append((prev_line + 1, curr_line, "\n".join(raw_slice)))
            prev_line = curr_line
    except Exception:
        # Fallback to simple line-based chunking if CSV parser fails
        return chunk_text_lines(lines, source_ordinal=source_ordinal)

    if not records:
        return []

    header_record = records[0]
    header_text = header_record[2]
    data_records = records[1:]

    if not data_records:
        return [
            ChunkRecord(
                label=f"S{source_ordinal}:L{header_record[0]}-{header_record[1]}",
                start_line=header_record[0],
                end_line=header_record[1],
                text=header_text,
                source_ordinal=source_ordinal,
            )
        ]

    chunks: list[ChunkRecord] = []
    num_data = len(data_records)
    idx = 0

    while idx < num_data:
        end_idx = min(idx + rows_per_chunk, num_data)
        slice_records = data_records[idx:end_idx]

        start_line = slice_records[0][0]
        end_line = slice_records[-1][1]

        data_text = "\n".join(r[2] for r in slice_records)
        chunk_text = header_text + "\n" + data_text

        chunks.append(
            ChunkRecord(
                label=f"S{source_ordinal}:L{start_line}-{end_line}",
                start_line=start_line,
                end_line=end_line,
                text=chunk_text,
                source_ordinal=source_ordinal,
            )
        )
        idx = end_idx

    return chunks


def chunk_json(
    content: str,
    source_ordinal: int,
) -> list[ChunkRecord]:
    """
    Chunk JSON documents:
    - If valid JSON, pretty-print with indent=2, then treat like text.
    - If JSON parse fails, falls back to raw text lines with normal text chunking.
    """
    if not content.strip():
        return [
            ChunkRecord(
                label=f"S{source_ordinal}:L1-1",
                start_line=1,
                end_line=1,
                text="",
                source_ordinal=source_ordinal,
            )
        ]

    try:
        parsed = json.loads(content)
        formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
        lines = formatted.split("\n")
    except Exception:
        lines = content.split("\n")

    return chunk_text_lines(lines, source_ordinal=source_ordinal)


def chunk_source(
    content: str,
    kind: str,
    source_ordinal: int,
    source_id: Optional[str] = None,
) -> list[ChunkRecord]:
    """
    Dispatch chunking according to kind ('md', 'txt', 'paste', 'csv', 'json').
    Sets source_id on all returned ChunkRecord instances.
    """
    kind = kind.lower()
    if kind == "csv":
        chunks = chunk_csv(content, source_ordinal=source_ordinal)
    elif kind == "json":
        chunks = chunk_json(content, source_ordinal=source_ordinal)
    else:  # 'md', 'txt', 'paste' or default
        lines = content.split("\n")
        chunks = chunk_text_lines(lines, source_ordinal=source_ordinal)

    for c in chunks:
        c.source_id = source_id

    return chunks

