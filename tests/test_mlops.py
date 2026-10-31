"""
Comprehensive Unit & Integration Test Suite for AutoVend Enterprise MLOps & LLMOps Lifecycle.

Tests cover:
1. ExperimentTracker (runs, metrics, params, artifacts, best-run selection)
2. PromptRegistry (versioning, active promotion, instant rollback, diffing)
3. ModelRegistry (model catalog, stage promotion, production single-active lifecycle)
4. DatasetRegistry (SHA-256 fingerprinting and integrity verification)
5. SemanticDriftDetector (embedding drift, JS divergence intent shift, RAG degradation)
6. DeploymentRouter (Canary hashing, Shadow execution, SLA breach automated rollback)
7. Production Observability (OpenTelemetry spans, Prometheus metrics text, Alert triggers)
8. DLQReplayEngine (Dead Letter queueing, exponential backoff, precision replay)
9. FastAPI Endpoints (/api/v1/mlops/* and /metrics)
"""

import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from src.mlops.deployment import (
    CanaryConfig,
    DeploymentRouter,
    DeploymentStatus,
    RollbackPolicy,
    RoutingMode,
)
from src.mlops.dlq_replay import (
    DLQReplayEngine,
    DLQTaskStatus,
)
from src.mlops.drift import (
    DriftLevel,
    SemanticDriftDetector,
)
from src.mlops.observability import (
    AlertManager,
    AlertRule,
    AlertSeverity,
    OpenTelemetryTracer,
    PrometheusMetricsExporter,
)
from src.mlops.registry import (
    DatasetRegistry,
    ExperimentTracker,
    ModelRegistry,
    ModelStage,
    PromptRegistry,
    PromptStatus,
)


@pytest.fixture
def tmp_mlops_dir(tmp_path):
    """Isolated temporary storage directory for tests."""
    d = tmp_path / "mlops"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── 1. Experiment Tracker Tests ─────────────────────────────────────────


class TestExperimentTracker:
    def test_run_lifecycle_and_metrics(self, tmp_mlops_dir):
        tracker = ExperimentTracker(storage_dir=tmp_mlops_dir / "experiments")
        run = tracker.start_run(
            "retrieval_benchmark", run_name="bge_m3_fusion_v1", tags={"env": "test"}
        )

        assert run.status == "RUNNING"
        assert run.experiment_name == "retrieval_benchmark"

        tracker.log_param(run.run_id, "top_k", 5)
        tracker.log_param(run.run_id, "rerank", True)

        tracker.log_metric(run.run_id, "recall@5", 0.92, step=1)
        tracker.log_metric(run.run_id, "recall@5", 0.95, step=2)
        tracker.log_metric(run.run_id, "mrr@5", 0.88)

        artifact_file = tmp_mlops_dir / "report.json"
        artifact_file.write_text('{"ok": true}', encoding="utf-8")
        tracker.log_artifact(run.run_id, "report", str(artifact_file))

        ended = tracker.end_run(run.run_id, status="FINISHED")
        assert ended.status == "FINISHED"
        assert ended.end_time is not None
        assert ended.latest_metrics["recall@5"] == 0.95
        assert ended.latest_metrics["mrr@5"] == 0.88
        assert ended.params["top_k"] == 5

        # Query back
        fetched = tracker.get_run(run.run_id)
        assert fetched is not None
        assert fetched.run_id == run.run_id

    def test_best_run_selection(self, tmp_mlops_dir):
        tracker = ExperimentTracker(storage_dir=tmp_mlops_dir / "experiments")

        r1 = tracker.start_run("agent_eval", "v1")
        tracker.log_metric(r1.run_id, "faithfulness", 0.82)
        tracker.end_run(r1.run_id)

        r2 = tracker.start_run("agent_eval", "v2")
        tracker.log_metric(r2.run_id, "faithfulness", 0.96)
        tracker.end_run(r2.run_id)

        r3 = tracker.start_run("agent_eval", "v3")
        tracker.log_metric(r3.run_id, "faithfulness", 0.75)
        tracker.end_run(r3.run_id)

        best_max = tracker.get_best_run("agent_eval", "faithfulness", mode="max")
        assert best_max is not None
        assert best_max.run_id == r2.run_id
        assert best_max.latest_metrics["faithfulness"] == 0.96

        best_min = tracker.get_best_run("agent_eval", "faithfulness", mode="min")
        assert best_min is not None
        assert best_min.run_id == r3.run_id


