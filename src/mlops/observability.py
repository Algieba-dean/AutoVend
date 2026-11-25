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

from src.mlops.pg_store import MLOpsPostgresStore, is_test_env
from src.utils.config import PROJECT_ROOT, config
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_OBSERVABILITY_STORAGE = PROJECT_ROOT / "storage" / "mlops" / "observability"

# ── Real OpenTelemetry SDK initialization ─────────────────────────────────
_OTEL_SDK_AVAILABLE = False
_OTEL_PROVIDER = None
_OTEL_TRACER = None

try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover
    otel_trace = None  # type: ignore[assignment]


_OTEL_CONFIGURED_ENDPOINTS: set[str] = set()


def _init_otel_tracer(service_name: Optional[str] = None, otlp_endpoint: Optional[str] = None):
    global _OTEL_PROVIDER, _OTEL_TRACER
    if not _OTEL_SDK_AVAILABLE:
        return None

    endpoint = otlp_endpoint or config.otlp_endpoint
    if _OTEL_TRACER is not None:
        if endpoint and _OTEL_PROVIDER is not None and endpoint not in _OTEL_CONFIGURED_ENDPOINTS:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

                _OTEL_PROVIDER.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
                _OTEL_CONFIGURED_ENDPOINTS.add(endpoint)
                logger.info(f"OpenTelemetry OTLP exporter attached: endpoint={endpoint}")
            except Exception as exc:
                logger.warning(f"Failed to attach OTLPSpanExporter ({endpoint}): {exc}")
        return _OTEL_TRACER

    svc = service_name or config.otel_service_name or "autovend"
    resource = Resource.create({"service.name": svc, "deployment.environment": config.app_environment})
    provider = TracerProvider(resource=resource)

    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            _OTEL_CONFIGURED_ENDPOINTS.add(endpoint)
            logger.info(f"OpenTelemetry OTLP exporter configured: endpoint={endpoint}, service={svc}")
        except Exception as exc:
            logger.warning(f"Failed to configure OTLPSpanExporter ({endpoint}): {exc}")

    otel_trace.set_tracer_provider(provider)
    _OTEL_PROVIDER = provider
    _OTEL_TRACER = otel_trace.get_tracer("autovend.mlops", "2.0.0")
    return _OTEL_TRACER


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
    """OpenTelemetry span wrapper backed by real opentelemetry-sdk Span when available."""

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
    _sdk_span: Optional[Any] = field(default=None, repr=False, compare=False)
    _otel_token: Optional[Any] = field(default=None, repr=False, compare=False)

    def __enter__(self) -> "OtelSpan":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.end(status_code="ERROR", status_message=str(exc_val or exc_type.__name__))
        elif self.end_time is None:
            self.end(status_code="OK")

    def end(self, status_code: str = "OK", status_message: str = "") -> None:
        self.end_time = time.time()
        self.duration_s = round(self.end_time - self.start_time, 4)
        self.status_code = status_code
        self.status_message = status_message
        if self._otel_token is not None:
            try:
                var = getattr(self._otel_token, "var", None)
                if var is not None:
                    var.reset(self._otel_token)
                else:
                    from opentelemetry import context as otel_context

                    otel_context.detach(self._otel_token)
            except Exception:
                pass
            finally:
                self._otel_token = None
        if self._sdk_span is not None:
            try:
                from opentelemetry.trace import Status, StatusCode

                for k, v in self.attributes.items():
                    if isinstance(v, (str, bool, int, float)):
                        self._sdk_span.set_attribute(k, v)
                code = StatusCode.ERROR if status_code == "ERROR" else StatusCode.OK
                self._sdk_span.set_status(Status(code, status_message or ""))
                self._sdk_span.end()
            except Exception as exc:
                logger.debug(f"OTel SDK span end warning: {exc}")

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            }
        )
        if self._sdk_span is not None:
            try:
                self._sdk_span.add_event(name, attributes=attributes or {})
            except Exception:
                pass

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("_sdk_span", None)
        d.pop("_otel_token", None)
        return d


