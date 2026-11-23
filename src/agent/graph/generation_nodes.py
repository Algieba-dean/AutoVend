"""
Plugin/SubDAG, generation, tool-contract execution, anti-hallucination audit,
and safe-degradation graph nodes (`src/agent/graph/generation_nodes.py`).
"""

import asyncio
import hashlib
import json as _json
import logging
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, Dict, List, Literal, Tuple

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from src.agent.events import (
    AnyDialogueEvent,
    SystemNoteAdded,
    SystemNotesCleared,
    diff_to_events,
)
from src.agent.execution_guard import (
    ToolErrorSelfHealer,
    build_safe_degradation_response,
    check_step_budget,
)
from src.agent.graph.state import (
    PROMPT_PATCH_WINDOW,
    AgentGraphState,
    project_current_state,
)
from src.agent.guardrail.compliance import DualStreamComplianceGuard
from src.agent.langchain_chains import _fallback_response, build_reply_messages
from src.agent.langchain_tools import enforce_tool_result_limit, get_tool_contract
from src.agent.nba_planner import NextBestActionPlanner
from src.agent.patches import StatePatch, format_for_prompt
from src.agent.reflection import audit_response_against_evidence
from src.agent.schemas import SessionState, Stage
from src.agent.subdag import run_stage_subdag
from src.core.agentops import agent_slo_monitor, enqueue_agent_dlq, record_compliance_audit
from src.llm.cost_ledger import AgentNodeRole, cost_ledger, node_cost_context
from src.privacy.prompt_sanitizer import PromptSanitizer

logger = logging.getLogger(__name__)


def node_run_plugins_and_subdag(agent: Any, state: AgentGraphState) -> Dict[str, Any]:
    before_sess = state["session_state"].model_copy(deep=True)
    sess = before_sess.model_copy(deep=True)
    last_user_msg = state.get("safe_message") or state.get("user_message", "")
    conversation_text = state.get("conversation_text", "")
    turn_id = int(getattr(sess, "turn_count", 0))

    plugin_context: Dict[str, Any] = {
        "user_input": last_user_msg or conversation_text,
        "conversation_text": conversation_text,
        "matched_cars": sess.matched_cars,
        "skip_reflection_plugin": True,
    }
    agent.plugin_pipeline.run_before_response(sess, plugin_context)
    sess = run_stage_subdag(sess)

    nba_decision = NextBestActionPlanner.plan(
        sess=sess,
        user_message=last_user_msg,
        topic_intent=state.get("topic_intent", ""),
        hitl_triggered=bool(state.get("hitl_triggered", False)),
    )
    NextBestActionPlanner.update_ask_counter(sess, nba_decision)

    plugin_events = diff_to_events(
        before_sess,
        sess,
        turn_id=turn_id,
        source="plugins_and_subdag",
    )

    before_notes = set(before_sess.system_notes or [])
    notes = list(sess.system_notes)
    if nba_decision.directive and nba_decision.directive not in notes:
        notes.append(nba_decision.directive)
    for n in notes:
        if n and n not in before_notes:
            plugin_events.append(
                SystemNoteAdded(turn_id=turn_id, source="plugins_and_subdag", note=n)
            )
    patch_summary = format_for_prompt(
        [StatePatch.from_dict(p) for p in sess.patch_log[-PROMPT_PATCH_WINDOW:]]
    )
    if patch_summary:
        notes.append(patch_summary)

    trace = [*list(state.get("execution_trace") or []), "run_plugins_and_subdag"]
    return {
        "events": plugin_events,
        "session_state": sess,
        "notes": notes,
        "plugin_context": plugin_context,
        "next_best_action": nba_decision.action.value,
        "step_count": int(state.get("step_count", 0)) + 1,
        "execution_trace": trace,
    }


def build_generation_inputs(state: AgentGraphState) -> Tuple[SessionState, List[AnyMessage]]:
    sess = state["session_state"].model_copy(deep=True)
    conversation_text = state.get("conversation_text", "")
    notes = state.get("notes", [])
    all_msgs = list(state.get("messages") or [])

    trailing_tool_msgs: List[AnyMessage] = []
    dialogue_msgs = list(all_msgs)
    while dialogue_msgs and isinstance(dialogue_msgs[-1], (ToolMessage, AIMessage)):
        last = dialogue_msgs[-1]
        if isinstance(last, ToolMessage) or getattr(last, "tool_calls", None):
            trailing_tool_msgs.insert(0, dialogue_msgs.pop())
        else:
            break

    prompt_msgs = build_reply_messages(
        stage=sess.stage,
        conversation_history=conversation_text,
        profile=sess.profile,
        needs=sess.needs,
        matched_cars=sess.matched_cars,
        reservation=sess.reservation,
        system_notes=notes,
        messages=dialogue_msgs,
        preferences=sess.preferences,
        pending_confirmation=sess.pending_confirmation,
    )
    prompt_msgs.extend(trailing_tool_msgs)
    return sess, prompt_msgs


