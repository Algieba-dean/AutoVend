"""
Chain-of-Thought Thinking Block Scrubber for AutoVend Agent (src/agent/think_scrubber.py).

Inspired by NousResearch Hermes-Agent think_scrubber.py.
Strips or isolates `<think> ... </think>` and `<thought> ... </thought>` tags from reasoning LLMs
(DeepSeek-R1, Qwen2.5-Coder-Reasoning, Hermes 3) so customer-facing replies stay clean.
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Matches case-insensitive <think>...</think>, <thought>...</thought>, <reasoning>...</reasoning>
THINK_BLOCK_REGEX = re.compile(
    r"<(think|thought|reasoning)>\s*.*?\s*</\1>",
    re.DOTALL | re.IGNORECASE,
)


def scrub_think_blocks(text: str) -> Tuple[str, str]:
    """
    Scrub thinking blocks from text.
    Returns (cleaned_user_visible_text, extracted_thinking_thoughts).
    """
    if not text:
        return "", ""

    thoughts = THINK_BLOCK_REGEX.findall(text)
    thought_text = "\n".join(thoughts)

    cleaned = THINK_BLOCK_REGEX.sub("", text).strip()
    return cleaned, thought_text
