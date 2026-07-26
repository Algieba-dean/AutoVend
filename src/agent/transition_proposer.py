"""
LLM-side stage transition proposals.

The model is asked one narrow question — "is this step finished?" — and answers
with a structured `transition_to` call. It never *performs* the transition;
`stages.arbitrate` decides whether the proposal is legal and whether the
business guard on that edge passes.

That separation is the point. A model asked to manage the whole conversation
will declare the requirements complete because the exchange felt pleasant,
without ever having asked the budget. Here it may only ever *propose*, and the
guard on NEEDS_ANALYSIS → CAR_SELECTION refuses until a price range exists.

The prompt shows the model only the legal targets from its current stage, so a
well-behaved answer cannot name an impossible one. A misbehaving answer is
caught by the arbiter anyway — the prompt reduces retries, the graph enforces
correctness.
"""

import logging
from typing import List, Optional

from src.agent.extractors.base import parse_llm_json
from src.agent.schemas import SessionState, Stage
from src.agent.stages import (
    STAGE_TRANSITIONS,
    ProposalSource,
    TransitionProposal,
)

logger = logging.getLogger(__name__)

#: What each stage is trying to accomplish. Given to the model so "is this
#: finished?" has a concrete referent rather than being a vibe check.
STAGE_OBJECTIVES = {
    Stage.WELCOME: "问候客户，让对话开始",
    Stage.PROFILE_ANALYSIS: "了解客户基本情况：称呼、家庭结构、用车人、居住与停车条件",
    Stage.NEEDS_ANALYSIS: "澄清购车需求：预算区间、车型类别、动力形式、品牌偏好、座位需求",
    Stage.CAR_SELECTION: "介绍匹配到的车型并确认客户的意向车型",
    Stage.RESERVATION_4S: "收集试驾预约信息：日期、时间、门店、试驾人、联系电话",
    Stage.RESERVATION_CONFIRMATION: "复述并确认全部预约信息",
    Stage.FAREWELL: "总结并友好结束对话",
}

TRANSITION_PROMPT = """你是一个对话流程判定器。判断当前阶段的任务是否已经完成。

当前阶段：{stage}
本阶段目标：{objective}

已收集的信息：
{collected}

对话记录：
{conversation}

合法的下一阶段（只能从中选择，或选择留在当前阶段）：
{allowed}

只输出 JSON，不要任何解释：
- 任务已完成，应当进入下一阶段：{{"transition_to": "目标阶段值", "reason": "简短理由"}}
- 任务尚未完成，应当留在当前阶段：{{"transition_to": null, "reason": "还缺什么"}}

注意：你的输出只是一个"提议"，系统会做业务校验。宁可保守——信息不足时留在当前阶段。
"""


def propose_by_llm(
    llm,
    state: SessionState,
    conversation: str,
) -> Optional[TransitionProposal]:
    """
    Ask the model whether the current stage is complete.

    Returns None when the model says stay, when it names an illegal target, or
    when the call fails — every one of which means "no proposal", which the
    caller falls back on the rule-based proposer for. A transition judge that
    errors must not be able to stall the conversation.
    """
    allowed = sorted(STAGE_TRANSITIONS.get(state.stage, set()), key=lambda s: s.value)
    if not allowed:
        return None

    prompt = TRANSITION_PROMPT.format(
        stage=state.stage.value,
        objective=STAGE_OBJECTIVES.get(state.stage, ""),
        collected=_summarize_state(state),
        conversation=conversation[-2000:],
        allowed="\n".join(f"- {stage.value}" for stage in allowed),
    )

    try:
        response = llm.complete(prompt)
        parsed = parse_llm_json(getattr(response, "text", str(response)))
    except Exception as exc:
        logger.warning(f"Transition proposal failed, falling back to rules: {exc}")
        return None

    if not isinstance(parsed, dict):
        return None

    raw_target = parsed.get("transition_to")
    if not raw_target:
        return None

    target = _coerce_stage(str(raw_target))
    if target is None:
        logger.warning(f"LLM proposed an unknown stage {raw_target!r}; ignoring")
        return None
    if target not in allowed:
        # The arbiter would reject this anyway; dropping it here keeps the
        # rejection note about business rules rather than about the model
        # naming an edge that does not exist.
        logger.warning(
            f"LLM proposed illegal target {target.value} from {state.stage.value}; ignoring"
        )
        return None

    return TransitionProposal(
        target=target,
        source=ProposalSource.LLM,
        reason=str(parsed.get("reason", ""))[:200],
    )


def _coerce_stage(value: str) -> Optional[Stage]:
    normalised = value.strip().lower()
    for stage in Stage:
        if normalised in (stage.value.lower(), stage.name.lower()):
            return stage
    return None


def _summarize_state(state: SessionState) -> str:
    """Compact view of what has been collected, for the judge prompt."""
    lines: List[str] = []

    profile = {k: v for k, v in state.profile.model_dump().items() if v}
    lines.append(f"客户画像: {profile or '（空）'}")

    explicit = {k: v for k, v in state.needs.explicit.model_dump().items() if v}
    lines.append(f"明确需求: {explicit or '（空）'}")

    lines.append(f"匹配车型: {len(state.matched_cars)} 款")

    reservation = {k: v for k, v in state.reservation.model_dump().items() if v}
    lines.append(f"预约信息: {reservation or '（空）'}")

    return "\n".join(lines)
