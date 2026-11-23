"""
Standardized Human-in-the-Loop (HITL) Handoff & Resume Protocol (src/agent/hitl.py).

Supports LangGraph `interrupt()` & `Command(resume=...)` as first-class capabilities:
1. Precise triggers: high-intent closing (bottom-price/deposit), consecutive 2+ user
   corrections, or compliance/emotion risk.
2. Structured `HandoffContext` summary (profile, hard/soft constraints, negative
   exclusions, candidate models, core blocker) instead of dumping 30 raw turns.
3. Seamless state resumption when human operator returns `Command(resume=...)`.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from src.agent.schemas import HandoffContext, SessionState, Stage


class HITLTriggerReason(str, Enum):
    HIGH_INTENT_CLOSING = "high_intent_closing"
    CONSECUTIVE_CORRECTIONS = "consecutive_user_corrections"
    COMPLIANCE_EMOTION_RISK = "compliance_or_emotion_risk"


@dataclass(frozen=True)
class HITLDecision:
    triggered: bool
    reason: Optional[HITLTriggerReason] = None
    severity: str = "medium"
    detail: str = ""


_HIGH_INTENT_CLOSING_KEYWORDS = (
    "谈底价", "最低底价", "我要下定", "交定金", "付定金", "签合同", "锁单", "刷卡订车", "直接订车", "能少多少钱"
)

_EMOTION_OR_RISK_KEYWORDS = (
    "投诉", "骗子", "欺诈", "12315", "工商局", "找你们经理", "找领导", "太差劲了", "曝光你们", "退一赔三"
)

_CORRECTION_KEYWORDS = (
    "我说错了", "不是这个", "理解错了", "不对，我是说", "搞错了", "听不懂吗", "再说一遍", "刚才说错了"
)


def is_user_correction(user_message: str) -> bool:
    msg = (user_message or "").strip()
    return any(k in msg for k in _CORRECTION_KEYWORDS)


def evaluate_hitl_trigger(
    sess: SessionState,
    user_message: str,
    compliance_flagged: bool = False,
) -> HITLDecision:
    """Evaluate deterministic HITL escalation triggers for the current turn."""
    msg = (user_message or "").strip()

    if compliance_flagged or any(k in msg for k in _EMOTION_OR_RISK_KEYWORDS):
        return HITLDecision(
            triggered=True,
            reason=HITLTriggerReason.COMPLIANCE_EMOTION_RISK,
            severity="high",
            detail="检测到高情绪风险或合规红线诉求，需人工专家介入安抚与合规把关。",
        )

    if any(k in msg for k in _HIGH_INTENT_CLOSING_KEYWORDS):
        return HITLDecision(
            triggered=True,
            reason=HITLTriggerReason.HIGH_INTENT_CLOSING,
            severity="medium",
            detail="客户进入谈底价/下定锁单临门一脚阶段，需门店销售经理确认最终成交政策。",
        )

    if int(getattr(sess, "consecutive_corrections", 0)) >= 2:
        return HITLDecision(
            triggered=True,
            reason=HITLTriggerReason.CONSECUTIVE_CORRECTIONS,
            severity="medium",
            detail="客户连续两次纠正 Agent 理解，为避免体验恶化自动升级人工接管。",
        )

    return HITLDecision(triggered=False)


def build_handoff_context(
    sess: SessionState,
    decision: HITLDecision,
) -> HandoffContext:
    """Build a structured `HandoffContext` summary for human takeover."""
    prefs = sess.preferences
    hard = {k: {"value": c.value, "tolerance_pct": c.tolerance_pct} for k, c in prefs.hard_constraints.items()}
    soft = {k: {"value": c.value, "weight": c.weight} for k, c in prefs.soft_preferences.items()}
    neg = prefs.negative_exclusions.model_dump()

    candidate_models = [
        str(c.get("car_model"))
        for c in (sess.matched_cars or [])
        if isinstance(c, dict) and c.get("car_model")
    ]

    if decision.reason == HITLTriggerReason.HIGH_INTENT_CLOSING:
        blocker = "待确认门店底价政策、金融补贴与定金锁单流程"
        action = "核定可申请的最大现金/礼遇权限并联系客户完成锁单"
    elif decision.reason == HITLTriggerReason.CONSECUTIVE_CORRECTIONS:
        blocker = "多轮意图理解出现连续偏差，需人工快速澄清核心诉求"
        action = "致电或在线与客户确认核心预算/车型条件后更新状态并交还AI跟进"
    else:
        blocker = "情绪安抚或合规红线问题"
        action = "优先安抚客户情绪并按门店合规标准处理诉求"

    return HandoffContext(
        session_id=sess.session_id,
        trigger_reason=decision.reason.value if decision.reason else "",
        severity=decision.severity,
        stage=sess.stage.value,
        customer_profile=sess.profile.model_dump(exclude_none=True),
        hard_constraints=hard,
        soft_preferences=soft,
        negative_exclusions=neg,
        excluded_models=list(prefs.negative_exclusions.models),
        candidate_models=candidate_models[:5],
        core_blocker=blocker,
        recommended_human_action=action,
        recent_turns_count=int(getattr(sess, "turn_count", 0)),
    )


def apply_human_resume(
    sess: SessionState,
    resume_payload: Any,
) -> SessionState:
    """
    Apply human operator's `Command(resume=...)` payload back into `SessionState`
    so the LangGraph agent can resume seamlessly.
    """
    updated = sess.model_copy(deep=True)
    updated.consecutive_corrections = 0

    if isinstance(resume_payload, dict):
        human_note = str(resume_payload.get("human_note") or "").strip()
        if human_note:
            updated.system_notes.append(f"[人工专家交接反馈] {human_note}")

        target_stage = resume_payload.get("target_stage")
        if target_stage:
            try:
                updated.stage = Stage(str(target_stage))
            except ValueError:
                pass

        upd_constraints = resume_payload.get("updated_constraints")
        if isinstance(upd_constraints, dict):
            from src.agent.preference_model import PreferenceEngine

            if "budget_max" in upd_constraints and upd_constraints["budget_max"] is not None:
                updated.needs.explicit.budget_max = float(upd_constraints["budget_max"])
                updated.needs.explicit.price = f"{upd_constraints['budget_max']}万以内"
            if "powertrain_type" in upd_constraints and upd_constraints["powertrain_type"]:
                updated.needs.explicit.powertrain_type = str(upd_constraints["powertrain_type"])
            if "brand" in upd_constraints and upd_constraints["brand"]:
                updated.needs.explicit.brand = str(upd_constraints["brand"])
            PreferenceEngine.sync_from_needs(updated, turn_index=int(getattr(updated, "turn_count", 0)))

        if resume_payload.get("clear_handoff", True):
            updated.handoff_context = None
    elif isinstance(resume_payload, str) and resume_payload.strip():
        updated.system_notes.append(f"[人工专家交接反馈] {resume_payload.strip()}")
        updated.handoff_context = None

    return updated
