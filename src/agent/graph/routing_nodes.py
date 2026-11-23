"""
Guard, slot-extraction, policy-arbitration, and HITL graph nodes (`src/agent/graph/routing_nodes.py`).
"""

import logging
import re
import uuid
from typing import Any, Dict, List, Literal

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from src.agent.events import (
    AnyDialogueEvent,
    SessionInitialized,
    SlotUpdated,
    SystemNoteAdded,
    diff_to_events,
    project_state,
)
from src.agent.extractors.combined_needs_extractor import extract_combined_needs
from src.agent.extractors.profile_extractor import extract_profile
from src.agent.extractors.reservation_extractor import extract_reservation
from src.agent.graph.state import (
    AgentGraphState,
    format_messages_as_text,
    project_current_state,
)
from src.agent.hitl import (
    HITLDecision,
    HITLTriggerReason,
    apply_human_resume,
    build_handoff_context,
    is_user_correction,
)
from src.agent.policy_arbitration import (
    PolicyAction,
    arbitrate_policies,
    evaluate_active_loop_policy,
    evaluate_guardrail_policy,
    evaluate_llm_planner_policy,
    evaluate_stage_fsm_rule_policy,
)
from src.agent.preference_model import PreferenceEngine
from src.agent.schemas import SessionState, Stage
from src.agent.topic_manager import TopicManager, UserDialogueIntent
from src.agent.unified_schema import resolve_pending_confirmation
from src.core.agentops import (
    agent_slo_monitor,
    enqueue_agent_dlq,
    get_current_artifact_bundle_version,
    record_compliance_audit,
)
from src.core.long_term_memory import LongTermMemoryStore
from src.core.tiered_engine import TieredRetrievalEngine
from src.llm.cost_ledger import AgentNodeRole, node_cost_context

logger = logging.getLogger(__name__)


