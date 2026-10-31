"""
Automotive Knowledge Graph Facade (src/terminology/knowledge_graph.py).

Unified knowledge graph service combining terminology resolution, cross-brand comparisons,
OEM tech stack graph queries, RAG query expansion, and conversational sales notes generation.
"""

import logging
from typing import Dict, List, Optional

from src.terminology.comparator import TechnologyComparator
from src.terminology.registry import (
    ALL_AUTOMOTIVE_TECHNOLOGIES,
    OEM_TECHNOLOGY_REGISTRY,
)
from src.terminology.resolver import TerminologyResolver
from src.terminology.schemas import (
    MatchedTerm,
    ResolutionResult,
    TechComparisonMatrix,
    TechnologyEntity,
)

logger = logging.getLogger(__name__)


class AutomotiveKnowledgeGraph:
    """
    Automotive Knowledge Graph for OEM Proprietary Technologies.
    """

    _instance: Optional["AutomotiveKnowledgeGraph"] = None

    def __init__(self):
        self.resolver = TerminologyResolver(OEM_TECHNOLOGY_REGISTRY)
        self.comparator = TechnologyComparator(self.resolver)
        self._brand_index: Dict[str, List[TechnologyEntity]] = {}
        self._vehicle_index: Dict[str, List[TechnologyEntity]] = {}
        self._build_graph_indices()

    @classmethod
    def get_instance(cls) -> "AutomotiveKnowledgeGraph":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _build_graph_indices(self) -> None:
        """Construct multi-directional relational graph indices."""
        for entity in ALL_AUTOMOTIVE_TECHNOLOGIES:
            # Brand index
            b_key = entity.brand_key.lower()
            if b_key not in self._brand_index:
                self._brand_index[b_key] = []
            self._brand_index[b_key].append(entity)

            # Vehicle index
            for veh in entity.representative_vehicles:
                veh_clean = veh.lower().replace(" ", "")
                if veh_clean not in self._vehicle_index:
                    self._vehicle_index[veh_clean] = []
                self._vehicle_index[veh_clean].append(entity)

    # -------------------------------------------------------------------------
    # Core Terminology Resolution & Comparison
    # -------------------------------------------------------------------------
    def resolve_term(self, term: str, context: str = "") -> Optional[ResolutionResult]:
        """Resolve a specific automotive term with optional context."""
        return self.resolver.resolve(term, context)

    def extract_terms(self, text: str, context: str = "") -> List[MatchedTerm]:
        """Extract all proprietary terms mentioned in text with optional context."""
        return self.resolver.extract_terms(text, context=context)

    def compare_technologies(self, terms: List[str]) -> TechComparisonMatrix:
        """Compare multiple proprietary technologies across brands."""
        return self.comparator.compare(terms)

    def get_rival_technologies(self, term_or_id: str) -> List[TechnologyEntity]:
        """Find rival competing technologies from other OEMs."""
        return self.comparator.get_equivalents(term_or_id)

    # -------------------------------------------------------------------------
    # Graph Traversal Methods
    # -------------------------------------------------------------------------
    def get_brand_technologies(self, brand_name_or_key: str) -> List[TechnologyEntity]:
        """Retrieve all proprietary technologies for a given OEM brand."""
        b_clean = brand_name_or_key.lower().strip()
        # Check direct brand key
        if b_clean in self._brand_index:
            return self._brand_index[b_clean]

        # Check brand name substring
        for key, entities in self._brand_index.items():
            if any(b_clean in e.brand.lower() for e in entities):
                return entities

        return []

    def get_vehicle_technologies(self, vehicle_name: str) -> List[TechnologyEntity]:
        """Retrieve all proprietary technologies equipped on a specific vehicle model."""
        v_clean = vehicle_name.lower().replace(" ", "")
        if not v_clean:
            return []
        matched: List[TechnologyEntity] = []
        for veh_key, entities in self._vehicle_index.items():
            if (len(v_clean) >= 2 and (veh_key in v_clean or v_clean in veh_key)) or v_clean == veh_key:
                for ent in entities:
                    if ent not in matched:
                        matched.append(ent)
        return matched

    def get_synergistic_technologies(self, entity_id: str) -> List[TechnologyEntity]:
        """
        Find complementary/synergistic technologies within the same brand that frequently
        co-occur on flagship vehicles (e.g. 易四方 + 云辇 on 仰望; 摩德纳 + V8s + 800V on 小米SU7).
        """
        entity = self.resolver.get_entity(entity_id)
        if not entity:
            return []

        brand_entities = self.get_brand_technologies(entity.brand_key)
        # Find entities that share representative vehicles
        entity_vehicles = set(entity.representative_vehicles)
        synergistic: List[TechnologyEntity] = []

        for other in brand_entities:
            if other.id != entity.id:
                if any(v in entity_vehicles for v in other.representative_vehicles):
                    synergistic.append(other)

        return synergistic

    # -------------------------------------------------------------------------
    # RAG Pipeline Enrichment
    # -------------------------------------------------------------------------
    def enrich_rag_query(self, query: str) -> str:
        """
        Enrich a natural language user query with formal OEM technical labels and synonyms.
        Example: '我想了解V800架构的车' -> '我想了解V800架构的车 800V高压架构 全栈碳化硅SiC 871V真800V 小米SU7'
        """
        if not query:
            return query

        matched_terms = self.extract_terms(query)
        if not matched_terms:
            return query

        expanded_tokens: List[str] = [query]
        seen_entity_ids = set()
        for m in matched_terms:
            ent = m.entity
            if ent.id in seen_entity_ids:
                continue
            seen_entity_ids.add(ent.id)
            # Add canonical name
            expanded_tokens.append(ent.name)
            # Add standard labels
            expanded_tokens.extend(ent.standard_labels[:3])
            # Add top models
            expanded_tokens.extend(ent.representative_vehicles[:2])

        # If user query indicates a comparison, also inject equivalent competitor terms!
        if any(w in query for w in ["对比", "相比", "还是", "vs", "区别", "哪个好"]):
            for m in matched_terms:
                rivals = self.get_rival_technologies(m.entity.id)
                for r in rivals[:2]:
                    expanded_tokens.append(r.name)

        return " ".join(dict.fromkeys(expanded_tokens))

    def has_potential_terms(self, text: str) -> bool:
        """Fast prefilter check (< 0.05ms) to determine if text could mention proprietary terms."""
        return self.resolver.has_potential_terms(text)

    # -------------------------------------------------------------------------
    # Agent Sales Dialog & System Notes Generation
    # -------------------------------------------------------------------------
    def generate_system_sales_note(self, text: str, context: str = "") -> Optional[str]:
        """
        Generate a structured tactical sales note when customer mentions proprietary terms.
        Features a microsecond fast-path prefilter to bypass extraction on general conversation.
        """
        if not text or len(text.strip()) < 2:
            return None

        if not self.has_potential_terms(text):
            return None

        matched_terms = self.extract_terms(text, context=context)
        if not matched_terms:
            return None

        # De-duplicate terms by entity ID to prevent repeated advice blocks
        seen_entity_ids = set()
        deduped_terms: List[MatchedTerm] = []
        for m in matched_terms:
            if m.entity.id not in seen_entity_ids:
                seen_entity_ids.add(m.entity.id)
                deduped_terms.append(m)

        # Build note
        lines: List[str] = ["[系统专有名词解析与导购策略提示]:"]
        for m in deduped_terms:
            ent = m.entity
            lines.append(
                f"• 检测到客户提及【{ent.name}】（{ent.brand} | {ent.category.value}）："
            )
            lines.append(f"  - 核心定义：{ent.summary}")
            if ent.sales_talking_points:
                lines.append(f"  - 导购要点：{ent.sales_talking_points[0]}")

            # Check if rivals exist
            rivals = self.get_rival_technologies(ent.id)
            if rivals:
                rival_names = "、".join([r.name for r in rivals[:3]])
                lines.append(f"  - 行业对标技术：{rival_names}（如客户对比，请客观讲解各自侧重）")

        lines.append("请在回复中保持专业、客观且通俗易懂，准确解答客户对该项专有技术的疑问。")
        return "\n".join(lines)
