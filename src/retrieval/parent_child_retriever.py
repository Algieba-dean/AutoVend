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

import numpy as np

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
    Thread-safe with lockless Copy-on-Write reads and write-locked mutators.
    """

    def __init__(self, embedding_model: Optional[Any] = None):
        self.embedding_model = embedding_model
        self.chunks: List[Chunk] = []
        self.chunk_map: Dict[str, Chunk] = {}
        self._norm_matrix: Optional[np.ndarray] = None
        self._write_lock = threading.RLock()

    @property
    def embeddings(self) -> List[List[float]]:
        """Backwards compatibility view for test assertions; eliminates dual RAM storage."""
        if self._norm_matrix is None:
            return []
        return self._norm_matrix.tolist()

    def add_chunks(self, chunks: List[Chunk]) -> None:
        """
        Incrementally add chunks and embeddings.
        Avoids O(N^2) reallocation by only normalizing the newly added batch
        and vertically concatenating to the existing normalized matrix.
        """
        with self._write_lock:
            new_chunks: List[Chunk] = []
            for chunk in chunks:
                if chunk.chunk_id in self.chunk_map:
                    continue
                new_chunks.append(chunk)

            if not new_chunks:
                return

            new_norm_embeds = None
            if self.embedding_model:
                texts = [c.content for c in new_chunks]
                embeds = []
                if hasattr(self.embedding_model, "embed_documents"):
                    try:
                        embeds = self.embedding_model.embed_documents(texts)
                    except Exception as e:
                        logger.warning(f"Embedding model batch encoding failed: {e}")
                elif hasattr(self.embedding_model, "encode"):
                    try:
                        raw_embeds = self.embedding_model.encode(texts)
                        if hasattr(raw_embeds, "tolist"):
                            embeds = raw_embeds.tolist()
                        else:
                            embeds = [list(e) for e in raw_embeds]
                    except Exception as e:
                        logger.warning(f"SentenceTransformer batch encode failed: {e}")

                if embeds:
                    batch_mat = np.asarray(embeds, dtype=np.float32)
                    batch_norms = np.linalg.norm(batch_mat, axis=1, keepdims=True)
                    batch_norms = np.where(batch_norms == 0, 1e-9, batch_norms)
                    new_norm_embeds = batch_mat / batch_norms

            # Update map
            for c in new_chunks:
                self.chunk_map[c.chunk_id] = c

            updated_chunks = list(self.chunks) + new_chunks

            if new_norm_embeds is not None:
                if self._norm_matrix is None or len(self._norm_matrix) == 0:
                    updated_matrix = new_norm_embeds
                else:
                    updated_matrix = np.vstack([self._norm_matrix, new_norm_embeds])
            else:
                updated_matrix = self._norm_matrix

            # Copy-on-Write atomic publish
            self.chunks = updated_chunks
            self._norm_matrix = updated_matrix

    def evict(self, chunk_ids: List[str]) -> int:
        """
        Evict chunks by id from index, reclaiming memory and updating the matrix.
        Prevents memory leaks when documents are updated or deleted.
        """
        with self._write_lock:
            to_remove = set(chunk_ids)
            if not to_remove:
                return 0

            keep_indices = []
            new_chunks = []
            for idx, c in enumerate(self.chunks):
                if c.chunk_id in to_remove:
                    self.chunk_map.pop(c.chunk_id, None)
                else:
                    keep_indices.append(idx)
                    new_chunks.append(c)

            removed_count = len(self.chunks) - len(new_chunks)
            if removed_count == 0:
                return 0

            if self._norm_matrix is not None and len(keep_indices) > 0:
                updated_matrix = self._norm_matrix[keep_indices]
            else:
                updated_matrix = None

            # Copy-on-Write atomic publish
            self.chunks = new_chunks
            self._norm_matrix = updated_matrix
            return removed_count

    def delete_chunks(self, chunk_ids: List[str]) -> int:
        return self.evict(chunk_ids)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Chunk, float]]:
        """
        Dense cosine search (SIMD accelerated via NumPy) or fallback to token-overlap BM25-style scorer.
        Lockless read execution relying on Copy-on-Write snapshots of chunks and norm_matrix.
        """
        chunks_snapshot = self.chunks
        norm_matrix_snapshot = self._norm_matrix

        if not chunks_snapshot:
            return []

        # If embeddings are populated and embedding model is present
        if self.embedding_model and norm_matrix_snapshot is not None and len(norm_matrix_snapshot) == len(chunks_snapshot):
            try:
                if hasattr(self.embedding_model, "embed_query"):
                    query_vec = self.embedding_model.embed_query(query)
                elif hasattr(self.embedding_model, "encode"):
                    raw_vec = self.embedding_model.encode(query)
                    query_vec = raw_vec.tolist() if hasattr(raw_vec, "tolist") else list(raw_vec)
                else:
                    query_vec = None

                if query_vec is not None:
                    q_arr = np.asarray(query_vec, dtype=np.float32)
                    q_norm = np.linalg.norm(q_arr)
                    if q_norm > 0:
                        q_arr = q_arr / q_norm

                    if not filter_metadata:
                        ranked = vectorized_cosine_search(q_arr, norm_matrix_snapshot, top_k=top_k)
                        return [(chunks_snapshot[idx], score) for idx, score in ranked]

                    valid_indices = [
                        i for i in range(len(chunks_snapshot))
                        if self._matches_filter(chunks_snapshot[i], filter_metadata)
                    ]
                    if not valid_indices:
                        return []
                    sub_matrix = norm_matrix_snapshot[valid_indices]
                    sub_ranked = vectorized_cosine_search(q_arr, sub_matrix, top_k=top_k)
                    return [(chunks_snapshot[valid_indices[sub_idx]], score) for sub_idx, score in sub_ranked]
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

        candidate_chunks = chunks_snapshot
        if filter_metadata:
            candidate_chunks = [
                c for c in candidate_chunks if self._matches_filter(c, filter_metadata)
            ]

        if not query_terms:
            return [(c, 0.0) for c in candidate_chunks[:top_k]]

        scored: List[Tuple[Chunk, float]] = []
        for chunk in candidate_chunks:
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

    @staticmethod
    def _matches_filter(chunk: Chunk, filter_metadata: Dict[str, Any]) -> bool:
        for k, v in filter_metadata.items():
            val = chunk.metadata.get(k)
            if isinstance(v, str) and isinstance(val, str):
                if v.lower() not in val.lower() and val.lower() not in v.lower():
                    return False
            elif val != v:
                return False
        return True


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
        self._write_lock = threading.RLock()
        self._lock = self._write_lock

    def index_document(self, doc: ParsedDocument) -> Dict[str, int]:
        """Index a single ParsedDocument."""
        chunk_dict = self.chunker.chunk_document(doc)
        return self.index_chunks(chunk_dict)

    def index_chunks(self, chunk_dict: Dict[str, List[Chunk]]) -> Dict[str, int]:
        """
        Index parents in Key-Value store and children in vector/lexical index.
        """
        with self._write_lock:
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

    def evict_document(self, doc_id: str) -> Dict[str, int]:
        """
        Evict all parent and child chunks associated with a document/vehicle.
        Prevents ghost chunks and memory leaks across updates.
        """
        with self._write_lock:
            parent_ids_to_remove = set()
            for pid, p in list(self.parent_store.items()):
                if (
                    pid == doc_id
                    or p.metadata.get("doc_id") == doc_id
                    or p.metadata.get("vehicle_model") == doc_id
                    or p.metadata.get("car_model") == doc_id
                ):
                    parent_ids_to_remove.add(pid)
                    self.parent_store.pop(pid, None)

            child_ids_to_remove = [
                c.chunk_id
                for c in self.child_index.chunks
                if (
                    c.parent_id in parent_ids_to_remove
                    or c.chunk_id == doc_id
                    or c.metadata.get("doc_id") == doc_id
                    or c.metadata.get("vehicle_model") == doc_id
                    or c.metadata.get("car_model") == doc_id
                )
            ]
            evicted_children = self.child_index.evict(child_ids_to_remove)
            return {
                "parents_evicted": len(parent_ids_to_remove),
                "children_evicted": evicted_children,
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
        1. Search vector index for top-k children (lockless).
        2. Group matched children by parent_id.
        3. Retrieve parent chunk and aggregate child scores.
        4. Apply optional metadata filters (e.g. is_table, vehicle_model).
        5. Return top-k parent contexts with matched evidence.
        """
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


