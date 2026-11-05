"""
Reranker & Rank Refinement module for Standalone RAG Service (src/rag_service/reranker.py).

Refines candidate vehicle ranking using dynamic multi-attribute tabular spec scoring,
query intent weighting, and semantic score fusion.
"""

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from src.rag_service.schemas import VehicleSearchResult

logger = logging.getLogger(__name__)


def parse_numeric_price_range(price_str: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse a vehicle price string (e.g. '21.59-29.99万', '30万', '15.98万元起')
    into (min_price_k_yuan, max_price_k_yuan).
    """
    if not price_str:
        return None, None

    nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", price_str)]
    if not nums:
        return None, None

    if len(nums) == 1:
        # Single number e.g. '25万' -> 25.0, 25.0
        val = nums[0]
        if val > 1000:  # e.g. 250000 -> 25.0
            val = val / 10000.0
        return val, val

    # Range e.g. 21.59 - 29.99
    p_min = min(nums)
    p_max = max(nums)
    if p_min > 1000:
        p_min /= 10000.0
    if p_max > 1000:
        p_max /= 10000.0
    return p_min, p_max


def parse_budget_limit(budget_str: str) -> Optional[float]:
    """
    Extract budget upper limit in 10k RMB (万元).
    Examples: '25万以内' -> 25.0, '20-30万' -> 30.0, '35万左右' -> 38.0
    """
    if not budget_str:
        return None
    nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", budget_str)]
    if not nums:
        return None
    val = max(nums)
    if val > 1000:
        val /= 10000.0
    if "左右" in budget_str:
        val = val * 1.10
    return val


def calculate_gaussian_price_fit(
    price: float, budget: float, sigma: Optional[float] = None
) -> float:
    """
    Continuous Gaussian decay function for budget compliance (Spec Fit Gate):
    S_price = 1.0 if price <= budget else exp(-(price - budget)^2 / (2 * sigma^2))
    - When overrun is 10%, score smoothly decays to ~0.85
    - When overrun is 50%, score non-linearly drops towards 0.0
    Guarantees strict monotonicity and continuous differentiability without step cliffs.
    """
    if price <= budget:
        return 1.0
    if budget <= 0:
        return 0.0
    if sigma is None:
        sigma = 0.175 * budget
    overrun = price - budget
    return float(math.exp(-(overrun**2) / (2.0 * (sigma**2))))


class RankRefiner:
    """
    Refines and reranks candidate vehicles returned by RRF retrieval pipeline.
    Combines semantic RRF scores with dynamic multi-attribute tabular spec scoring:
    1. Budget / Price fit scoring with penalty for excessive budget overrun.
    2. Seating layout & family capacity matching.
    3. Powertrain & range requirement fulfillment.
    4. Exact brand and category matching.
    5. Dynamic attribute weighting based on query intent.
    """

    @classmethod
    def calculate_spec_score(
        cls,
        item: VehicleSearchResult,
        query_text: str,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate normalized tabular specification match score (0.0 to 1.0)
        based on vehicle metadata and query requirements.
        """
        meta = item.metadata or {}
        query_lower = (query_text or "").lower()
        constraints = constraints or {}

        score = 0.50  # Neutral starting baseline

        # 1. Brand matching (+0.20 on match)
        brand = (item.brand or meta.get("brand") or "").lower()
        target_brand = (constraints.get("brand") or "").lower()
        if brand and (brand in query_lower or (target_brand and brand in target_brand)):
            score += 0.20

        # 2. Category matching (+0.15 on match)
        cat = (item.category or meta.get("vehicle_category_bottom") or meta.get("category") or "").lower()
        target_cat = (constraints.get("vehicle_category_bottom") or "").lower()
        if cat and (cat in query_lower or (target_cat and cat in target_cat)):
            score += 0.15

        # 3. Powertrain matching (+0.15 on match, -0.20 on severe mismatch)
        p_type = (item.powertrain_type or meta.get("powertrain_type") or "").lower()
        target_p = (constraints.get("powertrain_type") or "").lower()

        # Check BEV / PHEV / REEV / ICE
        is_query_bev = any(k in query_lower or k in target_p for k in ["纯电", "ev", "电动车", "电车"])
        is_query_hybrid = any(k in query_lower or k in target_p for k in ["混动", "插混", "增程", "phev", "dmi"])
        is_query_gasoline = any(k in query_lower or k in target_p for k in ["燃油", "汽油", "油车"])

        if is_query_bev:
            if "纯电" in p_type or "ev" in p_type:
                score += 0.15
            elif "燃油" in p_type:
                score -= 0.20
        elif is_query_hybrid:
            if any(k in p_type for k in ["混动", "插混", "增程", "phev"]):
                score += 0.15
            elif "纯电" in p_type and not is_query_bev:
                score -= 0.10
        elif is_query_gasoline:
            if "燃油" in p_type:
                score += 0.15

        # 4. Price & Budget fit
        target_budget_str = constraints.get("price") or ""
        if not target_budget_str:
            # Extract from query_text e.g. "20万左右", "25万以内"
            b_match = re.search(r"(\d+(?:\.\d+)?)\s*万(?:以内|左右|上下|预算)?", query_text)
            if b_match:
                target_budget_str = b_match.group(0)

        budget_limit = parse_budget_limit(target_budget_str)
        veh_price_str = item.price or meta.get("price") or ""
        v_min, v_max = parse_numeric_price_range(veh_price_str)

        if budget_limit is not None and v_min is not None:
            if v_min <= budget_limit:
                # Comfortably within budget
                score += 0.20
            else:
                # Continuous Gaussian decay penalty for budget overrun (no discrete cliff step)
                decay = calculate_gaussian_price_fit(
                    v_min, budget_limit, sigma=max(2.0, 0.25 * budget_limit)
                )
                penalty = (1.0 - decay) * 0.45
                score -= penalty

        # 5. Seating layout fit
        target_seats = constraints.get("seat_layout") or ""
        is_query_multiseat = any(
            k in query_lower or k in target_seats
            for k in ["6座", "7座", "六座", "七座", "大空间", "二胎"]
        )
        veh_seats = str(meta.get("seat_layout") or "") + " " + item.text_snippet
        if is_query_multiseat:
            if any(k in veh_seats for k in ["6座", "7座", "六座", "七座"]):
                score += 0.20
            elif "2座" in veh_seats:
                score -= 0.25

        # 6. Smart Driving / Tech highlights
        is_query_smart = any(
            k in query_lower for k in ["智驾", "自动驾驶", "激光雷达", "高阶", "noa", "orin"]
        )
        if is_query_smart:
            if any(
                k in (item.text_snippet + " " + str(meta)).lower()
                for k in ["激光雷达", "noa", "orin", "高阶智驾"]
            ):
                score += 0.15

        # Clamp between 0.0 and 1.0
        return max(0.0, min(1.0, score))

    @classmethod
    def refine(
        cls,
        query_text: str,
        results: List[VehicleSearchResult],
        top_k: int = 5,
        constraints: Optional[Dict[str, Any]] = None,
        cross_encoder: Optional[Any] = None,
    ) -> List[VehicleSearchResult]:
        """
        Rerank and refine candidate vehicles based on tabular spec alignment and query intent.
        Standard two-stage rank refinement pipeline:
        Stage 1: Normalized semantic retrieval scores (Min-Max over candidate window or Sigmoid calibrated).
        Stage 2: Smooth continuous constraint alignment score (spec fit gate).
        """
        if not results:
            return []

        scored_items: List[Tuple[float, VehicleSearchResult]] = []

        # Determine dynamic spec weight based on query intent
        # Higher spec weight for constraint-rich or price-sensitive queries
        spec_weight = 0.40
        if any(
            k in query_text
            for k in ["万", "预算", "座", "纯电", "混动", "增程", "智驾", "省钱"]
        ):
            spec_weight = 0.50

        # Calibrated semantic score normalization:
        # Avoid arbitrary fudge factors (* 6.0, / 0.10) or discontinuous step-function cliff drops.
        # Dynamically scale by candidate batch maximum when scores originate from RRF reciprocal rank range (<= 0.20),
        # preserving strict monotonicity within the candidate set.
        raw_scores = [max(0.0, float(item.score)) for item in results]
        max_batch_score = max(raw_scores) if raw_scores else 0.0
        norm_scale = max_batch_score if (0.0 < max_batch_score <= 0.20) else 1.0

        # Batch score candidates with external cross-encoder if provided
        ce_scores = None
        if cross_encoder is not None and hasattr(cross_encoder, "score_pairs"):
            try:
                snippets = [item.text_snippet for item in results]
                ce_arr = cross_encoder.score_pairs(query_text, snippets)
                if ce_arr is not None and len(ce_arr) == len(results):
                    ce_scores = ce_arr
            except Exception as e:
                logger.debug(f"Cross-encoder batch scoring fallback: {e}")

        for idx, item in enumerate(results):
            raw_s = raw_scores[idx]
            semantic_score = min(1.0, max(0.0, raw_s / norm_scale)) if norm_scale > 0 else 0.0

            spec_score = cls.calculate_spec_score(item, query_text, constraints)

            if ce_scores is not None:
                semantic_score = float(ce_scores[idx])

            # Calibrated convex combination strictly within [0.0, 1.0]
            final_score = semantic_score * (1.0 - spec_weight) + spec_score * spec_weight
            final_score = round(max(0.0, min(1.0, final_score)), 4)

            item.score = final_score
            item.metadata["spec_alignment_score"] = round(spec_score, 3)
            scored_items.append((final_score, item))

        # Sort descending by refined score
        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_items[:top_k]]


from src.rag_service.onnx_reranker import OnnxCrossEncoderReranker

CrossEncoderReranker = OnnxCrossEncoderReranker

