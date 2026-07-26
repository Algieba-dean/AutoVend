"""
LLM-side tool planning.

Shows the model the candidate tools for its *current* stage and asks which to
call for this turn. The answer is a list of calls, dispatched by
`tools.dispatch_all`, which refuses anything outside the stage's set regardless
of what the model asked for.

Two layers of the same restriction, on purpose. The prompt only lists the legal
tools, which keeps well-behaved answers legal and cuts retries. The dispatcher
refuses illegal ones anyway, because a prompt is a request and a registry is a
rule — and the failure this prevents is specific: a model in profile-gathering
recording a test-drive booking because the customer said "next Saturday works
for me" while describing their commute.

This is a third LLM call per turn, so it is opt-in. The extractors already
capture profile and needs from the transcript; tools earn their place when the
turn calls for an *action* — selecting a vehicle, asking for one specific
missing field, requesting fresh candidates — rather than another field written.
"""

import logging
from typing import Any, Dict, List

from src.agent.extractors.base import parse_llm_json
from src.agent.schemas import SessionState
from src.agent.tools import render_catalog, tools_for

logger = logging.getLogger(__name__)

TOOL_PROMPT = """你是一个工具调用规划器。根据当前对话，决定本轮需要调用哪些工具。

当前阶段：{stage}

本阶段可用的工具（只能使用这些，不得调用未列出的工具）：
{catalog}

已收集的信息：
{collected}

对话记录：
{conversation}

只输出 JSON 数组，不要任何解释。每个元素形如：
{{"tool": "工具名", "args": {{...}}}}

不需要调用任何工具时输出：[]

注意：
- 只在信息确实发生变化时才调用记录类工具，不要重复写入已有的值。
- 宁可少调用。系统会校验每次调用，越权调用会被拒绝。
"""


def plan_tools(llm, state: SessionState, conversation: str) -> List[Dict[str, Any]]:
    """
    Ask the model which tools to call this turn.

    Returns `[]` on any failure — no tools available, unparseable answer, LLM
    error. A planner that errors must not be able to stall the turn; the
    extractors and the rule-based proposer still carry the conversation.
    """
    if not tools_for(state.stage):
        return []

    prompt = TOOL_PROMPT.format(
        stage=state.stage.value,
        catalog=render_catalog(state.stage),
        collected=_summarize(state),
        conversation=conversation[-2000:],
    )

    try:
        response = llm.complete(prompt)
        parsed = parse_llm_json(getattr(response, "text", str(response)))
    except Exception as exc:
        logger.warning(f"Tool planning failed, continuing without tools: {exc}")
        return []

    calls = _coerce_calls(parsed)
    if calls:
        logger.info(f"Tool plan for {state.stage.value}: {[c.get('tool') for c in calls]}")
    return calls


def _coerce_calls(parsed: Any) -> List[Dict[str, Any]]:
    """
    Normalise whatever the model returned into a list of call dicts.

    Models wrap the array in an object about as often as they return it bare,
    so both shapes are accepted rather than treated as a parse failure.
    """
    if isinstance(parsed, dict):
        for key in ("calls", "tools", "tool_calls"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break
        else:
            parsed = [parsed] if "tool" in parsed else []

    if not isinstance(parsed, list):
        return []

    calls: List[Dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = item.get("tool") or item.get("name")
        if not name:
            continue
        args = item.get("args") or item.get("arguments") or {}
        calls.append({"tool": str(name), "args": args if isinstance(args, dict) else {}})
    return calls


def _summarize(state: SessionState) -> str:
    parts = []
    profile = {k: v for k, v in state.profile.model_dump().items() if v}
    parts.append(f"客户画像: {profile or '（空）'}")
    explicit = {k: v for k, v in state.needs.explicit.model_dump().items() if v}
    parts.append(f"明确需求: {explicit or '（空）'}")
    parts.append(f"匹配车型: {[c.get('car_model') for c in state.matched_cars[:5]] or '（空）'}")
    reservation = {k: v for k, v in state.reservation.model_dump().items() if v}
    parts.append(f"预约信息: {reservation or '（空）'}")
    return "\n".join(parts)
