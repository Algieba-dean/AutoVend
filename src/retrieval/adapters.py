"""
Adapters between the retrieval layer and the Agent/API protocol.

The Agent receives candidate vehicles as `AgentInput.retrieved_cars`, a plain
list of dicts. The frontend (`Chat.js`) reads the same shape straight off the
API response. That shape was originally produced by the LlamaIndex query
engine's `format_retrieval_results`, so keeping it byte-compatible means the
retrieval backend can be swapped without touching the agent or the UI.

Shape (one dict per car):
    {
        "car_model":    str,
        "score":        float | None,   # 0-1, higher is better
        "metadata":     dict,           # structured labels
        "text_snippet": str,            # <= 300 chars of the source document
    }
"""

from typing import Any, Dict, List, Optional

SNIPPET_LIMIT = 300


def search_response_to_cars(
    response: Optional[Any],
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Convert a `src.models.query.SearchResponse` into the agent/API car list.

    Accepts None (retrieval failed or was skipped) and returns an empty list,
    so callers do not need to special-case failures.
    """
    if response is None or not getattr(response, "results", None):
        return []

    results = response.results[:limit] if limit else response.results
    return [_search_result_to_car(r) for r in results]


def hybrid_result_to_cars(
    result: Optional[Any],
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Convert a `HybridPipelineResult` into the agent/API car list."""
    if result is None:
        return []
    return search_response_to_cars(getattr(result, "search_response", None), limit)


def _search_result_to_car(result: Any) -> Dict[str, Any]:
    vehicle = result.vehicle
    precise = vehicle.precise_labels
    ambiguous = vehicle.ambiguous_labels

    # Only surface labels that are actually populated — a metadata dict full of
    # nulls makes the recommendation prompt noisier without adding information.
    metadata = {
        k: v
        for k, v in {
            "car_model": vehicle.car_model,
            "brand": precise.brand,
            "price": precise.prize,
            "category": precise.vehicle_category_bottom,
            "powertrain_type": precise.powertrain_type,
            "size": ambiguous.size,
            "family_friendliness": ambiguous.family_friendliness,
            "comfort_level": ambiguous.comfort_level,
        }.items()
        if v is not None
    }

    text_snippet = (vehicle.key_details.key_details or "")[:SNIPPET_LIMIT]

    return {
        "car_model": vehicle.car_model,
        "score": round(float(result.score.overall_score), 4),
        "metadata": metadata,
        "text_snippet": text_snippet,
    }


def needs_to_query_text(explicit: Any, implicit: Optional[Any] = None) -> str:
    """
    Build a rich natural-language retrieval query from the agent's explicit & implicit needs.

    Emits label values verbatim to match rule engine vocabulary, and includes
    key implicit preference dimensions for enhanced dense vector semantic retrieval.
    """
    parts: List[str] = []
    
    # Explicit core attributes
    for attr in (
        "vehicle_category_bottom",
        "powertrain_type",
        "drive_type",
        "seat_layout",
        "design_style",
        "autonomous_driving_level",
        "electric_range",
    ):
        value = getattr(explicit, attr, None) if explicit else None
        if value:
            parts.append(str(value))

    brand = getattr(explicit, "brand", None) if explicit else None
    if brand:
        parts.append(str(brand))

    prize = getattr(explicit, "prize", None) if explicit else None
    if prize:
        parts.append(str(prize))

    # Implicit semantic preferences (boost dense vector recall for comfort, smartness, space)
    if implicit:
        for imp_attr in ("comfort_level", "smartness", "space", "family_friendliness"):
            imp_val = getattr(implicit, imp_attr, None)
            if imp_val and str(imp_val).strip():
                parts.append(f"{imp_attr}:{imp_val}")

    if not parts:
        return "recommend a good vehicle"
    return " ".join(parts)
