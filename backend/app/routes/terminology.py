"""
Terminology & Automotive Knowledge Graph API Routes (backend/app/routes/terminology.py).

Provides REST endpoints for querying OEM proprietary automotive terminology,
discovering cross-brand equivalents, comparing technologies, and querying tech stacks.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.core.terminology import (
    AutomotiveKnowledgeGraph,
    TechCategory,
)

router = APIRouter(prefix="/api/terminology", tags=["terminology"])


class ExtractTermsRequest(BaseModel):
    text: str


class CompareRequest(BaseModel):
    terms: List[str]


@router.get("/resolve")
def resolve_term(
    term: str = Query(..., description="Automotive term to resolve, e.g. 'V800', '云辇'"),
    context: str = Query("", description="Optional conversation context or brand hint"),
) -> Dict[str, Any]:
    """Resolve an automotive proprietary term with optional context."""
    kg = AutomotiveKnowledgeGraph.get_instance()
    res = kg.resolve_term(term, context=context)
    if not res:
        return {"found": False, "query": term, "message": "未找到匹配的车企专有名词"}

    return {
        "found": True,
        "query": res.query,
        "primary_entity": res.primary_entity.model_dump() if res.primary_entity else None,
        "category": res.category.value if res.category else None,
        "confidence": res.confidence,
        "disambiguation_needed": res.disambiguation_needed,
        "alternatives": [e.model_dump() for e in res.alternative_entities],
        "formal_explanation": res.formal_explanation,
        "conversational_pitch": res.conversational_pitch,
        "standard_labels": res.standard_labels,
        "suggested_query_expansions": res.suggested_query_expansions,
    }


@router.post("/extract")
def extract_terms(request: ExtractTermsRequest) -> Dict[str, Any]:
    """Extract all mentioned OEM proprietary technologies from text with offsets."""
    kg = AutomotiveKnowledgeGraph.get_instance()
    matched = kg.extract_terms(request.text)
    return {
        "count": len(matched),
        "terms": [
            {
                "matched_text": m.matched_text,
                "start_idx": m.start_idx,
                "end_idx": m.end_idx,
                "entity": m.entity.model_dump(),
                "confidence": m.confidence,
            }
            for m in matched
        ],
    }


@router.post("/compare")
def compare_technologies(request: CompareRequest) -> Dict[str, Any]:
    """Compare multiple proprietary automotive technologies across brands."""
    kg = AutomotiveKnowledgeGraph.get_instance()
    matrix = kg.compare_technologies(request.terms)
    return {
        "equivalence_domain": matrix.equivalence_domain.value if matrix.equivalence_domain else None,
        "domain_name": matrix.domain_chinese_name,
        "target_function": matrix.target_function,
        "compared_entities": [e.model_dump() for e in matrix.compared_entities],
        "dimensions": [
            {"dimension_name": d.dimension_name, "evaluations": d.tech_evaluations}
            for d in matrix.dimensions
        ],
        "key_differentiators": matrix.key_differentiators,
        "sales_guidance": matrix.sales_guidance,
        "summary_markdown": matrix.summary_markdown,
    }


@router.get("/equivalents/{term}")
def get_equivalents(term: str) -> Dict[str, Any]:
    """Retrieve competing equivalent technologies from other OEMs for a term."""
    kg = AutomotiveKnowledgeGraph.get_instance()
    rivals = kg.get_rival_technologies(term)
    return {
        "term": term,
        "rival_count": len(rivals),
        "rivals": [r.model_dump() for r in rivals],
    }


@router.get("/brand/{brand_key}")
def get_brand_tech_stack(brand_key: str) -> Dict[str, Any]:
    """Retrieve full proprietary technology stack for an OEM brand (e.g. 'byd', 'xiaomi', 'hima')."""
    kg = AutomotiveKnowledgeGraph.get_instance()
    entities = kg.get_brand_technologies(brand_key)
    return {
        "brand_key": brand_key,
        "count": len(entities),
        "technologies": [e.model_dump() for e in entities],
    }


@router.get("/categories")
def list_categories() -> Dict[str, Any]:
    """List all categories and registered technologies."""
    kg = AutomotiveKnowledgeGraph.get_instance()
    res = {}
    for cat in TechCategory:
        ents = kg.resolver.list_entities_by_category(cat)
        res[cat.value] = [e.model_dump() for e in ents]
    return {"categories": res}