# ── 2. Prompt Registry Tests ────────────────────────────────────────────


class TestPromptRegistry:
    def test_prompt_registration_and_versioning(self, tmp_mlops_dir):
        registry = PromptRegistry(storage_dir=tmp_mlops_dir / "prompts")

        # Register v1
        p1 = registry.register_prompt(
            prompt_name="sales_reply",
            template="You are AutoVend sales assistant. Help customer: {message}",
            input_variables=["message"],
            status=PromptStatus.ACTIVE,
        )
        assert p1.version == "v1"
        assert p1.status == PromptStatus.ACTIVE
        assert p1.prompt_hash != ""

        # Register v2 as CANARY
        p2 = registry.register_prompt(
            prompt_name="sales_reply",
            template="You are AutoVend sales consultant. Empathize and help: {message}",
            input_variables=["message"],
            status=PromptStatus.CANARY,
        )
        assert p2.version == "v2"
        assert p2.status == PromptStatus.CANARY

        # Active prompt should still be v1
        active = registry.get_active_prompt("sales_reply")
        assert active is not None
        assert active.version == "v1"

    def test_promotion_and_instant_rollback(self, tmp_mlops_dir):
        registry = PromptRegistry(storage_dir=tmp_mlops_dir / "prompts")

        registry.register_prompt("intent_parse", "Template 1", ["q"], status=PromptStatus.ACTIVE)
        registry.register_prompt("intent_parse", "Template 2", ["q"], status=PromptStatus.CANARY)

        # Promote v2 to ACTIVE
        promoted = registry.promote_prompt("intent_parse", "v2", PromptStatus.ACTIVE)
        assert promoted.status == PromptStatus.ACTIVE
        assert registry.get_active_prompt("intent_parse").version == "v2"

        # Rollback back to v1
        rolled_back = registry.rollback_prompt("intent_parse", "v1")
        assert rolled_back.version == "v1"
        assert registry.get_active_prompt("intent_parse").version == "v1"

    def test_prompt_diffing(self, tmp_mlops_dir):
        registry = PromptRegistry(storage_dir=tmp_mlops_dir / "prompts")
        registry.register_prompt("greeting", "Hello {name}!", ["name"])
        registry.register_prompt("greeting", "Welcome {name}! How can I help you?", ["name"])

        diff = registry.diff_prompts("greeting", "v1", "v2")
        assert diff["identical"] is False
        assert "-Hello {name}!" in diff["unified_diff"]
        assert "+Welcome {name}!" in diff["unified_diff"]


# ── 3. Model Registry Tests ─────────────────────────────────────────────


class TestModelRegistry:
    def test_model_lifecycle_and_promotion(self, tmp_mlops_dir):
        registry = ModelRegistry(storage_dir=tmp_mlops_dir / "models")

        m1 = registry.register_model(
            model_id="qwen-7b",
            version="v1.0.0",
            provider="vllm",
            model_name="Qwen/Qwen2.5-7B-Instruct",
            stage=ModelStage.PRODUCTION,
        )
        assert m1.stage == ModelStage.PRODUCTION

        m2 = registry.register_model(
            model_id="qwen-7b",
            version="v1.1.0",
            provider="vllm",
            model_name="Qwen/Qwen2.5-7B-Instruct",
            stage=ModelStage.CANARY,
        )
        assert m2.stage == ModelStage.CANARY

        # Promote v1.1.0 to PRODUCTION -> v1.0.0 should be archived
        promoted = registry.promote_model("qwen-7b", "v1.1.0", ModelStage.PRODUCTION)
        assert promoted.stage == ModelStage.PRODUCTION

        v1_updated = registry.get_model("qwen-7b", "v1.0.0")
        assert v1_updated.stage == ModelStage.ARCHIVED


# ── 4. Dataset Registry Tests ───────────────────────────────────────────


