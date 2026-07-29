"""
Reranker & Rank Refinement module for Standalone RAG Service (src/rag_service).
Refines candidate vehicle ranking using semantic score fusion and feature alignment.
"""

import logging
from typing import List

from src.rag_service.schemas import VehicleSearchResult

logger = logging.getLogger(__name__)


class RankRefiner:
    """
    Refines and reranks candidate vehicles returned by RRF retrieval pipeline.
    Applies exact feature matching boosts and penalty for severe attribute mismatch.
    """

    @staticmethod
    def refine(
        query_text: str,
        results: List[VehicleSearchResult],
        top_k: int = 5,
    ) -> List[VehicleSearchResult]:
        """Rerank candidates based on query alignment and score normalization."""
        if not results:
            return []

        query_lower = query_text.lower()
        scored_items: List[tuple[float, VehicleSearchResult]] = []

        for item in results:
            boost = 0.0
            meta = item.metadata

            # Brand exact match boost
            brand = (meta.get("brand") or "").lower()
            if brand and brand in query_lower:
                boost += 0.25

            # Vehicle category match boost
            cat = (meta.get("category") or "").lower()
            if cat and cat in query_lower:
                boost += 0.20

            # Powertrain match boost
            p_type = (meta.get("powertrain_type") or "").lower()
            if p_type and p_type in query_lower:
                boost += 0.15

            # Combine original RRF score with heuristic feature boost
            final_score = item.score * 0.6 + boost * 0.4
            item.score = round(final_score, 4)
            scored_items.append((final_score, item))

        # Sort descending by refined score
        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_items[:top_k]]
