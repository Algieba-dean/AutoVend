"""
Core AgentOps / MLOps / LLMOps Bridge (src/core/agentops.py).

Provides a clean facade over `src.mlops` (observability, drift, registry,
deployment, dlq_replay) and `src.privacy.security_logger` so `src/agent/`
remains isolated from `src.mlops` while gaining full enterprise telemetry,
SLO alerting, 4-in-1 artifact versioning, DLQ capture, and compliance auditing.
"""

import re
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.mlops.dlq_replay import dlq_replay_engine
from src.mlops.observability import alert_manager, otel_tracer, prometheus_exporter
from src.mlops.registry import artifact_bundle_registry
from src.privacy.security_logger import security_audit_logger

_PHONE_MASK_RE = re.compile(r"1[3-9]\d{9}")


def _sanitize_text(text: str) -> str:
    if not text:
        return ""
    return _PHONE_MASK_RE.sub("<CN_PHONE>", str(text))


def _sanitize_dict(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _sanitize_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_dict(v) for v in data[:10]]
    if isinstance(data, str):
        return _sanitize_text(data)[:500]
    return data


_DEFAULT_LOCAL_BUNDLE_VERSION = "v1.0.0-local"


def reset_artifact_bundle_cache() -> None:
    """Clear the in-memory artifact bundle version TTL cache (for tests)."""
    with artifact_bundle_registry._lock:
        artifact_bundle_registry._current = None
        artifact_bundle_registry._cached_at = 0.0


def get_current_artifact_bundle_version() -> str:
    """Return the active 4-in-1 artifact bundle version string (TTL-cached in registry, fail-open)."""
    try:
        return artifact_bundle_registry.get_current().bundle_version
    except Exception:
        return _DEFAULT_LOCAL_BUNDLE_VERSION


def extract_real_top1_score(matched_cars: Optional[List[Dict[str, Any]]]) -> float:
    """
    Extract real retrieval/rerank Top-1 confidence score from `matched_cars`.
    Returns 0.0 when `matched_cars` is empty.
    """
    if not matched_cars:
        return 0.0
    top1 = matched_cars[0] if isinstance(matched_cars[0], dict) else {}
    meta = top1.get("metadata") if isinstance(top1.get("metadata"), dict) else {}
    raw = (
        top1.get("rerank_score")
        if top1.get("rerank_score") is not None
        else top1.get("score")
        if top1.get("score") is not None
        else meta.get("rerank_score", meta.get("score"))
    )
    if raw is None:
        return 0.5
    try:
        val = float(raw)
        return max(0.0, min(1.0, round(val, 4)))
    except (TypeError, ValueError):
        return 0.5


