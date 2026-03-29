"""
Reranker — cross-attention reranking for RAG retrieval results.

Aligned with architecture "知识增强系统 RAG Engine":
- Takes coarse-ranked Top-20 candidates from dual-path retrieval
- Applies cross-attention scoring (or metadata-based scoring as fallback)
- Returns refined Top-3 high-precision results

Supports two modes:
1. Model-based: uses a cross-encoder reranker (e.g., bge-reranker-v2-m3)
2. Rule-based fallback: metadata field matching + score boosting
"""

import logging
from dataclasses import dataclass
from typing import Dict, List

from llama_index.core.schema import NodeWithScore

logger = logging.getLogger(__name__)


@dataclass
class RerankConfig:
    """Configuration for reranking behavior."""

    top_k: int = 3
    metadata_boost_weight: float = 0.1
    negative_penalty_weight: float = 0.3
    min_score_threshold: float = 0.0


def rerank_with_cross_attention(
    candidates: List[NodeWithScore],
    query: str,
    user_needs: Dict[str, str],
    negative_filters: List[str],
    config: RerankConfig = RerankConfig(),
) -> List[NodeWithScore]:
    """
    Rerank candidates using metadata matching + negative filtering.

    This is the rule-based reranker that serves as both the primary
    reranker and fallback. In production, this would be replaced by
    a cross-encoder model (e.g., BAAI/bge-reranker-v2-m3).

    Scoring formula:
        final_score = original_score
                    + (matched_fields * boost_weight)
                    - (negative_matches * penalty_weight)

    Args:
        candidates: Coarse-ranked retrieval results.
        query: The semantic query used for retrieval.
        user_needs: Dict of explicit need field→value for boosting.
        negative_filters: List of negative terms to penalize.
        config: Reranking configuration.

    Returns:
        Reranked and filtered list, trimmed to top_k.
    """
    if not candidates:
        return []

    scored: List[NodeWithScore] = []

    for node in candidates:
        original_score = node.score if node.score is not None else 0.0
        bonus = 0.0
        penalty = 0.0
        meta = node.metadata

        # Positive matching: boost for each metadata field match
        for key, value in user_needs.items():
            if not value:
                continue
            meta_val = str(meta.get(key, "")).lower()
            need_val = str(value).lower()
            if meta_val and need_val:
                if need_val in meta_val or meta_val in need_val:
                    bonus += config.metadata_boost_weight

        # Negative filtering: penalize for matching negative terms
        node_text = (node.text or "").lower()
        node_model = str(meta.get("car_model", "")).lower()
        node_brand = str(meta.get("brand", "")).lower()

        for neg_term in negative_filters:
            neg_lower = neg_term.lower()
            if (
                neg_lower in node_text
                or neg_lower in node_model
                or neg_lower in node_brand
            ):
                penalty += config.negative_penalty_weight

        final_score = original_score + bonus - penalty
        node.score = max(final_score, 0.0)

        # Skip items below threshold
        if node.score >= config.min_score_threshold:
            scored.append(node)

    # Sort by final score descending
    scored.sort(key=lambda n: n.score or 0.0, reverse=True)

    result = scored[: config.top_k]

    logger.info(
        f"Reranked {len(candidates)} candidates → "
        f"{len(result)} results "
        f"(negatives={negative_filters})"
    )
    for i, node in enumerate(result):
        car = node.metadata.get("car_model", "?")
        logger.debug(f"  [{i+1}] {car} score={node.score:.4f}")

    return result
