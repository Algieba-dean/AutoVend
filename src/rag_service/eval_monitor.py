"""
Online RAG Evaluation & Query Drift Alerting Engine (src/rag_service/eval_monitor.py).

Monitors live RAG retrieval quality, score distribution, latency p95/p99,
and detects Out-of-Domain / vocabulary query drift to trigger automated alerts.
"""

import logging
import math
import time
from collections import deque
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RetrievalMetricsSnapshot(BaseModel):
    """Snapshot of metrics for a single RAG retrieval event."""

    timestamp: float = Field(default_factory=time.time)
    query_text: str
    top1_score: float
    candidate_count: int
    result_count: int
    latency_ms: float
    degrade_level: int
    is_out_of_domain: bool = False
    is_zero_result: bool = False


class QueryDriftAlert(BaseModel):
    """Structured alert emitted when query drift or performance degradation occurs."""

    alert_type: str  # e.g. "LOW_CONFIDENCE", "ZERO_RESULT_SPIKE", "OUT_OF_DOMAIN_DRIFT", "LATENCY_DRIFT"
    severity: str  # "WARNING" | "CRITICAL"
    message: str
    metrics_summary: Dict[str, Any]


class RAGEvalMonitor:
    """
    In-memory rolling analytics & drift detection engine for RAG Service.
    Maintains a sliding window of recent search events and evaluates drift indicators.
    """

    def __init__(
        self,
        window_size: int = 100,
        low_score_threshold: float = 0.35,
        max_latency_ms_threshold: float = 1500.0,
        ood_alert_ratio_threshold: float = 0.15,
    ):
        self.window_size = window_size
        self.low_score_threshold = low_score_threshold
        self.max_latency_ms_threshold = max_latency_ms_threshold
        self.ood_alert_ratio_threshold = ood_alert_ratio_threshold
        
        self.window: deque[RetrievalMetricsSnapshot] = deque(maxlen=window_size)

    def record_retrieval(
        self,
        query_text: str,
        results: List[Any],
        candidate_count: int,
        latency_ms: float,
        degrade_level: int = 0,
    ) -> List[QueryDriftAlert]:
        """
        Record a single retrieval execution, update rolling window, and run drift checks.

        Returns:
            List of generated QueryDriftAlerts (if any thresholds breached).
        """
        top1_score = results[0].score if (results and hasattr(results[0], "score")) else (
            results[0].get("score", 0.0) if (results and isinstance(results[0], dict)) else 0.0
        )
        result_count = len(results)
        is_zero = (result_count == 0 or candidate_count == 0)

        # Simple Out-of-Domain heuristic check for non-automotive topics
        is_ood = self._detect_out_of_domain(query_text)

        snapshot = RetrievalMetricsSnapshot(
            query_text=query_text,
            top1_score=top1_score,
            candidate_count=candidate_count,
            result_count=result_count,
            latency_ms=latency_ms,
            degrade_level=degrade_level,
            is_out_of_domain=is_ood,
            is_zero_result=is_zero,
        )

        self.window.append(snapshot)

        # Run real-time drift & quality evaluation
        return self._evaluate_drift_alerts(snapshot)

    def _detect_out_of_domain(self, text: str) -> bool:
        """Heuristic check for query domain drift (e.g. non-automotive prompts)."""
        if not text:
            return False
        ood_keywords = ["火锅", "烧烤", "代码", "python", "股市", "股票", "天气", "旅游", "电影", "游戏"]
        text_lower = text.lower()
        return any(kw in text_lower for kw in ood_keywords)

    def _evaluate_drift_alerts(self, current: RetrievalMetricsSnapshot) -> List[QueryDriftAlert]:
        """Check current snapshot and rolling metrics for alert conditions."""
        alerts: List[QueryDriftAlert] = []

        # 1. Single-event Critical: Zero candidate result
        if current.is_zero_result:
            alerts.append(
                QueryDriftAlert(
                    alert_type="ZERO_RESULT_SPIKE",
                    severity="CRITICAL",
                    message=f"检索出现空候选结果！Query: '{current.query_text}'",
                    metrics_summary={"query": current.query_text, "degrade_level": current.degrade_level},
                )
            )

        # 2. Single-event Warning: Latency Spike
        if current.latency_ms > self.max_latency_ms_threshold:
            alerts.append(
                QueryDriftAlert(
                    alert_type="LATENCY_DRIFT",
                    severity="WARNING",
                    message=f"RAG 检索延迟超时过高: {current.latency_ms:.1f} ms (阈值 {self.max_latency_ms_threshold} ms)",
                    metrics_summary={"query": current.query_text, "latency_ms": current.latency_ms},
                )
            )

        # 3. Rolling Window Drift Checks (triggers when window has >= 10 samples)
        if len(self.window) >= 10:
            total_samples = len(self.window)
            ood_count = sum(1 for s in self.window if s.is_out_of_domain)
            ood_ratio = ood_count / total_samples

            low_score_count = sum(1 for s in self.window if s.top1_score < self.low_score_threshold)
            low_score_ratio = low_score_count / total_samples

            avg_latency = sum(s.latency_ms for s in self.window) / total_samples

            # Alert if Query Out-of-Domain ratio > threshold
            if ood_ratio >= self.ood_alert_ratio_threshold:
                alerts.append(
                    QueryDriftAlert(
                        alert_type="OUT_OF_DOMAIN_DRIFT",
                        severity="WARNING",
                        message=f"检测到 Query 语义漂移！非汽车领域提问比例达到 {ood_ratio*100:.1f}%",
                        metrics_summary={
                            "window_size": total_samples,
                            "ood_ratio": round(ood_ratio, 3),
                            "avg_latency_ms": round(avg_latency, 1),
                        },
                    )
                )

            # Alert if Low Confidence score ratio > 30%
            if low_score_ratio > 0.30:
                alerts.append(
                    QueryDriftAlert(
                        alert_type="LOW_CONFIDENCE_DRIFT",
                        severity="WARNING",
                        message=f"滑动窗口内低置信度结果比例较高: {low_score_ratio*100:.1f}%",
                        metrics_summary={
                            "window_size": total_samples,
                            "low_score_ratio": round(low_score_ratio, 3),
                        },
                    )
                )

        return alerts

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Compute rolling summary stats over the current monitoring window."""
        if not self.window:
            return {"status": "NO_DATA", "total_samples": 0}

        total = len(self.window)
        scores = [s.top1_score for s in self.window if s.top1_score > 0]
        latencies = sorted([s.latency_ms for s in self.window])

        avg_score = sum(scores) / len(scores) if scores else 0.0
        p50_latency = latencies[int(total * 0.5)] if latencies else 0.0
        p95_latency = latencies[int(total * 0.95)] if latencies else 0.0

        return {
            "window_sample_count": total,
            "avg_top1_score": round(avg_score, 4),
            "p50_latency_ms": round(p50_latency, 1),
            "p95_latency_ms": round(p95_latency, 1),
            "zero_result_rate": round(sum(1 for s in self.window if s.is_zero_result) / total, 3),
            "ood_query_rate": round(sum(1 for s in self.window if s.is_out_of_domain) / total, 3),
        }
