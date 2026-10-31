"""
Parent-Child Document Retriever for AutoVend (src/retrieval/parent_child_retriever.py).

Implements enterprise-grade Parent-Document Retrieval:
1. Indexes granular Child Chunks (~200 tokens) in dense vector space (and/or BM25)
   for high-precision semantic matching without noisy diluting context.
2. Resolves matched children to cohesive Parent Chunks (~1000 tokens) or complete
   Markdown Tables for generation without context truncation.
3. Automatically deduplicates parent chunks and ranks parents by aggregated child relevance.
"""

import logging
import math
import re
import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from src.ingestion.hierarchical_chunker import Chunk, HierarchicalChunker
from src.ingestion.layout_parser import ParsedDocument

logger = logging.getLogger(__name__)


class ChildHit:
    """Represents a matched child chunk with score."""

    def __init__(self, chunk: Chunk, score: float):
        self.chunk = chunk
        self.score = score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "parent_id": self.chunk.parent_id,
            "score": round(self.score, 4),
            "content": self.chunk.content,
            "metadata": self.chunk.metadata,
        }


class ParentRetrievalResult:
    """Represents a resolved parent context with matched child evidence."""

    def __init__(
        self,
        parent_chunk: Chunk,
        score: float,
        matched_children: List[ChildHit],
    ):
        self.parent_chunk = parent_chunk
        self.score = score
        self.matched_children = matched_children

    @property
    def parent_id(self) -> str:
        return self.parent_chunk.chunk_id

    @property
    def content(self) -> str:
        return self.parent_chunk.content

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.parent_chunk.metadata

    @property
    def is_table(self) -> bool:
        return self.parent_chunk.metadata.get("is_table", False)

    @property
    def is_stitched(self) -> bool:
        return self.parent_chunk.metadata.get("is_stitched", False)

    @property
    def breadcrumbs(self) -> List[str]:
        return self.parent_chunk.metadata.get("breadcrumb_path", [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parent_id": self.parent_id,
            "score": round(self.score, 4),
            "is_table": self.is_table,
            "is_stitched": self.is_stitched,
            "breadcrumbs": self.breadcrumbs,
            "content": self.content,
            "metadata": self.metadata,
            "matched_children": [c.to_dict() for c in self.matched_children],
        }


class ParentChildSearchResponse:
    """Standardized response from Parent-Child Retrieval."""

    def __init__(
        self,
        query: str,
        results: List[ParentRetrievalResult],
        child_hit_count: int,
        search_time: float,
    ):
        self.query = query
        self.results = results
        self.child_hit_count = child_hit_count
        self.search_time = search_time

    def format_llm_context(self, max_parents: int = 3) -> str:
        """
        Formats retrieved parent contexts directly into LLM-ready context block.
        Includes table indication, cross-page stitched flag, and hierarchical breadcrumbs.
        """
        context_blocks: List[str] = []
        for i, res in enumerate(self.results[:max_parents]):
            prefix = f"### [参考资料 {i+1}] (相关度得分: {res.score:.2f})"
            if res.is_table:
                prefix += " - [结构化技术规格表"
                if res.is_stitched:
                    prefix += " (跨页拼接)]"
                else:
                    prefix += "]"
            if res.breadcrumbs:
                prefix += f" - [层级路径: {' > '.join(res.breadcrumbs)}]"
            context_blocks.append(f"{prefix}\n{res.content}")
        return "\n\n".join(context_blocks)


class SimpleVectorIndex:
    """
    In-memory vector & lexical index for child chunks.
    Allows zero-dependency high-speed cosine & token matching with optional dense embedding model.
    Thread-safe for concurrent ingestion and query operations.
    """

    def __init__(self, embedding_model: Optional[Any] = None):
        self.embedding_model = embedding_model
        self.chunks: List[Chunk] = []
        self.chunk_map: Dict[str, Chunk] = {}
        self.embeddings: List[List[float]] = []
        self._lock = threading.RLock()

    def add_chunks(self, chunks: List[Chunk]) -> None:
        with self._lock:
            new_chunks: List[Chunk] = []
            for chunk in chunks:
                if chunk.chunk_id in self.chunk_map:
                    continue
                self.chunks.append(chunk)
                self.chunk_map[chunk.chunk_id] = chunk
                new_chunks.append(chunk)

            if not new_chunks or not self.embedding_model:
                return

            texts = [c.content for c in new_chunks]
            if hasattr(self.embedding_model, "embed_documents"):
                try:
                    embeds = self.embedding_model.embed_documents(texts)
                    self.embeddings.extend(embeds)
                except Exception as e:
                    logger.warning(f"Embedding model batch encoding failed: {e}")
            elif hasattr(self.embedding_model, "encode"):
                try:
                    raw_embeds = self.embedding_model.encode(texts)
                    if hasattr(raw_embeds, "tolist"):
                        embeds = raw_embeds.tolist()
                    else:
                        embeds = [list(e) for e in raw_embeds]
                    self.embeddings.extend(embeds)
                except Exception as e:
                    logger.warning(f"SentenceTransformer batch encode failed: {e}")

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """Dense cosine search or fallback to token-overlap BM25-style scorer."""
        with self._lock:
            if not self.chunks:
                return []

            # If embeddings are populated and embedding model is present
            if self.embedding_model and len(self.embeddings) == len(self.chunks):
                try:
                    if hasattr(self.embedding_model, "embed_query"):
                        query_vec = self.embedding_model.embed_query(query)
                    elif hasattr(self.embedding_model, "encode"):
                        raw_vec = self.embedding_model.encode(query)
                        query_vec = raw_vec.tolist() if hasattr(raw_vec, "tolist") else list(raw_vec)
                    else:
                        query_vec = None

                    if query_vec:
                        scores: List[Tuple[Chunk, float]] = []
                        for chunk, vec in zip(self.chunks, self.embeddings):
                            dot = sum(a * b for a, b in zip(query_vec, vec))
                            norm_a = math.sqrt(sum(a * a for a in query_vec)) or 1e-9
                            norm_b = math.sqrt(sum(b * b for b in vec)) or 1e-9
                            sim = dot / (norm_a * norm_b)
                            scores.append((chunk, float(sim)))
                        scores.sort(key=lambda x: x[1], reverse=True)
                        return scores[:top_k]
                except Exception as e:
                    logger.warning(f"Dense vector query failed: {e}. Falling back to lexical scoring.")

            # Robust lexical scoring (character unigrams + bigrams + alphanumeric tokens for bilingual accuracy)
            clean_q = query.lower()
            query_terms = set(re.findall(r"[A-Za-z0-9\.\-]+", clean_q))
            zh_chars = re.findall(r"[\u4e00-\u9fa5]", clean_q)
            for ch in zh_chars:
                query_terms.add(ch)
            for i in range(len(zh_chars) - 1):
                query_terms.add(zh_chars[i] + zh_chars[i + 1])
            for i in range(len(zh_chars) - 2):
                query_terms.add(zh_chars[i] + zh_chars[i + 1] + zh_chars[i + 2])

            if not query_terms:
                return [(c, 0.0) for c in self.chunks[:top_k]]

            scored: List[Tuple[Chunk, float]] = []
            for chunk in self.chunks:
                chunk_text = chunk.content.lower()
                overlap = 0.0
                for term in query_terms:
                    if term in chunk_text:
                        # Higher weight for longer domain terms (e.g. bigrams, trigrams, model names)
                        overlap += 1.0 + (len(term) * 0.5)
                norm_score = overlap / (len(query_terms) + 1.0)
                if norm_score > 0.0:
                    scored.append((chunk, norm_score))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]