def start_span(
    name: str,
    trace_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    return otel_tracer.start_span(
        name=name,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        attributes=attributes,
    )


def record_node_metrics(
    node_name: str,
    duration_s: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cached_tokens: int = 0,
    cost_usd: float = 0.0,
) -> None:
    """Record per-node latency, tokens, prompt cache hits, and cost to Prometheus."""
    labels = {"node": node_name}
    prometheus_exporter.observe_histogram("autovend_node_duration_seconds", duration_s, labels=labels)
    if prompt_tokens:
        prometheus_exporter.inc_counter("autovend_node_prompt_tokens_total", prompt_tokens, labels=labels)
    if completion_tokens:
        prometheus_exporter.inc_counter("autovend_node_completion_tokens_total", completion_tokens, labels=labels)
    if cached_tokens:
        prometheus_exporter.inc_counter("autovend_prompt_cache_hits_total", cached_tokens, labels=labels)
    if cost_usd > 0:
        prometheus_exporter.inc_counter("autovend_node_cost_usd_total", cost_usd, labels=labels)


@dataclass
class AgentSLOSnapshot:
    total_turns: int = 0
    crag_rewrites: int = 0
    auditor_rejects: int = 0
    zero_hits: int = 0
    circuit_breaker_trips: int = 0

    @property
    def crag_rewrite_rate(self) -> float:
        return self.crag_rewrites / self.total_turns if self.total_turns else 0.0

    @property
    def auditor_reject_rate(self) -> float:
        return self.auditor_rejects / self.total_turns if self.total_turns else 0.0

    @property
    def zero_hit_rate(self) -> float:
        return self.zero_hits / self.total_turns if self.total_turns else 0.0

    @property
    def circuit_breaker_trip_rate(self) -> float:
        return self.circuit_breaker_trips / self.total_turns if self.total_turns else 0.0

    def to_metrics_dict(self) -> Dict[str, float]:
        return {
            "crag_rewrite_rate": round(self.crag_rewrite_rate, 4),
            "auditor_reject_rate": round(self.auditor_reject_rate, 4),
            "zero_hit_rate": round(self.zero_hit_rate, 4),
            "circuit_breaker_trip_rate": round(self.circuit_breaker_trip_rate, 4),
        }


class AgentSLOMonitor:
    """Tracks Agent business SLOs and feeds AlertManager & Prometheus."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snap = AgentSLOSnapshot()

    def record_turn(
        self,
        *,
        crag_rewritten: bool = False,
        auditor_rejected: bool = False,
        zero_hit: bool = False,
        circuit_breaker_tripped: bool = False,
        evaluate_alerts: bool = True,
    ) -> Dict[str, float]:
        with self._lock:
            self._snap.total_turns += 1
            if crag_rewritten:
                self._snap.crag_rewrites += 1
            if auditor_rejected:
                self._snap.auditor_rejects += 1
            if zero_hit:
                self._snap.zero_hits += 1
            if circuit_breaker_tripped:
                self._snap.circuit_breaker_trips += 1
            metrics = self._snap.to_metrics_dict()

        for k, v in metrics.items():
            prometheus_exporter.set_gauge(f"autovend_slo_{k}", v)
        if evaluate_alerts:
            alert_manager.evaluate_metrics(metrics)
        return metrics

    def get_snapshot(self) -> Dict[str, float]:
        with self._lock:
            return self._snap.to_metrics_dict()

    def reset(self) -> None:
        with self._lock:
            self._snap = AgentSLOSnapshot()


agent_slo_monitor = AgentSLOMonitor()


def enqueue_agent_dlq(
    *,
    task_type: str,
    session_id: str,
    error_message: str,
    error_category: str,
    checkpoint_id: str = "",
    trace_id: str = "",
    user_message: str = "",
    stage: str = "",
    context_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Sanitize and enqueue an Agent failure event into DLQReplayEngine."""
    payload = {
        "session_id": session_id,
        "checkpoint_id": checkpoint_id,
        "trace_id": trace_id,
        "user_message": _sanitize_text(user_message),
        "stage": stage,
        "context_snapshot": _sanitize_dict(context_snapshot or {}),
    }
    try:
        dlq_replay_engine.enqueue_failed_task(
            task_type=task_type,
            payload=payload,
            error_message=_sanitize_text(error_message),
            error_category=error_category,
        )
    except Exception as exc:
        security_audit_logger.log_event(
            event_type="AGENT_DLQ_FALLBACK",
            severity="WARNING",
            session_id=session_id,
            trace_id=trace_id,
            details={"task_type": task_type, "dlq_error": str(exc)},
        )


def record_compliance_audit(
    *,
    event_type: str,
    session_id: str,
    trace_id: str = "",
    checkpoint_id: str = "",
    severity: str = "INFO",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Write structured compliance audit record (PromptSanitizer, EvidenceLedger,
    financial/reservation tools) correlated with `trace_id` and `checkpoint_id`.
    """
    sanitized_details = _sanitize_dict(details or {})
    sanitized_details["checkpoint_id"] = checkpoint_id
    security_audit_logger.log_event(
        event_type=event_type,
        severity=severity,
        session_id=session_id,
        trace_id=trace_id,
        details=sanitized_details,
    )
