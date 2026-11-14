"""LLM Adapter service.

Provides a unified interface `generate_json(system: str, user: str) -> dict`.
Features:
- Providers: "openai_compatible", "mock", "gemini" (stub), "anthropic" (stub).
- Automatic single retry with JSON repair prompt on malformed JSON.
- 60-second timeout with backoff retry (up to 2 times) on 429 and 5xx.
- SHA-256 disk caching under DATA_DIR/llm_cache/.
- Safe logging (never logs API keys or full user prompts).
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when LLM extraction fails or produces irrecoverable output."""
    pass


# Deterministic mock responses for tests
MOCK_RESPONSE: dict[str, Any] = {
    "items": [
        {
            "type": "decision",
            "statement": "Adopted SQLite for local database storage.",
            "owner": None,
            "quote": "Adopted SQLite for local database storage.",
            "chunk_id": "S1:L1-1",
            "confidence": "high",
            "reason": "Explicit choice mentioned in notes",
        }
    ],
    "warnings": [],
}


def compute_cache_key(provider: str, model: str, system: str, user: str) -> str:
    """Compute sha256 cache key from provider, model, system, and user prompt."""
    payload = f"{provider}:{model}:{system}:{user}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def get_cache_dir() -> Path:
    """Return the disk cache directory Path and ensure it exists."""
    cache_dir = settings.data_path / "llm_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def read_from_cache(cache_key: str) -> Optional[dict[str, Any]]:
    """Read cached JSON result if available."""
    cache_file = get_cache_dir() / f"{cache_key}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def write_to_cache(cache_key: str, data: dict[str, Any]) -> None:
    """Write result JSON to disk cache."""
    cache_file = get_cache_dir() / f"{cache_key}.json"
    try:
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to write LLM cache: {e}")


def _call_openai_compatible(
    system: str,
    user: str,
    api_key: str,
    model: str,
    base_url: str = "https://api.openai.com/v1",
) -> str:
    """Execute raw chat completion against an OpenAI-compatible endpoint with retries on 429 and 5xx."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
    }

    url = f"{base_url.rstrip('/')}/chat/completions"
    max_retries = 2
    timeout = 60.0

    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, headers=headers, json=payload)

            if response.status_code in (429, 500, 502, 503, 504):
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 1.5
                    logger.warning(
                        f"LLM request returned HTTP {response.status_code}. Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    raise ExtractionError(
                        f"LLM request failed with HTTP {response.status_code} after {max_retries} retries."
                    )

            response.raise_for_status()
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            if attempt < max_retries:
                time.sleep(1.0)
                continue
            raise ExtractionError("LLM request timed out after 60 seconds.")
        except httpx.HTTPStatusError as e:
            raise ExtractionError(f"LLM HTTP error {e.response.status_code}: {e.response.text[:200]}")
        except Exception as e:
            if attempt < max_retries and not isinstance(e, ExtractionError):
                time.sleep(1.0)
                continue
            raise ExtractionError(f"LLM request failed: {e}")

    raise ExtractionError("LLM request failed after max retries.")


def _call_provider_raw(provider: str, model: str, api_key: str, system: str, user: str) -> str:
    """Route raw LLM call to appropriate provider implementation."""
    provider = provider.lower()
    if provider == "mock":
        return json.dumps(MOCK_RESPONSE)

    if provider == "openai_compatible":
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        return _call_openai_compatible(
            system=system,
            user=user,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )

    if provider == "gemini":
        # Small stub for Gemini provider
        raise NotImplementedError("Gemini provider stub: configure LLM_PROVIDER=openai_compatible or mock.")

    if provider == "anthropic":
        # Small stub for Anthropic provider
        raise NotImplementedError("Anthropic provider stub: configure LLM_PROVIDER=openai_compatible or mock.")

    raise ExtractionError(f"Unsupported LLM provider: '{provider}'")


def generate_json(
    system: str,
    user: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    bypass_cache: bool = False,
) -> tuple[dict[str, Any], bool]:
    """
    Generate JSON from system and user prompts using the configured LLM provider.

    Returns:
        tuple[dict[str, Any], bool]: (parsed_json_dict, cached_bool)

    Behavior:
        - Checks disk cache first (reports cached=True on hit).
        - Attempts JSON parse; on malformed JSON, retries ONCE with repair instruction.
        - On second failure, raises ExtractionError.
    """
    prov = (provider or settings.LLM_PROVIDER).lower()
    mod = model or settings.LLM_MODEL
    key = api_key if api_key is not None else settings.LLM_API_KEY

    cache_key = compute_cache_key(prov, mod, system, user)

    # 1. Check disk cache
    if not bypass_cache:
        cached = read_from_cache(cache_key)
        if cached is not None:
            return cached, True

    # 2. Invoke provider
    raw_response = _call_provider_raw(prov, mod, key, system, user)

    # 3. Parse JSON or retry once with repair prompt
    parsed: Optional[dict[str, Any]] = None
    try:
        parsed = json.loads(raw_response.strip())
        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON root object")
    except Exception:
        # Retry ONCE with repair instruction
        repair_user = (
            f"Your previous response was not valid JSON. Please fix it and return strictly valid JSON:\n\n"
            f"{raw_response}\n\n"
            "Respond ONLY with valid JSON."
        )
        logger.info("Invalid JSON received from LLM; retrying once with repair prompt.")
        repair_raw = _call_provider_raw(prov, mod, key, system, repair_user)
        try:
            parsed = json.loads(repair_raw.strip())
            if not isinstance(parsed, dict):
                raise ValueError("Expected JSON root object")
        except Exception as e:
            raise ExtractionError(f"LLM returned invalid JSON after repair retry: {e}")

    # 4. Save to cache
    write_to_cache(cache_key, parsed)
    return parsed, False
