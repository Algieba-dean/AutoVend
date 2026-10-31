"""
Context Compression & Hallucination-Grounded Pruning Engine (src/retrieval/compression.py).

Provides backward-compatible re-exports from src/core/compression.py.
"""

from src.core.compression import (
    FACTUAL_SPEC_PATTERNS,
    MARKETING_FLUFF_PATTERNS,
    CompressedContext,
    ContextCompressor,
)

__all__ = [
    "MARKETING_FLUFF_PATTERNS",
    "FACTUAL_SPEC_PATTERNS",
    "CompressedContext",
    "ContextCompressor",
]
