"""
Core Terminology & Knowledge Graph Abstractions (src/core/terminology.py).

Provides clean architectural re-exports of automotive terminology services,
schemas, and knowledge graph facades for cross-module integration.
"""

from src.terminology.comparator import TechnologyComparator
from src.terminology.generic_registry import (
    GENERIC_AUTOMOTIVE_TECHNOLOGIES,
    GENERIC_TECHNOLOGY_REGISTRY,
)
from src.terminology.knowledge_graph import AutomotiveKnowledgeGraph
from src.terminology.registry import (
    ALL_AUTOMOTIVE_TECHNOLOGIES,
    OEM_TECHNOLOGIES,
    OEM_TECHNOLOGY_REGISTRY,
)
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
    "OEM_TECHNOLOGIES",
    "OEM_TECHNOLOGY_REGISTRY",
    "GENERIC_AUTOMOTIVE_TECHNOLOGIES",
    "GENERIC_TECHNOLOGY_REGISTRY",
    "ALL_AUTOMOTIVE_TECHNOLOGIES",
    "TerminologyResolver",
    "TechnologyComparator",
    "AutomotiveKnowledgeGraph",
]