class TestDatasetRegistry:
    def test_dataset_checksum_and_integrity(self, tmp_mlops_dir):
        registry = DatasetRegistry(storage_dir=tmp_mlops_dir / "datasets")
        ds_file = tmp_mlops_dir / "golden_set.json"
        ds_file.write_text('[{"query": "suv", "expected": ["ES6"]}]', encoding="utf-8")

        ver = registry.register_dataset(
            dataset_name="golden_set",
            version="v1.0",
            file_path=ds_file,
            sample_count=1,
            schema_fields=["query", "expected"],
        )
        assert ver.sha256_hash != ""

        # Initial integrity check passes
        assert registry.verify_integrity("golden_set", "v1.0") is True

        # Tampering with dataset triggers integrity check failure
        ds_file.write_text('[{"tampered": true}]', encoding="utf-8")
        assert registry.verify_integrity("golden_set", "v1.0") is False


# ── 5. Semantic Drift Detector Tests ────────────────────────────────────


class TestSemanticDriftDetector:
    def test_embedding_drift_detection(self, tmp_mlops_dir):
        detector = SemanticDriftDetector(
            embedding_warning_threshold=0.15,
            embedding_critical_threshold=0.30,
            storage_dir=tmp_mlops_dir / "drift",
        )

        # Baseline: cluster around [1.0, 0.0, 0.0]
        rng = np.random.RandomState(42)
        base = rng.normal(loc=[1.0, 0.0, 0.0], scale=0.05, size=(50, 3))
        detector.set_baseline_embeddings(base)

        # Normal queries: same distribution
        normal_queries = rng.normal(loc=[1.0, 0.0, 0.0], scale=0.05, size=(20, 3))
        res_normal = detector.detect_embedding_drift(normal_queries)
        assert res_normal is not None
        assert res_normal.level == DriftLevel.NORMAL
        assert res_normal.centroid_distance < 0.10

        # Drifted queries: shifted towards [0.0, 1.0, 0.0]
        drifted_queries = rng.normal(loc=[0.0, 1.0, 0.0], scale=0.05, size=(20, 3))
        res_drifted = detector.detect_embedding_drift(drifted_queries)
        assert res_drifted is not None
        assert res_drifted.centroid_distance > 0.40
        assert res_drifted.level == DriftLevel.CRITICAL

    def test_query_intent_js_divergence(self, tmp_mlops_dir):
        detector = SemanticDriftDetector(storage_dir=tmp_mlops_dir / "drift")

        baseline_intent = {
            "welcome": 0.20,
            "profile_analysis": 0.20,
            "needs_analysis": 0.30,
            "car_selection": 0.20,
            "reservation": 0.10,
        }
        detector.set_baseline_intent_distribution(baseline_intent)

        # Matched production intents
        stable_intents = (
            ["welcome"] * 20
            + ["profile_analysis"] * 20
            + ["needs_analysis"] * 30
            + ["car_selection"] * 20
            + ["reservation"] * 10
        )
        shift_stable = detector.detect_intent_shift(stable_intents)
        assert shift_stable is not None
        assert shift_stable.level == DriftLevel.NORMAL
        assert shift_stable.js_divergence < 0.05

        # Heavily shifted distribution (e.g. sudden influx of reservations)
        drifted_intents = ["reservation"] * 80 + ["welcome"] * 20
        shift_drifted = detector.detect_intent_shift(drifted_intents)
        assert shift_drifted is not None
        assert shift_drifted.js_divergence > 0.15
        assert shift_drifted.max_shifted_intent == "reservation"
        assert shift_drifted.level in (DriftLevel.WARNING, DriftLevel.CRITICAL)

    def test_retrieval_degradation_and_report(self, tmp_mlops_dir):
        detector = SemanticDriftDetector(storage_dir=tmp_mlops_dir / "drift")
        # Record poor retrieval metrics
        for _ in range(15):
            detector.record_production_query(
                retrieval_hit=False, retrieval_top1_score=0.10, used_fallback=True
            )
        for _ in range(5):
            detector.record_production_query(
                retrieval_hit=True, retrieval_top1_score=0.75, used_fallback=False
            )

        rag_res = detector.detect_retrieval_degradation()
        assert rag_res is not None
        assert rag_res.hit_rate == 0.25
        assert rag_res.level == DriftLevel.CRITICAL
        assert len(rag_res.violations) > 0

        # Executive report generation
        report = detector.generate_drift_report()
        assert report.overall_level == DriftLevel.CRITICAL
        assert len(report.alerts) > 0

        md = report.to_markdown()
        assert "# AutoVend 生产环境语义漂移与分布偏移监控报告" in md
        assert "CRITICAL" in md


