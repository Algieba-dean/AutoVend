"""
Standalone RAG Service Manager (src/rag_service/service.py).

Provides decoupled, high-performance RAG retrieval and side-by-side vehicle spec
comparison services to the Agent and API layers.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union

from src.core.interfaces import BaseRAGService, RAGQueryRequest, RAGQueryResponse
from src.filter.vehicle_db import VehicleDB
from src.rag_service.eval_monitor import RAGEvalMonitor
from src.rag_service.reranker import RankRefiner
from src.rag_service.schemas import (
    SpecCompareRequest,
    SpecCompareResponse,
    SpecDiffItem,
    VehicleQueryRequest,
    VehicleQueryResponse,
    VehicleSearchResult,
)
from src.retrieval.adapters import hybrid_result_to_cars, needs_to_query_text
from src.retrieval.compression import ContextCompressor
from src.retrieval.hybrid_pipeline import HybridPipeline, build_default_pipeline
from src.retrieval.tiered_engine import TieredRetrievalEngine

logger = logging.getLogger(__name__)


class RAGService(BaseRAGService):
    """
    Standalone RAG Service for AutoVend.

    Implements BaseRAGService contract and is decoupled from FastAPI routes and Agent internal logic.
    Maintains vehicle database, ChromaDB vector store, BM25 index, and live drift monitor.
    Features 3-Tier low-latency retrieval routing (Tier 0 fast-path <1-2ms, Tier 1 hybrid, Tier 2 deep).
    """

    def __init__(
        self,
        pipeline: Optional[HybridPipeline] = None,
        db: Optional[VehicleDB] = None,
        monitor: Optional[RAGEvalMonitor] = None,
        parent_child_retriever: Optional[Any] = None,
    ):
        self.pipeline = pipeline or build_default_pipeline()
        self.db = db or getattr(self.pipeline, "db", None) or VehicleDB()
        self.monitor = monitor or RAGEvalMonitor()
        self.parent_child_retriever = parent_child_retriever
        self.tiered_engine = TieredRetrievalEngine.get_instance(
            db=self.db,
            hybrid_pipeline=self.pipeline,
            parent_child_retriever=self.parent_child_retriever,
        )

    def search_vehicles(
        self, request: Union[VehicleQueryRequest, RAGQueryRequest]
    ) -> Union[VehicleQueryResponse, RAGQueryResponse]:
        """
        Execute multi-stage hybrid retrieval with Tier 0 fast-path routing (< 1-2 ms).

        Supports both VehicleQueryRequest and core RAGQueryRequest contracts.
        """
        is_core_contract = isinstance(request, RAGQueryRequest)
        if is_core_contract:
            veh_req = VehicleQueryRequest(
                query_text=request.query_text,
                explicit_needs=request.explicit_conditions,
                implicit_needs=request.implicit_needs,
                top_k=request.top_k,
            )
        else:
            veh_req = request

        resp = self._search_vehicles_impl(veh_req)
        if is_core_contract:
            return RAGQueryResponse(
                results=[r.model_dump() for r in resp.results],
                total_count=len(resp.results),
                candidate_count=resp.candidate_count,
                latency_ms=resp.total_time_ms,
                degrade_level=resp.degrade_level,
            )
        return resp

    def _search_vehicles_impl(self, request: VehicleQueryRequest) -> VehicleQueryResponse:
        start_time = time.time()

        # Formulate enriched query text
        if request.explicit_needs or request.implicit_needs:
            query_text = needs_to_query_text(request.explicit_needs, request.implicit_needs)
            if request.query_text and request.query_text not in query_text:
                query_text = f"{request.query_text} {query_text}".strip()
        else:
            query_text = request.query_text or "recommend a good vehicle"

        # Check Tier 0 In-Memory Fast-Path (< 1-2 ms)
        t0_res = self.tiered_engine.search_tier0(query_text)
        if t0_res is not None and t0_res.results:
            elapsed_ms = t0_res.latency_ms
            alerts = self.monitor.record_retrieval(
                query_text=query_text,
                results=t0_res.results,
                candidate_count=t0_res.candidate_count,
                latency_ms=elapsed_ms,
                degrade_level=0,
            )
            summary = {
                "parse_method": "fast_path_spec",
                "tier": 0,
                "fast_path": True,
                "routing_reason": t0_res.routing_reason,
                "total_time": round(elapsed_ms / 1000.0, 4),
                "alerts_triggered": [a.model_dump() for a in alerts],
            }
            return VehicleQueryResponse(
                results=t0_res.results,
                candidate_count=t0_res.candidate_count,
                degrade_level=0,
                total_time_ms=round(elapsed_ms, 2),
                search_summary=summary,
            )

        # Search via hybrid pipeline
        pipeline_result = self.pipeline.search(query_text, top_k=request.top_k * 2)
        raw_cars = hybrid_result_to_cars(pipeline_result, limit=request.top_k * 2)

        # Convert to VehicleSearchResult models
        results: List[VehicleSearchResult] = []
        for car in raw_cars:
            meta = car.get("metadata", {})
            results.append(
                VehicleSearchResult(
                    car_model=car.get("car_model", ""),
                    score=float(car.get("score", 0.0)),
                    brand=meta.get("brand", ""),
                    price=meta.get("price", ""),
                    category=meta.get("category", ""),
                    powertrain_type=meta.get("powertrain_type", ""),
                    metadata=meta,
                    text_snippet=car.get("text_snippet", ""),
                )
            )

        # Apply Rank Refinement / Reranking if enabled
        if request.enable_rerank and results:
            results = RankRefiner.refine(
                query_text,
                results,
                top_k=request.top_k,
                constraints=request.explicit_needs,
            )
        else:
            results = results[: request.top_k]

        # Apply Context Compression & Hallucination-Grounded Pruning on snippets
        if getattr(request, "enable_context_compression", True):
            for item in results:
                compressed = ContextCompressor.compress_snippet(
                    item.text_snippet,
                    query_text=query_text,
                    active_constraints=request.explicit_needs,
                )
                item.text_snippet = compressed.compressed_text


        elapsed_ms = (time.time() - start_time) * 1000.0

        # Record telemetry & check query drift
        alerts = self.monitor.record_retrieval(
            query_text=query_text,
            results=results,
            candidate_count=pipeline_result.candidate_count,
            latency_ms=elapsed_ms,
            degrade_level=pipeline_result.degrade_level,
        )
        if alerts:
            logger.warning(f"RAG Service Drift Alerts triggered: {[a.alert_type for a in alerts]}")

        summary = pipeline_result.summary()
        summary["alerts_triggered"] = [a.model_dump() for a in alerts]

        return VehicleQueryResponse(
            results=results,
            candidate_count=pipeline_result.candidate_count,
            degrade_level=pipeline_result.degrade_level,
            total_time_ms=round(elapsed_ms, 2),
            search_summary=summary,
        )

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get rolling summary statistics of online RAG performance and query drift."""
        return self.monitor.get_summary_statistics()

    def compare_vehicles(self, request: SpecCompareRequest) -> SpecCompareResponse:
        """
        Build a side-by-side specification diff matrix comparing requested car models.

        Args:
            request: SpecCompareRequest with list of car_models.

        Returns:
            SpecCompareResponse with diff matrix.
        """
        models = request.car_models
        diff_matrix: List[SpecDiffItem] = []

        # Feature properties to extract for comparison
        feature_keys = [
            ("官方指导价", "prize"),
            ("级别/类型", "vehicle_category_bottom"),
            ("品牌", "brand"),
            ("动力形式", "powertrain_type"),
            ("座椅布局", "seat_layout"),
            ("驱动类型", "drive_type"),
            ("续航表现", "electric_range"),
            ("舒适度评级", "comfort_level"),
            ("智能座舱/智驾", "smartness"),
        ]

        # Query SQLite vehicle records
        vehicles_data: Dict[str, Dict[str, Any]] = {}
        for car_model in models:
            rec = self.db.get_by_model(car_model)
            if rec:
                vehicles_data[car_model] = rec.to_dict() if hasattr(rec, "to_dict") else dict(rec)
            else:
                vehicles_data[car_model] = {}

        # Build comparison rows
        for label_cn, key in feature_keys:
            val_map: Dict[str, str] = {}
            for car_model in models:
                v_dict = vehicles_data.get(car_model, {})
                precise = v_dict.get("precise_labels", {}) if isinstance(v_dict.get("precise_labels"), dict) else {}
                ambiguous = v_dict.get("ambiguous_labels", {}) if isinstance(v_dict.get("ambiguous_labels"), dict) else {}
                val = v_dict.get(key) or precise.get(key) or ambiguous.get(key) or "信息待补充"
                val_map[car_model] = str(val)

            diff_matrix.append(SpecDiffItem(feature_name=label_cn, values=val_map))

        summary = f"已完成【{' vs '.join(models)}】的跨车型配置横向对比分析。"

        return SpecCompareResponse(
            car_models=models,
            diff_matrix=diff_matrix,
            comparison_summary=summary,
        )

    def get_vehicle_detail(self, car_model: str) -> Optional[Dict[str, Any]]:
        """Fetch full details of a single vehicle model."""
        rec = self.db.get_by_model(car_model)
        if rec:
            return rec.to_dict() if hasattr(rec, "to_dict") else dict(rec)
        return None

    def search_documents(
        self,
        query: str,
        top_k_children: int = 6,
        top_k_parents: int = 3,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Search ingested enterprise multi-format documents via Parent-Child Hierarchical Retriever.
        """
        if not self.parent_child_retriever:
            raise ValueError("ParentChildRetriever is not configured on this RAGService instance.")
        return self.parent_child_retriever.search(
            query=query,
            top_k_children=top_k_children,
            top_k_parents=top_k_parents,
            filter_metadata=filter_metadata,
        )
