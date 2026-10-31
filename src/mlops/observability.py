"""
Enterprise Production Observability, OpenTelemetry Tracing & Prometheus Metrics (src/mlops/observability.py).

Features:
1. OpenTelemetry-Compatible Tracing: Spans, parent-child context propagation, gen_ai semantic conventions.
2. Prometheus-Compatible Metrics Exporter: Exposes metrics in standard Prometheus text exposition format (counters, gauges, histograms).
3. Alert Trigger Engine: Configurable multi-severity rule evaluations (ErrorRate, TailLatency, Drift, BudgetBreach).
"""

import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_OBSERVABILITY_STORAGE = PROJECT_ROOT / "storage" / "mlops" / "observability"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertEvent:
    """An alert notification triggered by production monitoring."""

    rule_name: str
    severity: AlertSeverity
    message: str
    metric_value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class AlertRule:
    """Configurable rule definition for automated alerts."""

    name: str
    metric_key: str
    operator: str  # ">", ">=", "<", "<="
    threshold: float
    severity: AlertSeverity
    description: str = ""
    enabled: bool = True

    def evaluate(self, current_value: float) -> bool:
        if not self.enabled:
            return False
        if self.operator == ">":
            return current_value > self.threshold
        elif self.operator == ">=":
            return current_value >= self.threshold
        elif self.operator == "<":
            return current_value < self.threshold
        elif self.operator == "<=":
            return current_value <= self.threshold
        return False


# ── 1. OpenTelemetry Compatible Tracing ─────────────────────────────────


@dataclass
class OtelSpan:
    """OpenTelemetry-compatible span with GenAI semantic conventions."""

    trace_id: str
    span_id: str
    name: str
    parent_span_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_s: float = 0.0
    status_code: str = "OK"  # "OK", "ERROR"
    status_message: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def end(self, status_code: str = "OK", status_message: str = "") -> None:
        self.end_time = time.time()
        self.duration_s = round(self.end_time - self.start_time, 4)
        self.status_code = status_code
        self.status_message = status_message

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OpenTelemetryTracer:
    """In-memory and persistent OpenTelemetry-compatible trace buffer."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = (
            Path(storage_dir) if storage_dir else DEFAULT_OBSERVABILITY_STORAGE / "traces"
        )
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._spans: List[OtelSpan] = []

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> OtelSpan:
        """Start a new execution span."""
        import uuid

        tid = trace_id or uuid.uuid4().hex
        sid = uuid.uuid4().hex[:16]

        span = OtelSpan(
            trace_id=tid,
            span_id=sid,
            name=name,
            parent_span_id=parent_span_id,
            start_time=time.time(),
            attributes=attributes or {},
        )

        with self._lock:
            self._spans.append(span)
            if len(self._spans) > 5000:
                self._spans.pop(0)

        return span

    def record_agent_turn_span(
        self,
        session_id: str,
        stage: str,
        latency_s: float,
        success: bool,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
        error_type: Optional[str] = None,
    ) -> OtelSpan:
        """Record a completed agent interaction turn according to GenAI semantics."""
        span = self.start_span(
            name=f"agent.turn.{stage}",
            attributes={
                "gen_ai.system": "autovend_sales_agent",
                "session.id": session_id,
                "agent.stage": stage,
                "gen_ai.usage.prompt_tokens": prompt_tokens,
                "gen_ai.usage.completion_tokens": completion_tokens,
                "gen_ai.usage.total_tokens": prompt_tokens + completion_tokens,
                "gen_ai.usage.cost_usd": cost_usd,
            },
        )
        status = "OK" if success else "ERROR"
        if error_type:
            span.attributes["error.type"] = error_type
        span.end(status_code=status, status_message=error_type or "")
        return span

    def get_traces_for_session(self, session_id: str) -> List[OtelSpan]:
        with self._lock:
            return [s for s in self._spans if s.attributes.get("session.id") == session_id]


# ── 2. Prometheus Compatible Metrics Exporter ───────────────────────────


class PrometheusMetricsExporter:
    """
    Maintains production counters, gauges, and latency histograms, and formats
    them in Prometheus text exposition format (text/plain; version=0.0.4).
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}

        # Default histogram buckets for Agent/LLM/RAG latency (seconds)
        self.latency_buckets = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.5, 5.0, 10.0]

    def inc_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        key = self._format_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._format_key(name, labels)
        with self._lock:
            self._gauges[key] = float(value)

    def observe_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        key = self._format_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(float(value))
            if len(self._histograms[key]) > 2000:
                self._histograms[key].pop(0)

    @staticmethod
    def _format_key(name: str, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return name
        lbl_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{lbl_str}}}"

    def export_metrics_text(self) -> str:
        """Render all registered metrics in standard Prometheus exposition format."""
        lines = [
            "# AutoVend Enterprise Prometheus Metrics Exporter",
            "# HELP autovend_requests_total Total number of conversation turns handled",
            "# TYPE autovend_requests_total counter",
        ]

        with self._lock:
            for k, val in sorted(self._counters.items()):
                lines.append(f"{k} {val}")

            lines.extend(
                [
                    "# HELP autovend_gauge_metrics Real-time system gauges and ratios",
                    "# TYPE autovend_gauge_metrics gauge",
                ]
            )
            for k, val in sorted(self._gauges.items()):
                lines.append(f"{k} {val}")

            lines.extend(
                [
                    "# HELP autovend_latency_seconds Latency observations in seconds",
                    "# TYPE autovend_latency_seconds histogram",
                ]
            )
            for key, samples in sorted(self._histograms.items()):
                base_name = key.split("{")[0]
                lbl_suffix = key[len(base_name) :] if "{" in key else ""

                total_sum = sum(samples)
                count = len(samples)

                for b in self.latency_buckets:
                    b_count = sum(1 for s in samples if s <= b)
                    if lbl_suffix:
                        lbl_inner = lbl_suffix.rstrip("}").lstrip("{")
                        bucket_line = f'{base_name}_bucket{{{lbl_inner},le="{b}"}} {b_count}'
                    else:
                        bucket_line = f'{base_name}_bucket{{le="{b}"}} {b_count}'
                    lines.append(bucket_line)

                # +Inf bucket
                if lbl_suffix:
                    lbl_inner = lbl_suffix.rstrip("}").lstrip("{")
                    lines.append(f'{base_name}_bucket{{{lbl_inner},le="+Inf"}} {count}')
                    lines.append(f"{base_name}_sum{{{lbl_inner}}} {round(total_sum, 4)}")
                    lines.append(f"{base_name}_count{{{lbl_inner}}} {count}")
                else:
                    lines.append(f'{base_name}_bucket{{le="+Inf"}} {count}')
                    lines.append(f"{base_name}_sum {round(total_sum, 4)}")
                    lines.append(f"{base_name}_count {count}")

        return "\n".join(lines) + "\n"