# ── 6. Canary / Shadow Deployment & Automated Rollback Tests ───────────


class TestDeploymentRouter:
    def test_session_stickiness_and_routing(self, tmp_mlops_dir):
        router = DeploymentRouter(
            config=CanaryConfig(
                baseline_version="v1",
                candidate_version="v2",
                mode=RoutingMode.CANARY,
                canary_weight=0.30,
            ),
            storage_dir=tmp_mlops_dir / "deployment",
        )

        # Same session ID must deterministically route to the exact same variant
        decision_1 = router.decide_route("user_session_abc_123")
        decision_2 = router.decide_route("user_session_abc_123")
        assert decision_1.target_variant == decision_2.target_variant
        assert decision_1.routed_version == decision_2.routed_version

    def test_shadow_execution_mode(self, tmp_mlops_dir):
        router = DeploymentRouter(
            config=CanaryConfig(
                baseline_version="v1",
                candidate_version="v2",
                mode=RoutingMode.SHADOW,
            ),
            storage_dir=tmp_mlops_dir / "deployment",
        )

        candidate_called = False

        def _baseline():
            return "baseline_reply"

        def _candidate():
            nonlocal candidate_called
            candidate_called = True
            return "candidate_reply"

        res = router.execute_turn("sess_shadow_1", _baseline, _candidate)
        assert res.primary_result == "baseline_reply"
        assert res.decision.is_shadow is True

        time.sleep(0.1)  # Allow background thread worker to finish
        assert candidate_called is True

    def test_automated_rollback_on_sla_breach(self, tmp_mlops_dir):
        policy = RollbackPolicy(
            max_error_rate=0.10,
            min_sample_size=5,
            consecutive_breaches_required=1,
        )
        router = DeploymentRouter(
            config=CanaryConfig(
                baseline_version="v1",
                candidate_version="v2",
                mode=RoutingMode.CANARY,
                canary_weight=0.50,
                policy=policy,
            ),
            storage_dir=tmp_mlops_dir / "deployment",
        )

        assert router.config.status == DeploymentStatus.MONITORING

        # Feed consecutive candidate failures
        for i in range(10):
            router.record_turn_metric(
                session_id=f"sess_{i}",
                variant="candidate",
                success=False,
                latency_s=1.2,
            )

        # Router must have automatically triggered emergency rollback!
        assert router.config.status == DeploymentStatus.ROLLED_BACK
        assert router.config.mode == RoutingMode.BASELINE_ONLY
        assert router.config.canary_weight == 0.0
        assert "exceeded threshold" in router.config.last_rollback_reason


# ── 7. Observability, Prometheus Exporter & Alerts ───────────────────────