def node_guard_and_route(agent: Any, state: AgentGraphState) -> Dict[str, Any]:
    session_id = state.get("session_id") or "default"
    user_message = state.get("user_message", "")
    existing_events = list(state.get("events") or [])
    base_sess = state.get("base_session_state")
    new_events: List[AnyDialogueEvent] = []

    if existing_events:
        sess = project_state(existing_events, base_state=base_sess)
        raw_sess = state.get("session_state")
        if raw_sess is not None:
            caller_events = diff_to_events(
                sess,
                raw_sess,
                turn_id=int(getattr(raw_sess, "turn_count", 0)),
                source="caller_state",
            )
            if caller_events:
                new_events.extend(caller_events)
                sess = raw_sess.model_copy(deep=True)
    else:
        raw_sess = state.get("session_state")
        if raw_sess is None:
            sess = SessionState(session_id=session_id)
            new_events.append(
                SessionInitialized(
                    turn_id=0,
                    source="guard_and_route",
                    session_id=session_id,
                )
            )
        else:
            sess = raw_sess.model_copy(deep=True)
            base_sess = raw_sess.model_copy(deep=True)
            new_events.append(
                SessionInitialized(
                    turn_id=int(getattr(sess, "turn_count", 0)),
                    source="guard_and_route",
                    session_id=sess.session_id or session_id,
                    snapshot=sess.model_dump(mode="json"),
                )
            )

    if not sess.trace_id:
        sess.trace_id = uuid.uuid4().hex[:16]
        new_events.append(
            SlotUpdated(
                turn_id=int(getattr(sess, "turn_count", 0)),
                source="guard_and_route",
                field_path="trace_id",
                value=sess.trace_id,
            )
        )

    turn_hook_ctx = agent.hook_manager.run_pre_turn(
        session_id=sess.session_id,
        raw_message=user_message,
        trace_id=sess.trace_id,
    )
    effective_message = turn_hook_ctx.safe_message
    bundle_ver = get_current_artifact_bundle_version()
    if turn_hook_ctx.injection_detected:
        record_compliance_audit(
            event_type="PROMPT_SANITIZER_INTERCEPT",
            session_id=sess.session_id,
            trace_id=sess.trace_id,
            checkpoint_id=sess.session_id,
            severity="CRITICAL",
            details={
                "detected_patterns": turn_hook_ctx.detected_patterns,
                "artifact_bundle_version": bundle_ver,
            },
        )

    new_turn = int(getattr(sess, "turn_count", 0)) + 1
    new_events.append(
        SlotUpdated(
            turn_id=new_turn,
            source="guard_and_route",
            field_path="turn_count",
            value=new_turn,
        )
    )

    user_key = sess.profile.phone_number or sess.session_id
    if user_key:
        recalled = LongTermMemoryStore.get_instance().recall(user_key)
        if recalled is not None:
            if recalled.parking_conditions and not sess.profile.parking_conditions:
                new_events.append(
                    SlotUpdated(
                        turn_id=new_turn,
                        source="ltm_recall",
                        field_path="profile.parking_conditions",
                        value=recalled.parking_conditions,
                    )
                )
            if recalled.family_size and not sess.profile.family_size:
                new_events.append(
                    SlotUpdated(
                        turn_id=new_turn,
                        source="ltm_recall",
                        field_path="profile.family_size",
                        value=recalled.family_size,
                    )
                )
            if recalled.residence and not sess.profile.residence:
                new_events.append(
                    SlotUpdated(
                        turn_id=new_turn,
                        source="ltm_recall",
                        field_path="profile.residence",
                        value=recalled.residence,
                    )
                )
            mem_note = LongTermMemoryStore.format_for_prompt(recalled)
            if mem_note and mem_note not in sess.system_notes:
                new_events.append(
                    SystemNoteAdded(turn_id=new_turn, source="ltm_recall", note=mem_note)
                )

    existing_msgs = list(state.get("messages") or [])
    new_msg = HumanMessage(content=effective_message)
    conversation_text = format_messages_as_text([*existing_msgs, new_msg])

    new_corr = (
        int(getattr(sess, "consecutive_corrections", 0)) + 1
        if is_user_correction(effective_message)
        else 0
    )
    new_events.append(
        SlotUpdated(
            turn_id=new_turn,
            source="guard_and_route",
            field_path="consecutive_corrections",
            value=new_corr,
        )
    )

    projected = project_state([*existing_events, *new_events], base_state=base_sess)

    if projected.pending_confirmation:
        stripped = effective_message.strip()
        if any(k in stripped for k in ("对", "是的", "确认", "没错", "好")):
            before_confirm = projected.model_copy(deep=True)
            resolved = resolve_pending_confirmation(projected, confirmed=True)
            PreferenceEngine.sync_from_needs(resolved, turn_index=new_turn)
            confirm_events = diff_to_events(
                before_confirm, resolved, turn_id=new_turn, source="confirm_slot"
            )
            new_events.extend(confirm_events)
            projected = project_state([*existing_events, *new_events], base_state=base_sess)
        elif any(k in stripped for k in ("不对", "不是", "不用", "取消")):
            before_confirm = projected.model_copy(deep=True)
            resolved = resolve_pending_confirmation(projected, confirmed=False)
            confirm_events = diff_to_events(
                before_confirm, resolved, turn_id=new_turn, source="reject_slot"
            )
            new_events.extend(confirm_events)
            projected = project_state([*existing_events, *new_events], base_state=base_sess)

    return {
        "messages": [new_msg],
        "events": new_events,
        "base_session_state": base_sess,
        "safe_message": effective_message,
        "session_state": projected,
        "conversation_text": conversation_text,
        "tool_iterations": 0,
        "retrieval_retries": 0,
        "retrieval_query_override": None,
        "retrieval_relaxed_constraints": None,
        "retrieval_grade_passed": True,
        "retrieval_grade_reason": "",
        "evidence_anchors": [],
        "audit_retries": 0,
        "audit_passed": True,
        "critic_feedback": None,
        "artifact_bundle_version": bundle_ver,
        "step_count": 1,
        "budget_exhausted": False,
        "degrade_reason": "",
        "next_best_action": "",
        "hitl_triggered": False,
        "hitl_decision": None,
        "injection_detected": bool(turn_hook_ctx.injection_detected),
        "policy_veto_log": [],
        "last_extraction_confidence": None,
        "last_ambiguous_fields": [],
        "execution_trace": ["guard_and_route"],
    }


def route_after_guard(
    state: AgentGraphState,
) -> Literal["extract_slots", "arbitrate_stage"]:
    if state.get("skip_extraction"):
        return "arbitrate_stage"
    return "extract_slots"


