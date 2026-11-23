"""
Context Compression & Specification Distillation Engine (src/core/compression.py).

Implements semantic and information-theoretic context compression for prompt contexts:
1. Sentence-level segmentation preserving Markdown tables.
2. Semantic relevance scoring via dense embeddings (pluggable `embed_fn`) with
   character-bigram + token TF-IDF cosine similarity fallback.
3. Normalized factual information-density scoring (numeric-unit pairs, spec tokens,
   and tabular structure) combined via convex weighting.
4. Optional LLM-backed abstractive spec distillation (`compress_with_llm`).
"""

import logging
import math
import re
from collections import Counter
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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

FACTUAL_SPEC_PATTERNS = [
    r"\d+(?:\.\d+)?\s*(?:万|万元|元)",
    r"\d{3,4}\s*(?:km|公里|KM)",
    r"\d+(?:\.\d+)?\s*(?:秒|s|S)\s*(?:破百|百公里加速)?",
    r"\d{3,4}\s*(?:mm|毫米|MM)",
    r"\d+(?:\.\d+)?\s*(?:度|kWh|KWh|度电)",
    r"(?:800V|400V|高压快充|超充)",
    r"(?:双电机|单电机|四驱|后驱|前驱|两驱)",
    r"(?:激光雷达|Orin-X|高通8295|8155|8255|NOA|L2\+)",
    r"(?:空气悬架|CDC|魔毯悬架|双叉臂|五连杆)",
    r"(?:5座|6座|7座|大五座|大六座)",
    r"(?:CLTC|WLTC|NEDC)",
]

_COMPILED_SPEC_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FACTUAL_SPEC_PATTERNS]
_TABLE_SEP_RE = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+$")
_TOKEN_RE = re.compile(r"[a-z0-9\.\-]+|[\u4e00-\u9fff]")


def _text_to_ngram_vector(text: str) -> Counter:
    """Build a normalized unigram + character-bigram frequency vector for cosine similarity."""
    cleaned = re.sub(r"\s+", " ", text.lower()).strip()
    tokens = _TOKEN_RE.findall(cleaned)
    grams: List[str] = list(tokens)
    for i in range(len(tokens) - 1):
        grams.append(f"{tokens[i]}_{tokens[i + 1]}")
    return Counter(grams)


