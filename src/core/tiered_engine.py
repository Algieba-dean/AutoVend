"""
Core Tiered Retrieval Facade (src/core/tiered_engine.py).

Provides architectural re-export of TieredRetrievalEngine for agent layer
without violating import boundaries.
"""

from src.retrieval.tiered_engine import FastSpecIndex, TieredRetrievalEngine, TieredSearchResult

__all__ = ["TieredRetrievalEngine", "TieredSearchResult", "FastSpecIndex"]

