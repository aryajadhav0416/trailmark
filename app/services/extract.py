"""Extraction service.

Orchestrates LLM handover knowledge extraction from chunked sources:
- Groups chunks into ~6,000 char batches.
- Wraps chunks in untrusted <source_chunk id="..."> data tags.
- Uses app/prompts/extract_system.txt as system prompt.
- Validates items via Pydantic (type enum, quote 12-300 chars, statement <= 240 chars).
- Drops invalid items and counts them.
- Drops exact duplicates across batches (same type + normalised statement).
- Returns items, warnings, and extraction stats.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError

from app.services.chunker import ChunkRecord
from app.services.llm import generate_json

BATCH_TARGET_CHARS = 6000
SYSTEM_PROMPT_PATH = Path("app/prompts/extract_system.txt")


class ItemType(str, Enum):
    """Allowed item types defined in PROJECT_BRIEF.md."""
    decision = "decision"
    ownership = "ownership"
    risk = "risk"
    open_question = "open_question"
    dependency = "dependency"
    next_action = "next_action"


class ConfidenceLevel(str, Enum):
    """LLM confidence levels."""
    high = "high"
    medium = "medium"
    low = "low"


class ExtractedItemSchema(BaseModel):
    """Pydantic schema enforcing extraction item constraints."""
    type: ItemType
    statement: str = Field(..., max_length=240)
    owner: Optional[str] = None
    quote: str = Field(..., min_length=12, max_length=300)
    chunk_id: str
    confidence: ConfidenceLevel = ConfidenceLevel.medium
    reason: Optional[str] = Field(None, max_length=160)


@dataclass
class ExtractionStats:
    """Extraction run statistics."""
    total_batches: int = 0
    cached_batches: int = 0
    raw_items_count: int = 0
    dropped_invalid_count: int = 0
    dropped_duplicate_count: int = 0
    final_items_count: int = 0


@dataclass
class ExtractionResult:
    """Result returned by extract_case_knowledge."""
    items: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: ExtractionStats = field(default_factory=ExtractionStats)


def load_extract_system_prompt() -> str:
    """Load system prompt from app/prompts/extract_system.txt."""
    if not SYSTEM_PROMPT_PATH.exists():
        raise FileNotFoundError(f"Missing extract system prompt file: {SYSTEM_PROMPT_PATH}")
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def batch_chunks(chunks: list[ChunkRecord], target_chars: int = BATCH_TARGET_CHARS) -> list[list[ChunkRecord]]:
    """Group chunks into batches of approximately target_chars characters."""
    if not chunks:
        return []

    batches: list[list[ChunkRecord]] = []
    current_batch: list[ChunkRecord] = []
    current_chars = 0

    for chunk in chunks:
        chunk_len = len(chunk.text)
        if current_batch and (current_chars + chunk_len > target_chars):
            batches.append(current_batch)
            current_batch = [chunk]
            current_chars = chunk_len
        else:
            current_batch.append(chunk)
            current_chars += chunk_len

    if current_batch:
        batches.append(current_batch)

    return batches


def build_user_prompt(
    project_name: str,
    leaver_name: str,
    newcomer_role: str,
    batch: list[ChunkRecord],
) -> str:
    """Build user prompt embedding chunk data safely in <source_chunk> tags."""
    header = (
        f"Project: {project_name}\n"
        f"Team member leaving: {leaver_name}\n"
        f"Incoming handover role: {newcomer_role}\n\n"
        "Source data chunks:\n"
    )

    chunk_blocks = []
    for chunk in batch:
        block = f'<source_chunk id="{chunk.label}">\n{chunk.text}\n</source_chunk>'
        chunk_blocks.append(block)

    return header + "\n\n".join(chunk_blocks)


def normalize_statement_for_dedupe(statement: str) -> str:
    """Normalize statement by trimming, lowercasing, and collapsing whitespace."""
    return re.sub(r"\s+", " ", statement.strip().lower())


def extract_case_knowledge(
    project_name: str,
    leaver_name: str,
    newcomer_role: str,
    chunks: list[ChunkRecord],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    bypass_cache: bool = False,
) -> ExtractionResult:
    """
    Run extraction pipeline over chunks in batches:
    1. Group chunks into ~6,000 char batches.
    2. Invoke LLM with extract_system.txt and structured user prompt.
    3. Validate and filter items with Pydantic.
    4. Deduplicate items by (type, normalised statement).
    5. Aggregate warnings and statistics.
    """
    system_prompt = load_extract_system_prompt()
    batches = batch_chunks(chunks)

    stats = ExtractionStats(total_batches=len(batches))
    all_raw_items: list[dict[str, Any]] = []
    all_warnings: list[str] = []

    for batch in batches:
        user_prompt = build_user_prompt(project_name, leaver_name, newcomer_role, batch)
        response_data, cached = generate_json(
            system=system_prompt,
            user=user_prompt,
            provider=provider,
            model=model,
            api_key=api_key,
            bypass_cache=bypass_cache,
        )

        if cached:
            stats.cached_batches += 1

        batch_items = response_data.get("items", [])
        batch_warnings = response_data.get("warnings", [])

        all_raw_items.extend(batch_items)
        all_warnings.extend(batch_warnings)

    stats.raw_items_count = len(all_raw_items)

    # Validate items with Pydantic schema
    valid_items: list[dict[str, Any]] = []
    for raw in all_raw_items:
        try:
            validated = ExtractedItemSchema.model_validate(raw)
            valid_items.append(validated.model_dump())
        except ValidationError:
            stats.dropped_invalid_count += 1

    # Deduplicate items: same type + normalised statement
    seen_keys: set[tuple[str, str]] = set()
    deduped_items: list[dict[str, Any]] = []

    for item in valid_items:
        norm_stmt = normalize_statement_for_dedupe(item["statement"])
        key = (item["type"], norm_stmt)
        if key in seen_keys:
            stats.dropped_duplicate_count += 1
            continue
        seen_keys.add(key)
        deduped_items.append(item)

    stats.final_items_count = len(deduped_items)

    return ExtractionResult(
        items=deduped_items,
        warnings=all_warnings,
        stats=stats,
    )