def _sparse_cosine_similarity(a: str, b: str) -> float:
    """Compute cosine similarity in [0, 1] over unigram+bigram vectors."""
    if not a or not b:
        return 0.0
    va = _text_to_ngram_vector(a)
    vb = _text_to_ngram_vector(b)
    if not va or not vb:
        return 0.0
    common = set(va.keys()) & set(vb.keys())
    dot = sum(va[k] * vb[k] for k in common)
    if dot <= 0:
        return 0.0
    norm_a = math.sqrt(sum(v * v for v in va.values()))
    norm_b = math.sqrt(sum(v * v for v in vb.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(max(0.0, min(1.0, dot / (norm_a * norm_b))))


class CompressedContext(BaseModel):
    """Result of context compression for a single vehicle snippet or text."""

    original_text: str
    compressed_text: str
    original_length: int
    compressed_length: int
    compression_ratio: float
    preserved_facts: List[str] = Field(default_factory=list)
    pruned_sentences: List[str] = Field(default_factory=list)


class ContextCompressor:
    """
    Condenses retrieval contexts by normalizing promotional noise and prioritizing
    semantically relevant, high-information-density technical specifications.
    """

    _embed_fn: Optional[Callable[[List[str]], np.ndarray]] = None

    @classmethod
    def set_embedder(cls, embed_fn: Optional[Callable[[List[str]], np.ndarray]]) -> None:
        """Register a dense embedding callable `(texts) -> ndarray[N, D]` for semantic scoring."""
        cls._embed_fn = embed_fn

    @classmethod
    def clean_marketing_fluff(cls, text: str, query_text: str = "") -> str:
        """
        Normalize subjective promotional exaggerations while preserving grammatical integrity
        and Markdown table separator rows.
        """
        if not text:
            return ""

        trimmed = text.strip()
        if _TABLE_SEP_RE.match(trimmed):
            return trimmed

        query_lower = query_text.lower()
        active_query_fluff = {
            p for p in MARKETING_FLUFF_PATTERNS if p.lower() in query_lower
        }

        cleaned = text
        for pattern in MARKETING_FLUFF_PATTERNS:
            if pattern in active_query_fluff:
                continue
            regex = (
                rf"(?:被[^\s，。、]{{1,10}}(?:誉为|称为|评为|冠以)|堪称|号称|自诩)?\s*"
                rf"{pattern}\s*"
                rf"(?:的|之称|级别|体验)?\s*(?:同级)?\s*(?:于[^\s，。、]{{1,10}})?(?:[!！，,。]*)?"
            )
            cleaned = re.sub(regex, "", cleaned)

        cleaned = re.sub(r"[,，、]{2,}", "，", cleaned)
        cleaned = re.sub(r"[。\.]{2,}", "。", cleaned)
        cleaned = re.sub(r"[;；]{2,}", "；", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"[,，、；;]\s*([。！？!?])", r"\1", cleaned)
        return cleaned.strip("，, 。.；; \t\n")

    @classmethod
    def split_sentences(cls, text: str, query_text: str = "") -> List[str]:
        """
        Split text into discrete spec sentences/clauses, preserving Markdown tables intact.
        """
        if not text:
            return []

        sentences: List[str] = []
        for line in text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            if (line_str.startswith("|") and line_str.endswith("|")) or line_str.count("|") >= 2:
                cleaned_row = cls.clean_marketing_fluff(line_str, query_text=query_text)
                if cleaned_row:
                    sentences.append(cleaned_row)
            else:
                raw_parts = re.split(r"[。！？!?；;]+", line_str)
                for p in raw_parts:
                    p_clean = cls.clean_marketing_fluff(p.strip(), query_text=query_text)
                    if p_clean and len(p_clean) >= 4:
                        sentences.append(p_clean)

        return sentences

    @classmethod
    def _compute_information_density(cls, sentence: str) -> float:
        """
        Compute normalized factual information density in [0.0, 1.0]:
        combines spec-pattern coverage, numeric-token ratio, and tabular structure.
        """
        s_stripped = sentence.strip()
        if _TABLE_SEP_RE.match(s_stripped):
            return 1.0

        is_table_row = (s_stripped.startswith("|") and s_stripped.endswith("|")) or s_stripped.count("|") >= 2
        spec_hits = sum(1 for pat in _COMPILED_SPEC_PATTERNS if pat.search(sentence))
        spec_density = min(1.0, spec_hits / 3.0)

        tokens = _TOKEN_RE.findall(sentence.lower())
        num_tokens = sum(1 for t in tokens if any(ch.isdigit() for ch in t))
        numeric_ratio = min(1.0, (num_tokens / max(len(tokens), 1)) * 3.0)

        table_bonus = 0.25 if is_table_row else 0.0
        return float(min(1.0, 0.55 * spec_density + 0.25 * numeric_ratio + table_bonus))

    @classmethod
    def _compute_semantic_similarity(
        cls,
        query_context: str,
        sentence: str,
        embed_fn: Optional[Callable[[List[str]], np.ndarray]] = None,
    ) -> float:
        """Compute semantic cosine similarity between query_context and sentence in [0, 1]."""
        if not query_context or not sentence:
            return 0.0
        fn = embed_fn or cls._embed_fn
        if fn is not None:
            try:
                vecs = np.asarray(fn([query_context, sentence]), dtype=np.float32)
                if vecs.shape[0] == 2:
                    v0, v1 = vecs[0], vecs[1]
                    n0 = float(np.linalg.norm(v0))
                    n1 = float(np.linalg.norm(v1))
                    if n0 > 0 and n1 > 0:
                        cos = float(np.dot(v0, v1) / (n0 * n1))
                        return max(0.0, min(1.0, (cos + 1.0) / 2.0 if cos < 0 else cos))
            except Exception as exc:
                logger.debug(f"Dense embedder fallback to sparse cosine: {exc}")
        return _sparse_cosine_similarity(query_context, sentence)

    @classmethod
    def score_sentence(
        cls,
        sentence: str,
        query_text: str = "",
        active_constraints: Optional[Dict[str, Any]] = None,
        embed_fn: Optional[Callable[[List[str]], np.ndarray]] = None,
    ) -> float:
        """
        Score a sentence via convex combination of semantic similarity to query/constraints
        and factual information density.
        """
        s_stripped = sentence.strip()
        if _TABLE_SEP_RE.match(s_stripped):
            return 1.5  # Always preserve Markdown table header separator

        constraint_parts = [
            f"{k}:{v}" for k, v in (active_constraints or {}).items() if v is not None and str(v).strip()
        ]
        query_context = " ".join([p for p in [query_text, *constraint_parts] if p]).strip()

        info_density = cls._compute_information_density(sentence)
        if not query_context:
            return round(info_density, 4)

        semantic_sim = cls._compute_semantic_similarity(query_context, sentence, embed_fn=embed_fn)
        return round(0.55 * semantic_sim + 0.45 * info_density, 4)

    @classmethod
    def compress_snippet(
        cls,
        snippet: str,
        query_text: str = "",
        active_constraints: Optional[Dict[str, Any]] = None,
        max_length: int = 220,
        embed_fn: Optional[Callable[[List[str]], np.ndarray]] = None,
    ) -> CompressedContext:
        """Compress a single vehicle text snippet into a concise, factual context."""
        if not snippet or len(snippet) <= max_length:
            cleaned = cls.clean_marketing_fluff(snippet or "", query_text=query_text)
            return CompressedContext(
                original_text=snippet or "",
                compressed_text=cleaned,
                original_length=len(snippet or ""),
                compressed_length=len(cleaned),
                compression_ratio=1.0
                if not snippet
                else round(len(cleaned) / max(len(snippet), 1), 3),
                preserved_facts=[cleaned] if cleaned else [],
                pruned_sentences=[],
            )

        sentences = cls.split_sentences(snippet, query_text=query_text)
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

        scored_sentences = [
            (
                cls.score_sentence(
                    s,
                    query_text=query_text,
                    active_constraints=active_constraints,
                    embed_fn=embed_fn,
                ),
                s,
            )
            for s in sentences
        ]
        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        chosen: List[str] = []
        pruned: List[str] = []
        current_len = 0

        for _score, sentence in scored_sentences:
            if current_len + len(sentence) + 1 <= max_length or not chosen:
                chosen.append(sentence)
                current_len += len(sentence) + 1
            else:
                pruned.append(sentence)

        preserved = [s for s in sentences if s in chosen]
        if any(s.strip().startswith("|") and s.strip().endswith("|") for s in preserved):
            compressed_text = "\n".join(preserved)
        else:
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
    def compress_with_llm(
        cls,
        snippet: str,
        llm: Any,
        query_text: str = "",
        max_length: int = 220,
    ) -> CompressedContext:
        """Optional LLM-backed abstractive specification distillation."""
        if not snippet or len(snippet) <= max_length or llm is None:
            return cls.compress_snippet(snippet, query_text=query_text, max_length=max_length)
        try:
            prompt = (
                f"请将以下车型资料压缩为不超过 {max_length} 字的纯客观参数摘要（保留价格、续航、动力、智驾、空间等核心数字与配置，去除一切主观宣传语）：\n"
                f"用户关注点：{query_text or '综合选车'}\n"
                f"原文：{snippet}"
            )
            res = llm.invoke(prompt)
            text = res.content if hasattr(res, "content") else str(res)
            text = text.strip()[:max_length]
            if text:
                return CompressedContext(
                    original_text=snippet,
                    compressed_text=text,
                    original_length=len(snippet),
                    compressed_length=len(text),
                    compression_ratio=round(len(text) / max(len(snippet), 1), 3),
                    preserved_facts=[text],
                    pruned_sentences=[],
                )
        except Exception as exc:
            logger.debug(f"LLM compression fallback to extractive: {exc}")
        return cls.compress_snippet(snippet, query_text=query_text, max_length=max_length)

    @classmethod
    def compress_matched_cars(
        cls,
        matched_cars: List[Dict[str, Any]],
        query_text: str = "",
        active_constraints: Optional[Dict[str, Any]] = None,
        max_length_per_car: int = 220,
    ) -> List[Dict[str, Any]]:
        """Compress text_snippets for all matched cars, attaching compression metadata."""
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