class OpenTelemetryTracer:
    """OpenTelemetry SDK-backed tracer with bounded in-memory ring buffer for session lookup."""

    def __init__(self, storage_dir: Optional[Path] = None, otlp_endpoint: Optional[str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._lock = threading.RLock()
        self._spans: List[OtelSpan] = []
        self._sdk_tracer = _init_otel_tracer(otlp_endpoint=otlp_endpoint)

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> OtelSpan:
        """Start a new execution span (and corresponding OTel SDK span)."""
        import uuid

        attrs = dict(attributes or {})
        sdk_span = None
        otel_token = None
        tid = trace_id or uuid.uuid4().hex
        sid = uuid.uuid4().hex[:16]

        if self._sdk_tracer is not None:
            try:
                from opentelemetry import context as otel_context
                from opentelemetry import trace as otel_trace

                safe_attrs = {k: v for k, v in attrs.items() if isinstance(v, (str, bool, int, float))}
                parent_ctx = otel_context.get_current()
                sdk_span = self._sdk_tracer.start_span(
                    name=name, context=parent_ctx, attributes=safe_attrs
                )
                otel_token = otel_context.attach(otel_trace.set_span_in_context(sdk_span, parent_ctx))
                ctx = sdk_span.get_span_context()
                if ctx and ctx.trace_id:
                    tid = trace_id or f"{ctx.trace_id:032x}"
                    sid = f"{ctx.span_id:016x}"
            except Exception as exc:
                logger.debug(f"OTel SDK start_span fallback: {exc}")
                sdk_span = None
                otel_token = None

        span = OtelSpan(
            trace_id=tid,
            span_id=sid,
            name=name,
            parent_span_id=parent_span_id,
            start_time=time.time(),
            attributes=attrs,
            _sdk_span=sdk_span,
            _otel_token=otel_token,
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
        # Cumulative monotonic histogram accumulators (Prometheus spec)
        self._histogram_counts: Dict[str, int] = {}
        self._histogram_sums: Dict[str, float] = {}
        self._histogram_buckets: Dict[str, Dict[float, int]] = {}

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
        val = float(value)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
                self._histogram_counts[key] = 0
                self._histogram_sums[key] = 0.0
                self._histogram_buckets[key] = {b: 0 for b in self.latency_buckets}
            self._histograms[key].append(val)
            if len(self._histograms[key]) > 2000:
                self._histograms[key].pop(0)
            self._histogram_counts[key] += 1
            self._histogram_sums[key] += val
            for b in self.latency_buckets:
                if val <= b:
                    self._histogram_buckets[key][b] += 1

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
            for key in sorted(self._histogram_counts.keys()):
                base_name = key.split("{")[0]
                lbl_suffix = key[len(base_name) :] if "{" in key else ""

                total_sum = self._histogram_sums[key]
                count = self._histogram_counts[key]
                bucket_counts = self._histogram_buckets[key]

                for b in self.latency_buckets:
                    b_count = bucket_counts.get(b, 0)
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
    Evaluates production metrics against alert rules, persists events to PostgreSQL
    in non-test environments, and dispatches notifications.
    """

    def __init__(self, storage_dir: Optional[Path] = None, cooldown_s: float = 300.0):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self.cooldown_s = max(0.0, float(cooldown_s))
        self._lock = threading.RLock()
        self.rules: Dict[str, AlertRule] = {}
        self.history: List[AlertEvent] = []
        self._last_fired_at: Dict[str, float] = {}

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
        # Agent Business SLO rules
        self.add_rule(
            AlertRule(
                name="CRAGRewriteRateHigh",
                metric_key="crag_rewrite_rate",
                operator=">",
                threshold=0.30,
                severity=AlertSeverity.WARNING,
                description="CRAG query rewrite rate exceeded 30%",
            )
        )
        self.add_rule(
            AlertRule(
                name="AuditorRejectRateHigh",
                metric_key="auditor_reject_rate",
                operator=">",
                threshold=0.15,
                severity=AlertSeverity.CRITICAL,
                description="Anti-hallucination auditor reject rate exceeded 15%",
            )
        )
        self.add_rule(
            AlertRule(
                name="ZeroHitRateHigh",
                metric_key="zero_hit_rate",
                operator=">",
                threshold=0.10,
                severity=AlertSeverity.WARNING,
                description="RAG zero-hit rate exceeded 10%",
            )
        )
        self.add_rule(
            AlertRule(
                name="CircuitBreakerTripRateHigh",
                metric_key="circuit_breaker_trip_rate",
                operator=">",
                threshold=0.05,
                severity=AlertSeverity.CRITICAL,
                description="Agent anti-loop circuit breaker trip rate exceeded 5%",
            )
        )

    def add_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self.rules[rule.name] = rule

    def evaluate_metrics(self, current_metrics: Dict[str, float]) -> List[AlertEvent]:
        """Check all rules against latest metrics snapshot with deduplication & cooldown."""
        triggered: List[AlertEvent] = []
        now = time.time()
        with self._lock:
            for rule in self.rules.values():
                val = current_metrics.get(rule.metric_key)
                if val is not None and rule.evaluate(val):
                    last_ts = self._last_fired_at.get(rule.name)
                    if self.cooldown_s > 0 and last_ts is not None and (now - last_ts) < self.cooldown_s:
                        continue
                    self._last_fired_at[rule.name] = now
                    event = AlertEvent(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=f"{rule.name}: {rule.description} (value={val:.4f}, threshold={rule.threshold:.4f})",
                        metric_value=val,
                        threshold=rule.threshold,
                        timestamp=now,
                    )
                    triggered.append(event)
                    self.history.append(event)
                    if not is_test_env() and self.storage_dir is None:
                        try:
                            MLOpsPostgresStore.append_alert_event(event.to_dict())
                        except Exception as exc:
                            logger.warning(f"Failed to persist alert event to PostgreSQL: {exc}")
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
