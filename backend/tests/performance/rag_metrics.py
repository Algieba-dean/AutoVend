"""
RAG-specific evaluation metrics — Faithfulness, Answer Relevance, Retrieval Quality.

These metrics fill the critical gap in the original KPI system which completely
lacked RAG evaluation. In automotive sales, hallucinated vehicle specs are fatal.

Metrics:
  1. Retrieval Relevance: Do retrieved vehicles match user's explicit needs?
  2. Faithfulness: Are vehicle claims in the response grounded in retrieved data?
  3. Answer Relevance: Does the response actually address the user's question?
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class RetrievalScore:
    """Scores how well retrieved vehicles match user needs."""

    total_retrieved: int = 0
    needs_matched: int = 0        # How many retrieved cars match ≥1 need field
    needs_fields_checked: int = 0  # Total need fields checked across all cars
    needs_fields_hit: int = 0      # Total need field matches

    @property
    def precision(self) -> float:
        """Fraction of retrieved cars that match at least one need."""
        return self.needs_matched / self.total_retrieved if self.total_retrieved else 0.0

    @property
    def field_match_rate(self) -> float:
        """Fraction of need-field checks that matched."""
        return self.needs_fields_hit / self.needs_fields_checked if self.needs_fields_checked else 0.0

    @property
    def score_100(self) -> float:
        """Combined score on 0-100 scale."""
        return (0.6 * self.precision + 0.4 * self.field_match_rate) * 100

    def to_dict(self) -> dict:
        return {
            "total_retrieved": self.total_retrieved,
            "needs_matched": self.needs_matched,
            "precision": round(self.precision, 3),
            "field_match_rate": round(self.field_match_rate, 3),
            "score": round(self.score_100, 1),
        }


def score_retrieval_relevance(
    retrieved_cars: List[Dict[str, Any]],
    user_needs: Dict[str, str],
) -> RetrievalScore:
    """
    Evaluate how well retrieved vehicles match user's explicit needs.

    For each retrieved car, checks if its metadata matches the user's
    stated needs (brand, powertrain, price range, etc.).

    Args:
        retrieved_cars: List of retrieved car dicts with 'metadata' field.
        user_needs: Dict of explicit need field → value.

    Returns:
        RetrievalScore with precision and field match rate.
    """
    score = RetrievalScore(total_retrieved=len(retrieved_cars))

    # Filter to non-empty needs
    active_needs = {k: v for k, v in user_needs.items() if v and v.strip()}
    if not active_needs or not retrieved_cars:
        return score

    for car in retrieved_cars:
        meta = car.get("metadata", {})
        car_matched = False
        for need_key, need_val in active_needs.items():
            score.needs_fields_checked += 1
            meta_val = str(meta.get(need_key, "")).lower()
            need_val_lower = need_val.lower()
            if meta_val and (need_val_lower in meta_val or meta_val in need_val_lower):
                score.needs_fields_hit += 1
                car_matched = True
        if car_matched:
            score.needs_matched += 1

    return score


@dataclass
class FaithfulnessScore:
    """Scores whether response claims are grounded in retrieved data."""

    total_claims: int = 0      # Number of factual claims detected in response
    grounded_claims: int = 0   # Claims supported by retrieved data
    ungrounded_claims: int = 0  # Claims NOT found in retrieved data

    @property
    def score(self) -> float:
        """Faithfulness score 0-100. 100 = all claims grounded or no claims made."""
        if self.total_claims == 0:
            return 100.0  # No factual claims = no hallucination risk
        return (self.grounded_claims / self.total_claims) * 100

    def to_dict(self) -> dict:
        return {
            "total_claims": self.total_claims,
            "grounded": self.grounded_claims,
            "ungrounded": self.ungrounded_claims,
            "score": round(self.score, 1),
        }


# Patterns that indicate factual vehicle claims
_CLAIM_PATTERNS = [
    # Chinese number patterns: "续航500公里", "马力200匹"
    re.compile(r"[\u4e00-\u9fff]*\d+[\u4e00-\u9fff]+"),
    # Price patterns: "15万", "25-35万"
    re.compile(r"\d+[-~到]\d*万"),
    # Spec patterns: "L2自动驾驶", "7座"
    re.compile(r"L\d自动驾驶|[0-9]+座|[0-9]+T|[0-9]+\.?[0-9]*L"),
    # English specs: "200hp", "500km range"
    re.compile(r"\d+\s*(hp|kw|km|mph|kwh|nm)", re.IGNORECASE),
]


def score_faithfulness(
    response: str,
    retrieved_cars: List[Dict[str, Any]],
) -> FaithfulnessScore:
    """
    Check if factual claims in the response are grounded in retrieved data.

    Extracts number-based factual claims from the response and checks
    whether they appear in the retrieved vehicle text snippets or metadata.

    Args:
        response: The agent's response text.
        retrieved_cars: List of retrieved car dicts.

    Returns:
        FaithfulnessScore with grounded/ungrounded counts.
    """
    score = FaithfulnessScore()

    # Build reference corpus from retrieved data
    reference_text = ""
    for car in retrieved_cars:
        reference_text += " " + car.get("text_snippet", "")
        meta = car.get("metadata", {})
        reference_text += " " + " ".join(str(v) for v in meta.values())
    reference_lower = reference_text.lower()

    # Extract claims from response
    claims = set()
    for pattern in _CLAIM_PATTERNS:
        for match in pattern.finditer(response):
            claims.add(match.group())

    score.total_claims = len(claims)

    for claim in claims:
        claim_lower = claim.lower()
        # Check if claim text appears in reference
        if claim_lower in reference_lower:
            score.grounded_claims += 1
        else:
            # Fuzzy: check if the numbers in the claim appear
            numbers = re.findall(r"\d+", claim)
            if numbers and all(n in reference_lower for n in numbers):
                score.grounded_claims += 1
            else:
                score.ungrounded_claims += 1
                logger.debug(f"Ungrounded claim: '{claim}'")

    return score


@dataclass
class RAGEvaluation:
    """Combined RAG evaluation for a single turn."""

    retrieval: RetrievalScore = field(default_factory=RetrievalScore)
    faithfulness: FaithfulnessScore = field(default_factory=FaithfulnessScore)

    @property
    def overall_score(self) -> float:
        """Weighted RAG score: 50% retrieval + 50% faithfulness."""
        return 0.5 * self.retrieval.score_100 + 0.5 * self.faithfulness.score

    def to_dict(self) -> dict:
        return {
            "retrieval": self.retrieval.to_dict(),
            "faithfulness": self.faithfulness.to_dict(),
            "overall": round(self.overall_score, 1),
        }


def evaluate_rag(
    response: str,
    retrieved_cars: List[Dict[str, Any]],
    user_needs: Dict[str, str],
) -> RAGEvaluation:
    """
    Run full RAG evaluation on a single turn.

    Args:
        response: Agent response text.
        retrieved_cars: Retrieved vehicle data.
        user_needs: User's explicit needs dict.

    Returns:
        RAGEvaluation with retrieval and faithfulness scores.
    """
    return RAGEvaluation(
        retrieval=score_retrieval_relevance(retrieved_cars, user_needs),
        faithfulness=score_faithfulness(response, retrieved_cars),
    )
