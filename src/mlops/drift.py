"""
Semantic Drift & Distribution Shift Detection Engine (src/mlops/drift.py).

Monitors:
1. Embedding Drift: Centroid shift & cosine similarity distribution shift between reference and production embeddings.
2. Query Intent Shift: Jensen-Shannon divergence over user intent / conversation stage distributions.
3. RAG Retrieval Quality Degradation: Hit rate drop, zero-hit query spikes, top-1 confidence degradation.
"""

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DRIFT_STORAGE = PROJECT_ROOT / "storage" / "mlops" / "drift"


class DriftLevel(str, Enum):
    """Severity level for detected distribution drift."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class EmbeddingDriftResult:
    """Drift metrics for query embeddings."""

    centroid_distance: float
    mean_similarity_to_baseline_centroid: float
    similarity_percentile_p10: float
    similarity_percentile_p50: float
    similarity_percentile_p90: float
    sample_size: int
    level: DriftLevel
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentShiftResult:
    """Shift metrics for query intent and stage distribution."""

    js_divergence: float  # Jensen-Shannon Divergence in [0.0, 1.0]
    max_shifted_intent: str
    max_intent_delta: float
    observed_distribution: Dict[str, float]
    baseline_distribution: Dict[str, float]
    sample_size: int
    level: DriftLevel


@dataclass
class RetrievalDegradationResult:
    """Production RAG retrieval quality monitoring result."""

    hit_rate: float
    zero_hit_ratio: float
    mean_top1_score: float
    fallback_rate: float
    sample_size: int
    level: DriftLevel
    violations: List[str] = field(default_factory=list)


@dataclass
class DriftReport:
    """Comprehensive production distribution shift & quality degradation report."""

    timestamp: float = field(default_factory=time.time)
    overall_level: DriftLevel = DriftLevel.NORMAL
    embedding_drift: Optional[EmbeddingDriftResult] = None
    intent_shift: Optional[IntentShiftResult] = None
    retrieval_degradation: Optional[RetrievalDegradationResult] = None
    alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_level": self.overall_level.value,
            "embedding_drift": asdict(self.embedding_drift) if self.embedding_drift else None,
            "intent_shift": asdict(self.intent_shift) if self.intent_shift else None,
            "retrieval_degradation": asdict(self.retrieval_degradation)
            if self.retrieval_degradation
            else None,
            "alerts": self.alerts,
        }

    def to_markdown(self) -> str:
        lines = [
            "# AutoVend 生产环境语义漂移与分布偏移监控报告",
            f"*生成时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))} | 总体状态: **{self.overall_level.value.upper()}***\n",
        ]

        if self.alerts:
            lines.append("### ⚠️ 触发告警事项 (Active Drift Alerts):")
            for alert in self.alerts:
                lines.append(f"- 🚨 {alert}")
            lines.append("")

        if self.embedding_drift:
            ed = self.embedding_drift
            lines.extend(
                [
                    "## 1. 语义嵌入向量漂移 (Embedding Space Drift)",
                    "| 监控指标 | 当前测量值 | 判定状态 | 阈值说明 |",
                    "|---|---|---|---|",
                    f"| **中心点余弦距离 (Centroid Distance)** | **{ed.centroid_distance:.4f}** | `{ed.level.value}` | Warning ≥ 0.15, Critical ≥ 0.25 |",
                    f"| **对基线中心平均相似度** | {ed.mean_similarity_to_baseline_centroid:.4f} | - | 期望 ≥ 0.70 |",
                    f"| **相似度 P10 (尾部分布)** | {ed.similarity_percentile_p10:.4f} | - | 监测低相似度异常离群点 |",
                    f"| **相似度 P50 (中位数)** | {ed.similarity_percentile_p50:.4f} | - | - |",
                    f"| **生产采样数量** | {ed.sample_size} | - | - |",
                    "",
                ]
            )

        if self.intent_shift:
            ish = self.intent_shift
            lines.extend(
                [
                    "## 2. 用户意图分布偏移 (Query Intent & Stage Shift)",
                    "| 监控指标 | 当前数值 | 判定状态 | 阈值说明 |",
                    "|---|---|---|---|",
                    f"| **JS 散度 (Jensen-Shannon Divergence)** | **{ish.js_divergence:.4f}** | `{ish.level.value}` | Warning ≥ 0.12, Critical ≥ 0.20 |",
                    f"| **最大漂移类别** | `{ish.max_shifted_intent}` (Δ={ish.max_intent_delta:+.2%}) | - | 意图占比显著异动类别 |",
                    f"| **生产意图采样量** | {ish.sample_size} | - | - |",
                    "",
                ]
            )

        if self.retrieval_degradation:
            rd = self.retrieval_degradation
            lines.extend(
                [
                    "## 3. RAG 混合检索质量劣化 (Retrieval Quality Degradation)",
                    "| 指标 | 统计值 | 目标 SLA | 状态 |",
                    "|---|---|---|---|",
                    f"| **检索召回成功率 (Hit Rate)** | **{rd.hit_rate * 100:.1f}%** | 目标 ≥ 90.0% | `{rd.level.value}` |",
                    f"| **零命中查询率 (Zero-hit Ratio)** | **{rd.zero_hit_ratio * 100:.1f}%** | 目标 ≤ 5.0% | - |",
                    f"| **Top-1 检索平均置信分** | {rd.mean_top1_score:.4f} | 目标 ≥ 0.65 | - |",
                    f"| **降级策略触发率 (Fallback Rate)** | {rd.fallback_rate * 100:.1f}% | 目标 ≤ 8.0% | - |",
                    "",
                ]
            )

        return "\n".join(lines)


class SemanticDriftDetector:
    """
    Enterprise Drift and Distribution Shift Detector.
    Supports streaming rolling-window updates and offline comparative benchmark checks.
    """

    def __init__(
        self,
        embedding_warning_threshold: float = 0.15,
        embedding_critical_threshold: float = 0.25,
        intent_js_warning_threshold: float = 0.12,
        intent_js_critical_threshold: float = 0.20,
        retrieval_hit_rate_warning: float = 0.90,
        retrieval_hit_rate_critical: float = 0.80,
        storage_dir: Optional[Path] = None,
    ):
        self.embedding_warning_threshold = embedding_warning_threshold
        self.embedding_critical_threshold = embedding_critical_threshold
        self.intent_js_warning_threshold = intent_js_warning_threshold
        self.intent_js_critical_threshold = intent_js_critical_threshold
        self.retrieval_hit_rate_warning = retrieval_hit_rate_warning
        self.retrieval_hit_rate_critical = retrieval_hit_rate_critical

        self.storage_dir = Path(storage_dir) if storage_dir else DEFAULT_DRIFT_STORAGE
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        # In-memory baseline reference
        self.baseline_embeddings: Optional[np.ndarray] = None
        self.baseline_centroid: Optional[np.ndarray] = None
        self.baseline_intent_distribution: Dict[str, float] = {
            "welcome": 0.15,
            "profile_analysis": 0.25,
            "needs_analysis": 0.35,
            "car_selection": 0.15,
            "reservation": 0.10,
        }

        # Streaming production buffers
        self.recent_embeddings: List[np.ndarray] = []
        self.recent_intents: List[str] = []
        self.recent_retrievals: List[Dict[str, Any]] = []

    # ── Baseline Configuration ───────────────────────────────────────

    def set_baseline_embeddings(self, embeddings: Sequence[Sequence[float]] | np.ndarray) -> None:
        """Register golden / initial production reference query embeddings."""
        arr = np.array(embeddings, dtype=np.float32)
        if arr.ndim != 2 or len(arr) == 0:
            raise ValueError("Embeddings must be non-empty 2D array")

        # Normalize rows to unit length for cosine distance
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = arr / norms

        with self._lock:
            self.baseline_embeddings = normalized
            centroid = np.mean(normalized, axis=0)
            c_norm = np.linalg.norm(centroid)
            self.baseline_centroid = centroid / (c_norm if c_norm > 0 else 1.0)

        logger.info(f"[Drift] Baseline registered: {len(arr)} embeddings, dim={arr.shape[1]}")

    def set_baseline_intent_distribution(self, distribution: Dict[str, float]) -> None:
        """Register expected baseline proportion for intents or stages."""
        total = sum(distribution.values())
        if total <= 0:
            raise ValueError("Distribution weights must sum to > 0")
        with self._lock:
            self.baseline_intent_distribution = {k: v / total for k, v in distribution.items()}
        logger.info(
            f"[Drift] Baseline intent distribution registered: {self.baseline_intent_distribution}"
        )

    # ── Production Ingestion ──────────────────────────────────────────

    def record_production_query(
        self,
        embedding: Optional[Sequence[float] | np.ndarray] = None,
        intent: Optional[str] = None,
        retrieval_hit: Optional[bool] = None,
        retrieval_top1_score: Optional[float] = None,
        used_fallback: bool = False,
        max_buffer_size: int = 5000,
    ) -> None:
        """Record one live production user query for drift tracking."""
        with self._lock:
            if embedding is not None:
                vec = np.array(embedding, dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                self.recent_embeddings.append(vec)
                if len(self.recent_embeddings) > max_buffer_size:
                    self.recent_embeddings.pop(0)

            if intent:
                self.recent_intents.append(intent)
                if len(self.recent_intents) > max_buffer_size:
                    self.recent_intents.pop(0)

            if retrieval_hit is not None:
                self.recent_retrievals.append(
                    {
                        "hit": bool(retrieval_hit),
                        "score": float(retrieval_top1_score)
                        if retrieval_top1_score is not None
                        else 0.0,
                        "fallback": bool(used_fallback),
                        "timestamp": time.time(),
                    }
                )
                if len(self.recent_retrievals) > max_buffer_size:
                    self.recent_retrievals.pop(0)

    # ── Calculation Methods ───────────────────────────────────────────

    def detect_embedding_drift(
        self,
        current_embeddings: Optional[Sequence[Sequence[float]] | np.ndarray] = None,
    ) -> Optional[EmbeddingDriftResult]:
        """
        Compute embedding distribution drift against baseline centroid and percentiles.
        """
        with self._lock:
            if current_embeddings is None:
                if not self.recent_embeddings:
                    return None
                curr_arr = np.array(self.recent_embeddings, dtype=np.float32)
            else:
                curr_arr = np.array(current_embeddings, dtype=np.float32)
                norms = np.linalg.norm(curr_arr, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                curr_arr = curr_arr / norms

            if self.baseline_centroid is None or len(curr_arr) == 0:
                return None

            curr_centroid = np.mean(curr_arr, axis=0)
            cc_norm = np.linalg.norm(curr_centroid)
            if cc_norm > 0:
                curr_centroid = curr_centroid / cc_norm

            # Validate embedding dimensionality match
            if curr_centroid.shape != self.baseline_centroid.shape:
                logger.warning(
                    f"[Drift] Embedding dimension mismatch: baseline={self.baseline_centroid.shape}, observed={curr_centroid.shape}"
                )
                return EmbeddingDriftResult(
                    centroid_distance=1.0,
                    mean_similarity_to_baseline_centroid=0.0,
                    similarity_percentile_p10=0.0,
                    similarity_percentile_p50=0.0,
                    similarity_percentile_p90=0.0,
                    sample_size=len(curr_arr),
                    level=DriftLevel.CRITICAL,
                    details={
                        "error": f"Dimension mismatch: expected {self.baseline_centroid.shape[0]}, got {curr_centroid.shape[0]}"
                    },
                )

            # Cosine distance between centroids: 1 - dot(c1, c2)
            centroid_sim = float(np.dot(self.baseline_centroid, curr_centroid))
            centroid_distance = max(0.0, 1.0 - centroid_sim)

            # Similarities of individual production queries to baseline centroid
            sims = np.dot(curr_arr, self.baseline_centroid)
            mean_sim = float(np.mean(sims))
            p10 = float(np.percentile(sims, 10))
            p50 = float(np.percentile(sims, 50))
            p90 = float(np.percentile(sims, 90))

            level = DriftLevel.NORMAL
            if centroid_distance >= self.embedding_critical_threshold:
                level = DriftLevel.CRITICAL
            elif centroid_distance >= self.embedding_warning_threshold:
                level = DriftLevel.WARNING

            return EmbeddingDriftResult(
                centroid_distance=round(centroid_distance, 4),
                mean_similarity_to_baseline_centroid=round(mean_sim, 4),
                similarity_percentile_p10=round(p10, 4),
                similarity_percentile_p50=round(p50, 4),
                similarity_percentile_p90=round(p90, 4),
                sample_size=len(curr_arr),
                level=level,
            )

    def detect_intent_shift(
        self,
        current_intents: Optional[Sequence[str]] = None,
    ) -> Optional[IntentShiftResult]:
        """
        Compute Jensen-Shannon Divergence between baseline and observed intent distributions.
        """
        with self._lock:
            intents = (
                list(current_intents) if current_intents is not None else list(self.recent_intents)
            )
            if not intents or not self.baseline_intent_distribution:
                return None

            # Calculate observed empirical distribution
            counts: Dict[str, int] = {}
            for item in intents:
                counts[item] = counts.get(item, 0) + 1
            total = len(intents)
            observed = {k: v / total for k, v in counts.items()}

            all_keys = set(self.baseline_intent_distribution.keys()).union(observed.keys())

            # Form probability vectors with Laplace-like epsilon smoothing for unobserved keys
            eps = 1e-6
            p_list = []
            q_list = []
            for k in all_keys:
                p_list.append(self.baseline_intent_distribution.get(k, 0.0) + eps)
                q_list.append(observed.get(k, 0.0) + eps)

            p_vec = np.array(p_list) / sum(p_list)
            q_vec = np.array(q_list) / sum(q_list)

            # Compute JS Divergence: JS = 0.5 * KL(P||M) + 0.5 * KL(Q||M)
            m_vec = 0.5 * (p_vec + q_vec)
            kl_p_m = float(np.sum(p_vec * np.log2(p_vec / m_vec)))
            kl_q_m = float(np.sum(q_vec * np.log2(q_vec / m_vec)))
            js_div = max(0.0, min(1.0, 0.5 * (kl_p_m + kl_q_m)))

            # Identify category with largest percentage shift
            max_delta = 0.0
            max_intent = ""
            for k in all_keys:
                delta = observed.get(k, 0.0) - self.baseline_intent_distribution.get(k, 0.0)
                if abs(delta) > abs(max_delta):
                    max_delta = delta
                    max_intent = k

            level = DriftLevel.NORMAL
            if js_div >= self.intent_js_critical_threshold:
                level = DriftLevel.CRITICAL
            elif js_div >= self.intent_js_warning_threshold:
                level = DriftLevel.WARNING

            return IntentShiftResult(
                js_divergence=round(js_div, 4),
                max_shifted_intent=max_intent,
                max_intent_delta=round(max_delta, 4),
                observed_distribution={k: round(v, 4) for k, v in observed.items()},
                baseline_distribution={
                    k: round(v, 4) for k, v in self.baseline_intent_distribution.items()
                },
                sample_size=total,
                level=level,
            )

    def detect_retrieval_degradation(
        self,
        current_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[RetrievalDegradationResult]:
        """
        Analyze recent RAG retrieval queries for quality degradation.
        """
        with self._lock:
            records = current_records if current_records is not None else self.recent_retrievals
            if not records:
                return None

            total = len(records)
            hits = sum(1 for r in records if r["hit"])
            hit_rate = hits / total
            zero_hit_ratio = 1.0 - hit_rate

            scores = [r["score"] for r in records if r.get("score") is not None]
            mean_score = float(np.mean(scores)) if scores else 0.0

            fallbacks = sum(1 for r in records if r.get("fallback"))
            fallback_rate = fallbacks / total

            violations = []
            level = DriftLevel.NORMAL

            if hit_rate < self.retrieval_hit_rate_critical:
                level = DriftLevel.CRITICAL
                violations.append(
                    f"Hit rate dropped to {hit_rate * 100:.1f}% (critical < {self.retrieval_hit_rate_critical * 100:.0f}%)"
                )
            elif hit_rate < self.retrieval_hit_rate_warning:
                level = DriftLevel.WARNING
                violations.append(
                    f"Hit rate dropped to {hit_rate * 100:.1f}% (warning < {self.retrieval_hit_rate_warning * 100:.0f}%)"
                )

            if zero_hit_ratio > 0.15:
                if level != DriftLevel.CRITICAL:
                    level = DriftLevel.WARNING
                violations.append(
                    f"Zero-hit query ratio reached {zero_hit_ratio * 100:.1f}% (> 15%)"
                )

            return RetrievalDegradationResult(
                hit_rate=round(hit_rate, 4),
                zero_hit_ratio=round(zero_hit_ratio, 4),
                mean_top1_score=round(mean_score, 4),
                fallback_rate=round(fallback_rate, 4),
                sample_size=total,
                level=level,
                violations=violations,
            )

    def generate_drift_report(self) -> DriftReport:
        """Run full drift detection suite and assemble executive report."""
        emb_res = self.detect_embedding_drift()
        intent_res = self.detect_intent_shift()
        rag_res = self.detect_retrieval_degradation()

        alerts: List[str] = []
        overall = DriftLevel.NORMAL

        if emb_res and emb_res.level != DriftLevel.NORMAL:
            alerts.append(
                f"Embedding Drift: Centroid distance {emb_res.centroid_distance:.4f} is {emb_res.level.value.upper()}"
            )
            if emb_res.level == DriftLevel.CRITICAL:
                overall = DriftLevel.CRITICAL
            elif overall != DriftLevel.CRITICAL:
                overall = DriftLevel.WARNING

        if intent_res and intent_res.level != DriftLevel.NORMAL:
            alerts.append(
                f"Intent Shift: JS Divergence {intent_res.js_divergence:.4f} is {intent_res.level.value.upper()} (Top shift: {intent_res.max_shifted_intent})"
            )
            if intent_res.level == DriftLevel.CRITICAL:
                overall = DriftLevel.CRITICAL
            elif overall != DriftLevel.CRITICAL:
                overall = DriftLevel.WARNING

        if rag_res and rag_res.level != DriftLevel.NORMAL:
            for v in rag_res.violations:
                alerts.append(f"RAG Degradation: {v}")
            if rag_res.level == DriftLevel.CRITICAL:
                overall = DriftLevel.CRITICAL
            elif overall != DriftLevel.CRITICAL:
                overall = DriftLevel.WARNING

        report = DriftReport(
            timestamp=time.time(),
            overall_level=overall,
            embedding_drift=emb_res,
            intent_shift=intent_res,
            retrieval_degradation=rag_res,
            alerts=alerts,
        )

        # Persist report to storage
        try:
            report_file = self.storage_dir / f"drift_report_{int(time.time())}.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error(f"Failed to persist drift report: {exc}")

        return report


# Global Singleton
semantic_drift_detector = SemanticDriftDetector()