class TestObservabilityAndPrometheus:
    def test_opentelemetry_tracing(self, tmp_mlops_dir):
        tracer = OpenTelemetryTracer(storage_dir=tmp_mlops_dir / "traces")
        span = tracer.record_agent_turn_span(
            session_id="sess_trace_1",
            stage="needs_analysis",
            latency_s=0.45,
            success=True,
            prompt_tokens=250,
            completion_tokens=80,
            cost_usd=0.0012,
        )
        assert span.trace_id != ""
        assert span.attributes["gen_ai.usage.prompt_tokens"] == 250
        assert span.duration_s >= 0.0

        traces = tracer.get_traces_for_session("sess_trace_1")
        assert len(traces) >= 1

    def test_prometheus_exposition_format(self):
        exporter = PrometheusMetricsExporter()
        exporter.inc_counter("autovend_requests_total", 5.0, labels={"stage": "welcome"})
        exporter.set_gauge("autovend_canary_ratio", 0.15)
        exporter.observe_histogram("autovend_step_latency_seconds", 0.42, labels={"model": "vllm"})

        text = exporter.export_metrics_text()
        assert "# TYPE autovend_requests_total counter" in text
        assert 'autovend_requests_total{stage="welcome"} 5.0' in text
        assert "# TYPE autovend_gauge_metrics gauge" in text
        assert "autovend_canary_ratio 0.15" in text
        assert "# TYPE autovend_latency_seconds histogram" in text
        assert 'autovend_step_latency_seconds_bucket{model="vllm",le="0.5"} 1' in text

    def test_alert_manager_evaluation(self, tmp_mlops_dir):
        mgr = AlertManager(storage_dir=tmp_mlops_dir / "alerts")
        mgr.add_rule(
            AlertRule(
                name="CustomErrorBreach",
                metric_key="custom_failure_ratio",
                operator=">",
                threshold=0.04,
                severity=AlertSeverity.CRITICAL,
            )
        )

        # Under threshold -> no alert
        alerts_low = mgr.evaluate_metrics({"custom_failure_ratio": 0.02})
        assert len(alerts_low) == 0

        # Over threshold -> triggers critical alert
        alerts_high = mgr.evaluate_metrics({"custom_failure_ratio": 0.08})
        assert len(alerts_high) == 1
        assert alerts_high[0].rule_name == "CustomErrorBreach"
        assert alerts_high[0].severity == AlertSeverity.CRITICAL


# ── 8. DLQ & Precision Replay Tests ─────────────────────────────────────


class TestDLQReplayEngine:
    def test_enqueue_and_precision_replay(self, tmp_mlops_dir):
        engine = DLQReplayEngine(storage_dir=tmp_mlops_dir / "dlq", base_backoff_s=0.01)

        task = engine.enqueue_failed_task(
            task_type="llm_generation",
            payload={"prompt": "Describe car", "session_id": "s1"},
            error_message="503 Service Unavailable",
            error_category="network_error",
        )
        assert task.status == DLQTaskStatus.PENDING

        # Replay with succeeding executor
        def _successful_worker(payload):
            return f"Processed: {payload['prompt']}"

        ok = engine.replay_single_task(task.task_id, _successful_worker)
        assert ok is True

        tasks = engine.list_tasks(status=DLQTaskStatus.RESOLVED)
        assert len(tasks) == 1
        assert tasks[0].execution_result == "Processed: Describe car"

        purged = engine.purge_resolved()
        assert purged == 1
        assert len(engine.list_tasks()) == 0

    def test_max_attempts_exhaustion_to_dead_letter(self, tmp_mlops_dir):
        engine = DLQReplayEngine(storage_dir=tmp_mlops_dir / "dlq", base_backoff_s=0.01)

        task = engine.enqueue_failed_task(
            task_type="eval_judge",
            payload={"id": "item_9"},
            error_message="Model context length exceeded",
            max_attempts=3,
        )

        def _failing_worker(payload):
            raise RuntimeError("Fatal: still fails")

        # Retry 1 -> still pending
        engine.replay_single_task(task.task_id, _failing_worker)
        assert task.status == DLQTaskStatus.PENDING
        assert task.attempts == 2

        # Retry 2 -> exhausted to DEAD_LETTER
        engine.replay_single_task(task.task_id, _failing_worker)
        assert task.status == DLQTaskStatus.DEAD_LETTER
        assert task.attempts == 3


# ── 9. FastAPI Endpoint Integration Tests ───────────────────────────────


