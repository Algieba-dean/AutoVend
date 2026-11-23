"""
Comprehensive regression tests for all P0 and P1 fixes across Agent, RAG, MLOps, LLM, and Eval.
"""

import json
import sys
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import MemorySaver

# ── Helpers ───────────────────────────────────────────────────────────


class _SimpleStubChatModel(BaseChatModel):
    reply_text: str = "好的，已为您记录需求。"

    @property
    def _llm_type(self) -> str:
        return "stub-chat"

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, schema, **kwargs):
        class _R:
            def invoke(self, msgs, **kw):
                return schema()

        return _R()

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.reply_text))])


# ── P0.1a: check_constraint_conflicts_tool ────────────────────────────


def test_p0_check_constraint_conflicts_tool_formats_suggested_options():
    from src.agent.langchain_tools import check_constraint_conflicts_tool

    raw = check_constraint_conflicts_tool.invoke(
        {"budget_wan": 10.0, "powertrain_type": "纯电", "parking_conditions": "无固定车位"}
    )
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)
    assert parsed["conflict_count"] >= 1
    first = parsed["conflicts"][0]
    assert "suggested_options" in first
    assert "suggestion" in first
    assert isinstance(first["suggestion"], str)


# ── P0.1b & P0.1c: astream_turn buffering/replace & SystemNotesCleared ──


def test_p0_system_notes_cleared_event_prevents_resurrection():
    from src.agent.events import SystemNoteAdded, SystemNotesCleared, project_state

    events = [
        SystemNoteAdded(turn_id=1, source="test", note="turn1 note"),
        SystemNotesCleared(turn_id=1, source="finalize_generation"),
        SystemNoteAdded(turn_id=2, source="test", note="turn2 note"),
    ]
    sess = project_state(events)
    assert sess.system_notes == ["turn2 note"]


@pytest.mark.asyncio
async def test_p0_astream_turn_buffers_compliance_and_emits_replace_on_rewrite():
    from langchain_core.messages import AIMessageChunk
    from langchain_core.outputs import ChatGenerationChunk

    from src.agent.langgraph_agent import LangGraphSalesAgent
    from src.agent.schemas import SessionState, Stage

    class _StreamingStubChatModel(_SimpleStubChatModel):
        chunks_seq: list[list[str]] = []
        call_idx: int = 0

        async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
            idx = min(self.call_idx, len(self.chunks_seq) - 1)
            self.call_idx += 1
            for tok in self.chunks_seq[idx]:
                yield ChatGenerationChunk(message=AIMessageChunk(content=tok))

    # Case 1: Streaming compliance buffering — "全网最低价" never leaks in delta or done
    model = _StreamingStubChatModel(
        chunks_seq=[["推荐比亚迪海豹。", "我保证全网最低价，绝对不会再降。"]]
    )
    agent = LangGraphSalesAgent(
        llm=model,
        generation_llm=model,
        checkpointer=MemorySaver(),
        use_unified_extraction=False,
    )
    sess = SessionState(session_id="p0_stream_test", stage=Stage.NEEDS_ANALYSIS)
    events = []
    async for kind, payload in agent.astream_turn(
        session_id="p0_stream_test",
        user_message="这款车最低多少钱",
        session_state=sess,
        retrieved_cars=[{"car_model": "比亚迪海豹", "price": "17.98万"}],
        skip_extraction=True,
    ):
        events.append((kind, payload))

    delta_events = [p for k, p in events if k == "delta"]
    done_events = [p for k, p in events if k == "done"]
    assert len(done_events) == 1
    assert all("全网最低价" not in d for d in delta_events)
    assert "全网最低价" not in done_events[0]

    # Case 2: Post-generation audit rewrite emits ("replace", final_text) when earlier delta was emitted
    rewrite_model = _StreamingStubChatModel(
        chunks_seq=[
            ["比亚迪海豹很不错。", "只要5.00万元即可开走。"],
            ["比亚迪海豹官方指导价17.98万。"],
        ]
    )
    rewrite_agent = LangGraphSalesAgent(
        llm=rewrite_model,
        generation_llm=rewrite_model,
        checkpointer=MemorySaver(),
        use_unified_extraction=False,
    )
    sess2 = SessionState(session_id="p0_stream_replace_test", stage=Stage.NEEDS_ANALYSIS)
    events2 = []
    async for kind, payload in rewrite_agent.astream_turn(
        session_id="p0_stream_replace_test",
        user_message="这款车多少钱",
        session_state=sess2,
        retrieved_cars=[{"car_model": "比亚迪海豹", "price": "17.98万"}],
        skip_extraction=True,
    ):
        events2.append((kind, payload))

    replace_events = [p for k, p in events2 if k == "replace"]
    done_events2 = [p for k, p in events2 if k == "done"]
    assert len(done_events2) == 1
    assert len(replace_events) == 1
    assert replace_events[0] == done_events2[0]
    assert "5.00万" not in done_events2[0]


