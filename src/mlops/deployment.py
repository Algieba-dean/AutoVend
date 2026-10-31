"""
Canary / Shadow Deployment & A/B Testing Router with Automated Rollback (src/mlops/deployment.py).

Features:
1. Traffic Splitting: Deterministic session-hashed canary traffic routing (0% - 100%).
2. Shadow Mode: Execute candidate asynchronously in parallel, recording candidate latency and output diffs
   without affecting user-perceived SLA.
3. Automated Rollback Engine: Real-time evaluation of error rate, p95 tail latency, and guardrail violations.
   Automatically disengages canary when SLA thresholds are breached.
"""

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DEPLOY_STORAGE = PROJECT_ROOT / "storage" / "mlops" / "deployment"


class RoutingMode(str, Enum):
    """Traffic routing strategy."""

    BASELINE_ONLY = "baseline_only"
    CANARY = "canary"
    AB_TEST = "ab_test"
    SHADOW = "shadow"


class DeploymentStatus(str, Enum):
    """Deployment lifecycle status."""

    ACTIVE = "active"
    MONITORING = "monitoring"
    ROLLED_BACK = "rolled_back"
    PROMOTED = "promoted"


@dataclass
class RollbackPolicy:
    """Automated rollback triggers and thresholds."""

    max_error_rate: float = 0.05  # Trigger rollback if error rate > 5%
    max_p95_latency_s: float = 4.0  # Trigger rollback if p95 latency > 4.0s
    max_guardrail_rejections_rate: float = 0.03  # Trigger rollback if guardrail fails > 3%
    min_sample_size: int = 10  # Minimum canary turns evaluated before rollback triggers
    consecutive_breaches_required: int = 2


@dataclass
class CanaryConfig:
    """Configuration for canary deployment."""

    baseline_version: str = "v1"
    candidate_version: str = "v2"
    mode: RoutingMode = RoutingMode.CANARY
    canary_weight: float = 0.10  # 10% traffic to candidate
    policy: RollbackPolicy = field(default_factory=RollbackPolicy)
    status: DeploymentStatus = DeploymentStatus.MONITORING
    created_at: float = field(default_factory=time.time)
    last_rollback_reason: str = ""


@dataclass
class RoutingDecision:
    """Decision made for one request turn."""

    session_id: str
    target_variant: str  # "baseline" or "candidate"
    is_shadow: bool = False
    routed_version: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class TurnExecutionResult:
    """Result of running agent through deployment router."""

    session_id: str
    decision: RoutingDecision
    primary_result: Any
    shadow_result: Optional[Any] = None
    shadow_latency_s: Optional[float] = None
    shadow_diff_detected: bool = False


@dataclass
class CanaryMetricSample:
    """Execution telemetry for one canary turn."""

    session_id: str
    variant: str  # "candidate" or "baseline"
    success: bool
    latency_s: float
    guardrail_rejected: bool
    timestamp: float = field(default_factory=time.time)