def finalize_generation_output(
    agent: Any, state: AgentGraphState, sess: SessionState, ai_msg: AIMessage
) -> Dict[str, Any]:
    tool_calls = getattr(ai_msg, "tool_calls", None) or []
    iters = int(state.get("tool_iterations", 0))
    trace = [*list(state.get("execution_trace") or []), "generate_reply"]
    step = int(state.get("step_count", 0)) + 1
    if tool_calls and iters < agent.budget_config.max_tool_iterations:
        return {
            "messages": [ai_msg],
            "tool_iterations": iters + 1,
            "step_count": step,
            "execution_trace": trace,
        }

    raw_text = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
    post_ctx = agent.hook_manager.run_post_response(sess.session_id, raw_text)
    reply = post_ctx.sanitized_response or _fallback_response(sess.stage, sess.profile)
    plugin_context = state.get("plugin_context", {})
    reply = agent.plugin_pipeline.run_after_response(reply, plugin_context)
    clear_events: List[AnyDialogueEvent] = []
    if sess.system_notes:
        clear_events.append(
            SystemNotesCleared(
                turn_id=int(getattr(sess, "turn_count", 0)),
                source="finalize_generation",
            )
        )
    sess.system_notes = []

    return {
        "events": clear_events,
        "session_state": sess,
        "response_text": reply,
        "messages": [AIMessage(content=reply)],
        "step_count": step,
        "execution_trace": trace,
    }


def node_generate_reply_sync(agent: Any, state: AgentGraphState) -> Dict[str, Any]:
    sess, prompt_msgs = build_generation_inputs(state)
    within_budget, reason = check_step_budget(int(state.get("step_count", 0)), agent.budget_config)
    if not within_budget:
        return {"budget_exhausted": True, "degrade_reason": reason}
    if not cost_ledger.check_budget(sess.session_id):
        logger.warning(f"[{sess.session_id}] CostLedger budget exceeded; degrading generation.")
        return {"budget_exhausted": True, "degrade_reason": "cost_ledger_budget_exceeded"}
    with node_cost_context(sess.session_id, AgentNodeRole.GENERATOR):
        try:
            runnable = agent._get_generation_runnable()
            timeout_s = float(getattr(agent.budget_config, "per_node_timeout_s", 0.0) or 0.0)
            if timeout_s > 0:
                fut = agent._sync_executor.submit(runnable.invoke, prompt_msgs)
                try:
                    ai_msg = fut.result(timeout=timeout_s)
                except FuturesTimeoutError:
                    fut.cancel()
                    logger.warning(
                        f"[{sess.session_id}] generate_reply sync timed out after {timeout_s}s"
                    )
                    return {
                        "budget_exhausted": True,
                        "degrade_reason": f"node_timeout:generate_reply:{timeout_s}s",
                    }
            else:
                ai_msg = runnable.invoke(prompt_msgs)
            if not isinstance(ai_msg, AIMessage):
                ai_msg = AIMessage(content=getattr(ai_msg, "content", str(ai_msg)))
        except Exception as exc:
            logger.error(f"LangGraph reply generation failed at stage {sess.stage.value}: {exc}")
            ai_msg = AIMessage(content=_fallback_response(sess.stage, sess.profile))
    return finalize_generation_output(agent, state, sess, ai_msg)


