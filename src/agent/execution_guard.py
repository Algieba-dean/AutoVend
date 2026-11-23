"""
Deterministic Execution & Loop-Prevention Guardrails (src/agent/execution_guard.py).

Protects cyclic LangGraph execution (CRAG retry loop, ToolNode loop, Auditor loop)
against infinite loops, runaway latency, and partial tool failures via:
1. Hard `recursion_limit` & per-turn step/token budget (`TurnBudgetConfig`).
2. Deterministic `safe_degrade` routing when any budget is exhausted.
3. Structured Tool Error Self-Healing (`ToolErrorSelfHealer`) so tool failures
   route to parameter adjustment, backup sources, or honest disclosure—never fabrication.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from src.agent.schemas import SessionState, Stage

logger = logging.getLogger(__name__)

DEFAULT_GRAPH_RECURSION_LIMIT = 15
DEFAULT_MAX_TURN_STEPS = 12
DEFAULT_PER_NODE_TIMEOUT_S = 15.0


@dataclass(frozen=True)
class TurnBudgetConfig:
    """Hard per-turn execution budget for cyclic LangGraph runs."""

    recursion_limit: int = DEFAULT_GRAPH_RECURSION_LIMIT
    max_turn_steps: int = DEFAULT_MAX_TURN_STEPS
    per_node_timeout_s: float = DEFAULT_PER_NODE_TIMEOUT_S
    max_crag_retries: int = 2
    max_audit_retries: int = 1
    max_tool_iterations: int = 3


def check_step_budget(
    step_count: int,
    config: Optional[TurnBudgetConfig] = None,
) -> Tuple[bool, str]:
    """Return `(within_budget, reason)` for the current turn's accumulated graph steps."""
    cfg = config or TurnBudgetConfig()
    if step_count >= cfg.max_turn_steps:
        return False, f"turn_step_budget_exhausted:{step_count}/{cfg.max_turn_steps}"
    return True, ""


def build_safe_degradation_response(sess: SessionState, reason: str = "") -> str:
    """
    Deterministic conservative fallback when execution budgets or retry loops exhaust.
    Never invents vehicle specs or prices.
    """
    name_prefix = f"{sess.profile.name}，" if sess.profile and sess.profile.name else ""
    if sess.stage in (Stage.RESERVATION_4S, Stage.RESERVATION_CONFIRMATION):
        return (
            f"{name_prefix}抱歉让您久等了，当前预约系统处理较繁忙。"
            "为确保您的试驾安排万无一失，我可以立即为您转接专属人工顾问协助核对并锁定门店档期，请问您方便吗？"
        )
    if sess.matched_cars:
        top_model = sess.matched_cars[0].get("car_model", "候选车型")
        return (
            f"{name_prefix}为了确保给到您最准确的配置与报价信息，当前系统已为您暂存「{top_model}」等候选方案。"
            "如需精准落地价或进一步对比，我可以为您转接门店产品专家为您一对一详细测算。"
        )
    return (
        f"{name_prefix}抱歉，当前查询条件较复杂或系统响应超时，暂时无法为您拉取完整实时报价。"
        "您可以告诉我您最看重的1-2个核心需求（例如预算范围或动力形式），或者我可以为您转接专属顾问继续服务。"
    )


class ToolErrorCategory(str, Enum):
    RETRYABLE_PARAM_ERROR = "retryable_param_error"
    TRANSIENT_TIMEOUT = "transient_timeout"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    POLICY_VIOLATION = "policy_violation"
    UNKNOWN_ERROR = "unknown_error"


@dataclass(frozen=True)
class ToolSelfHealAdvice:
    category: ToolErrorCategory
    retryable: bool
    healing_instruction: str
    user_safe_message: str


class ToolErrorSelfHealer:
    """Classifies tool exceptions or structured error payloads into deterministic recovery actions."""

    @classmethod
    def classify_error(
        cls,
        tool_name: str,
        error: Optional[Exception] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> ToolSelfHealAdvice:
        err_text = str(error or "").lower()
        err_code = str((payload or {}).get("error_code") or (payload or {}).get("error") or "").lower()
        combined = f"{err_code} {err_text}"

        if "policy_violation" in combined or "越界" in combined or "权限" in combined:
            return ToolSelfHealAdvice(
                category=ToolErrorCategory.POLICY_VIOLATION,
                retryable=False,
                healing_instruction=(
                    f"[Tool自愈: 权限/边界拦截] 工具 {tool_name} 入参超出业务规则边界。"
                    "严禁绕过或编造优惠/档期，请坦诚告知客户规则限制并引导合规方案。"
                ),
                user_safe_message="该参数超出系统合规授权范围，请调整后重试或转人工处理。",
            )

        if isinstance(error, TimeoutError) or any(
            k in combined for k in ("timeout", "timed out", "超时", "deadline")
        ):
            return ToolSelfHealAdvice(
                category=ToolErrorCategory.TRANSIENT_TIMEOUT,
                retryable=True,
                healing_instruction=(
                    f"[Tool自愈: 超时降级] 工具 {tool_name} 调用超时。"
                    "可尝试精简参数重试一次，或改用备用检索/坦诚告知客户当前无法实时查询，绝不可编造数据。"
                ),
                user_safe_message="当前外部服务响应超时，建议稍后重试或改用基础信息核对。",
            )

        if any(
            k in combined
            for k in ("not registered", "unavailable", "connection", "503", "502", "未注册", "不可用")
        ):
            return ToolSelfHealAdvice(
                category=ToolErrorCategory.BACKEND_UNAVAILABLE,
                retryable=False,
                healing_instruction=(
                    f"[Tool自愈: 服务不可用] 工具 {tool_name} 后端数据源暂不可用。"
                    "请切换备用信息源（如已召回车型快照）或坦诚告知客户暂无法查询，严禁虚构参数或价格。"
                ),
                user_safe_message="外部数据源暂时不可用，请基于已核验信息回答或坦诚告知无法查询。",
            )

        if any(
            k in combined
            for k in ("invalid", "validation", "missing", "not found", "未找到", "缺失", "格式")
        ):
            return ToolSelfHealAdvice(
                category=ToolErrorCategory.RETRYABLE_PARAM_ERROR,
                retryable=True,
                healing_instruction=(
                    f"[Tool自愈: 参数修正] 工具 {tool_name} 返回参数校验错误（{combined.strip()[:120]}）。"
                    "请检查并修正入参后重试，或向客户追问缺失字段。"
                ),
                user_safe_message="工具入参不完整或格式有误，请修正参数后重试。",
            )

        return ToolSelfHealAdvice(
            category=ToolErrorCategory.UNKNOWN_ERROR,
            retryable=False,
            healing_instruction=(
                f"[Tool自愈: 异常兜底] 工具 {tool_name} 执行失败。"
                "请勿吞掉异常或编造结果，应坦诚告知客户当前无法完成该项实时查询。"
            ),
            user_safe_message="工具执行遇到未预期异常，请坦诚告知客户无法实时查询。",
        )