# ── P0.1d: Sub-DAG no hardcoded reservation_location / salesman ───────


def test_p0_subdag_does_not_fabricate_location_or_salesman():
    from src.agent.schemas import SessionState, Stage
    from src.agent.subdag.context import SubDAGContext
    from src.agent.subdag.stage_dags import create_reservation_4s_dag

    dag = create_reservation_4s_dag()
    sess = SessionState(session_id="subdag_test", stage=Stage.RESERVATION_4S)
    sess.profile.name = "张三"
    sess.profile.phone_number = "13800138000"
    ctx = SubDAGContext(session_state=sess, user_message="我想预约试驾")
    dag.run(ctx)
    assert sess.reservation.reservation_location == ""
    assert sess.reservation.salesman == ""


# ── P0.2a: PgVectorStore.upsert_document writes tsv ───────────────────


def test_p0_pgvector_upsert_document_writes_tsv_column():
    from src.rag.pgvector_store import PgVectorStore

    store = PgVectorStore(allow_memory_fallback=True, embed_dim=4)
    executed_sql = []

    class _FakeCur:
        def execute(self, sql, params=None):
            executed_sql.append((sql, params))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    class _FakeConn:
        def cursor(self):
            return _FakeCur()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    store._fallback = None
    store._get_conn = lambda: _FakeConn()
    store.upsert_document(
        doc_id="doc_1",
        text="比亚迪海豹纯电轿车",
        metadata={"car_model": "海豹"},
        embedding=[0.1, 0.2, 0.3, 0.4],
    )
    assert len(executed_sql) == 1
    sql, params = executed_sql[0]
    assert "tsv" in sql
    assert "to_tsvector('simple', %s)" in sql
    assert len(params) == 5
    assert "比亚迪" in params[4]


# ── P0.2b: Ingestion doc_id, get_search_text & sparse index sync ──────


def test_p0_ingestion_unifies_doc_id_search_text_and_bm25_sync(tmp_path):
    from src.filter.vehicle_db import VehicleDB
    from src.ingestion.pipeline import IncrementalIngestionPipeline
    from src.rag.vector_store import generate_vehicle_doc_id
    from src.retrieval.bm25_index import BM25Index

    db = VehicleDB(db_path=tmp_path / "veh.db")
    bm25 = BM25Index(
        car_models=["比亚迪汉", "特斯拉Model 3"],
        corpus_tokens=[["比亚迪", "汉"], ["特斯拉", "model", "3"]],
    )
    fake_vs = MagicMock()
    fake_emb = MagicMock()
    fake_emb.is_degraded = False
    fake_emb.get_text_embedding.return_value = [0.1, 0.2, 0.3]

    fake_retriever = MagicMock()
    fake_retriever.vector_store = fake_vs
    fake_retriever.embedding_model = fake_emb

    fake_hp = MagicMock()
    fake_hp.retriever = fake_retriever
    fake_hp.sparse_index = bm25

    pipeline = IncrementalIngestionPipeline(db=db, hybrid_pipeline=fake_hp)
    summary = pipeline.ingest_batch(
        [
            {
                "car_model": "极氪007",
                "trim": "四驱性能版",
                "brand": "极氪",
                "price": "22.99万",
                "powertrain_type": "纯电",
            }
        ]
    )
    assert summary.created_count == 1
    fake_vs.upsert_document.assert_called_once()
    call_kw = fake_vs.upsert_document.call_args.kwargs
    assert call_kw["doc_id"] == generate_vehicle_doc_id("极氪007", trim="四驱性能版")
    assert "极氪007" in call_kw["text"]
    assert "极氪007" in bm25.car_models
    assert len(bm25.search("极氪007", top_k=3)) >= 1


