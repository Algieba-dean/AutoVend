"""
Automotive OEM Proprietary Terminology & Knowledge Graph Package.

Curates and resolves proprietary automotive technologies across Chinese and global OEMs,
providing alias matching, fuzzy resolution, cross-brand technology equivalence,
RAG query expansion, and conversational sales guidance.
"""

from src.terminology.comparator import TechnologyComparator
from src.terminology.knowledge_graph import AutomotiveKnowledgeGraph
from src.terminology.registry import OEM_TECHNOLOGY_REGISTRY
from src.terminology.resolver import TerminologyResolver
from src.terminology.schemas import (
    EquivalenceDomain,
    MatchedTerm,
    ResolutionResult,
    TechCategory,
    TechComparisonDimension,
    TechComparisonMatrix,
    TechMaturity,
    TechnologyEntity,
)

__all__ = [
    "TechCategory",
    "TechMaturity",
    "EquivalenceDomain",
    "TechnologyEntity",
    "MatchedTerm",
    "ResolutionResult",
    "TechComparisonDimension",
    "TechComparisonMatrix",
    "OEM_TECHNOLOGY_REGISTRY",
    "TerminologyResolver",
    "TechnologyComparator",
    "AutomotiveKnowledgeGraph",
]
