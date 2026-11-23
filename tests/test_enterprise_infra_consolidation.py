"""
Comprehensive tests for the 6 Enterprise Infrastructure Consolidation upgrades:
1. MLOps: Real OTel SDK spans, Postgres FOR UPDATE SKIP LOCKED DLQ, Postgres Registry fail-fast
2. Session & Lock: DistributedSessionStore & FileStorage/PostgresStorage fail-fast in prod/staging
3. Truth Engine: Master data repository & crawler incremental sync
4. Sparse & Hybrid SQL: PostgresFullTextIndex (tsvector + GIN) & single-SQL RRF CTE
5. Routing & Turn Classification: SemanticRouter calibration & structured-output TurnClassifier
6. PgVectorStore: Strict APP_ENV=test-only memory fallback, fail-fast in staging/prod
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.app.models.storage import FileStorage, PostgresStorage
from src.agent.schemas import SessionState, Stage
from src.agent.turn_classifier import TurnIntentClassification, classify_turn_intent
from src.core.storage.distributed_session import DistributedSessionStore
from src.crawler.engine import UniversalCrawlerEngine
from src.mlops.dlq_replay import DLQReplayEngine
from src.mlops.observability import OpenTelemetryTracer
from src.mlops.pg_store import MLOpsPostgresStore
from src.mlops.registry import ExperimentTracker
from src.rag.pgvector_store import PgVectorStore, _resolve_allow_memory_fallback
from src.retrieval.bm25_index import PostgresFullTextIndex
from src.semantic_router.anchors import AnchorSet
from src.semantic_router.router import SemanticRouter
from src.truth_engine.master_data import TruthMasterDataStore
from src.truth_engine.price_valuation import PriceValuationEngine


class TestIssue6PgVectorFailFast:
    def test_memory_fallback_blocked_in_staging_and_prod_even_if_explicit(self, monkeypatch):
        for env in ("production", "prod", "staging", "development"):
            monkeypatch.setenv("APP_ENV", env)
            assert _resolve_allow_memory_fallback(None) is False
            assert _resolve_allow_memory_fallback(True) is False

    def test_memory_fallback_allowed_only_in_test_env(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "test")
        assert _resolve_allow_memory_fallback(None) is True
        assert _resolve_allow_memory_fallback(False) is False

    def test_pgvector_raises_in_staging_when_pg_unavailable(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "staging")
        with pytest.raises(Exception):
            PgVectorStore(
                dsn="postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
                allow_memory_fallback=True,
            )


class TestIssue2SessionAndStorageFailFast:
    def test_distributed_session_requires_redis_in_prod_and_staging(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("REDIS_URL", raising=False)
        with pytest.raises(RuntimeError, match="REDIS_URL is required"):
            DistributedSessionStore(redis_url=None)

        monkeypatch.setenv("APP_ENV", "staging")
        with pytest.raises(RuntimeError, match="REDIS_URL is required"):
            DistributedSessionStore(redis_url=None)

    def test_distributed_session_allows_local_in_test_mode(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.delenv("REDIS_URL", raising=False)
        store = DistributedSessionStore(redis_url=None)
        assert store._allow_local_fallback is True

    def test_file_storage_disabled_outside_test_mode(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(RuntimeError, match="FileStorage is deprecated"):
            FileStorage.load_session("any-session")

    def test_postgres_storage_fails_fast_in_prod_without_pg(self, monkeypatch):
        PostgresStorage.reset_for_tests()
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setattr(
            "backend.app.models.storage.config.pgvector_dsn",
            "postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
        )
        with pytest.raises(RuntimeError, match="PostgreSQL is required"):
            PostgresStorage.load_session("s1")
        PostgresStorage.reset_for_tests()


class TestIssue1MLOpsEnterprise:
    def test_otel_tracer_creates_real_sdk_span(self):
        tracer = OpenTelemetryTracer()
        span = tracer.start_span("agent.test.span", attributes={"session.id": "s-otel-1"})
        assert span._sdk_span is not None
        span.add_event("checkpoint", {"step": 1})
        span.end(status_code="OK")
        assert span.status_code == "OK"
        assert "agent.test.span" == span.name
        assert len(tracer.get_traces_for_session("s-otel-1")) == 1

    def test_mlops_registry_and_dlq_fail_fast_in_prod_without_pg(self, monkeypatch):
        MLOpsPostgresStore.reset_for_tests()
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setattr(
            "src.mlops.pg_store.config.pgvector_dsn",
            "postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
        )
        tracker = ExperimentTracker()
        with pytest.raises(RuntimeError, match="PostgreSQL is required"):
            tracker.start_run("prod_exp")

        dlq = DLQReplayEngine()
        with pytest.raises(RuntimeError, match="PostgreSQL is required"):
            dlq.enqueue_failed_task("extractor", {"x": 1}, "boom")
        MLOpsPostgresStore.reset_for_tests()

    def test_dlq_uses_for_update_skip_locked_when_pg_active(self, monkeypatch):
        engine = DLQReplayEngine()
        monkeypatch.setattr(engine, "_use_postgres", lambda: True)
        claimed = [
            {
                "task_id": "dlq_1",
                "task_type": "extractor",
                "payload": {"msg": "hi"},
                "error_message": "err",
                "error_category": "schema",
                "attempts": 1,
                "max_attempts": 3,
                "next_retry_at": 0.0,
                "status": "replaying",
                "created_at": 1.0,
                "resolved_at": None,
                "execution_result": None,
            }
        ]
        with patch.object(MLOpsPostgresStore, "dlq_claim_pending", return_value=claimed) as mock_claim, \
             patch.object(MLOpsPostgresStore, "dlq_get", return_value=claimed[0]), \
             patch.object(MLOpsPostgresStore, "dlq_upsert") as mock_upsert:
            summary = engine.replay_pending_tasks(
                task_type="extractor",
                executors={"extractor": lambda p: {"ok": True}},
                force=True,
            )
            mock_claim.assert_called_once()
            assert mock_upsert.called
            assert summary.resolved_count == 1


class TestIssue3TruthEngineMasterData:
    def test_crawler_sync_updates_truth_engine_dynamically(self, monkeypatch):
        TruthMasterDataStore.reset_for_tests()
        monkeypatch.setenv("APP_ENV", "test")

        updated = UniversalCrawlerEngine.sync_pricing_to_truth_engine(
            [
                {
                    "car_model": "测试新车型X1",
                    "msrp_wan": 19.99,
                    "one_year_residual_rate": 0.82,
                    "three_year_residual_rate": 0.61,
                    "wholesale_price_range_wan": "15.0 - 16.0 万元",
                    "retail_price_range_wan": "16.5 - 17.5 万元",
                    "market_liquidity_rating": "极高",
                }
            ]
        )
        assert updated == 1

        engine = PriceValuationEngine()
        dep = engine.get_depreciation_data("测试新车型X1")
        assert dep is not None
        assert dep.one_year_residual_rate == 0.82

        calc = engine.calculate_drive_away_price("测试新车型X1")
        assert calc.msrp_wan == 19.99
        TruthMasterDataStore.reset_for_tests()

    def test_truth_master_data_fails_fast_in_prod_without_pg(self, monkeypatch):
        TruthMasterDataStore.reset_for_tests()
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setattr(
            "src.truth_engine.master_data.config.pgvector_dsn",
            "postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
        )
        with pytest.raises(RuntimeError, match="PostgreSQL is required"):
            TruthMasterDataStore.get_depreciation_valuation("小米SU7 Max")
        TruthMasterDataStore.reset_for_tests()


class TestIssue4PostgresSparseAndHybridSQL:
    def _mock_pool(self, fetchall_rows=None):
        pool = MagicMock()
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchall.return_value = fetchall_rows or []
        cur.fetchone.return_value = (2,)
        cur_ctx = MagicMock()
        cur_ctx.__enter__.return_value = cur
        cur_ctx.__exit__.return_value = False
        conn.cursor.return_value = cur_ctx
        conn_ctx = MagicMock()
        conn_ctx.__enter__.return_value = conn
        conn_ctx.__exit__.return_value = False
        pool.connection.return_value = conn_ctx
        return pool, cur

    def test_postgres_fulltext_index_uses_tsvector_and_gin(self, monkeypatch):
        pool, cur = self._mock_pool(fetchall_rows=[("小米SU7 Max", 0.75)])
        idx = PostgresFullTextIndex.__new__(PostgresFullTextIndex)
        idx.dsn = "postgresql://localhost/test"
        idx.table_name = "vehicle_sparse_fts"
        idx._pool = pool

        idx._ensure_schema()
        idx.upsert_document("小米SU7 Max", "纯电 四驱 800V")
        hits = idx.search("小米SU7 800V", top_k=5)

        sql_log = "\n".join(str(c.args[0]) for c in cur.execute.call_args_list)
        assert "USING GIN (tsv)" in sql_log
        assert "to_tsvector('simple'" in sql_log
        assert "ts_rank_cd(tsv, to_tsquery('simple'" in sql_log
        assert hits == [("小米SU7 Max", 0.75)]

    def test_pgvector_hybrid_search_rrf_single_sql(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchall.return_value = [
            ("doc-1", "小米SU7 Max 纯电", {"car_model": "小米SU7 Max"}, 0.032)
        ]
        cur_ctx = MagicMock()
        cur_ctx.__enter__.return_value = cur
        cur_ctx.__exit__.return_value = False
        conn.cursor.return_value = cur_ctx

        store = PgVectorStore(
            table_name="vehicle_knowledge",
            embed_dim=4,
            connection=conn,
            allow_memory_fallback=False,
        )
        results = store.hybrid_search_rrf(
            query_embedding=[0.1, 0.2, 0.3, 0.4],
            query_text="小米SU7 纯电",
            top_k=5,
            where={"brand": "小米"},
        )
        sql_log = "\n".join(str(c.args[0]) for c in cur.execute.call_args_list)
        assert "FULL OUTER JOIN sparse" in sql_log
        assert "ts_rank_cd(tsv" in sql_log
        assert len(results) == 1
        assert results[0]["id"] == "doc-1"


class TestIssue5RoutingAndStructuredTurnClassifier:
    def test_semantic_router_calibrate_thresholds(self):
        class _FakeEmbedder:
            def _get_text_embedding(self, text):
                if "预算" in text:
                    return [1.0, 0.0]
                return [0.0, 1.0]

        anchors = AnchorSet(
            vectors=np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
            intents=["change_budget", "greeting"],
            families=["control_flow", "control_flow"],
            model_name="fake",
            dim=2,
        )
        router = SemanticRouter(anchors=anchors, embedder=_FakeEmbedder(), threshold=0.95, margin=0.5)
        t, m = router.calibrate_thresholds(
            [("刚才那个预算不太行，咱往下降点", "change_budget"), ("你好呀", "greeting")]
        )
        assert t <= 0.70
        assert router.classify("刚才那个预算不太行").intent == "change_budget"

    def test_structured_turn_classifier_handles_colloquial_constraint_change(self):
        expected = TurnIntentClassification(
            intent="constraint_update",
            is_interrupt=True,
            is_constraint_change=True,
            should_push_goal=False,
            retracted_constraints=["budget"],
            confidence=0.96,
        )

        class _FakeStructuredLLM:
            def invoke(self, messages):
                return expected

        class _FakeChatModel:
            def with_structured_output(self, schema):
                assert schema is TurnIntentClassification
                return _FakeStructuredLLM()

        sess = SessionState(session_id="s-cls-1", stage=Stage.CAR_SELECTION)
        res = classify_turn_intent(
            _FakeChatModel(),
            "刚才那个预算不太行，咱往下降点",
            Stage.CAR_SELECTION,
            sess,
        )
        assert res.is_interrupt is True

    def test_semantic_router_update_anchors_hot_reload(self):
        class _FakeEmbedder:
            def _get_text_embedding(self, text):
                if "降点" in text or "预算" in text:
                    return [1.0, 0.0]
                return [0.0, 1.0]

        anchors = AnchorSet(
            vectors=np.array([[0.0, 1.0]], dtype=np.float32),
            intents=["greeting"],
            families=["control_flow"],
            model_name="fake",
            dim=2,
        )
        router = SemanticRouter(anchors=anchors, embedder=_FakeEmbedder(), threshold=0.6, margin=0.03)
        count = router.update_anchors({"change_budget": ["预算往下降点"], "greeting": ["你好"]})
        assert count == 2
        assert router.classify("咱预算往下降点").intent == "change_budget"


class TestReviewRegressionFixes:
    def test_artifact_bundle_registry_fails_fast_in_prod_without_pg(self, monkeypatch):
        from src.mlops.registry import ArtifactBundleRegistry

        MLOpsPostgresStore.reset_for_tests()
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setattr(
            "src.mlops.pg_store.config.pgvector_dsn",
            "postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
        )
        reg = ArtifactBundleRegistry()
        with pytest.raises(RuntimeError, match="PostgreSQL is required"):
            reg.register_bundle("p1", "g1", "m1", "v1")
        MLOpsPostgresStore.reset_for_tests()

    def test_pgvector_schema_adds_tsv_column_and_fallback_hybrid_rrf(self, monkeypatch):
        conn = MagicMock()
        cur = MagicMock()
        cur_ctx = MagicMock()
        cur_ctx.__enter__.return_value = cur
        cur_ctx.__exit__.return_value = False
        conn.cursor.return_value = cur_ctx

        PgVectorStore(
            table_name="vehicle_knowledge",
            embed_dim=4,
            connection=conn,
            allow_memory_fallback=False,
        )
        sql_log = "\n".join(str(c.args[0]) for c in cur.execute.call_args_list)
        assert "ADD COLUMN IF NOT EXISTS tsv TSVECTOR" in sql_log

        monkeypatch.setenv("APP_ENV", "test")
        mem_store = PgVectorStore(
            table_name="vehicle_knowledge_test",
            embed_dim=3,
            dsn="postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
            allow_memory_fallback=True,
        )
        mem_store._fallback.upsert("doc-a", "比亚迪汉EV 续航605公里", {"car_model": "比亚迪汉EV"}, [1.0, 0.0, 0.0])
        mem_store._fallback.upsert("doc-b", "小米SU7 Max 四驱 800V", {"car_model": "小米SU7 Max"}, [1.0, 0.0, 0.0])
        hits = mem_store.hybrid_search_rrf([1.0, 0.0, 0.0], "小米SU7 800V", top_k=2)
        assert hits[0]["id"] == "doc-b"
        assert hits[0]["rrf_score"] > hits[1]["rrf_score"]