def node_extract_slots(agent: Any, state: AgentGraphState) -> Dict[str, Any]:
    existing_events = list(state.get("events") or [])
    base_sess = state.get("base_session_state")
    before_sess = project_current_state(state)
    sess = before_sess.model_copy(deep=True)
    conversation_text = state.get("conversation_text", "")

    stage = sess.stage
    ext_model = agent.extraction_chat_model

    ext_confidence = None
    ext_ambiguous: List[str] = []

    with node_cost_context(sess.session_id, AgentNodeRole.EXTRACTOR):
        try:
            if agent.use_unified_extraction:
                from src.agent.extractors.unified_extractor import extract_unified_slots

                sess, tool_data = extract_unified_slots(ext_model, conversation_text, sess)
                ext_confidence = float(getattr(tool_data, "extraction_confidence", 1.0))
                ext_ambiguous = list(getattr(tool_data, "ambiguous_fields", None) or [])
            else:
                signal_text = state.get("safe_message") or state.get("user_message", "")
                has_profile_signal = stage in (Stage.WELCOME, Stage.PROFILE_ANALYSIS) or bool(
                    re.search(
                        r"我叫|我是|姓|先生|女士|本人|自己开|家人|老婆|老公|太太|爱人|小孩|孩子|老人|口之|代步|通勤|岁|居住|住在|工程师|<CN_PERSON",
                        signal_text,
                    )
                )
                has_needs_signal = stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION) or bool(
                    re.search(
                        r"\d+万|预算|价格|纯电|插混|增程|油车|混动|ev|suv|轿车|mpv|猎装|轿跑|续航|加速|马力|空间|座椅|\d座",
                        signal_text,
                        re.IGNORECASE,
                    )
                )
                has_reservation_signal = stage in (
                    Stage.RESERVATION_4S,
                    Stage.RESERVATION_CONFIRMATION,
                ) or bool(
                    re.search(
                        r"试驾|预约|门店|4s店|体验店|体验中心|明天|后天|周末|周[一二三四五六日天]|\d{1,2}\s*[点:：]|上午|下午|1[3-9]\d{9}|<CN_PHONE",
                        signal_text,
                        re.IGNORECASE,
                    )
                )
                if has_profile_signal:
                    sess.profile = extract_profile(ext_model, conversation_text, sess.profile)
                if has_needs_signal:
                    sess.needs = extract_combined_needs(
                        ext_model, conversation_text, sess.profile, sess.needs
                    )
                if has_reservation_signal:
                    sess.reservation = extract_reservation(
                        ext_model, conversation_text, sess.reservation
                    )
        except Exception as exc:
            logger.warning(f"[{sess.session_id}] Schema extraction failed, capturing to DLQ: {exc}")
            enqueue_agent_dlq(
                task_type="extractor",
                session_id=sess.session_id,
                checkpoint_id=sess.session_id,
                trace_id=sess.trace_id,
                user_message=state.get("safe_message") or state.get("user_message", ""),
                stage=sess.stage.value,
                error_message=str(exc),
                error_category="schema_extraction_failure",
                context_snapshot={"conversation_tail": conversation_text[-400:]},
            )

    last_user_msg = state.get("safe_message") or state.get("user_message", "")
    PreferenceEngine.parse_user_message_into_preferences(
        last_user_msg, sess, turn_index=sess.turn_count
    )
    if sess.matched_cars:
        sess.matched_cars = PreferenceEngine.filter_excluded_vehicles(
            sess.matched_cars, sess.preferences
        )

    new_events = diff_to_events(before_sess, sess, turn_id=sess.turn_count, source="extractor")

    projected = project_state([*existing_events, *new_events], base_state=base_sess)
    trace = [*list(state.get("execution_trace") or []), "extract_slots"]
    return {
        "events": new_events,
        "session_state": projected,
        "_state_snapshot_index": len(existing_events) + len(new_events),
        "conversation_text": conversation_text,
        "last_extraction_confidence": ext_confidence,
        "last_ambiguous_fields": ext_ambiguous,
        "step_count": int(state.get("step_count", 0)) + 1,
        "execution_trace": trace,
    }


