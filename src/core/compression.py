"""
Context Compression & Specification Distillation Engine (src/core/compression.py).

Implements context compression and factual pruning for prompt contexts:
1. Sentence-level segmentation & factual density extraction.
2. Hallucination-grounded pruning of marketing hyperbole and unsupported promotional fluff.
3. Query & constraint-guided relevance scoring.
4. Token budget condensation to maximize verifiable technical specification density.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Subjective hype, marketing fluff, and ungrounded hyperbole patterns to prune
MARKETING_FLUFF_PATTERNS = [
    r"遥遥领先",
    r"地表最强",
    r"降维打击",
    r"天花板",
    r"无敌奢华",
    r"极致奢华",
    r"顶奢体验",
    r"秒杀同级",
    r"吊打同级",
    r"独孤求败",
    r"前无古人",
    r"买到就是赚到",
    r"全网最低价保证",
    r"终身无忧",
    r"绝对保值",
    r"永不衰减",
    r"零故障率",
]

# High-value verifiable factual specification patterns
FACTUAL_SPEC_PATTERNS = [
    r"\d+(?:\.\d+)?\s*(?:万|万元|元)",              # Price: 25.98万
    r"\d{3,4}\s*(?:km|公里|KM)",                    # Range: 702km
    r"\d+(?:\.\d+)?\s*(?:秒|s|S)\s*(?:破百|百公里加速)?", # 0-100: 3.8秒
    r"\d{3,4}\s*(?:mm|毫米|MM)",                    # Dimension: 5020mm
    r"\d+(?:\.\d+)?\s*(?:度|kWh|KWh|度电)",         # Battery: 100kWh
    r"(?:800V|400V|高压快充|超充)",                  # Voltage / Charging
    r"(?:双电机|单电机|四驱|后驱|前驱|两驱)",          # Powertrain / Drive
    r"(?:激光雷达|Orin-X|高通8295|8155|8255|NOA|L2\+)", # Smart hardware / ADAS
    r"(?:空气悬架|CDC|魔毯悬架|双叉臂|五连杆)",        # Chassis
    r"(?:5座|6座|7座|大五座|大六座)",                 # Seating
    r"(?:CLTC|WLTC|NEDC)",                          # Test cycle
]


class CompressedContext(BaseModel):
    """Result of context compression for a single vehicle snippet or text."""

    original_text: str
    compressed_text: str
    original_length: int
    compressed_length: int
    compression_ratio: float  # e.g. 0.45 = compressed is 45% of original
    preserved_facts: List[str] = Field(default_factory=list)
    pruned_sentences: List[str] = Field(default_factory=list)


class ContextCompressor:
    """
    Condenses retrieval contexts by pruning subjective marketing noise and
    prioritizing verifiable technical specifications aligned with query intent.
    """

    @classmethod
    def clean_marketing_fluff(cls, text: str) -> str:
        """Strip marketing superlatives and ungrounded hyperbole."""
        cleaned = text
        for pattern in MARKETING_FLUFF_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned)
        # Clean double spaces or messy punctuation
        cleaned = re.sub(r"[,，、\s]{2,}", "，", cleaned).strip("，, 。.；; \t\n")
        return cleaned

    @classmethod
    def split_sentences(cls, text: str) -> List[str]:
        """Split text into discrete spec sentences/clauses."""
        if not text:
            return []
        # Split on sentence boundaries, pipes, or semicolons
        raw_parts = re.split(r"[。；;\n\r|｜]+", text)
        sentences = [cls.clean_marketing_fluff(p.strip()) for p in raw_parts if p.strip()]
        return [s for s in sentences if s and len(s) >= 4]

    @classmethod
    def score_sentence(
        cls,
        sentence: str,
        query_text: str = "",
        active_constraints: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Score factual density and intent alignment for a single sentence.
        Higher score = more factual and more pertinent to query.
        """
        score = 0.0

        # Base factual signal: presence of concrete technical metrics
        for pattern in FACTUAL_SPEC_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                score += 1.5

        # Query keywords relevance boost
        if query_text:
            query_tokens = [t for t in re.split(r"[\s,，、/]+", query_text.lower()) if len(t) >= 2]
            s_lower = sentence.lower()
            for token in query_tokens:
                if token in s_lower:
                    score += 2.0

        # Active constraints alignment boost
        if active_constraints:
            for k, val in active_constraints.items():
                if val and str(val).lower() in sentence.lower():
                    score += 2.5

        # Penalty for purely vague or generic marketing statements with no numbers or specs
        has_any_spec = any(re.search(pat, sentence, re.IGNORECASE) for pat in FACTUAL_SPEC_PATTERNS)
        if not has_any_spec:
            score -= 1.0

        return score

    @classmethod
    def compress_snippet(
        cls,
        snippet: str,
        query_text: str = "",
        active_constraints: Optional[Dict[str, Any]] = None,
        max_length: int = 220,
    ) -> CompressedContext:
        """
        Compress a single vehicle text snippet into a concise, factual context.
        """
        if not snippet or len(snippet) <= max_length:
            cleaned = cls.clean_marketing_fluff(snippet or "")
            return CompressedContext(
                original_text=snippet or "",
                compressed_text=cleaned,
                original_length=len(snippet or ""),
                compressed_length=len(cleaned),
                compression_ratio=1.0 if not snippet else round(len(cleaned) / max(len(snippet), 1), 3),
                preserved_facts=[cleaned] if cleaned else [],
                pruned_sentences=[],
            )

        sentences = cls.split_sentences(snippet)
        if not sentences:
            return CompressedContext(
                original_text=snippet,
                compressed_text="",
                original_length=len(snippet),
                compressed_length=0,
                compression_ratio=0.0,
                preserved_facts=[],
                pruned_sentences=[],
            )

        scored_sentences = []
        for s in sentences:
            s_score = cls.score_sentence(s, query_text, active_constraints)
            scored_sentences.append((s_score, s))

        # Sort by score descending to prioritize most factual & relevant content
        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        chosen: List[str] = []
        pruned: List[str] = []
        current_len = 0

        for score, sentence in scored_sentences:
            if current_len + len(sentence) + 1 <= max_length or not chosen:
                chosen.append(sentence)
                current_len += len(sentence) + 1
            else:
                pruned.append(sentence)

        # Restore original reading flow order from the source text
        preserved = [s for s in sentences if s in chosen]
        compressed_text = "；".join(preserved)
        if compressed_text and not compressed_text.endswith("。"):
            compressed_text += "。"

        ratio = round(len(compressed_text) / max(len(snippet), 1), 3)

        return CompressedContext(
            original_text=snippet,
            compressed_text=compressed_text,
            original_length=len(snippet),
            compressed_length=len(compressed_text),
            compression_ratio=ratio,
            preserved_facts=preserved,
            pruned_sentences=pruned,
        )

    @classmethod
    def compress_matched_cars(
        cls,
        matched_cars: List[Dict[str, Any]],
        query_text: str = "",
        active_constraints: Optional[Dict[str, Any]] = None,
        max_length_per_car: int = 220,
    ) -> List[Dict[str, Any]]:
        """
        Compress text_snippets for all matched cars, attaching compression metadata.
        """
        compressed_cars = []
        for car in matched_cars:
            car_copy = dict(car)
            raw_snippet = car.get("text_snippet") or ""
            compressed = cls.compress_snippet(
                raw_snippet,
                query_text=query_text,
                active_constraints=active_constraints,
                max_length=max_length_per_car,
            )
            car_copy["text_snippet"] = compressed.compressed_text
            car_copy["compression_meta"] = {
                "original_len": compressed.original_length,
                "compressed_len": compressed.compressed_length,
                "ratio": compressed.compression_ratio,
                "pruned_count": len(compressed.pruned_sentences),
            }
            compressed_cars.append(car_copy)

        return compressed_cars
