"""Safe JSON extraction from LLM responses.

Handles common issues:
- JSON wrapped in ```json ... ``` markdown blocks
- Extra text before/after JSON
- Partially malformed responses
"""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_from_response(raw: str) -> list[dict[str, Any]]:
    """Extract a JSON array from a possibly messy LLM response.

    Tries multiple strategies in order:
    1. Direct parse
    2. Extract from markdown code block
    3. Find first [ ... ] bracket pair
    4. Line-by-line repair
    """
    raw = raw.strip()

    # Strategy 1: direct parse
    result = _try_parse(raw)
    if result is not None:
        return result

    # Strategy 2: extract from ```json ... ``` or ``` ... ```
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
    if code_block:
        result = _try_parse(code_block.group(1).strip())
        if result is not None:
            return result

    # Strategy 3: find first [ ... ] pair
    bracket_start = raw.find("[")
    bracket_end = raw.rfind("]")
    if bracket_start != -1 and bracket_end > bracket_start:
        candidate = raw[bracket_start : bracket_end + 1]
        result = _try_parse(candidate)
        if result is not None:
            return result

    # Strategy 4: try to fix trailing commas and parse again
    if bracket_start != -1 and bracket_end > bracket_start:
        candidate = raw[bracket_start : bracket_end + 1]
        cleaned = _fix_trailing_commas(candidate)
        result = _try_parse(cleaned)
        if result is not None:
            return result

    raise ValueError(f"Could not extract valid JSON array from LLM response:\n{raw[:500]}")


def _try_parse(text: str) -> list[dict[str, Any]] | None:
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return None
    except (json.JSONDecodeError, TypeError):
        return None


def _fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before ] or }."""
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    return text
