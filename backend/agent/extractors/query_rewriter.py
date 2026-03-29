"""
Query Rewriter — Local/Edge processing layer.

Responsibilities (aligned with architecture "端侧处理中心"):
1. Negative-need cleaning: remove "不要X" patterns and convert to exclusion filters
2. Colloquial normalization: map slang/vague terms to standard vehicle vocabulary
3. Structured filter extraction: produce hard metadata filters as JSON
4. Semantic query generation: produce a clean query for embedding search

This module is designed to be lightweight and deterministic (no LLM call
required for the core path), suitable for edge deployment on a 1.5B–8B model.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from agent.schemas import ExplicitNeeds, UserProfile, VehicleNeeds

logger = logging.getLogger(__name__)

# ── Colloquial → standard vocabulary mapping ─────────────────────────
SLANG_MAP: Dict[str, str] = {
    # Price
    "便宜": "10万以下",
    "经济实惠": "15万以下",
    "中等价位": "15-25万",
    "贵一点": "25-40万",
    "高端": "40万以上",
    "豪华": "50万以上",
    # Vehicle type
    "小车": "紧凑型轿车",
    "大车": "中大型SUV",
    "面包车": "MPV",
    "越野车": "Off-road SUV",
    "跑车": "Sports Car",
    "家用车": "紧凑型SUV",
    "商务车": "中大型轿车",
    "买菜车": "微型轿车",
    "代步车": "紧凑型轿车",
    # Powertrain
    "电车": "Battery Electric Vehicle",
    "油车": "Gasoline Engine",
    "混动": "Hybrid Electric Vehicle",
    "插混": "Plug-in Hybrid Electric Vehicle",
    "增程": "Range-Extended Electric Vehicle",
    "纯电": "Battery Electric Vehicle",
    # Design
    "运动": "Sporty",
    "商务": "Business",
    "时尚": "Sporty",
    "稳重": "Business",
}

# ── Negative-need patterns ───────────────────────────────────────────
# Matches patterns like "不要SUV", "别选油车", "不考虑日系"
NEGATIVE_PATTERNS = [
    re.compile(r"不要(.+?)(?:[，。,.]|$)"),
    re.compile(r"别选(.+?)(?:[，。,.]|$)"),
    re.compile(r"不考虑(.+?)(?:[，。,.]|$)"),
    re.compile(r"不想要(.+?)(?:[，。,.]|$)"),
    re.compile(r"排除(.+?)(?:[，。,.]|$)"),
    re.compile(r"不喜欢(.+?)(?:[，。,.]|$)"),
    re.compile(r"don'?t want (.+?)(?:[,.]|$)", re.IGNORECASE),
    re.compile(r"no (.+?)(?:[,.]|$)", re.IGNORECASE),
    re.compile(r"not (.+?)(?:[,.]|$)", re.IGNORECASE),
    re.compile(r"avoid (.+?)(?:[,.]|$)", re.IGNORECASE),
    re.compile(r"exclude (.+?)(?:[,.]|$)", re.IGNORECASE),
]


@dataclass
class RewriteResult:
    """Output of the query rewriting pipeline."""

    semantic_query: str = ""
    metadata_filters: Dict[str, str] = field(default_factory=dict)
    negative_filters: List[str] = field(default_factory=list)
    normalized_terms: Dict[str, str] = field(default_factory=dict)


def extract_negative_needs(text: str) -> Tuple[List[str], str]:
    """
    Extract negative needs ("不要X") and return them separately.

    Returns:
        Tuple of (negative_items, cleaned_text_without_negatives)
    """
    negatives: List[str] = []
    cleaned = text

    for pattern in NEGATIVE_PATTERNS:
        for match in pattern.finditer(text):
            neg_item = match.group(1).strip()
            if neg_item and len(neg_item) < 20:
                negatives.append(neg_item)
                cleaned = cleaned.replace(match.group(0), "")

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return negatives, cleaned


def normalize_colloquial(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Replace colloquial/slang terms with standard vehicle vocabulary.

    Returns:
        Tuple of (normalized_text, mapping_of_replacements)
    """
    normalized = text
    mappings: Dict[str, str] = {}

    for slang, standard in SLANG_MAP.items():
        if slang in normalized:
            normalized = normalized.replace(slang, standard)
            mappings[slang] = standard

    return normalized, mappings