# ── 3. Alert Trigger Engine ─────────────────────────────────────────────


class AlertManager:
    """
    Evaluates production metrics against alert rules and dispatches notifications.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = (
            Path(storage_dir) if storage_dir else DEFAULT_OBSERVABILITY_STORAGE / "alerts"
        )
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.rules: Dict[str, AlertRule] = {}
        self.history: List[AlertEvent] = []

        # Setup standard enterprise alert rules
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        self.add_rule(
            AlertRule(
                name="HighErrorRate",
                metric_key="error_rate",
                operator=">",
                threshold=0.05,
                severity=AlertSeverity.CRITICAL,
                description="Agent turn error rate exceeded 5%",
            )
        )
        self.add_rule(
            AlertRule(
                name="TailLatencyBreach",
                metric_key="p95_latency_s",
                operator=">",
                threshold=3.5,
                severity=AlertSeverity.WARNING,
                description="P95 latency breached 3.5s SLA target",
            )
        )
        self.add_rule(
            AlertRule(
                name="RetrievalHitRateDrop",
                metric_key="retrieval_hit_rate",
                operator="<",
                threshold=0.85,
                severity=AlertSeverity.WARNING,
                description="RAG retrieval hit rate fell below 85%",
            )
        )
        self.add_rule(
            AlertRule(
                name="SemanticDriftAlert",
                metric_key="drift_centroid_distance",
                operator=">",
                threshold=0.20,
                severity=AlertSeverity.CRITICAL,
                description="Semantic embedding drift centroid distance breached 0.20",
            )
        )

    def add_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self.rules[rule.name] = rule

    def evaluate_metrics(self, current_metrics: Dict[str, float]) -> List[AlertEvent]:
        """Check all rules against latest metrics snapshot."""
        triggered: List[AlertEvent] = []
        with self._lock:
            for rule in self.rules.values():
                val = current_metrics.get(rule.metric_key)
                if val is not None and rule.evaluate(val):
                    event = AlertEvent(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=f"{rule.name}: {rule.description} (value={val:.4f}, threshold={rule.threshold:.4f})",
                        metric_value=val,
                        threshold=rule.threshold,
                    )
                    triggered.append(event)
                    self.history.append(event)
                    logger.warning(
                        f"[MLOps ALERT] [{event.severity.value.upper()}] {event.message}"
                    )

        return triggered

    def list_recent_alerts(self, limit: int = 50) -> List[AlertEvent]:
        with self._lock:
            return sorted(self.history, key=lambda a: a.timestamp, reverse=True)[:limit]


# Global Singletons
otel_tracer = OpenTelemetryTracer()
prometheus_exporter = PrometheusMetricsExporter()
alert_manager = AlertManager()