async def node_generate_reply_async(agent: Any, state: AgentGraphState) -> Dict[str, Any]:
    sess, prompt_msgs = build_generation_inputs(state)
    within_budget, reason = check_step_budget(int(state.get("step_count", 0)), agent.budget_config)
    if not within_budget:
        return {"budget_exhausted": True, "degrade_reason": reason}
    if not cost_ledger.check_budget(sess.session_id):
        logger.warning(f"[{sess.session_id}] CostLedger budget exceeded; degrading async generation.")
        return {"budget_exhausted": True, "degrade_reason": "cost_ledger_budget_exceeded"}
    with node_cost_context(sess.session_id, AgentNodeRole.GENERATOR):
        try:
            runnable = agent._get_generation_runnable()
            timeout_s = float(getattr(agent.budget_config, "per_node_timeout_s", 0.0) or 0.0)
            if timeout_s > 0:
                try:
                    ai_msg = await asyncio.wait_for(
                        runnable.ainvoke(prompt_msgs), timeout=timeout_s
                    )
                except (asyncio.TimeoutError, TimeoutError):
                    logger.warning(
                        f"[{sess.session_id}] generate_reply async timed out after {timeout_s}s"
                    )
                    return {
                        "budget_exhausted": True,
                        "degrade_reason": f"node_timeout:generate_reply:{timeout_s}s",
                    }
            else:
                ai_msg = await runnable.ainvoke(prompt_msgs)
            if not isinstance(ai_msg, AIMessage):
                ai_msg = AIMessage(content=getattr(ai_msg, "content", str(ai_msg)))
        except Exception as exc:
            logger.error(f"LangGraph async reply generation failed at stage {sess.stage.value}: {exc}")
            ai_msg = AIMessage(content=_fallback_response(sess.stage, sess.profile))
    return finalize_generation_output(agent, state, sess, ai_msg)