def build_metadata_filters(
    explicit: ExplicitNeeds,
) -> Dict[str, str]:
    """
    Build hard metadata filter conditions from explicit needs.

    These are used for exact-match database filtering (pre-retrieval).
    Only non-empty fields that map to indexed metadata are included.
    """
    filters: Dict[str, str] = {}

    field_map = {
        "brand": explicit.brand,
        "powertrain_type": explicit.powertrain_type,
        "prize": explicit.prize,
        "vehicle_category_bottom": explicit.vehicle_category_bottom,
        "design_style": explicit.design_style,
        "drive_type": explicit.drive_type,
        "seat_layout": explicit.seat_layout,
        "autonomous_driving_level": explicit.autonomous_driving_level,
    }

    for key, value in field_map.items():
        if value:
            filters[key] = value

    return filters


def build_semantic_query(
    profile: UserProfile,
    needs: VehicleNeeds,
) -> str:
    """
    Build a clean semantic query for embedding-based retrieval.

    Combines explicit needs into a natural language query
    suitable for vector similarity search.
    """
    explicit = needs.explicit
    parts: List[str] = []

    if explicit.vehicle_category_bottom:
        parts.append(explicit.vehicle_category_bottom)
    if explicit.powertrain_type:
        parts.append(explicit.powertrain_type)
    if explicit.design_style:
        parts.append(f"{explicit.design_style} design")
    if explicit.brand:
        parts.append(f"{explicit.brand} brand")
    if explicit.prize:
        parts.append(f"price range {explicit.prize}")
    if explicit.seat_layout:
        parts.append(explicit.seat_layout)

    # Enrich with implicit needs for better semantic matching
    implicit = needs.implicit
    if implicit.family_friendliness == "High":
        parts.append("family friendly spacious")
    if implicit.safety == "High":
        parts.append("high safety rating")
    if implicit.comfort_level == "High":
        parts.append("comfortable luxury ride")
    if implicit.energy_consumption_level == "Low":
        parts.append("energy efficient")

    # Context from profile
    if profile.family_size and profile.family_size not in ("", "1"):
        parts.append(f"suitable for family of {profile.family_size}")

    if not parts:
        parts.append("recommend a good vehicle")

    return " ".join(parts)


def rewrite_query(
    user_message: str,
    profile: UserProfile,
    needs: VehicleNeeds,
) -> RewriteResult:
    """
    Full query rewriting pipeline (端侧处理中心).

    Steps:
    1. Extract and strip negative needs from user message
    2. Normalize colloquial terms to standard vocabulary
    3. Build hard metadata filters from explicit needs
    4. Build semantic query for embedding search

    Args:
        user_message: Raw user input text.
        profile: Current user profile.
        needs: Current vehicle needs.

    Returns:
        RewriteResult with all processed components.
    """
    # Step 1: Negative need extraction
    negatives, cleaned_msg = extract_negative_needs(user_message)

    # Step 2: Colloquial normalization
    _, normalized_terms = normalize_colloquial(cleaned_msg)

    # Step 3: Hard metadata filters
    metadata_filters = build_metadata_filters(needs.explicit)

    # Step 4: Semantic query
    semantic_query = build_semantic_query(profile, needs)

    result = RewriteResult(
        semantic_query=semantic_query,
        metadata_filters=metadata_filters,
        negative_filters=negatives,
        normalized_terms=normalized_terms,
    )

    logger.info(
        f"Query rewrite: semantic='{semantic_query[:80]}', "
        f"filters={len(metadata_filters)}, "
        f"negatives={negatives}"
    )

    return result