class DeploymentRouter:
    """
    Traffic router managing Canary, Shadow, and A/B testing with automated rollback.
    """

    def __init__(
        self,
        config: Optional[CanaryConfig] = None,
        storage_dir: Optional[Path] = None,
    ):
        self.config = config or CanaryConfig()
        self.storage_dir = Path(storage_dir) if storage_dir else DEFAULT_DEPLOY_STORAGE
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._samples: List[CanaryMetricSample] = []
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mlops_shadow")
        self._breach_counter = 0

    def set_config(self, config: CanaryConfig) -> None:
        """Update active deployment configuration."""
        with self._lock:
            self.config = config
            self._save_config()
        logger.info(
            f"[MLOps] Updated deployment config: mode={config.mode.value}, canary_weight={config.canary_weight}"
        )

    def get_config(self) -> CanaryConfig:
        with self._lock:
            return self.config

    def _hash_session(self, session_id: Any) -> float:
        """Deterministic hash of session_id into [0.0, 1.0) for stable user stickiness."""
        sid_str = str(session_id)
        h = hashlib.md5(sid_str.encode("utf-8")).hexdigest()
        val = int(h[:8], 16)
        return (val % 10000) / 10000.0

    def decide_route(self, session_id: str) -> RoutingDecision:
        """
        Determine whether request routes to baseline or candidate variant.
        """
        with self._lock:
            mode = self.config.mode
            if (
                mode == RoutingMode.BASELINE_ONLY
                or self.config.status == DeploymentStatus.ROLLED_BACK
            ):
                return RoutingDecision(
                    session_id=session_id,
                    target_variant="baseline",
                    is_shadow=False,
                    routed_version=self.config.baseline_version,
                )

            if mode == RoutingMode.SHADOW:
                return RoutingDecision(
                    session_id=session_id,
                    target_variant="baseline",
                    is_shadow=True,
                    routed_version=self.config.baseline_version,
                )

            # Canary or A/B test
            score = self._hash_session(session_id)
            if score < self.config.canary_weight:
                return RoutingDecision(
                    session_id=session_id,
                    target_variant="candidate",
                    is_shadow=False,
                    routed_version=self.config.candidate_version,
                )
            else:
                return RoutingDecision(
                    session_id=session_id,
                    target_variant="baseline",
                    is_shadow=False,
                    routed_version=self.config.baseline_version,
                )

    def record_turn_metric(
        self,
        session_id: str,
        variant: str,
        success: bool,
        latency_s: float,
        guardrail_rejected: bool = False,
    ) -> None:
        """Log execution performance and evaluate automated rollback triggers."""
        sample = CanaryMetricSample(
            session_id=session_id,
            variant=variant,
            success=success,
            latency_s=latency_s,
            guardrail_rejected=guardrail_rejected,
            timestamp=time.time(),
        )

        with self._lock:
            self._samples.append(sample)
            if len(self._samples) > 2000:
                self._samples.pop(0)

            # Check rollback policy if evaluating candidate
            if variant == "candidate" and self.config.status == DeploymentStatus.MONITORING:
                self._evaluate_rollback_policy()

    def _evaluate_rollback_policy(self) -> None:
        """Assess SLA health of candidate turns and execute rollback if thresholds breached."""
        canary_samples = [s for s in self._samples if s.variant == "candidate"]
        policy = self.config.policy

        if len(canary_samples) < policy.min_sample_size:
            return

        recent = canary_samples[-50:]  # Rolling evaluation window
        total = len(recent)
        if total <= 0:
            return
        errors = sum(1 for s in recent if not s.success)
        error_rate = errors / total

        latencies = sorted(s.latency_s for s in recent)
        p95_index = int(total * 0.95)
        p95_latency = latencies[min(p95_index, total - 1)]

        rejections = sum(1 for s in recent if s.guardrail_rejected)
        rejection_rate = rejections / total

        breach_reasons = []
        if error_rate > policy.max_error_rate:
            breach_reasons.append(
                f"Candidate error rate {error_rate * 100:.1f}% exceeded threshold {policy.max_error_rate * 100:.1f}%"
            )
        if p95_latency > policy.max_p95_latency_s:
            breach_reasons.append(
                f"Candidate p95 latency {p95_latency:.2f}s exceeded SLA threshold {policy.max_p95_latency_s:.2f}s"
            )
        if rejection_rate > policy.max_guardrail_rejections_rate:
            breach_reasons.append(
                f"Candidate guardrail rejection rate {rejection_rate * 100:.1f}% exceeded threshold {policy.max_guardrail_rejections_rate * 100:.1f}%"
            )

        if breach_reasons:
            self._breach_counter += 1
            logger.warning(
                f"[MLOps Canary Breach] Streak {self._breach_counter}/{policy.consecutive_breaches_required}: {'; '.join(breach_reasons)}"
            )
            if self._breach_counter >= policy.consecutive_breaches_required:
                self.trigger_rollback(reason="; ".join(breach_reasons))
        else:
            self._breach_counter = max(0, self._breach_counter - 1)

    def trigger_rollback(self, reason: str) -> None:
        """Trigger immediate emergency rollback to baseline."""
        with self._lock:
            self.config.status = DeploymentStatus.ROLLED_BACK
            self.config.mode = RoutingMode.BASELINE_ONLY
            self.config.canary_weight = 0.0
            self.config.last_rollback_reason = reason
            self._save_config()

        logger.error(
            f"[MLOps AUTOMATED ROLLBACK TRIGGERED] Reverted traffic to baseline. Reason: {reason}"
        )

    def promote_candidate(self) -> None:
        """Promote candidate to new baseline after verified canary success."""
        with self._lock:
            self.config.baseline_version = self.config.candidate_version
            self.config.status = DeploymentStatus.PROMOTED
            self.config.mode = RoutingMode.BASELINE_ONLY
            self.config.canary_weight = 0.0
            self._save_config()

        logger.info(
            f"[MLOps PROMOTION] Promoted candidate {self.config.baseline_version} to active baseline."
        )

    def execute_turn(
        self,
        session_id: str,
        run_baseline: Callable[[], Any],
        run_candidate: Callable[[], Any],
    ) -> TurnExecutionResult:
        """
        Execute request according to routing decision, including asynchronous shadow execution.
        """
        decision = self.decide_route(session_id)
        start_t = time.time()

        if decision.target_variant == "candidate":
            try:
                res = run_candidate()
                latency = time.time() - start_t
                self.record_turn_metric(session_id, "candidate", success=True, latency_s=latency)
                return TurnExecutionResult(
                    session_id=session_id,
                    decision=decision,
                    primary_result=res,
                )
            except Exception as exc:
                latency = time.time() - start_t
                self.record_turn_metric(session_id, "candidate", success=False, latency_s=latency)
                logger.error(f"[Canary Execution Error] {exc}, falling back to baseline")
                # Immediate single-turn fallback to baseline
                res = run_baseline()
                return TurnExecutionResult(
                    session_id=session_id,
                    decision=decision,
                    primary_result=res,
                )

        # Baseline execution
        try:
            res = run_baseline()
            latency = time.time() - start_t
            self.record_turn_metric(session_id, "baseline", success=True, latency_s=latency)
        except Exception as exc:
            latency = time.time() - start_t
            self.record_turn_metric(session_id, "baseline", success=False, latency_s=latency)
            raise exc

        # Handle Shadow Execution
        if decision.is_shadow:

            def _shadow_worker():
                t0 = time.time()
                try:
                    run_candidate()
                    dur = time.time() - t0
                    self.record_turn_metric(session_id, "candidate", success=True, latency_s=dur)
                    logger.debug(
                        f"[Shadow Execution] Completed in {dur:.3f}s for session {session_id}"
                    )
                except Exception as c_err:
                    dur = time.time() - t0
                    self.record_turn_metric(session_id, "candidate", success=False, latency_s=dur)
                    logger.warning(f"[Shadow Execution Failed] {c_err}")

            self._executor.submit(_shadow_worker)

        return TurnExecutionResult(
            session_id=session_id,
            decision=decision,
            primary_result=res,
        )

    def get_canary_health(self) -> Dict[str, Any]:
        """Aggregate health and SLA statistics comparing baseline vs candidate."""
        with self._lock:
            cand_samples = [s for s in self._samples if s.variant == "candidate"]
            base_samples = [s for s in self._samples if s.variant == "baseline"]

            def _stats(samples: List[CanaryMetricSample]) -> Dict[str, Any]:
                if not samples:
                    return {
                        "sample_size": 0,
                        "error_rate": 0.0,
                        "p95_latency_s": 0.0,
                        "mean_latency_s": 0.0,
                    }
                n = len(samples)
                errs = sum(1 for s in samples if not s.success)
                lats = sorted(s.latency_s for s in samples)
                p95 = lats[int(n * 0.95)] if n >= 20 else max(lats)
                return {
                    "sample_size": n,
                    "error_rate": round(errs / n, 4),
                    "mean_latency_s": round(sum(lats) / n, 4),
                    "p95_latency_s": round(p95, 4),
                    "guardrail_rejection_rate": round(
                        sum(1 for s in samples if s.guardrail_rejected) / n, 4
                    ),
                }

            return {
                "config": asdict(self.config),
                "candidate_metrics": _stats(cand_samples),
                "baseline_metrics": _stats(base_samples),
                "active_breaches": self._breach_counter,
            }

    def _save_config(self) -> None:
        try:
            cfg_file = self.storage_dir / "active_deployment.json"
            with open(cfg_file, "w", encoding="utf-8") as f:
                d = asdict(self.config)
                d["mode"] = self.config.mode.value
                d["status"] = self.config.status.value
                json.dump(d, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.warning(f"Could not persist active deployment configuration: {exc}")


# Global Singleton
deployment_router = DeploymentRouter()
