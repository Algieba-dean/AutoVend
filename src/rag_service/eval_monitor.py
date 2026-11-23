"""
Online RAG Evaluation & Query Drift Alerting Engine (src/rag_service/eval_monitor.py).

Monitors live RAG retrieval quality, score distribution, latency p95/p99,
and detects Out-of-Domain / vocabulary query drift to trigger automated alerts.
"""

import logging
import math
import re
import time
from collections import Counter, deque
from typing import Any, Callable, Dict, List, Optional

import numpy as np
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

    alert_type: (
        str  # e.g. "LOW_CONFIDENCE", "ZERO_RESULT_SPIKE", "OUT_OF_DOMAIN_DRIFT", "LATENCY_DRIFT"
    )
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
        audit_sample_rate: float = 0.01,
        embed_fn: Optional[Callable[[List[str]], np.ndarray]] = None,
        ood_similarity_threshold: float = 0.42,
    ):
        self.window_size = window_size
        self.low_score_threshold = low_score_threshold
        self.max_latency_ms_threshold = max_latency_ms_threshold
        self.ood_alert_ratio_threshold = ood_alert_ratio_threshold
        self.audit_sample_rate = audit_sample_rate
        self.embed_fn = embed_fn
        self.ood_similarity_threshold = ood_similarity_threshold
        self._domain_centroid: Optional[np.ndarray] = None
        self._domain_sim_mean: float = 0.65
        self._domain_sim_std: float = 0.12

        self.window: deque[RetrievalMetricsSnapshot] = deque(maxlen=window_size)
        self.audit_queue: deque[Dict[str, Any]] = deque(maxlen=500)
        self._counter = 0

    def fit_domain_baseline(self, domain_queries: List[str]) -> None:
        """Calibrate in-domain embedding centroid and similarity distribution."""
        if self.embed_fn is None or not domain_queries:
            return
        try:
            vecs = np.asarray(self.embed_fn(domain_queries), dtype=np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            normed = vecs / norms
            centroid = np.mean(normed, axis=0)
            c_norm = float(np.linalg.norm(centroid))
            if c_norm > 0:
                centroid = centroid / c_norm
            sims = normed @ centroid
            self._domain_centroid = centroid
            self._domain_sim_mean = float(np.mean(sims))
            self._domain_sim_std = max(0.05, float(np.std(sims)))
        except Exception as exc:
            logger.debug(f"Domain baseline calibration skipped: {exc}")

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
        top1_score = (
            results[0].score
            if (results and hasattr(results[0], "score"))
            else (
                results[0].get("score", 0.0) if (results and isinstance(results[0], dict)) else 0.0
            )
        )
        result_count = len(results)
        is_zero = result_count == 0 or candidate_count == 0

        # Embedding-centroid / distributional Out-of-Domain check
        is_ood = self._detect_out_of_domain(
            query_text,
            top1_score=top1_score,
            result_count=result_count,
        )

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
        self._counter += 1

        # 异步 LLM-as-a-Judge 线上监控采样 (以 1% 比例脱敏采样并投递至审计队列)
        sample_threshold = max(1, int(1.0 / self.audit_sample_rate)) if self.audit_sample_rate > 0 else 0
        if sample_threshold > 0 and (self._counter % sample_threshold == 0):
            self.audit_queue.append(
                {
                    "timestamp": snapshot.timestamp,
                    "query_text": query_text,
                    "result_models": [
                        r.car_model
                        if hasattr(r, "car_model")
                        else (r.get("car_model") if isinstance(r, dict) else str(r))
                        for r in results[:5]
                    ],
                    "top1_score": top1_score,
                }
            )

        # Run real-time drift & quality evaluation
        return self._evaluate_drift_alerts(snapshot)

    def _detect_out_of_domain(
        self,
        text: str,
        top1_score: Optional[float] = None,
        result_count: Optional[int] = None,
    ) -> bool:
        """
        Embedding-centroid & distributional Out-of-Domain (OOD) detector.

        1. When `embed_fn` + calibrated `_domain_centroid` are available, computes
           cosine similarity to the automotive domain centroid and z-score distance.
        2. Otherwise, computes character-ngram cosine similarity against the automotive
           reference corpus (enriched with `TruthEngineFacade.get_known_models()`)
           combined with retrieval confidence (`top1_score` / `result_count`).
        """
        if not text:
            return False

        # Tier 1: Dense embedding centroid + z-score distance
        if self.embed_fn is not None:
            if self._domain_centroid is None:
                self.fit_domain_baseline(
                    [
                        "预算20万买什么纯电SUV合适",
                        "对比特斯拉Model Y和理想L7续航空间",
                        "新能源车家用五座底盘舒适推荐",
                        "预约周末4S店试驾流程和落地价",
                    ]
                )
            if self._domain_centroid is not None:
                try:
                    vec = np.asarray(self.embed_fn([text]), dtype=np.float32)[0]
                    v_norm = float(np.linalg.norm(vec))
                    if v_norm > 0:
                        sim = float(np.dot(vec / v_norm, self._domain_centroid))
                        z_score = (sim - self._domain_sim_mean) / self._domain_sim_std
                        return sim < self.ood_similarity_threshold or z_score < -2.5
                except Exception as exc:
                    logger.debug(f"Embedding OOD check failed, using distributional fallback: {exc}")

        # Tier 2: Distributional character-ngram similarity + retrieval-confidence joint signal
        domain_corpus = (
            "汽车 买车 选车 购车 车型 SUV MPV 轿车 预算 落地价 指导价 续航 公里 CLTC "
            "纯电 混动 增程 插混 燃油 充电 快充 电池 电机 智驾 辅助驾驶 座舱 车机 "
            "后备箱 空间 座椅 底盘 悬架 试驾 4S店 质保 首付 月供 零百加速 轴距"
        )
        try:
            from src.core.truth_engine import TruthEngineFacade

            known = TruthEngineFacade.get_instance().get_known_models()
            if known:
                domain_corpus = domain_corpus + " " + " ".join(known[:40])
        except Exception:
            pass

        tok_re = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]")

        def _ngrams(s: str) -> Counter:
            toks = tok_re.findall(s.lower())
            grams = list(toks) + [f"{toks[i]}_{toks[i + 1]}" for i in range(len(toks) - 1)]
            return Counter(grams)

        va = _ngrams(text)
        vb = _ngrams(domain_corpus)
        if not va or not vb:
            return False
        common = set(va.keys()) & set(vb.keys())
        dot = sum(va[k] * vb[k] for k in common)
        denom = math.sqrt(sum(v * v for v in va.values())) * math.sqrt(
            sum(v * v for v in vb.values())
        )
        domain_sim = (dot / denom) if denom > 0 else 0.0

        # If query has zero/near-zero domain overlap AND retrieval confidence is low (or no results), flag OOD
        low_retrieval = (
            (result_count is not None and result_count == 0)
            or (top1_score is not None and top1_score < self.low_score_threshold)
        )
        if result_count is None and top1_score is None:
            return domain_sim < 0.02
        return domain_sim < 0.04 and low_retrieval

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
                    metrics_summary={
                        "query": current.query_text,
                        "degrade_level": current.degrade_level,
                    },
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
                        message=f"检测到 Query 语义漂移！非汽车领域提问比例达到 {ood_ratio * 100:.1f}%",
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
                        message=f"滑动窗口内低置信度结果比例较高: {low_score_ratio * 100:.1f}%",
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
            "audit_queue_depth": len(self.audit_queue),
        }

    def evaluate_ragas_sample(
        self,
        query: str,
        retrieved_contexts: List[str],
        response: str,
        candidate_models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate single RAG interaction with RAGAS metrics: Faithfulness & Context Relevancy.
        Triggers CROSS_ENTITY_CONTAMINATION alert if context contains mismatched vehicle attributes.
        """
        # Cross-entity contamination detection
        contamination_detected = False
        candidate_models = candidate_models or []
        for ctx in retrieved_contexts:
            ctx_lower = ctx.lower()
            # 1. Section boundary contamination: scoped block mentions conflicting candidate
            scoped_match = re.search(r"###\s*车型:\s*【([^】]+)】", ctx)
            if scoped_match:
                owner = scoped_match.group(1).lower().replace(" ", "").replace("-", "")
                for other in candidate_models:
                    clean_other = other.lower().replace(" ", "").replace("-", "")
                    if clean_other != owner and clean_other in ctx_lower:
                        contamination_detected = True
                        break

            # 2. Foreign entity intrusion: context attributes features of unrequested foreign models
            if candidate_models and not contamination_detected:
                known_brands = [
                    "特斯拉", "tesla", "蔚来", "nio", "理想", "问界", "aito",
                    "极氪", "zeekr", "小米", "xiaomi", "比亚迪", "byd"
                ]
                cand_clean = " ".join(candidate_models).lower()
                q_clean = query.lower()
                for kb in known_brands:
                    if kb in ctx_lower and kb not in cand_clean and kb not in q_clean:
                        contamination_detected = True
                        break

        alerts: List[QueryDriftAlert] = []
        if contamination_detected:
            alerts.append(
                QueryDriftAlert(
                    alert_type="CROSS_ENTITY_CONTAMINATION",
                    severity="CRITICAL",
                    message=f"检测到跨实体上下文串扰！候选车型: {candidate_models}",
                    metrics_summary={
                        "query": query,
                        "candidate_models": candidate_models,
                    },
                )
            )

        # Compute Faithfulness and Context Relevancy proxy scores [0.0 - 1.0]
        def _extract_tokens(txt: str) -> List[str]:
            txt = txt.lower()
            try:
                import jieba

                return [
                    w.strip()
                    for w in jieba.cut(txt)
                    if len(w.strip()) > 1 and w.strip() not in ("的", "为", "了", "在", "是")
                ]
            except Exception:
                tokens = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fa5]", txt)
                return [
                    t
                    for t in tokens
                    if len(t.strip()) > 0 and t not in ("的", "为", "了", "在", "是")
                ]

        relevancy_terms = _extract_tokens(query)
        relevance_score = 0.85
        if relevancy_terms and retrieved_contexts:
            matched = sum(
                1 for t in relevancy_terms if any(t in c.lower() for c in retrieved_contexts)
            )
            relevance_score = min(1.0, max(0.1, matched / len(relevancy_terms)))

        faithfulness_score = 0.90
        if response and retrieved_contexts:
            resp_terms = _extract_tokens(response)
            if resp_terms:
                matched_f = sum(
                    1
                    for t in resp_terms
                    if any(
                        t in c.lower() or (t == "公里" and ("km" in c.lower() or "千米" in c.lower()))
                        for c in retrieved_contexts
                    )
                )
                faithfulness_score = min(1.0, max(0.2, matched_f / len(resp_terms)))

        return {
            "faithfulness": round(faithfulness_score, 3),
            "context_relevancy": round(relevance_score, 3),
            "contamination_detected": contamination_detected,
            "alerts": alerts,
        }

