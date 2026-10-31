"""
Automotive OEM Proprietary Terminology Resolver (src/terminology/resolver.py).

Implements:
1. Token normalization & inverted alias index lookup
2. Fuzzy matching and typo tolerance (e.g. '云撵' -> '云辇', '图灵底盘' -> '途灵智能底盘')
3. Brand context-aware disambiguation (e.g. '800V' + '小米' -> Xiaomi V800; '800V' + '问界' -> Huawei Whale 800V)
4. Full text term extraction with offset detection
5. RAG query expansion and conversational explanations
"""

import difflib
import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from src.terminology.registry import OEM_TECHNOLOGY_REGISTRY
from src.terminology.schemas import (
    MatchedTerm,
    ResolutionResult,
    TechCategory,
    TechnologyEntity,
)

logger = logging.getLogger(__name__)


def _normalize_token(text: str) -> str:
    """Normalize term for comparison: lowercase, strip punctuation and whitespace."""
    if not text:
        return ""
    # Remove whitespace, hyphens, underscores, dots, and common punctuation
    lowered = text.lower().strip()
    return re.sub(r"[\s\-_·\.,，。/（）\(\)]+", "", lowered)


# Common brand keyword hints for context-aware disambiguation
BRAND_CONTEXT_HINTS: Dict[str, Set[str]] = {
    "byd": {"比亚迪", "byd", "仰望", "腾势", "方程豹", "汉", "唐", "宋", "秦", "海豹", "海豚", "元", "豹5", "u8", "u9", "z9"},
    "xiaomi": {"小米", "xiaomi", "su7", "su7max", "su7ultra", "雷军", "ultra"},
    "hima": {"华为", "huawei", "鸿蒙", "鸿蒙智行", "问界", "智界", "享界", "尊界", "m5", "m7", "m9", "s7", "r7", "s9", "s800", "阿维塔"},
    "tesla": {"特斯拉", "tesla", "马斯克", "modely", "model3", "models", "modelx", "cybertruck"},
    "li_auto": {"理想", "liauto", "l6", "l7", "l8", "l9", "mega", "李想"},
    "zeekr": {"极氪", "zeekr", "吉利", "geely", "001", "007", "009", "7x", "mix", "极越", "领克", "银河"},
    "nio": {"蔚来", "nio", "李斌", "es6", "et5", "et5t", "es8", "et7", "et9", "ec6", "乐道", "l60"},
    "xpeng": {"小鹏", "xpeng", "何小鹏", "g6", "g9", "x9", "p7", "p7+", "mona", "m03"},
    "im": {"智己", "immotors", "im", "上汽", "l6", "ls6", "l7", "ls7"},
    "gac_aion": {"广汽", "埃安", "aion", "昊铂", "hyper", "广汽埃安"},
    "gwm": {"长城", "gwm", "哈弗", "坦克", "魏牌", "欧拉", "蓝山", "猛龙"},
    "chery": {"奇瑞", "chery", "星途", "捷途", "风云"},
    "porsche": {"保时捷", "porsche", "taycan", "macan", "panamera", "911"},
    "mercedes": {"奔驰", "mercedes", "benz", "amg", "eva", "mma", "eqs", "eqe", "4matic"},
    "bmw": {"宝马", "bmw", "neueklasse", "新世代", "i3", "i4", "i5", "i7", "ix3", "ix"},
    "generic": {"通用", "行业标准", "汽车技术", "行业技术", "generic", "通用技术"},
}