def route_after_generate(
    agent: Any, state: AgentGraphState
) -> Literal["tools", "audit_hallucination", "safe_degrade"]:
    if state.get("budget_exhausted"):
        return "safe_degrade"
    messages = state.get("messages") or []
    if messages:
        last = messages[-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            if int(state.get("tool_iterations", 0)) <= agent.budget_config.max_tool_iterations:
                return "tools"
    return "audit_hallucination"


def node_tools_with_contract(agent: Any, state: AgentGraphState) -> Dict[str, Any]:
    """Contract-aware ToolNode: PreToolHook, idempotency_key, self-healing & output isolation."""
    sess = state.get("session_state")
    session_id = sess.session_id if sess is not None else (state.get("session_id") or "default")
    messages = list(state.get("messages") or [])
    last_msg = messages[-1] if messages else None
    tool_calls = getattr(last_msg, "tool_calls", None) or []

    blocked_msgs: List[ToolMessage] = []
    allowed_calls = []
    for tc in tool_calls:
        t_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
        t_args = dict(tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {}) or {})
        t_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")

        contract = get_tool_contract(t_name)
        if contract.requiresIdempotencyKey and not str(t_args.get("idempotency_key") or "").strip():
            raw_sig = _json.dumps(t_args, sort_keys=True, ensure_ascii=False)
            t_args["idempotency_key"] = (
                f"{session_id}:{t_name}:{hashlib.sha256(raw_sig.encode('utf-8')).hexdigest()[:12]}"
            )
            if isinstance(tc, dict):
                tc = {**tc, "args": t_args}

        hook_ctx = agent.hook_manager.run_pre_tool(session_id, t_name, t_args)
        if not hook_ctx.approved:
            record_compliance_audit(
                event_type="TOOL_POLICY_BLOCKED",
                session_id=session_id,
                trace_id=sess.trace_id if sess else "",
                checkpoint_id=session_id,
                severity="WARNING",
                details={"tool_name": t_name, "args": t_args, "reason": hook_ctx.rejection_reason},
            )
            blocked_msgs.append(
                ToolMessage(
                    content=hook_ctx.rejection_reason,
                    tool_call_id=t_id,
                    name=t_name,
                )
            )
        else:
            allowed_calls.append(tc)

    trace = [*list(state.get("execution_trace") or []), "tools"]
    step = int(state.get("step_count", 0)) + 1

    if blocked_msgs and not allowed_calls:
        return {"messages": blocked_msgs, "step_count": step, "execution_trace": trace}

    call_args_by_id: Dict[str, Any] = {}
    for tc in allowed_calls:
        tc_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
        tc_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
        if tc_id:
            call_args_by_id[tc_id] = tc_args

    invoke_state = state
    if last_msg is not None and isinstance(last_msg, AIMessage):
        filtered_ai = last_msg.model_copy(update={"tool_calls": allowed_calls})
        invoke_state = {**state, "messages": [*messages[:-1], filtered_ai]}

    base_tool_node = ToolNode(agent.tools)
    try:
        out = base_tool_node.invoke(invoke_state)
    except Exception as exc:
        enqueue_agent_dlq(
            task_type="tool_execution",
            session_id=session_id,
            checkpoint_id=session_id,
            trace_id=sess.trace_id if sess else "",
            error_message=str(exc),
            error_category="tool_exception",
            context_snapshot={"tool_calls": [str(tc)[:200] for tc in tool_calls]},
        )
        healed_msgs: List[ToolMessage] = []
        for tc in allowed_calls:
            tc_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
            tc_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
            advice = ToolErrorSelfHealer.classify_error(tc_name, error=exc)
            healed_msgs.append(
                ToolMessage(
                    content=_json.dumps(
                        {
                            "error_code": advice.category.value.upper(),
                            "retryable": advice.retryable,
                            "healing_instruction": advice.healing_instruction,
                            "message": advice.user_safe_message,
                        },
                        ensure_ascii=False,
                    ),
                    tool_call_id=tc_id,
                    name=tc_name,
                )
            )
        return {
            "messages": [*blocked_msgs, *healed_msgs],
            "step_count": step,
            "execution_trace": trace,
        }

    out_msgs = list(out.get("messages") or [])
    bounded_msgs: List[AnyMessage] = []
    audit_tools = {
        "calculate_drive_away_price",
        "submit_test_drive_reservation",
        "validate_test_drive_slot",
    }
    external_text_tools = {"search_vehicles", "get_vehicle_detail"}
    for msg in out_msgs:
        if isinstance(msg, ToolMessage):
            t_name = getattr(msg, "name", None) or ""
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if content.lstrip().startswith("{"):
                try:
                    parsed_payload = _json.loads(content)
                    if isinstance(parsed_payload, dict) and (
                        parsed_payload.get("error")
                        or parsed_payload.get("error_code")
                        or parsed_payload.get("submitted") is False
                    ):
                        advice = ToolErrorSelfHealer.classify_error(t_name, payload=parsed_payload)
                        parsed_payload.setdefault("error_category", advice.category.value)
                        parsed_payload.setdefault("retryable", advice.retryable)
                        parsed_payload.setdefault(
                            "healing_instruction", advice.healing_instruction
                        )
                        content = _json.dumps(parsed_payload, ensure_ascii=False)
                except Exception:
                    pass
            bounded_content = enforce_tool_result_limit(t_name, content)
            if t_name in external_text_tools:
                bounded_content, inj = PromptSanitizer.wrap_tool_output(t_name, bounded_content)
                if inj:
                    record_compliance_audit(
                        event_type="INDIRECT_PROMPT_INJECTION",
                        session_id=session_id,
                        trace_id=sess.trace_id if sess else "",
                        checkpoint_id=session_id,
                        severity="CRITICAL",
                        details={"tool_name": t_name, "detected_patterns": inj},
                    )
            if t_name in audit_tools:
                record_compliance_audit(
                    event_type="TOOL_COMPLIANCE_AUDIT",
                    session_id=session_id,
                    trace_id=sess.trace_id if sess else "",
                    checkpoint_id=session_id,
                    details={
                        "tool_name": t_name,
                        "input_args": call_args_by_id.get(msg.tool_call_id, {}),
                        "output_preview": bounded_content[:300],
                    },
                )
            bounded_msgs.append(
                ToolMessage(
                    content=bounded_content,
                    tool_call_id=msg.tool_call_id,
                    name=getattr(msg, "name", None),
                )
            )
        else:
            bounded_msgs.append(msg)
    return {
        "messages": [*blocked_msgs, *bounded_msgs],
        "step_count": step,
        "execution_trace": trace,
    }