def vectorized_cosine_search(
    query_vec: np.ndarray, doc_matrix: np.ndarray, top_k: int = 5
) -> List[Tuple[int, float]]:
    """
    Vectorized cosine similarity search using NumPy matrix multiplication.
    doc_matrix shape: (N, D), query_vec shape: (D,)
    Assumes query_vec and doc_matrix rows are unit-norm (pre-normalized).
    Returns list of (index, similarity_score) sorted descending by similarity.
    """
    if doc_matrix.size == 0 or query_vec.size == 0:
        return []
    sims = np.dot(doc_matrix, query_vec)
    n_docs = len(sims)
    k = min(top_k, n_docs)
    if k <= 0:
        return []
    if k < n_docs:
        top_indices = np.argpartition(sims, -k)[-k:]
        sorted_top = top_indices[np.argsort(-sims[top_indices])]
    else:
        sorted_top = np.argsort(-sims)
    return [(int(idx), float(sims[idx])) for idx in sorted_top]


def retrieve_multi_vehicle_context(
    query: str,
    car_models: List[str],
    parent_child_retriever: Any,
    top_k_per_vehicle: int = 2,
) -> Dict[str, List[Chunk]]:
    """
    Slot-based Entity-Scoped Context Retrieval.
    Guarantees zero cross-entity context contamination.
    """
    scoped_contexts: Dict[str, List[Chunk]] = {}

    for model in car_models:
        if not model:
            continue
        scoped_filter = {"car_model": model}
        try:
            car_docs = parent_child_retriever.search(
                query=f"{model} {query}",
                filter_metadata=scoped_filter,
                top_k_parents=top_k_per_vehicle,
            )
        except Exception as e:
            logger.warning(f"retrieve_multi_vehicle_context error for {model}: {e}")
            car_docs = []

        chunks: List[Chunk] = []
        if hasattr(car_docs, "results"):
            for r in car_docs.results:
                if hasattr(r, "parent_chunk"):
                    chunks.append(r.parent_chunk)
                elif isinstance(r, Chunk):
                    chunks.append(r)
        elif isinstance(car_docs, list):
            for r in car_docs:
                if hasattr(r, "parent_chunk"):
                    chunks.append(r.parent_chunk)
                elif isinstance(r, Chunk):
                    chunks.append(r)
        scoped_contexts[model] = chunks

    return scoped_contexts


def format_isolated_llm_context(scoped_contexts: Dict[str, List[Chunk]]) -> str:
    """按实体明确分块组装，禁止扁平无差别拼接."""
    context_blocks = []
    for model, chunks in scoped_contexts.items():
        valid_snippets = [
            f"  - {getattr(c, 'content', str(c)).strip()}"
            for c in chunks
            if getattr(c, "content", str(c)).strip()
        ]
        doc_texts = "\n".join(valid_snippets) if valid_snippets else "  - 暂无专属深度评测"
        block = f"### 车型: 【{model}】专属参考资料:\n{doc_texts}"
        context_blocks.append(block)

    return "\n\n".join(context_blocks)

