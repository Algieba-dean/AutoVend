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

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


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
    max_retries: int = 2,
) -> T:
    """
    Generic extraction via LangChain `chat_model.with_structured_output(type(current))`.

    Retries up to max_retries times on validation/parse failures.
    """
    from langchain_core.messages import HumanMessage

    from src.llm.langchain_adapter import ensure_chat_model

    chat_model = ensure_chat_model(llm)
    structured_llm = chat_model.with_structured_output(type(current))

    for attempt in range(max_retries):
        try:
            parsed = structured_llm.invoke([HumanMessage(content=prompt)])
            extracted = parsed.model_dump() if isinstance(parsed, BaseModel) else dict(parsed)
            return merge_model(current, extracted)
        except Exception as e:
            logger.warning(f"Extraction attempt {attempt + 1}/{max_retries} failed: {e}")
    return current