def node_audit_hallucination(agent: Any, state: AgentGraphState) -> Dict[str, Any]:
    """Anti-hallucination audit node + independent low-latency outbound compliance guardrail."""
    sess = state["session_state"].model_copy(deep=True)
    reply = state.get("response_text", "")
    retries = int(state.get("audit_retries", 0))
    anchors = state.get("evidence_anchors") or []
    trace = [*list(state.get("execution_trace") or []), "audit_hallucination"]
    step = int(state.get("step_count", 0)) + 1

    outbound_guard = DualStreamComplianceGuard.inspect(reply)
    if not outbound_guard.is_compliant:
        record_compliance_audit(
            event_type="OUTBOUND_COMPLIANCE_GUARDRAIL",
            session_id=sess.session_id,
            trace_id=sess.trace_id,
            checkpoint_id=sess.session_id,
            severity="CRITICAL",
            details={"violations": outbound_guard.violations},
        )
        reply = outbound_guard.guarded_text

    with node_cost_context(sess.session_id, AgentNodeRole.AUDITOR):
        report = audit_response_against_evidence(
            reply,
            matched_cars=sess.matched_cars,
            evidence_anchors=anchors,
            auditor_llm=getattr(agent, "auditor_chat_model", None),
        )

    if anchors:
        record_compliance_audit(
            event_type="EVIDENCE_LEDGER_SNAPSHOT",
            session_id=sess.session_id,
            trace_id=sess.trace_id,
            checkpoint_id=sess.session_id,
            details={"anchors": anchors[:10]},
        )

    is_zero_hit = sess.stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION) and not sess.matched_cars
    crag_rewritten = int(state.get("retrieval_retries", 0)) > 0

    if report.is_clean:
        agent_slo_monitor.record_turn(
            crag_rewritten=crag_rewritten,
            auditor_rejected=False,
            zero_hit=is_zero_hit,
        )
        return {
            "audit_passed": True,
            "response_text": reply,
            "critic_feedback": None,
            "step_count": step,
            "execution_trace": trace,
        }

    critic_msg = "; ".join(report.warnings)
    enqueue_agent_dlq(
        task_type="auditor_rejection",
        session_id=sess.session_id,
        checkpoint_id=sess.session_id,
        trace_id=sess.trace_id,
        user_message=state.get("safe_message") or state.get("user_message", ""),
        stage=sess.stage.value,
        error_message=critic_msg,
        error_category="hallucination_or_compliance_violation",
        context_snapshot={"draft_reply": reply[:400], "anchors": anchors[:5]},
    )

    within_budget, _ = check_step_budget(step, agent.budget_config)
    if within_budget and retries < agent.budget_config.max_audit_retries and report.hallucination_detected:
        logger.warning(
            f"[{sess.session_id}] Audit flagged hallucination (retry #{retries + 1}): {critic_msg}"
        )
        critic_note = f"[反幻觉审计 Critic 意见] 上一版草稿存在事实/参数偏差：{critic_msg}。请严格依据匹配车型与证据账本重写回复。"
        notes = list(state.get("notes") or [])
        if critic_note not in notes:
            notes.append(critic_note)
        return {
            "audit_passed": False,
            "audit_retries": retries + 1,
            "critic_feedback": critic_msg,
            "notes": notes,
            "step_count": step,
            "execution_trace": trace,
        }

    agent_slo_monitor.record_turn(
        crag_rewritten=crag_rewritten,
        auditor_rejected=True,
        zero_hit=is_zero_hit,
    )
    safe_reply = report.sanitized_text.strip() or _fallback_response(sess.stage, sess.profile)
    return {
        "audit_passed": True,
        "response_text": safe_reply,
        "critic_feedback": critic_msg,
        "step_count": step,
        "execution_trace": trace,
    }


def route_after_audit(
    agent: Any, state: AgentGraphState
) -> Literal["generate_reply", "safe_degrade", "__end__"]:
    if state.get("budget_exhausted"):
        return "safe_degrade"
    if not state.get("audit_passed", True):
        within_budget, _ = check_step_budget(int(state.get("step_count", 0)), agent.budget_config)
        if not within_budget:
            return "safe_degrade"
        return "generate_reply"
    return "__end__"


def node_safe_degrade(state: AgentGraphState) -> Dict[str, Any]:
    """Deterministic safe degradation node when step/token/retry budgets exhaust."""
    sess = project_current_state(state)
    reason = state.get("degrade_reason", "budget_exhausted")
    logger.warning(f"[{sess.session_id}] Routing to safe_degrade node (reason={reason})")
    safe_reply = build_safe_degradation_response(sess, reason=reason)
    clear_events: List[AnyDialogueEvent] = []
    if sess.system_notes:
        clear_events.append(
            SystemNotesCleared(
                turn_id=int(getattr(sess, "turn_count", 0)),
                source="safe_degrade",
            )
        )
    sess.system_notes = []
    trace = [*list(state.get("execution_trace") or []), "safe_degrade"]
    return {
        "events": clear_events,
        "session_state": sess,
        "response_text": safe_reply,
        "messages": [AIMessage(content=safe_reply)],
        "execution_trace": trace,
    }