def node_arbitrate_stage(agent: Any, state: AgentGraphState) -> Dict[str, Any]:
    existing_events = list(state.get("events") or [])
    base_sess = state.get("base_session_state")
    sess = project_current_state(state)
    session_id = sess.session_id
    last_user_msg = state.get("safe_message") or state.get("user_message", "")
    old_stage = sess.stage
    turn_id = int(getattr(sess, "turn_count", 0))

    from src.agent.turn_classifier import classify_turn_intent

    before_goals = list(sess.interrupted_goals)
    turn_cls = classify_turn_intent(
        agent.extraction_chat_model,
        last_user_msg,
        old_stage,
        sess,
        semantic_decision=state.get("semantic_route"),
    )
    is_topic_hopping = False
    extra_events: List[AnyDialogueEvent] = []

    if turn_cls.is_interrupt:
        if not turn_cls.is_constraint_change and turn_cls.should_push_goal and turn_cls.topic_label:
            TopicManager.push_goal(sess, old_stage, turn_cls.topic_label)
            if turn_cls.intent != "multi_intent":
                is_topic_hopping = True

    if list(sess.interrupted_goals) != before_goals:
        extra_events.append(
            SlotUpdated(
                turn_id=turn_id,
                source="topic_manager",
                field_path="interrupted_goals",
                value=list(sess.interrupted_goals),
            )
        )

    if turn_cls.is_interrupt:
        try:
            car_hint = (
                sess.matched_cars[0].get("car_model")
                if sess.matched_cars and isinstance(sess.matched_cars[0], dict)
                else None
            )
            t0_hit = TieredRetrievalEngine.get_instance().search_tier0(
                last_user_msg, car_model_hint=car_hint
            )
            if t0_hit is not None and t0_hit.results:
                fact_note = f"[技术与规格事实依据] {t0_hit.facts_summary}"
                if fact_note not in sess.system_notes:
                    extra_events.append(
                        SystemNoteAdded(turn_id=turn_id, source="tier0_lookup", note=fact_note)
                    )
        except Exception as te:
            logger.debug(f"Tier 0 lookup failed in arbitrate_stage: {te}")

    if turn_cls.suggested_directive and turn_cls.suggested_directive not in sess.system_notes:
        extra_events.append(
            SystemNoteAdded(
                turn_id=turn_id, source="turn_classifier", note=turn_cls.suggested_directive
            )
        )

    ext_conf = state.get("last_extraction_confidence")
    ambig_fields = list(state.get("last_ambiguous_fields") or [])
    cand_slot = ambig_fields[0] if ambig_fields else None
    cand_val = None
    if cand_slot and "." in cand_slot:
        target_obj: Any = sess
        for part in cand_slot.split("."):
            target_obj = getattr(target_obj, part, None) if target_obj is not None else None
        cand_val = target_obj

    p3_active_loop = evaluate_active_loop_policy(
        sess,
        turn_cls,
        last_user_msg,
        slot_confidence=ext_conf,
        candidate_slot=cand_slot,
        candidate_value=cand_val,
        turn_id=turn_id,
    )
    p2_fsm_rule = evaluate_stage_fsm_rule_policy(
        sess,
        turn_cls,
        turn_id=turn_id,
    )
    proposed_raw = state.get("proposed_stage")
    proposed_stage = (
        proposed_raw
        if isinstance(proposed_raw, Stage)
        else (Stage(proposed_raw) if isinstance(proposed_raw, str) and proposed_raw else None)
    )
    p1_llm_planner = evaluate_llm_planner_policy(
        sess,
        proposed_stage=proposed_stage,
        reason=str(state.get("proposed_stage_reason") or ""),
        turn_id=turn_id,
    )

    preliminary_rej_reason = (
        p2_fsm_rule.reason if p2_fsm_rule.action == PolicyAction.BLOCK else None
    )
    preliminary_stage = p3_active_loop.target_stage or p2_fsm_rule.target_stage or old_stage
    trip = agent.circuit_breaker.record_turn(
        session_id=session_id,
        current_stage=preliminary_stage,
        rejection_reason=preliminary_rej_reason,
        is_topic_hopping=is_topic_hopping or (p2_fsm_rule.action == PolicyAction.SIDE_QA_ALLOW),
    )
    if trip:
        extra_events.append(
            SystemNoteAdded(turn_id=turn_id, source="circuit_breaker", note=trip.intervention_note)
        )
        enqueue_agent_dlq(
            task_type="circuit_breaker",
            session_id=session_id,
            checkpoint_id=session_id,
            trace_id=sess.trace_id,
            user_message=last_user_msg,
            stage=preliminary_stage.value,
            error_message=trip.intervention_note,
            error_category="circuit_breaker_trip",
            context_snapshot={"reason": str(getattr(trip, "reason", ""))},
        )
        agent_slo_monitor.record_turn(circuit_breaker_tripped=True)

    p4_guardrail = evaluate_guardrail_policy(
        sess,
        last_user_msg,
        injection_detected=bool(state.get("injection_detected", False)),
        circuit_breaker_trip=trip,
        turn_id=turn_id,
    )

    arb_res = arbitrate_policies(
        [p4_guardrail, p3_active_loop, p2_fsm_rule, p1_llm_planner],
        current_stage=old_stage,
    )

    all_new_events = [*extra_events, *arb_res.events]
    projected = project_state([*existing_events, *all_new_events], base_state=base_sess)
    projected.previous_stage = old_stage.value

    trace = [*list(state.get("execution_trace") or []), "arbitrate_stage"]
    return {
        "events": all_new_events,
        "session_state": projected,
        "stage_changed": arb_res.stage_changed,
        "topic_intent": turn_cls.intent,
        "hitl_triggered": arb_res.hitl_triggered,
        "hitl_decision": arb_res.hitl_decision,
        "policy_veto_log": arb_res.veto_log,
        "step_count": int(state.get("step_count", 0)) + 1,
        "execution_trace": trace,
    }