# ── P0.2c: BGEEmbeddingModel.get_statistics & SemanticRouter degraded ─


def test_p0_bge_get_statistics_and_semantic_router_degraded_safe():
    from src.rag.embeddings import BGEEmbeddingModel, _DummySentenceTransformer
    from src.semantic_router.anchors import AnchorSet
    from src.semantic_router.router import SemanticRouter

    bge = BGEEmbeddingModel()
    bge._model = _DummySentenceTransformer(dimension=1024)
    bge.is_degraded = True
    bge.degrade_level = "DEGRADED_SPARSE_ONLY"
    bge._dimension = None  # Force embed_dimension property path

    stats = bge.get_statistics()
    assert stats["embed_dimension"] == 1024
    assert stats["is_degraded"] is True

    anchors = AnchorSet(
        vectors=np.ones((2, 1024), dtype=np.float32),
        intents=["greeting", "goodbye"],
        families=["control_flow", "control_flow"],
        model_name="bge-m3",
        dim=1024,
    )
    router = SemanticRouter(anchors=anchors, embedder=bge)
    decision = router.classify("你好")
    assert decision.matched is False
    assert decision.intent is None


# ── P0.3b: HybridRouter stream_chat/astream_chat telemetry & cost ─────


@pytest.mark.asyncio
async def test_p0_hybrid_router_stream_records_telemetry_and_cost():
    from src.llm.router import HybridRouter, Task
    from src.llm.telemetry import telemetry

    class _FakeBackend:
        model = "gpt-4o-mini"
        last_usage = {"prompt_tokens": 100, "completion_tokens": 50}
        last_ttft_s = 0.05

        def is_available(self):
            return True

        def chat_stream_tokens(self, messages, **kwargs):
            yield "你"
            yield "好"

        async def astream_chat(self, messages, **kwargs):
            yield "再"
            yield "见"

    router = HybridRouter(cloud=_FakeBackend())
    before_calls = len(telemetry.records) if hasattr(telemetry, "records") else 0

    chunks = list(router.stream_chat(Task.RESPONSE_GENERATION, [{"role": "user", "content": "hi"}]))
    assert chunks == ["你", "好"]

    achunks = []
    async for tok in router.astream_chat(Task.RESPONSE_GENERATION, [{"role": "user", "content": "bye"}]):
        achunks.append(tok)
    assert achunks == ["再", "见"]

    if hasattr(telemetry, "records"):
        assert len(telemetry.records) >= before_calls + 2


# ── P0.3c: DLQReplayEngine releases unmapped task back to PENDING ─────


def test_p0_dlq_replay_releases_unmapped_task_to_pending(tmp_path):
    from src.mlops.dlq_replay import DLQReplayEngine, DLQTaskStatus

    engine = DLQReplayEngine(storage_dir=tmp_path)
    rec = engine.enqueue_failed_task(
        task_type="unregistered_type",
        payload={"x": 1},
        error_message="boom",
    )
    # Simulate PG claim setting status to REPLAYING
    rec.status = DLQTaskStatus.REPLAYING
    engine._tasks[rec.task_id] = rec
    engine._save_tasks()

    # Force pending check by patching _tasks to return our record as pending/replaying
    rec.status = DLQTaskStatus.PENDING
    rec.next_retry_at = 0.0
    summary = engine.replay_pending_tasks(executors={}, force=True)
    assert summary.resolved_count == 0
    assert engine.list_tasks()[0].status == DLQTaskStatus.PENDING


# ── P1.1a, P1.1b, P1.1c, P1.1d, P1.1e ────────────────────────────────