class ParentChildRetriever:
    """
    Parent-Document Retriever:
    1. Indexes Child Chunks in Vector Store.
    2. Stores Parent Chunks (and Atomic Tables) in Parent Store.
    3. On query: retrieves top Child chunks, expands to Parent chunks, and deduplicates.
    Thread-safe for concurrent ingestion and query operations.
    """

    def __init__(
        self,
        chunker: Optional[HierarchicalChunker] = None,
        embedding_model: Optional[Any] = None,
    ):
        self.chunker = chunker or HierarchicalChunker()
        self.embedding_model = embedding_model
        self.parent_store: Dict[str, Chunk] = {}
        self.child_index = SimpleVectorIndex(embedding_model=embedding_model)
        self._lock = threading.RLock()

    def index_document(self, doc: ParsedDocument) -> Dict[str, int]:
        """Index a single ParsedDocument."""
        chunk_dict = self.chunker.chunk_document(doc)
        return self.index_chunks(chunk_dict)

    def index_chunks(self, chunk_dict: Dict[str, List[Chunk]]) -> Dict[str, int]:
        """
        Index parents in Key-Value store and children in vector/lexical index.
        """
        with self._lock:
            parents = chunk_dict.get("parents", [])
            children = chunk_dict.get("children", [])

            # Store parents
            for p in parents:
                self.parent_store[p.chunk_id] = p

            # Index children
            self.child_index.add_chunks(children)

            logger.info(
                f"Indexed {len(parents)} parents and {len(children)} children in ParentChildRetriever."
            )

            return {
                "parents_indexed": len(parents),
                "children_indexed": len(children),
                "total_parents": len(self.parent_store),
                "total_children": len(self.child_index.chunks),
            }

    def search(
        self,
        query: str,
        top_k_children: int = 15,
        top_k_parents: int = 3,
        min_score: float = 0.05,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> ParentChildSearchResponse:
        """
        Execute parent-child retrieval:
        1. Search vector index for top-k children.
        2. Group matched children by parent_id.
        3. Retrieve parent chunk and aggregate child scores.
        4. Apply optional metadata filters (e.g. is_table, vehicle_model).
        5. Return top-k parent contexts with matched evidence.
        """
        with self._lock:
            start_time = time.time()
            effective_k_children = max(top_k_children, top_k_parents * 4)
            child_matches = self.child_index.search(query=query, top_k=effective_k_children)

            # Filter by min_score
            valid_child_matches = [
                (c, s) for c, s in child_matches if s >= min_score
            ]

            # Group by parent_id
            parent_child_groups: Dict[str, List[ChildHit]] = defaultdict(list)
            parent_max_scores: Dict[str, float] = defaultdict(float)

            for chunk, score in valid_child_matches:
                pid = chunk.parent_id or chunk.chunk_id
                hit = ChildHit(chunk=chunk, score=score)
                parent_child_groups[pid].append(hit)
                if score > parent_max_scores[pid]:
                    parent_max_scores[pid] = score

            results: List[ParentRetrievalResult] = []
            for pid, hits in parent_child_groups.items():
                parent_chunk = self.parent_store.get(pid)
                if not parent_chunk:
                    # If parent not in store, fallback to child chunk itself
                    parent_chunk = hits[0].chunk

                # Metadata filtering (supports substring and case-insensitive matching for string fields)
                if filter_metadata:
                    match = True
                    for k, v in filter_metadata.items():
                        val = parent_chunk.metadata.get(k)
                        if isinstance(v, str) and isinstance(val, str):
                            if v.lower() not in val.lower() and val.lower() not in v.lower():
                                match = False
                                break
                        elif val != v:
                            match = False
                            break
                    if not match:
                        continue

                # Aggregate score: max child score + bonus for multiple matching child chunks
                base_score = parent_max_scores[pid]
                diversity_bonus = min(0.2, (len(hits) - 1) * 0.05)
                final_score = base_score + diversity_bonus

                results.append(
                    ParentRetrievalResult(
                        parent_chunk=parent_chunk,
                        score=final_score,
                        matched_children=hits,
                    )
                )

            # Sort parents by final score descending
            results.sort(key=lambda r: r.score, reverse=True)
            truncated_results = results[:top_k_parents]

            elapsed = time.time() - start_time
            return ParentChildSearchResponse(
                query=query,
                results=truncated_results,
                child_hit_count=len(valid_child_matches),
                search_time=elapsed,
            )