class TestFastAPIMLOpsEndpoints:
    def test_mlops_api_endpoints(self):
        client = TestClient(app)

        # 1. Prometheus /metrics
        res_metrics = client.get("/metrics")
        assert res_metrics.status_code == 200
        assert "text/plain" in res_metrics.headers["content-type"]
        assert "autovend_requests_total" in res_metrics.text

        # 2. Experiments
        res_exp = client.get("/api/v1/mlops/experiments")
        assert res_exp.status_code == 200
        assert "runs" in res_exp.json()

        # 3. Prompts
        res_prompts = client.get("/api/v1/mlops/prompts")
        assert res_prompts.status_code == 200

        # 4. Drift report
        res_drift = client.get("/api/v1/mlops/drift")
        assert res_drift.status_code == 200
        assert "overall_level" in res_drift.json()

        res_drift_md = client.get("/api/v1/mlops/drift?format=markdown")
        assert res_drift_md.status_code == 200
        assert "# AutoVend 生产环境语义漂移与分布偏移监控报告" in res_drift_md.text

        # 5. Canary health & config
        res_canary = client.get("/api/v1/mlops/canary")
        assert res_canary.status_code == 200
        assert "candidate_metrics" in res_canary.json()

        res_canary_cfg = client.post(
            "/api/v1/mlops/canary/config",
            json={"canary_weight": 0.25, "mode": "canary"},
        )
        assert res_canary_cfg.status_code == 200

        # 6. DLQ list and replay
        res_dlq = client.get("/api/v1/mlops/dlq")
        assert res_dlq.status_code == 200
        assert "tasks" in res_dlq.json()

        res_replay = client.post("/api/v1/mlops/dlq/replay?force=true")
        assert res_replay.status_code == 200
        assert res_replay.json()["status"] == "completed"


# ── 10. Hardening, Concurrency & Extreme Edge Cases ──────────────────────