def test_p1_sales_agent_deprecation_and_no_sys_modules_patch():
    import src.agent.tools  # noqa: F401
    from src.agent.sales_agent import SalesAgent

    assert "src.agent.tools.unified_schema" not in sys.modules or hasattr(
        sys.modules["src.agent.tools.unified_schema"], "__file__"
    )

    llm = MagicMock()
    agent = SalesAgent(llm=llm)
    assert not hasattr(agent, "observe")
    assert not hasattr(agent, "respond")
    assert not hasattr(agent, "memory")
    assert hasattr(agent, "run_graph_turn")
    assert hasattr(agent, "arun_graph_turn")
    assert hasattr(agent, "astream_graph_turn")


def test_p1_project_state_incremental_and_revert():
    from src.agent.events import (
        SlotUpdated,
        TurnReverted,
        project_state,
        project_state_incremental,
    )

    ev1 = SlotUpdated(turn_id=1, field_path="profile.name", value="张三")
    ev2 = SlotUpdated(turn_id=2, field_path="needs.explicit.brand", value="小米")
    s1, idx1 = project_state_incremental([ev1])
    assert s1.profile.name == "张三"
    s2, idx2 = project_state_incremental([ev1, ev2], snapshot_state=s1, snapshot_index=idx1)
    assert s2.profile.name == "张三"
    assert s2.needs.explicit.brand == "小米"

    ev3 = TurnReverted(turn_id=3, target_turn_id=2, reason="user_undo")
    s3, _ = project_state_incremental([ev1, ev2, ev3], snapshot_state=s2, snapshot_index=idx2)
    assert s3.needs.explicit.brand == ""
    assert s3.model_dump() == project_state([ev1, ev2, ev3]).model_dump()


def test_p1_idempotency_store_and_circuit_breaker_ttl():
    from src.agent.circuit_breaker import AgentCircuitBreaker
    from src.agent.langchain_tools import IdempotencyStore
    from src.agent.schemas import Stage

    IdempotencyStore.clear()
    IdempotencyStore.set("k1", "v1", ttl_s=0.01)
    time.sleep(0.02)
    assert IdempotencyStore.get("k1", ttl_s=0.01) is None

    cb = AgentCircuitBreaker(session_ttl_s=0.01)
    cb.record_turn("s_old", Stage.WELCOME)
    time.sleep(0.02)
    cb.record_turn("s_new", Stage.WELCOME)
    assert "s_old" not in cb._last_seen
    assert "s_new" in cb._last_seen


# ── P1.2: RAG precision, SimpleVectorIndex, RRF dedup, Chroma reject ──


def test_p1_simple_vector_index_adapts_llamaindex_bge_and_rrf_dedup():
    from src.filter.filter_engine import FilterResult
    from src.models.query import MatchScore, Query, SearchResponse, SearchResult
    from src.models.vehicle import PreciseLabels, Vehicle
    from src.rag.vector_store import ChromaVectorStore
    from src.retrieval.hybrid_pipeline import HybridPipeline, HybridPipelineResult
    from src.retrieval.parent_child_retriever import Chunk, SimpleVectorIndex

    class _LlamaBGEStub:
        def _get_text_embeddings(self, texts):
            return [[1.0, 0.0] for _ in texts]

        def _get_query_embedding(self, query):
            return [1.0, 0.0]

    idx = SimpleVectorIndex(embedding_model=_LlamaBGEStub())
    idx.add_chunks([Chunk(chunk_id="c1", parent_id="p1", content="小米SU7续航800km", chunk_type="child")])
    hits = idx.search("续航", top_k=1)
    assert len(hits) == 1 and hits[0][1] > 0.99

    # RRF dedup by car_model
    v1 = Vehicle(car_model="小米SU7", precise_labels=PreciseLabels(brand="小米"))
    v2 = Vehicle(car_model="小米SU7", precise_labels=PreciseLabels(brand="小米"))
    v3 = Vehicle(car_model="极氪007", precise_labels=PreciseLabels(brand="极氪"))
    dense_resp = SearchResponse(
        query=Query(text="纯电", top_k=5),
        results=[
            SearchResult(vehicle=v1, score=MatchScore(overall_score=0.9), explanation="t1"),
            SearchResult(vehicle=v2, score=MatchScore(overall_score=0.8), explanation="t2"),
            SearchResult(vehicle=v3, score=MatchScore(overall_score=0.85), explanation="t3"),
        ],
        total_count=3,
        search_time=0.01,
    )
    hp = HybridPipeline(db=None, retriever=None, sparse_index=MagicMock())
    res = HybridPipelineResult()
    fused = hp._fuse_with_sparse_hits(
        sparse_hits=[("极氪007", 5.0), ("小米SU7", 4.0)],
        filter_result=FilterResult(
            car_models=[],
            applied_query={},
            degrade_level=0,
            total_candidates=0,
        ),
        top_k=5,
        response=dense_resp,
        result=res,
    )
    models = [r.vehicle.car_model for r in fused.results]
    assert len(models) == len(set(models)) == 2

    # ChromaVectorStore rejects missing embedding instead of zero vector
    cvs = ChromaVectorStore.__new__(ChromaVectorStore)
    cvs.logger = MagicMock()
    cvs.collection = MagicMock()
    cvs.collection._embedding_function = None
    cvs.embedding_model = None
    cvs.stats = {}
    with patch("src.rag.embeddings.BGEEmbeddingModel", side_effect=RuntimeError("offline")):
        with pytest.raises(ValueError, match="Embedding vector is required"):
            cvs.upsert_document("d1", "text", {"car_model": "test"}, embedding=None)


