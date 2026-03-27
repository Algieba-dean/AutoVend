"""
Base extraction utilities shared across all extractors.

Provides common JSON parsing, markdown stripping, and merge logic
to avoid duplication in individual extractors.
"""

import json
import logging
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def parse_llm_json(response_text: str) -> dict:
    """
    Parse JSON from LLM response text, handling markdown code blocks.

    Supports:
    - Raw JSON
    - JSON wrapped in ```json ... ```
    - JSON wrapped in ``` ... ```

    Args:
        response_text: Raw LLM response string.

    Returns:
        Parsed dict.

    Raises:
        json.JSONDecodeError: If no valid JSON found.
    """
    text = response_text.strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    return json.loads(text)


def merge_model(
    current: T,
    extracted: dict,
) -> T:
    """
    Merge extracted dict into an existing Pydantic model.

    Non-empty extracted values overwrite current values.
    Unknown keys in extracted are silently ignored.

    Args:
        current: The existing Pydantic model instance.
        extracted: Dict of extracted key-value pairs.

    Returns:
        New model instance with merged values.
    """
    merged = current.model_dump()
    for key, value in extracted.items():
        if key in merged and value and str(value).strip():
            merged[key] = str(value).strip()
    return type(current)(**merged)


def extract_with_llm(
    llm,
    prompt: str,
    current: T,
) -> T:
    """
    Generic extraction: call LLM, parse JSON, merge into model.

    Args:
        llm: LLM instance with .complete() method.
        prompt: Formatted prompt string.
        current: Current Pydantic model to merge into.

    Returns:
        Updated model instance, or current if extraction fails.
    """
    try:
        response = llm.complete(prompt)
        extracted = parse_llm_json(response.text)
        return merge_model(current, extracted)
    except Exception as e:
        logger.warning(f"Extraction failed: {e}")
        return current