class TestEnterpriseHardeningAndEdgeCases:
    def test_concurrent_load_and_thread_safety(self, tmp_mlops_dir):
        """Verify thread-safety of DeploymentRouter and DLQ under concurrent thread contention."""
        import concurrent.futures

        router = DeploymentRouter(storage_dir=tmp_mlops_dir / "canary_concurrent")
        dlq = DLQReplayEngine(storage_dir=tmp_mlops_dir / "dlq_concurrent")

        def _worker(worker_id: int):
            for i in range(20):
                sess_id = f"worker_{worker_id}_sess_{i}"
                decision = router.decide_route(sess_id)
                router.record_turn_metric(
                    session_id=sess_id,
                    variant=decision.target_variant,
                    success=(i % 5 != 0),
                    latency_s=0.1 + (i * 0.01),
                )
                if i % 7 == 0:
                    dlq.enqueue_failed_task(
                        task_type="llm_generation",
                        payload={"worker": worker_id, "idx": i},
                        error_message="Simulated concurrency error",
                    )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_worker, w) for w in range(10)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        health = router.get_canary_health()
        assert health["baseline_metrics"]["sample_size"] > 0
        tasks = dlq.list_tasks()
        assert len(tasks) > 0

    def test_canary_routing_arbitrary_session_types(self, tmp_mlops_dir):
        """Verify routing consistency across unicode, UUID, int, and complex session identifiers."""
        import uuid

        router = DeploymentRouter(storage_dir=tmp_mlops_dir / "canary_types")

        types_to_test = [
            "客户_北京_朝阳_9527",
            "Customer_🚗_Electric_SUV",
            uuid.uuid4(),
            12345678,
            "user@domain.com#session-token",
            "",
        ]

        for s_id in types_to_test:
            d1 = router.decide_route(s_id)
            d2 = router.decide_route(s_id)
            # Deterministic stickiness: identical session must yield identical route
            assert d1.target_variant == d2.target_variant
            assert d1.routed_version == d2.routed_version

    def test_drift_detector_dimension_mismatch_resilience(self, tmp_mlops_dir):
        """Verify drift detector handles embedding dimension changes gracefully without uncaught ValueError."""
        detector = SemanticDriftDetector(storage_dir=tmp_mlops_dir / "drift_dim")

        # Baseline with 1024-dim vectors (e.g. BGE-M3)
        np.random.seed(42)
        base_embs = np.random.randn(20, 1024).astype(np.float32)
        detector.set_baseline_embeddings(base_embs)

        # Mismatched 768-dim production vector (e.g. MiniLM or updated model without migration)
        mismatched_embs = np.random.randn(5, 768).astype(np.float32)
        res = detector.detect_embedding_drift(mismatched_embs)

        assert res is not None
        assert res.level == DriftLevel.CRITICAL
        assert "Dimension mismatch" in str(res.details)

    def test_default_bootstrap_artifacts(self):
        """Verify that singletons are auto-bootstrapped with enterprise production templates and models."""
        from src.mlops import model_registry, prompt_registry

        prompt = prompt_registry.get_active_prompt("response_generation_welcome")
        assert prompt is not None
        assert "AutoVend" in prompt.template

        models = model_registry.list_models()
        assert len(models) >= 1
        qwen = model_registry.get_model("qwen2.5-7b-instruct", "v1.0")
        assert qwen is not None
        assert qwen.stage == ModelStage.PRODUCTION

    def test_deployment_router_baseline_error_capture(self, tmp_mlops_dir):
        """Verify baseline execution failures are captured in metrics and not lost."""
        router = DeploymentRouter(storage_dir=tmp_mlops_dir / "canary_err")

        def failing_baseline():
            raise RuntimeError("Database connection timed out in baseline")

        with pytest.raises(RuntimeError):
            router.execute_turn(
                session_id="err_sess_1",
                run_baseline=failing_baseline,
                run_candidate=lambda: "ok",
            )

        health = router.get_canary_health()
        assert health["baseline_metrics"]["sample_size"] == 1
        assert health["baseline_metrics"]["error_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_voice_process_event_loop_safety(self):
        """Verify VoicePipeline handles TTS inside an existing running asyncio loop without crashing."""
        from unittest.mock import MagicMock

        from src.agent.schemas import AgentResult, SessionState, Stage
        from src.agent.voice.pipeline import VoicePipeline
        from src.agent.voice.tts import TTSResult

        mock_agent = MagicMock()
        mock_agent.process.return_value = AgentResult(
            session_state=SessionState(session_id="loop_sess", stage=Stage.PROFILE_ANALYSIS),
            response_text="您好，请问您怎么称呼？",
            stage_changed=True,
        )

        mock_asr = MagicMock()
        mock_trans = MagicMock()
        mock_trans.text = "你好"
        mock_trans.language = "zh"
        mock_trans.language_probability = 0.99
        mock_trans.processing_time_ms = 45.0
        mock_asr.transcribe_bytes.return_value = mock_trans

        mock_tts = MagicMock()
        mock_tts.voice = "zh-CN-XiaoxiaoNeural"
        mock_tts.synthesize.return_value = TTSResult(
            audio_bytes=b"\x00\x01\x02",
            voice="zh-CN-XiaoxiaoNeural",
            processing_time_ms=80.0,
        )

        pipeline = VoicePipeline(agent=mock_agent, asr=mock_asr, tts=mock_tts)
        state = SessionState(session_id="loop_sess", stage=Stage.WELCOME)

        # Call within running async loop
        turn_result = pipeline.process_audio_bytes(b"dummy_pcm", state)

        assert turn_result.agent_response == "您好，请问您怎么称呼？"
        assert turn_result.session_state is not None
        assert turn_result.session_state.stage == Stage.PROFILE_ANALYSIS
        assert turn_result.stage_changed is True

    def test_live_chat_mlops_integration(self):
        """Verify real chat route calls update Prometheus exporter, OpenTelemetry traces, and drift buffers."""
        from unittest.mock import MagicMock

        from backend.app.routes.chat import set_agent
        from src.agent.sales_agent import SalesAgent

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(text="{}")
        agent = SalesAgent(llm=mock_llm)
        set_agent(agent)

        client = TestClient(app)

        # Create session
        res_create = client.post("/api/chat/session", json={"phone_number": "13800138000"})
        assert res_create.status_code == 200
        sess_id = res_create.json()["session_id"]

        # Send turn
        res_msg = client.post(
            "/api/chat/message", json={"session_id": sess_id, "message": "我想看看30万左右的SUV"}
        )
        assert res_msg.status_code == 200

        # Check Prometheus exposition format output
        res_prom = client.get("/metrics")
        assert res_prom.status_code == 200
        assert "autovend_requests_total" in res_prom.text

        # Check drift buffer
        from src.mlops import semantic_drift_detector

        assert len(semantic_drift_detector.recent_intents) > 0
