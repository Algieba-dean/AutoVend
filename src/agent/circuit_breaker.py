"""
Anti-Loop Circuit Breaker for AutoVend Agent (src/agent/circuit_breaker.py).

Guards against conversational repetition and infinite state-machine ping-pong loops:
1. Stage Dwell Loop: detects customer or agent stuck in a single stage beyond threshold.
2. Guard Rejection Loop: detects repeated rejections of the same stage transition guard.
3. Oscillation Loop: detects rapid back-and-forth toggling between adjacent stages.
4. Proactive Circuit Breaker Intervention: generates concrete escalation directives
   to break deadlocks and guide customer forward.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional

from pydantic import BaseModel

from src.agent.schemas import Stage

logger = logging.getLogger(__name__)

# Configurable thresholds
MAX_STAGE_DWELL_TURNS = 4       # Max turns allowed in a single stage without progress
MAX_GUARD_REJECTIONS = 2        # Max times the same guard can be consecutively rejected
MAX_OSCILLATION_CYCLES = 2      # Max times state can ping-pong between two stages


class CircuitBreakerTrip(BaseModel):
    """Details of a tripped circuit breaker event."""

    trip_type: str  # "REJECTION_LOOP", "DWELL_LOOP", "OSCILLATION_LOOP"
    stage: str
    reasons: List[str]
    intervention_note: str


class AgentCircuitBreaker:
    """
    State machine anti-loop circuit breaker.
    Maintains per-session execution history and intervenes when a deadlock is detected.
    """

    def __init__(
        self,
        max_dwell: int = MAX_STAGE_DWELL_TURNS,
        max_rejections: int = MAX_GUARD_REJECTIONS,
        max_oscillations: int = MAX_OSCILLATION_CYCLES,
    ):
        self.max_dwell = max_dwell
        self.max_rejections = max_rejections
        self.max_oscillations = max_oscillations

        # Per-session metrics
        self._dwell_counter: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._last_stage: Dict[str, str] = {}
        self._rejection_history: Dict[str, List[str]] = defaultdict(list)
        self._stage_history: Dict[str, List[str]] = defaultdict(list)
        self._topic_hopping_counter: Dict[str, int] = defaultdict(int)

    def record_turn(
        self,
        session_id: str,
        current_stage: Stage,
        rejection_reason: Optional[str] = None,
        is_topic_hopping: bool = False,
    ) -> Optional[CircuitBreakerTrip]:
        """
        Record a turn outcome and check if an anti-loop circuit breaker is tripped.
        Returns CircuitBreakerTrip if tripped, or None if healthy.
        """
        if is_topic_hopping:
            # Active topic hopping or side-question consultation is a healthy dialogue turn,
            # not a state-machine deadlock. Clear rejection history and bypass anti-loop trip.
            self._rejection_history[session_id].clear()
            self._topic_hopping_counter[session_id] += 1
            if self._topic_hopping_counter[session_id] >= 5:
                intervention = (
                    "【断路器温和建议 - 线下实车体验指引】客户已连续进行多轮深度技术细节咨询："
                    "纸上参数不如现场操控。请在专业解答本轮问题的同时，主动真诚提议为客户安排到店专属试驾体验。"
                )
                return CircuitBreakerTrip(
                    trip_type="TOPIC_HOPPING_DWELL",
                    stage=current_stage.value,
                    reasons=["Extended technical consultation turns"],
                    intervention_note=intervention,
                )
            return None
        else:
            self._topic_hopping_counter[session_id] = 0

        stage_str = current_stage.value
        last_st = self._last_stage.get(session_id)

        # Track stage history
        history = self._stage_history[session_id]
        if not history or history[-1] != stage_str:
            history.append(stage_str)
            if len(history) > 10:
                history.pop(0)

        # Track dwell turns in current stage
        if last_st == stage_str:
            self._dwell_counter[session_id][stage_str] += 1
        else:
            self._dwell_counter[session_id][stage_str] = 1
            self._last_stage[session_id] = stage_str

        dwell_count = self._dwell_counter[session_id][stage_str]

        # Track guard rejection history
        rej_hist = self._rejection_history[session_id]
        if rejection_reason:
            rej_hist.append(rejection_reason)
            if len(rej_hist) > 6:
                rej_hist.pop(0)
        else:
            rej_hist.clear()

        # ── 1. Check Guard Rejection Loop ──────────────────────────────────
        if len(rej_hist) >= self.max_rejections:
            # Check if recent rejections stem from the same root guard (e.g. budget, profile, etc.)
            recent = rej_hist[-self.max_rejections:]
            if all("预算" in r for r in recent):
                intervention = (
                    "【断路器干预 - 预算死锁解除】检测到连续多次因缺少预算而阻塞推荐："
                    "严禁再次生硬向客户索要预算。请直接为客户提供主流预算区间阶梯选项"
                    "（如：经济实用12-18万、品质升级20-30万、高端豪华35万以上），"
                    "并主动推荐每个区间的代表性高性价比车型，引导客户做选择题。"
                )
                if len(rej_hist) == self.max_rejections:
                    logger.warning(f"[{session_id}] Circuit breaker tripped: REJECTION_LOOP on budget")
                else:
                    logger.debug(f"[{session_id}] Circuit breaker continued: REJECTION_LOOP on budget")
                return CircuitBreakerTrip(
                    trip_type="REJECTION_LOOP",
                    stage=stage_str,
                    reasons=recent,
                    intervention_note=intervention,
                )
            elif all("画像" in r or "基本情况" in r for r in recent):
                intervention = (
                    "【断路器干预 - 用户画像死锁解除】检测到用户画像信息多次无法完整提取："
                    "跳过深度画像收集，基于通用大众场景直接询问客户的核心购车用途（代步/家用/商务）及意向车型。"
                )
                if len(rej_hist) == self.max_rejections:
                    logger.warning(f"[{session_id}] Circuit breaker tripped: REJECTION_LOOP on profile")
                else:
                    logger.debug(f"[{session_id}] Circuit breaker continued: REJECTION_LOOP on profile")
                return CircuitBreakerTrip(
                    trip_type="REJECTION_LOOP",
                    stage=stage_str,
                    reasons=recent,
                    intervention_note=intervention,
                )

        # ── 2. Check Stage Oscillation Loop ────────────────────────────────
        # E.g. [A, B, A, B] pattern in history
        if len(history) >= 4:
            tail = history[-4:]
            if tail[0] == tail[2] and tail[1] == tail[3] and tail[0] != tail[1]:
                intervention = (
                    f"【断路器干预 - 阶段振荡抑制】检测到在 {tail[0]} 与 {tail[1]} 之间来回反复："
                    "请主动帮客户做阶段性事实小结，固定已确认的购车偏好，并明确提出二选一问题以锁定推进方向。"
                )
                logger.warning(f"[{session_id}] Circuit breaker tripped: OSCILLATION_LOOP between {tail[0]} and {tail[1]}")
                return CircuitBreakerTrip(
                    trip_type="OSCILLATION_LOOP",
                    stage=stage_str,
                    reasons=[f"Oscillating between {tail[0]} and {tail[1]}"],
                    intervention_note=intervention,
                )

        # ── 3. Check Stage Dwell Timeout ───────────────────────────────────
        if dwell_count >= self.max_dwell:
            if current_stage == Stage.NEEDS_ANALYSIS:
                intervention = (
                    "【断路器干预 - 需求分析停留超时】在需求挖掘阶段已连续停留多个回合："
                    "不再继续盘问细节，请立即根据当前已知的需求碎片，主动整理并推荐 2-3 款匹配度最高的热门车型供客户挑选。"
                )
            elif current_stage == Stage.PROFILE_ANALYSIS:
                intervention = (
                    "【断路器干预 - 画像停留超时】已收集足够基本信息，请立刻平滑过渡到询问购车预算与意向车型类别。"
                )
            elif current_stage == Stage.CAR_SELECTION:
                intervention = (
                    "【断路器干预 - 推荐阶段停留超时】请主动询问客户对上述哪款车型最感兴趣，并直接提议预约线下 4S 店试驾体验。"
                )
            else:
                intervention = (
                    f"【断路器干预】当前阶段（{stage_str}）对话已达到停留上限，请主动推进下一业务节点。"
                )

            if dwell_count == self.max_dwell:
                logger.warning(f"[{session_id}] Circuit breaker tripped: DWELL_LOOP in {stage_str} ({dwell_count} turns)")
            else:
                logger.debug(f"[{session_id}] Circuit breaker continued: DWELL_LOOP in {stage_str} ({dwell_count} turns)")
            return CircuitBreakerTrip(
                trip_type="DWELL_LOOP",
                stage=stage_str,
                reasons=[f"Dwell count {dwell_count} exceeded limit {self.max_dwell}"],
                intervention_note=intervention,
            )

        return None

    def reset_session(self, session_id: str) -> None:
        """Clear tracking data for a session."""
        self._dwell_counter.pop(session_id, None)
        self._last_stage.pop(session_id, None)
        self._rejection_history.pop(session_id, None)
        self._stage_history.pop(session_id, None)
        self._topic_hopping_counter.pop(session_id, None)


# Default global breaker instance
default_circuit_breaker = AgentCircuitBreaker()