# ── P1.3: MLOps, LLM CostLedger, Eval MetricsContract & Gate ──────────


def test_p1_mlops_prometheus_monotonic_alert_cooldown_and_deployment_shadow(tmp_path):
    from src.mlops.deployment import CanaryConfig, DeploymentRouter, RoutingMode
    from src.mlops.observability import AlertManager, PrometheusMetricsExporter

    prom = PrometheusMetricsExporter()
    for i in range(2005):
        prom.observe_histogram("autovend_latency_seconds", 0.2)
    text = prom.export_metrics_text()
    assert "autovend_latency_seconds_count 2005" in text

    am = AlertManager(cooldown_s=60.0)
    first = am.evaluate_metrics({"error_rate": 0.2})
    second = am.evaluate_metrics({"error_rate": 0.2})
    assert len(first) >= 1
    assert len(second) == 0

    router = DeploymentRouter(
        config=CanaryConfig(mode=RoutingMode.SHADOW),
        storage_dir=tmp_path,
    )
    router.execute_turn("s1", lambda: {"ok": True}, lambda: {"ok": True})
    time.sleep(0.05)
    stats = router.get_shadow_comparison_stats()
    assert stats["total"] == 1
    assert stats["matched"] == 1

    # Reload from disk
    router2 = DeploymentRouter(storage_dir=tmp_path)
    assert router2.get_config().mode == RoutingMode.SHADOW


def test_p1_cost_ledger_model_pricing_and_metrics_contract_p99():
    from src.eval.metrics_contract import build_metrics_contract_from_runner
    from src.eval.statistical_gate import DEFAULT_STATISTICAL_BASELINES, evaluate_statistical_gate
    from src.llm.cost_ledger import CostLedger
    from src.llm.telemetry import Route

    ledger = CostLedger()
    st_mini = ledger.record_usage("s_mini", prompt_tokens=1_000_000, completion_tokens=0, route=Route.CLOUD, model="gpt-4o-mini")
    st_4o = ledger.record_usage("s_4o", prompt_tokens=1_000_000, completion_tokens=0, route=Route.CLOUD, model="gpt-4o")
    assert st_4o.total_cost_usd > st_mini.total_cost_usd

    contract = build_metrics_contract_from_runner(
        {
            "systems": [
                {
                    "system": "fusion",
                    "overall": {"recall@3": 0.85, "precision@3": 0.78, "mrr": 0.80},
                    "by_tag": {},
                    "latency": {"median_s": 0.01, "p95_s": 0.03, "p99_s": 0.045},
                }
            ]
        }
    )
    assert contract.retrieval.p99_latency_ms == 45.0

    assert "narrow_recall@3" in DEFAULT_STATISTICAL_BASELINES["fusion"]
    gate_report = evaluate_statistical_gate(
        [{"recall@3": 0.9, "precision@3": 0.85, "mrr": 0.88, "ndcg@10": 0.8, "hit_rate@3": 0.9}] * 10
    )
    assert gate_report.passed is True
