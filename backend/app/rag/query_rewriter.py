"""
RAG Query Rewriter — transforms user needs into optimized retrieval queries.

Converts vague user expressions like "适合二胎家庭" into precise vehicle
parameter queries that match the knowledge base vocabulary.
"""

import logging

from llama_index.core.llms import LLM

from agent.schemas import UserProfile, VehicleNeeds

logger = logging.getLogger(__name__)

QUERY_REWRITE_PROMPT = """You are a vehicle search query optimizer.

Given the user's profile and vehicle needs, generate an optimized search query
for a vehicle knowledge base. The query should:
1. Include specific vehicle parameters (type, powertrain, price range)
2. Translate vague preferences into concrete vehicle attributes
3. Be written in Chinese (matching the knowledge base language)
4. Be a single paragraph, 2-3 sentences, covering all key requirements

User Profile:
- Family size: {family_size}
- Target driver: {target_driver}
- Price sensitivity: {price_sensitivity}
- Residence: {residence}

Explicit Needs:
- Budget: {prize}
- Vehicle type: {vehicle_category}
- Brand: {brand}
- Powertrain: {powertrain}
- Design style: {design_style}
- Seat layout: {seat_layout}
- Drive type: {drive_type}

Implicit Needs:
- Family friendliness: {family_friendliness}
- Comfort level: {comfort_level}
- Safety priority: {safety}
- Space requirement: {space}
- Energy efficiency: {energy_consumption}

Output ONLY the optimized search query, nothing else."""


def rewrite_query(
    llm: LLM,
    profile: UserProfile,
    needs: VehicleNeeds,
) -> str:
    """
    Use LLM to rewrite user needs into an optimized retrieval query.

    Args:
        llm: LLM instance for query generation.
        profile: Current user profile.
        needs: Current vehicle needs (explicit + implicit).

    Returns:
        Optimized query string for vector search.
    """
    explicit = needs.explicit
    implicit = needs.implicit

    prompt = QUERY_REWRITE_PROMPT.format(
        family_size=profile.family_size or "unknown",
        target_driver=profile.target_driver or "unknown",
        price_sensitivity=profile.price_sensitivity or "unknown",
        residence=profile.residence or "unknown",
        prize=explicit.prize or "not specified",
        vehicle_category=explicit.vehicle_category_bottom or "not specified",
        brand=explicit.brand or "not specified",
        powertrain=explicit.powertrain_type or "not specified",
        design_style=explicit.design_style or "not specified",
        seat_layout=explicit.seat_layout or "not specified",
        drive_type=explicit.drive_type or "not specified",
        family_friendliness=implicit.family_friendliness or "not specified",
        comfort_level=implicit.comfort_level or "not specified",
        safety=implicit.safety or "not specified",
        space=implicit.space or "not specified",
        energy_consumption=implicit.energy_consumption_level or "not specified",
    )

    try:
        response = llm.complete(prompt)
        rewritten = response.text.strip()
        logger.info(f"Query rewritten: '{rewritten[:100]}...'")
        return rewritten
    except Exception as e:
        logger.warning(f"Query rewrite failed: {e}, falling back to keyword query")
        return _build_fallback_query(explicit)


def _build_fallback_query(explicit) -> str:
    """Build a simple keyword query as fallback when LLM rewrite fails."""
    parts = []
    if explicit.vehicle_category_bottom:
        parts.append(explicit.vehicle_category_bottom)
    if explicit.powertrain_type:
        parts.append(explicit.powertrain_type)
    if explicit.brand:
        parts.append(explicit.brand)
    if explicit.design_style:
        parts.append(explicit.design_style)
    if explicit.prize:
        parts.append(f"价格{explicit.prize}")
    if explicit.seat_layout:
        parts.append(explicit.seat_layout)
    return " ".join(parts) if parts else "推荐一款适合的车型"