class TerminologyResolver:
    """
    Dedicated Automotive OEM Proprietary & Generic Technical Terminology Resolver.
    """

    def __init__(self, registry: Optional[Dict[str, TechnologyEntity]] = None):
        self.registry: Dict[str, TechnologyEntity] = registry or OEM_TECHNOLOGY_REGISTRY
        self.alias_to_entity: Dict[str, TechnologyEntity] = {}
        self.normalized_alias_index: Dict[str, List[TechnologyEntity]] = {}
        self._raw_alias_to_entity: Dict[str, TechnologyEntity] = {}
        self._fuzzy_candidates: List[Tuple[str, TechnologyEntity, int, Set[str], str]] = []
        self._alias_pattern: Optional[re.Pattern] = None
        self._code_pattern = re.compile(
            r"(?<![a-zA-Z0-9])(V800|800V|4680|CTB|CTC|ADS|DiSus|FSD|SEA|SkyOS|XNGP|Hi4|Hi4-T|Hi4T|CDM|C-DM|PASM|PSCM|EVA|MMA|CDC|E2E|BEV|NOA|LFP|4C|5C|EREV|PHEV|4WS|BaaS)(?![a-zA-Z0-9])",
            re.IGNORECASE,
        )
        self._build_indices()

    def _build_indices(self) -> None:
        """Construct inverted alias index, normalized lookup map, and pre-compiled search patterns."""
        all_aliases: List[Tuple[str, TechnologyEntity]] = []
        for entity in self.registry.values():
            # Canonical name
            canon_norm = _normalize_token(entity.name)
            self._register_alias(canon_norm, entity)
            all_aliases.append((entity.name, entity))

            # English name
            eng_norm = _normalize_token(entity.english_name)
            self._register_alias(eng_norm, entity)
            all_aliases.append((entity.english_name, entity))

            # Aliases
            for alias in entity.aliases:
                alias_norm = _normalize_token(alias)
                self._register_alias(alias_norm, entity)
                all_aliases.append((alias, entity))

            # Sub-variants
            for var_key in entity.sub_variants.keys():
                var_norm = _normalize_token(var_key)
                self._register_alias(var_norm, entity)
                all_aliases.append((var_key, entity))

        # Build raw alias mapping and precompiled regex
        unique_aliases: Dict[str, TechnologyEntity] = {}
        for a, ent in all_aliases:
            a_clean = a.strip()
            if len(a_clean) >= 2 and a_clean not in unique_aliases:
                unique_aliases[a_clean] = ent
                self._raw_alias_to_entity[a_clean.lower()] = ent

        sorted_aliases = sorted(unique_aliases.keys(), key=len, reverse=True)
        pattern_parts = []
        for a in sorted_aliases:
            esc = re.escape(a)
            if re.match(r"^[a-zA-Z0-9\-_]+$", a):
                pattern_parts.append(r"(?<![a-zA-Z0-9])" + esc + r"(?![a-zA-Z0-9])")
            else:
                pattern_parts.append(esc)

        self._alias_pattern = re.compile("|".join(pattern_parts), re.IGNORECASE)

        # Precompute fuzzy candidates for distinctive Chinese technical terms (length 3-8)
        self._fuzzy_candidates = []
        seen_fuzzy = set()
        for ent in self.registry.values():
            for a in [ent.name] + ent.aliases:
                a_clean = a.strip()
                if 3 <= len(a_clean) <= 8 and not re.match(r"^[a-zA-Z0-9]+$", a_clean):
                    if a_clean not in seen_fuzzy:
                        seen_fuzzy.add(a_clean)
                        self._fuzzy_candidates.append(
                            (a_clean, ent, len(a_clean), set(a_clean.lower()), a_clean.lower())
                        )

    def _register_alias(self, normalized_alias: str, entity: TechnologyEntity) -> None:
        if not normalized_alias:
            return
        if normalized_alias not in self.normalized_alias_index:
            self.normalized_alias_index[normalized_alias] = []
        if entity not in self.normalized_alias_index[normalized_alias]:
            self.normalized_alias_index[normalized_alias].append(entity)

    def has_potential_terms(self, text: str) -> bool:
        """
        Ultra-fast prefilter check (< 0.05ms) to determine if arbitrary text
        potentially mentions any registered technology.
        """
        if not text or len(text.strip()) < 2:
            return False
        if self._alias_pattern and self._alias_pattern.search(text):
            return True
        text_lower = text.lower()
        text_chars = set(text_lower)
        text_len = len(text)
        for _, _, a_len, cand_chars, _ in self._fuzzy_candidates:
            if a_len <= text_len and len(text_chars & cand_chars) >= max(2, a_len - 1):
                return True
        return False

    def resolve(
        self,
        term: str,
        context: str = "",
        fuzzy_threshold: float = 0.70,
    ) -> Optional[ResolutionResult]:
        """
        Resolve a proprietary terminology string into a canonical TechnologyEntity.

        Args:
            term: The input terminology query (e.g. 'V800', '云辇系统', '途灵底盘', '4680').
            context: Optional conversational history or surrounding sentence to disambiguate.
            fuzzy_threshold: Minimum similarity ratio for fuzzy matching.

        Returns:
            ResolutionResult or None if no matching technology found.
        """
        if not term or not term.strip():
            return None

        clean_term = term.strip()
        norm_term = _normalize_token(clean_term)

        matched_candidates: List[TechnologyEntity] = []
        confidence = 1.0

        # 1. Exact Normalized Lookup
        if norm_term in self.normalized_alias_index:
            matched_candidates = list(self.normalized_alias_index[norm_term])
            confidence = 1.0

        # 2. Substring matching in normalized aliases (if term contains or is contained)
        if not matched_candidates:
            substring_matches: Set[str] = set()
            for alias_key, entities in self.normalized_alias_index.items():
                if len(alias_key) >= 2 and (alias_key in norm_term or norm_term in alias_key):
                    for ent in entities:
                        if ent.id not in substring_matches:
                            substring_matches.add(ent.id)
                            matched_candidates.append(ent)
            if matched_candidates:
                confidence = 0.85

        # 3. Fuzzy matching via string similarity
        if not matched_candidates and len(norm_term) >= 2:
            scored_fuzzy: List[Tuple[float, TechnologyEntity]] = []
            for alias_key, entities in self.normalized_alias_index.items():
                if len(alias_key) < 2:
                    continue
                ratio = difflib.SequenceMatcher(None, norm_term, alias_key).ratio()
                if ratio >= fuzzy_threshold:
                    for ent in entities:
                        scored_fuzzy.append((ratio, ent))

            if scored_fuzzy:
                scored_fuzzy.sort(key=lambda x: x[0], reverse=True)
                top_ratio = scored_fuzzy[0][0]
                best_entities: List[TechnologyEntity] = []
                for r, ent in scored_fuzzy:
                    if r >= top_ratio - 0.05 and ent not in best_entities:
                        best_entities.append(ent)
                matched_candidates = best_entities
                confidence = round(top_ratio, 2)

        if not matched_candidates:
            return None

        # 4. Context-Aware Disambiguation
        # Include clean_term in disambiguation context so hints like '华为的800V' or '小米的CTB' resolve correctly
        combined_context = f"{clean_term} {context}".strip()
        primary_entity, alternatives = self._disambiguate_candidates(
            matched_candidates, combined_context
        )

        # Build formal explanation and conversational pitch
        formal_explanation = self._build_formal_explanation(primary_entity)
        conversational_pitch = primary_entity.summary

        # Build suggested query expansions
        suggested_expansions = self._build_query_expansions(primary_entity)

        return ResolutionResult(
            query=clean_term,
            primary_entity=primary_entity,
            all_matched_entities=matched_candidates,
            category=primary_entity.category,
            confidence=confidence,
            disambiguation_needed=len(matched_candidates) > 1,
            alternative_entities=alternatives,
            formal_explanation=formal_explanation,
            conversational_pitch=conversational_pitch,
            standard_labels=list(primary_entity.standard_labels),
            suggested_query_expansions=suggested_expansions,
        )

    def _disambiguate_candidates(
        self,
        candidates: List[TechnologyEntity],
        context: str,
        match_idx: Optional[int] = None,
    ) -> Tuple[TechnologyEntity, List[TechnologyEntity]]:
        """Disambiguate candidates using brand context keywords and proximity weighting."""
        if len(candidates) <= 1:
            return (candidates[0], []) if candidates else (None, [])

        context_lower = context.lower()
        norm_context = _normalize_token(context)
        scored_candidates: List[Tuple[float, TechnologyEntity]] = []

        for cand in candidates:
            # Baseline priority: generic engineering concepts take precedence in zero-context queries,
            # while brand-specific context weighting boosts OEM proprietary technologies
            score = 1.0 if cand.is_generic else 0.0
            brand_hints = BRAND_CONTEXT_HINTS.get(cand.brand_key, set())
            if cand.is_generic:
                all_hints = list(brand_hints)
            else:
                all_hints = list(brand_hints) + cand.representative_vehicles + [cand.brand, cand.name]

            for hint in all_hints:
                if not hint:
                    continue
                hint_lower = hint.lower()
                norm_hint = _normalize_token(hint)

                if match_idx is not None:
                    # Proximity-weighted scoring
                    start = 0
                    while True:
                        pos = context_lower.find(hint_lower, start)
                        if pos == -1:
                            break
                        dist = abs(pos - match_idx)
                        score += 15.0 / (1.0 + dist * 0.15)
                        start = pos + len(hint_lower)
                else:
                    # Global context scoring
                    if hint_lower in context_lower or norm_hint in norm_context:
                        score += 3.0

            scored_candidates.append((score, cand))

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        primary = scored_candidates[0][1]
        alternatives = [item[1] for item in scored_candidates[1:]]
        return primary, alternatives

    def extract_terms(self, text: str, context: str = "") -> List[MatchedTerm]:
        """
        Extract all OEM proprietary terms mentioned in arbitrary text with exact spans.
        Supports exact alias matching, regex codes, and fuzzy typo tolerance.

        Args:
            text: Customer input or sentence, e.g.
                  '我想了解下小米的V800电车架构和比亚迪云辇系统还有华为途灵底盘'
            context: Optional surrounding conversation context used to disambiguate ambiguous terms.

        Returns:
            List of non-overlapping MatchedTerm objects sorted by start_idx.
        """
        if not text or not self.has_potential_terms(text):
            return []

        # Find all raw alias matches in the text: (start, end, matched_text, entity, alias, conf, match_type)
        raw_matches: List[Tuple[int, int, str, TechnologyEntity, str, float, str]] = []

        # 1. Exact alias matching via precompiled regex automaton (O(len(text)) C-speed pass)
        if self._alias_pattern:
            for m in self._alias_pattern.finditer(text):
                tok = m.group(0)
                norm = _normalize_token(tok)
                candidates = self.normalized_alias_index.get(norm, [])
                chosen_entity = candidates[0] if candidates else self._raw_alias_to_entity.get(tok.lower(), None)
                if chosen_entity:
                    raw_matches.append(
                        (m.start(), m.end(), tok, chosen_entity, tok, 1.0, "exact_alias")
                    )

        # 2. Fallback regex for technical codes if any span not covered
        exact_spans = {(m[0], m[1]) for m in raw_matches}
        resolve_ctx = f"{text} {context}".strip() if context else text
        for match in self._code_pattern.finditer(text):
            if not any(match.start() >= s and match.end() <= e for s, e in exact_spans):
                tok = match.group(0)
                res = self.resolve(tok, context=resolve_ctx)
                if res and res.primary_entity:
                    raw_matches.append(
                        (match.start(), match.end(), tok, res.primary_entity, tok, res.confidence, "regex_code")
                    )

        exact_spans = {(m[0], m[1]) for m in raw_matches}

        # 3. Fuzzy typo extraction for distinctive Chinese technical terms (length 3-8)
        # Accelerated via precomputed candidate character-set filters (< 0.05ms)
        text_len = len(text)
        if text_len >= 3 and len(raw_matches) < text_len // 2:
            lowered_text = text.lower()
            text_chars = set(lowered_text)
            for alias, entity, a_len, cand_chars, cand_lower in self._fuzzy_candidates:
                if a_len > text_len:
                    continue
                min_common = max(2, a_len - 1)
                if len(text_chars & cand_chars) < min_common:
                    continue
                for i in range(text_len - a_len + 1):
                    if any(not (i + a_len <= s or i >= e) for s, e in exact_spans):
                        continue
                    window = lowered_text[i : i + a_len]
                    if len(set(window) & cand_chars) < min_common:
                        continue
                    ratio = difflib.SequenceMatcher(None, window, cand_lower).ratio()
                    if ratio >= 0.75:
                        raw_matches.append(
                            (i, i + a_len, text[i : i + a_len], entity, alias, round(ratio, 2), "fuzzy_alias")
                        )

        # 4. De-duplicate and resolve overlapping spans (greedy: start_idx, then longest span, then highest confidence)
        raw_matches.sort(key=lambda m: (m[0], -(m[1] - m[0]), -m[5]))

        filtered_matches: List[MatchedTerm] = []
        last_end = -1
        seen_entities: Set[str] = set()

        for start_idx, end_idx, matched_str, entity, alias, conf, m_type in raw_matches:
            if start_idx >= last_end:
                # Disambiguate entity using local context with proximity weighting
                candidates = self.normalized_alias_index.get(_normalize_token(matched_str), [entity])
                combined_context = f"{text} {context}".strip() if context else text
                chosen_entity, _ = self._disambiguate_candidates(candidates, combined_context, match_idx=start_idx)

                filtered_matches.append(
                    MatchedTerm(
                        matched_text=matched_str,
                        start_idx=start_idx,
                        end_idx=end_idx,
                        entity=chosen_entity,
                        match_type=m_type,
                        confidence=conf,
                        matched_alias=alias,
                    )
                )
                last_end = end_idx
                seen_entities.add(chosen_entity.id)

        return filtered_matches

    def _build_formal_explanation(self, entity: TechnologyEntity) -> str:
        """Build technical and customer-facing explanation string."""
        principles_str = "；".join(entity.technical_principles[:2]) if entity.technical_principles else "高度集成的软硬件一体化创新"
        advantages_str = "；".join(entity.advantages[:2]) if entity.advantages else "提升行车性能与安全"
        models_str = "、".join(entity.representative_vehicles[:4]) if entity.representative_vehicles else "品牌旗下主力新能源车型"

        return (
            f"【{entity.name}】（所属车企：{entity.brand} | 类别：{entity.category.value}）：\n"
            f"• 核心定位：{entity.summary}\n"
            f"• 技术原理：{principles_str}。\n"
            f"• 核心优势：{advantages_str}。\n"
            f"• 搭载代表车型：{models_str}。"
        )

    def _build_query_expansions(self, entity: TechnologyEntity) -> List[str]:
        """Build search expansion keywords for RAG retrieval."""
        expansions = [entity.name]
        expansions.extend(entity.standard_labels)
        expansions.extend(entity.representative_vehicles[:3])
        return list(dict.fromkeys(expansions))

    def explain_term(self, term: str, context: str = "") -> str:
        """Convenience method returning conversational explanation for a term."""
        res = self.resolve(term, context)
        if not res or not res.primary_entity:
            return f"暂未收录关于专有名词【{term}】的解析数据。"
        return res.formal_explanation

    def expand_for_rag(self, query_text: str) -> List[str]:
        """
        Extract terms and return list of formal technical keywords to enrich RAG search queries.
        """
        matched = self.extract_terms(query_text)
        if not matched:
            return []

        expanded_labels: List[str] = []
        for m in matched:
            expanded_labels.append(m.entity.name)
            expanded_labels.extend(m.entity.standard_labels[:3])
            # Add top representative models
            expanded_labels.extend(m.entity.representative_vehicles[:2])

        return list(dict.fromkeys(expanded_labels))

    def list_entities_by_category(self, category: TechCategory) -> List[TechnologyEntity]:
        """Filter registered technologies by category."""
        return [e for e in self.registry.values() if e.category == category]

    def list_entities_by_brand(self, brand_key: str) -> List[TechnologyEntity]:
        """Filter registered technologies by brand key."""
        b_clean = brand_key.lower().strip()
        return [e for e in self.registry.values() if e.brand_key == b_clean]

    def get_entity(self, entity_id: str) -> Optional[TechnologyEntity]:
        """Retrieve technology entity by canonical ID."""
        return self.registry.get(entity_id)
