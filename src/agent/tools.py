"""
Per-stage tool sets.

Each stage exposes only the tools that make sense there. The model is shown
that subset and nothing else, and a call to a tool outside the current stage's
set is refused by the dispatcher — the same treatment an illegal graph edge
gets. Prompting alone would make the tool set a suggestion; the registry makes
it an invariant.

Why that matters concretely: without it, a model still in profile-gathering can
call `record_reservation` because the customer mentioned "next Saturday" in
passing, and the conversation acquires a booking for a car nobody has chosen.
Restricting by stage means the SOP is enforced by which verbs exist, not only
by which stage label is set.

Tools mutate the session state and nothing else. No retrieval, no storage, no
network — `src/agent` must stay importable without a backend (see
tests/test_agent_isolation.py), so anything needing the outside world is
expressed as a *request* the caller fulfils, not a call the agent makes.

Every write returns the `StatePatch` list it produced, so the patch log records
which tool set which field rather than only that the field changed.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.agent.patches import PatchOp, StatePatch, apply_patches, invert
from src.agent.schemas import SessionState, Stage, UserRole
from src.privacy.security_logger import security_audit_logger

logger = logging.getLogger(__name__)

ROLE_ALLOWED_TOOLS: Dict[UserRole, Tuple[str, ...]] = {
    UserRole.CUSTOMER: (
        "record_profile",
        "record_need",
        "record_reservation",
        "request_clarification",
        "transition_to",
        "select_vehicle",
        "request_more_options",
        "confirm_reservation",
    ),
    UserRole.SALESPERSON: (
        "record_profile",
        "record_need",
        "record_reservation",
        "request_clarification",
        "transition_to",
        "select_vehicle",
        "confirm_reservation",
        "apply_discount",
        "override_stage",
    ),
    UserRole.ADMIN: (
        "record_profile",
        "record_need",
        "record_reservation",
        "request_clarification",
        "transition_to",
        "select_vehicle",
        "confirm_reservation",
        "apply_discount",
        "override_stage",
    ),
}


def sanitize_tool_args(
    tool_name: str, args: Dict[str, Any], state: SessionState
) -> Tuple[Dict[str, Any], bool]:
    """
    Sanitize tool call arguments:
    1. Truncate ultra-long string inputs (>500 chars).
    2. Strip dangerous HTML/Script tags and SQL injection keywords.
    """
    sanitized: Dict[str, Any] = {}
    was_sanitized = False

    for k, v in args.items():
        if isinstance(v, str):
            orig = v
            if len(v) > 500:
                v = v[:500]
                was_sanitized = True

            v_clean = re.sub(
                r"<(script|iframe|object|embed)[^>]*>.*?</\1>", "", v, flags=re.IGNORECASE
            )
            v_clean = re.sub(r"javascript:", "", v_clean, flags=re.IGNORECASE)
            v_clean = re.sub(
                r"(\b(SELECT|INSERT|DELETE|UPDATE|DROP|UNION)\b)", "", v_clean, flags=re.IGNORECASE
            )

            if v_clean != orig:
                was_sanitized = True
                v = v_clean

            sanitized[k] = v
        elif isinstance(v, dict):
            sub_san, sub_flag = sanitize_tool_args(tool_name, v, state)
            sanitized[k] = sub_san
            if sub_flag:
                was_sanitized = True
        else:
            sanitized[k] = v

    if was_sanitized:
        security_audit_logger.log_event(
            event_type="ARGS_SANITIZED",
            severity="WARNING",
            session_id=state.session_id,
            trace_id=state.trace_id,
            details={"tool": tool_name, "raw_args": str(args)[:200]},
        )

    return sanitized, was_sanitized


@dataclass
class ToolResult:
    """Outcome of one tool call."""

    ok: bool
    tool: str
    message: str = ""
    patches: List[StatePatch] = field(default_factory=list)
    #: Something the caller must act on — a transition proposal, a request for
    #: retrieval. The agent states the intent; the orchestrator carries it out.
    request: Optional[Dict[str, Any]] = None
    rolled_back: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "tool": self.tool,
            "message": self.message,
            "patches": [p.to_dict() for p in self.patches],
            "request": self.request,
            "rolled_back": self.rolled_back,
        }


@dataclass(frozen=True)
class ToolSpec:
    """A tool the model may call: name, description, parameter schema, handler."""

    name: str
    description: str
    parameters: Dict[str, str]
    handler: Callable[[SessionState, Dict[str, Any]], ToolResult]
    required: Tuple[str, ...] = ()

    def signature(self) -> str:
        """One-line rendering for the prompt."""
        params = ", ".join(
            f"{name}{'' if name in self.required else '?'}: {desc}"
            for name, desc in self.parameters.items()
        )
        return f"{self.name}({params}) — {self.description}"


# ── Handlers ──────────────────────────────────────────────────────────


def _write_fields(model, values: Dict[str, Any], prefix: str, tool: str) -> List[StatePatch]:
    """
    Set fields on a Pydantic sub-model, emitting a patch per real change.

    Unknown field names are dropped with a warning rather than raising: a model
    inventing `budget` where the schema says `prize` should cost that one field,
    not the turn.
    """
    patches: List[StatePatch] = []
    for name, value in values.items():
        if not hasattr(model, name):
            logger.warning(f"[{tool}] unknown field {name!r}; ignored")
            continue
        if value in ("", None):
            continue
        previous = getattr(model, name)
        if previous == value:
            continue
        setattr(model, name, value)
        patches.append(
            StatePatch(
                op=PatchOp.UPDATE if previous else PatchOp.ADD,
                path=f"{prefix}.{name}",
                value=value,
                previous=previous,
                source=tool,
            )
        )
    return patches


def _record_profile(state: SessionState, args: Dict[str, Any]) -> ToolResult:
    fields = args.get("fields") or {}
    if not isinstance(fields, dict):
        return ToolResult(False, "record_profile", "fields 必须是对象")
    patches = _write_fields(state.profile, fields, "profile", "record_profile")
    return ToolResult(
        ok=True,
        tool="record_profile",
        message=f"已记录 {len(patches)} 项客户信息" if patches else "没有新信息",
        patches=patches,
    )


def _record_need(state: SessionState, args: Dict[str, Any]) -> ToolResult:
    fields = args.get("fields") or {}
    if not isinstance(fields, dict):
        return ToolResult(False, "record_need", "fields 必须是对象")
    patches = _write_fields(state.needs.explicit, fields, "needs.explicit", "record_need")
    return ToolResult(
        ok=True,
        tool="record_need",
        message=f"已记录 {len(patches)} 项需求" if patches else "没有新需求",
        patches=patches,
    )


def _record_reservation(state: SessionState, args: Dict[str, Any]) -> ToolResult:
    fields = args.get("fields") or {}
    if not isinstance(fields, dict):
        return ToolResult(False, "record_reservation", "fields 必须是对象")
    patches = _write_fields(state.reservation, fields, "reservation", "record_reservation")
    return ToolResult(
        ok=True,
        tool="record_reservation",
        message=f"已记录 {len(patches)} 项预约信息" if patches else "没有新的预约信息",
        patches=patches,
    )


def _select_vehicle(state: SessionState, args: Dict[str, Any]) -> ToolResult:
    """
    Mark which of the retrieved cars the customer settled on.

    Reorders rather than filters: the runner-up stays available in case the
    customer changes their mind, which they do.
    """
    car_model = str(args.get("car_model", "")).strip()
    if not car_model:
        return ToolResult(False, "select_vehicle", "缺少 car_model")

    matched = list(state.matched_cars)
    chosen = [c for c in matched if c.get("car_model") == car_model]
    if not chosen:
        available = [c.get("car_model") for c in matched]
        return ToolResult(
            False,
            "select_vehicle",
            f"{car_model} 不在当前匹配结果中（可选：{available}）",
        )

    state.matched_cars = chosen + [c for c in matched if c.get("car_model") != car_model]
    return ToolResult(
        ok=True,
        tool="select_vehicle",
        message=f"已确认意向车型：{car_model}",
        patches=[
            StatePatch(
                op=PatchOp.UPDATE,
                path="matched_cars.selected",
                value=car_model,
                source="select_vehicle",
            )
        ],
    )


def _request_clarification(state: SessionState, args: Dict[str, Any]) -> ToolResult:
    """Declare which field is blocking, so the reply asks one clear question."""
    field_name = str(args.get("field", "")).strip()
    if not field_name:
        return ToolResult(False, "request_clarification", "缺少 field")
    return ToolResult(
        ok=True,
        tool="request_clarification",
        message=f"需要向客户询问：{field_name}",
        request={"type": "clarify", "field": field_name, "reason": args.get("reason", "")},
    )


def _request_more_options(state: SessionState, args: Dict[str, Any]) -> ToolResult:
    """
    Ask the orchestrator to retrieve again.

    A request, not a call: retrieval lives in the backend and the agent may not
    import it.
    """
    return ToolResult(
        ok=True,
        tool="request_more_options",
        message="已请求更多候选车型",
        request={"type": "retrieve", "reason": str(args.get("reason", ""))[:200]},
    )


def _confirm_reservation(state: SessionState, args: Dict[str, Any]) -> ToolResult:
    """Assert the booking is complete. Refuses while any slot is empty."""
    missing = [
        label
        for label, value in (
            ("试驾人", state.reservation.test_driver),
            ("日期", state.reservation.reservation_date),
            ("时间", state.reservation.reservation_time),
            ("门店", state.reservation.reservation_location),
            ("联系电话", state.reservation.reservation_phone_number),
        )
        if not value
    ]
    if missing:
        return ToolResult(
            False,
            "confirm_reservation",
            f"预约信息不完整，缺少：{'、'.join(missing)}",
        )
    return ToolResult(ok=True, tool="confirm_reservation", message="预约信息已齐备")


def _transition_to(state: SessionState, args: Dict[str, Any]) -> ToolResult:
    """
    Propose a stage change. Never performs one.

    The proposal goes to `stages.arbitrate`, which checks the edge and its
    guard. This tool exists so the model has a structured way to say "I think
    this step is done", not so it can decide.
    """
    raw = str(args.get("stage", "")).strip()
    target = next((s for s in Stage if raw.lower() in (s.value.lower(), s.name.lower())), None)
    if target is None:
        return ToolResult(False, "transition_to", f"未知阶段：{raw!r}")
    return ToolResult(
        ok=True,
        tool="transition_to",
        message=f"提议进入 {target.value}",
        request={
            "type": "transition",
            "stage": target.value,
            "reason": str(args.get("reason", ""))[:200],
        },
    )


# ── Registry ──────────────────────────────────────────────────────────

TOOLS: Dict[str, ToolSpec] = {
    spec.name: spec
    for spec in (
        ToolSpec(
            name="record_profile",
            description="记录客户画像信息",
            parameters={
                "fields": "对象，键为 name/age/family_size/residence/parking_conditions"
                "/target_driver/expertise/price_sensitivity/title"
            },
            handler=_record_profile,
            required=("fields",),
        ),
        ToolSpec(
            name="record_need",
            description="记录客户明确表达的购车需求",
            parameters={
                "fields": "对象，键为 prize/brand/powertrain_type"
                "/vehicle_category_bottom/design_style/seat_layout 等"
            },
            handler=_record_need,
            required=("fields",),
        ),
        ToolSpec(
            name="record_reservation",
            description="记录试驾预约信息",
            parameters={
                "fields": "对象，键为 test_driver/reservation_date/reservation_time"
                "/reservation_location/reservation_phone_number"
            },
            handler=_record_reservation,
            required=("fields",),
        ),
        ToolSpec(
            name="select_vehicle",
            description="确认客户选定的意向车型",
            parameters={"car_model": "车型名，必须来自当前匹配结果"},
            handler=_select_vehicle,
            required=("car_model",),
        ),
        ToolSpec(
            name="request_clarification",
            description="指出当前缺失、需要向客户追问的字段",
            parameters={"field": "缺失字段名", "reason": "为什么需要"},
            handler=_request_clarification,
            required=("field",),
        ),
        ToolSpec(
            name="request_more_options",
            description="当前候选车型都不合适，请求重新检索",
            parameters={"reason": "为什么需要更多选项"},
            handler=_request_more_options,
        ),
        ToolSpec(
            name="confirm_reservation",
            description="确认预约信息已齐备",
            parameters={},
            handler=_confirm_reservation,
        ),
        ToolSpec(
            name="transition_to",
            description="提议进入下一阶段（系统会校验是否允许）",
            parameters={"stage": "目标阶段值", "reason": "简短理由"},
            handler=_transition_to,
            required=("stage",),
        ),
    )
}

#: The candidate tool set per stage. A stage's tools are the only ones the
#: model is shown and the only ones the dispatcher will run there.
#:
#: `transition_to` is available everywhere except FAREWELL, which is terminal.
#: `record_need` appears in CAR_SELECTION too: customers routinely revise a
#: requirement while looking at recommendations, and forcing that through a
#: stage change first would lose the correction.
STAGE_TOOLS: Dict[Stage, Tuple[str, ...]] = {
    Stage.WELCOME: ("transition_to",),
    Stage.PROFILE_ANALYSIS: ("record_profile", "request_clarification", "transition_to"),
    Stage.NEEDS_ANALYSIS: ("record_need", "request_clarification", "transition_to"),
    Stage.CAR_SELECTION: (
        "select_vehicle",
        "record_need",
        "request_more_options",
        "transition_to",
    ),
    Stage.RESERVATION_4S: ("record_reservation", "request_clarification", "transition_to"),
    Stage.RESERVATION_CONFIRMATION: (
        "confirm_reservation",
        "record_reservation",
        "transition_to",
    ),
    Stage.FAREWELL: (),
}


def tools_for(stage: Stage) -> List[ToolSpec]:
    """The candidate tools for a stage, in declaration order."""
    return [TOOLS[name] for name in STAGE_TOOLS.get(stage, ()) if name in TOOLS]


def is_allowed(stage: Stage, tool_name: str) -> bool:
    """Whether `tool_name` may be called in `stage`."""
    return tool_name in STAGE_TOOLS.get(stage, ())


def render_catalog(stage: Stage) -> str:
    """The tool list as shown to the model. Empty when the stage has none."""
    specs = tools_for(stage)
    if not specs:
        return "（当前阶段没有可用工具）"
    return "\n".join(f"- {spec.signature()}" for spec in specs)


def dispatch(state: SessionState, tool_name: str, args: Dict[str, Any]) -> ToolResult:
    """
    Run a tool call against the state, enforcing RBAC role permissions,
    stage tool sets, and argument sanitization.
    """
    spec = TOOLS.get(tool_name)
    if spec is None:
        return ToolResult(False, tool_name, f"未知工具：{tool_name}")

    # 1. RBAC UserRole permission check
    role_allowed = ROLE_ALLOWED_TOOLS.get(state.user_role, ())
    if tool_name not in role_allowed:
        msg = f"角色权限不足：当前角色 [{state.user_role.value}] 无权调用工具 [{tool_name}]"
        logger.warning(f"[{state.session_id}] RBAC refusal: {msg}")
        security_audit_logger.log_event(
            event_type="UNAUTHORIZED_TOOL",
            severity="WARNING",
            session_id=state.session_id,
            trace_id=state.trace_id,
            details={"tool": tool_name, "user_role": state.user_role.value},
        )
        return ToolResult(False, tool_name, msg)

    # 2. Stage permission check
    if not is_allowed(state.stage, tool_name):
        allowed = ", ".join(STAGE_TOOLS.get(state.stage, ())) or "无"
        logger.warning(
            f"Tool {tool_name!r} refused in stage {state.stage.value} (allowed: {allowed})"
        )
        return ToolResult(
            False,
            tool_name,
            f"当前阶段（{state.stage.value}）不允许调用 {tool_name}，可用工具：{allowed}",
        )

    # 3. Argument sanitization
    sanitized_args, _ = sanitize_tool_args(tool_name, args, state)

    missing = [name for name in spec.required if not sanitized_args.get(name)]
    if missing:
        return ToolResult(False, tool_name, f"缺少必需参数：{'、'.join(missing)}")

    try:
        return spec.handler(state, sanitized_args)
    except Exception as exc:
        logger.error(f"Tool {tool_name} raised: {exc}")
        return ToolResult(False, tool_name, f"工具执行失败：{exc}")


def dispatch_all(
    state: SessionState, calls: List[Dict[str, Any]], atomic: bool = False
) -> List[ToolResult]:
    """
    Run a batch of `{"tool": ..., "args": {...}}` calls in order.

    Order matters and is preserved: a turn that records a need and then
    proposes a transition must have the need in state before the guard on that
    transition is evaluated.

    If `atomic` is True:
        Runs as a transaction. If any tool fails or raises an exception, all state
        patches produced by preceding successful tools in this batch are cleanly
        inverted and applied back to `state`, rolling back state mutations to pre-batch.
    """
    results: List[ToolResult] = []
    accumulated_patches: List[StatePatch] = []

    for call in calls:
        name = str(call.get("tool") or call.get("name") or "")
        args = call.get("args") or call.get("arguments") or {}
        if not isinstance(args, dict):
            failed_res = ToolResult(False, name, "args 必须是对象", rolled_back=atomic)
            results.append(failed_res)
            if atomic:
                if accumulated_patches:
                    apply_patches(state, invert(accumulated_patches))
                break
            continue

        try:
            res = dispatch(state, name, args)
        except Exception as exc:
            res = ToolResult(False, name, f"工具执行异常：{exc}")

        if res.ok:
            accumulated_patches.extend(res.patches)
            results.append(res)
        else:
            if atomic:
                res.rolled_back = True
                res.message = f"{res.message} (事务已全额回滚)"
                results.append(res)
                if accumulated_patches:
                    apply_patches(state, invert(accumulated_patches))
                break
            else:
                results.append(res)

    return results


def dispatch_transactional(state: SessionState, calls: List[Dict[str, Any]]) -> List[ToolResult]:
    """
    Convenience wrapper to run a batch of tool calls with transactional rollback guarantee.
    """
    return dispatch_all(state, calls, atomic=True)
