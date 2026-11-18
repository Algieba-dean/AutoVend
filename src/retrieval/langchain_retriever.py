"""
LlamaIndex -> LangChain Retriever Bridge.

Exposes AutoVend's LlamaIndex VectorStoreIndex / HybridPipeline / TieredRetrievalEngine
as a standard LangChain `BaseRetriever` returning `langchain_core.documents.Document`
instances, so LangGraph nodes and LangChain tools can invoke LlamaIndex RAG natively.
"""

from typing import Any, Dict, List, Optional

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field


class LlamaIndexHybridRetriever(BaseRetriever):
    """
    LangChain `BaseRetriever` backed by AutoVend's LlamaIndex + Hybrid RAG stack.

    Priority order:
    1. Tier 0 in-memory exact spec fast-path (when `tiered_engine` is available)
    2. `HybridPipeline` (Structured SQLite Filter + LlamaIndex/pgvector Dense + BM25 + RRF)
    3. Direct LlamaIndex `VectorStoreIndex.as_retriever(...)` if provided
    """

    pipeline: Any = Field(default=None, exclude=True)
    llama_index: Any = Field(default=None, exclude=True)
    top_k: int = 5

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def retrieve_with_slots(
        self,
        query: str,
        explicit_conditions: Optional[Dict[str, Any]] = None,
        implicit_needs: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Invoke retrieval passing structured slots directly to HybridPipeline without NL re-parsing."""
        return self._search_impl(
            query,
            explicit_conditions=explicit_conditions,
            implicit_needs=implicit_needs,
        )

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
        explicit_conditions: Optional[Dict[str, Any]] = None,
        implicit_needs: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        return self._search_impl(
            query,
            explicit_conditions=explicit_conditions,
            implicit_needs=implicit_needs,
        )

    def _search_impl(
        self,
        query: str,
        explicit_conditions: Optional[Dict[str, Any]] = None,
        implicit_needs: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        docs: List[Document] = []

        # 1. HybridPipeline (LlamaIndex/pgvector dense + BM25 sparse + SQLite filter)
        if self.pipeline is not None:
            import inspect

            try:
                sig = inspect.signature(self.pipeline.search)
                if "explicit_conditions" in sig.parameters and (explicit_conditions or implicit_needs):
                    result = self.pipeline.search(
                        query,
                        top_k=self.top_k,
                        explicit_conditions=explicit_conditions,
                        implicit_needs=implicit_needs,
                    )
                else:
                    result = self.pipeline.search(query, top_k=self.top_k)
            except (TypeError, ValueError):
                result = self.pipeline.search(query, top_k=self.top_k)
            # Real HybridPipelineResult carries `.search_response`
            if getattr(result, "search_response", None) is not None:
                from src.retrieval.adapters import hybrid_result_to_cars

                for car in hybrid_result_to_cars(result, limit=self.top_k):
                    meta: Dict[str, Any] = dict(car.get("metadata") or {})
                    if car.get("car_model"):
                        meta["car_model"] = car["car_model"]
                    meta["score"] = float(car.get("score") or 0.0)
                    meta["source"] = "hybrid_pipeline"
                    text = car.get("text_snippet") or str(meta)
                    docs.append(Document(page_content=text, metadata=meta))
                return docs

            # Fallback for duck-typed mock pipelines exposing `.results`
            for item in getattr(result, "results", []):
                meta = dict(getattr(item, "metadata", {}) or {})
                car_model = getattr(item, "car_model", "") or meta.get("car_model", "")
                if car_model:
                    meta["car_model"] = car_model
                meta["score"] = float(getattr(item, "score", 0.0))
                meta["source"] = getattr(item, "source", "hybrid_pipeline")
                text = getattr(item, "text_snippet", "") or str(meta)
                docs.append(Document(page_content=text, metadata=meta))
            return docs

        # 2. Direct LlamaIndex VectorStoreIndex fallback
        if self.llama_index is not None:
            retriever = self.llama_index.as_retriever(similarity_top_k=self.top_k)
            nodes = retriever.retrieve(query)
            for node_with_score in nodes:
                node = getattr(node_with_score, "node", node_with_score)
                score = float(getattr(node_with_score, "score", 0.0) or 0.0)
                meta = dict(getattr(node, "metadata", {}) or {})
                meta["score"] = score
                meta["source"] = "llamaindex_vector_store"
                text = node.get_content() if hasattr(node, "get_content") else str(node)
                docs.append(Document(page_content=text, metadata=meta))
            return docs

        return docs


def documents_to_car_dicts(docs: List[Document], limit: int = 5) -> List[Dict[str, Any]]:
    """Convert LangChain Documents from `LlamaIndexHybridRetriever` to matched_cars dicts."""
    cars: List[Dict[str, Any]] = []
    for doc in docs[:limit]:
        meta = dict(doc.metadata or {})
        car_entry = {
            **meta,
            "car_model": meta.get("car_model", ""),
            "score": meta.get("score", 0.0),
            "metadata": meta,
            "text_snippet": doc.page_content,
        }
        cars.append(car_entry)
    return cars