def route_after_arbitrate(
    state: AgentGraphState,
) -> Literal["hitl_handoff", "retrieve_vehicles", "run_plugins_and_subdag"]:
    """Route to HITL handoff if triggered, else retrieve vehicles or run plugins."""
    if state.get("hitl_triggered"):
        return "hitl_handoff"
    if state.get("retrieved_cars"):
        return "retrieve_vehicles"
    if state.get("topic_intent") == UserDialogueIntent.SPEC_COMPARISON.value:
        return "retrieve_vehicles"
    sess = state.get("session_state")
    if sess is not None and sess.stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
        return "retrieve_vehicles"
    return "run_plugins_and_subdag"


def node_hitl_handoff(state: AgentGraphState) -> Dict[str, Any]:
    """First-class LangGraph interrupt() node for Human-in-the-Loop escalation & resumption."""
    sess = state["session_state"].model_copy(deep=True)
    dec_raw = state.get("hitl_decision") or {}
    reason_str = dec_raw.get("reason") or HITLTriggerReason.HIGH_INTENT_CLOSING.value
    try:
        reason_enum = HITLTriggerReason(reason_str)
    except ValueError:
        reason_enum = HITLTriggerReason.HIGH_INTENT_CLOSING
    decision = HITLDecision(
        triggered=True,
        reason=reason_enum,
        severity=str(dec_raw.get("severity") or "medium"),
        detail=str(dec_raw.get("detail") or ""),
    )
    handoff_ctx = build_handoff_context(sess, decision)
    handoff_payload = handoff_ctx.model_dump()
    sess.handoff_context = handoff_payload

    record_compliance_audit(
        event_type="HITL_HANDOFF_INTERRUPT",
        session_id=sess.session_id,
        trace_id=sess.trace_id,
        checkpoint_id=sess.session_id,
        severity=decision.severity.upper(),
        details={
            "trigger_reason": handoff_ctx.trigger_reason,
            "core_blocker": handoff_ctx.core_blocker,
        },
    )

    resume_payload = interrupt(handoff_payload)

    resumed_sess = apply_human_resume(sess, resume_payload)
    hitl_events = diff_to_events(
        sess,
        resumed_sess,
        turn_id=int(getattr(sess, "turn_count", 0)),
        source="hitl_resume",
    )
    constraints_updated = bool(
        isinstance(resume_payload, dict) and resume_payload.get("updated_constraints")
    )
    trace = [*list(state.get("execution_trace") or []), "hitl_handoff"]
    return {
        "events": hitl_events,
        "session_state": resumed_sess,
        "hitl_triggered": False,
        "hitl_decision": {"constraints_updated": constraints_updated},
        "step_count": int(state.get("step_count", 0)) + 1,
        "execution_trace": trace,
    }


def route_after_hitl(
    state: AgentGraphState,
) -> Literal["retrieve_vehicles", "run_plugins_and_subdag"]:
    dec = state.get("hitl_decision") or {}
    sess = state.get("session_state")
    if (
        dec.get("constraints_updated")
        and sess is not None
        and sess.stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION)
    ):
        return "retrieve_vehicles"
    return "run_plugins_and_subdag"
