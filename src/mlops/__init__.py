"""
AutoVend Enterprise MLOps & LLMOps Lifecycle Management Suite.

Modules:
- registry: Experiment tracking, prompt versioning, model registry, dataset metadata versioning
- drift: Semantic drift, embedding shift, query intent drift, RAG retrieval degradation detection
- deployment: Canary / Shadow deployment & A/B testing router with automated rollback
- observability: OpenTelemetry-compatible tracing, Prometheus metrics exporter, alert triggers
- dlq_replay: Dead Letter Queue (DLQ) persistent storage and precision retry/replay engine
"""

from src.mlops.deployment import (
    CanaryConfig,
    DeploymentRouter,
    RollbackPolicy,
    RoutingDecision,
    deployment_router,
)
from src.mlops.dlq_replay import (
    DLQReplayEngine,
    DLQTaskRecord,
    dlq_replay_engine,
)
from src.mlops.drift import (
    DriftReport,
    EmbeddingDriftResult,
    IntentShiftResult,
    RetrievalDegradationResult,
    SemanticDriftDetector,
    semantic_drift_detector,
)
from src.mlops.observability import (
    AlertEvent,
    AlertManager,
    AlertRule,
    AlertSeverity,
    OpenTelemetryTracer,
    PrometheusMetricsExporter,
    alert_manager,
    otel_tracer,
    prometheus_exporter,
)
from src.mlops.registry import (
    DatasetRegistry,
    DatasetVersion,
    ExperimentTracker,
    ModelRegistry,
    ModelStage,
    ModelVersion,
    PromptRegistry,
    PromptStatus,
    PromptVersion,
    RunRecord,
    dataset_registry,
    experiment_tracker,
    model_registry,
    prompt_registry,
)

__all__ = [
    # Registry
    "ExperimentTracker",
    "RunRecord",
    "experiment_tracker",
    "PromptRegistry",
    "PromptVersion",
    "PromptStatus",
    "prompt_registry",
    "ModelRegistry",
    "ModelVersion",
    "ModelStage",
    "model_registry",
    "DatasetRegistry",
    "DatasetVersion",
    "dataset_registry",
    # Drift
    "SemanticDriftDetector",
    "DriftReport",
    "EmbeddingDriftResult",
    "IntentShiftResult",
    "RetrievalDegradationResult",
    "semantic_drift_detector",
    # Deployment
    "DeploymentRouter",
    "CanaryConfig",
    "RollbackPolicy",
    "RoutingDecision",
    "deployment_router",
    # Observability
    "OpenTelemetryTracer",
    "otel_tracer",
    "PrometheusMetricsExporter",
    "prometheus_exporter",
    "AlertManager",
    "AlertRule",
    "AlertEvent",
    "AlertSeverity",
    "alert_manager",
    # DLQ Replay
    "DLQReplayEngine",
    "DLQTaskRecord",
    "dlq_replay_engine",
]
