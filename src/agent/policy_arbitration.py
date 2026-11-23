"""
Priority-Layered Policy Arbitration Engine (`src/agent/policy_arbitration.py`).

Replaces ad-hoc stage arbitration in `_node_arbitrate_stage` with a unified
`PolicyProposal` protocol and strict priority veto (`arbitrate_policies`):
- P4 (highest): `GuardrailPolicy` — safety / prompt injection / prohibited financial
  promise / circuit breaker / human handoff.
- P3: `ActiveLoopPolicy` — deterministic form validation & prompting, Two-Stage
  Fallback, or 1-turn side-QA allowance with automatic recovery hook.
- P2: `StageFSMRulePolicy` — hard business FSM preconditions (e.g. needs & matched
  cars before `RESERVATION_4S`, phone & date/time/store before confirmation,
  graph edge & evidence ledger checks).
- P1 (lowest): `LLMPlannerPolicy` — free planning within the deterministic cage.
"""

from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field

from src.agent.active_loop import (
    build_slot_prompt,
    ensure_active_loop_for_stage,
    evaluate_two_stage_fallback,
    next_missing_slot,
    validate_slot_value,
)
from src.agent.events import (
    ActiveLoopUpdated,
    AnyDialogueEvent,
    PendingConfirmationUpdated,
    SlotUpdated,
    StageTransitioned,
    SystemNoteAdded,
    TurnReverted,
)
from src.agent.hitl import HITLDecision, evaluate_hitl_trigger
from src.agent.schemas import SessionState, Stage
from src.agent.stages import (
    ProposalSource,
    TransitionProposal,
    advance,
    advance_adaptive,
    arbitrate,
    propose_forward,
    propose_rollback,
    should_advance_to_car_selection,
    should_advance_to_confirmation,
)
from src.agent.turn_classifier import TurnIntentClassification


class PolicyPriority(IntEnum):
    """Strict priority tiers: higher number always vetoes lower number."""

    LLM_PLANNER = 1       # P1 (lowest)
    STAGE_FSM_RULE = 2    # P2
    ACTIVE_LOOP = 3       # P3
    GUARDRAIL = 4         # P4 (highest)


class PolicyAction(str, Enum):
    """Canonical actions emitted by a PolicyProposal."""

    ALLOW = "allow"                  # Non-blocking pass-through
    BLOCK = "block"                  # Hard veto / reject transition
    TRANSITION = "transition"        # Move to `target_stage`
    ROLLBACK = "rollback"            # Lossless rollback to earlier turn / stage
    HOLD = "hold"                    # Hold current stage for this turn
    PROMPT_SLOT = "prompt_slot"      # Deterministic slot prompt in active form
    SIDE_QA_ALLOW = "side_qa_allow"  # Allow 1-turn side QA with recovery hook
    CONFIRM_SLOT = "confirm_slot"    # Stage-1 fallback: ask confirmation
    FALLBACK_OPTIONS = "fallback_options"  # Stage-2 fallback: structured enum options
    HITL_HANDOFF = "hitl_handoff"    # Escalate to LangGraph interrupt() HITL


class PolicyProposal(BaseModel):
    """Unified proposal emitted by each policy layer for deterministic arbitration."""

    policy_name: str
    priority: int = Field(ge=1, le=4)
    action: PolicyAction
    target_stage: Optional[Stage] = None
    reason: str = ""
    events: List[AnyDialogueEvent] = Field(default_factory=list)
    system_notes: List[str] = Field(default_factory=list)
    hitl_decision: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyArbitrationResult(BaseModel):
    """Outcome of `arbitrate_policies(proposals)`."""

    winning_proposal: PolicyProposal
    rejected_proposals: List[PolicyProposal] = Field(default_factory=list)
    final_stage: Stage
    stage_changed: bool = False
    events: List[AnyDialogueEvent] = Field(default_factory=list)
    system_notes: List[str] = Field(default_factory=list)
    hitl_triggered: bool = False
    hitl_decision: Optional[Dict[str, Any]] = None
    veto_log: List[str] = Field(default_factory=list)


def arbitrate_policies(
    proposals: Sequence[PolicyProposal],
    current_stage: Stage,
) -> PolicyArbitrationResult:
    """
    Pure priority-layered arbiter with strict priority veto (P4 > P3 > P2 > P1).

    - `PolicyAction.ALLOW` is non-decisive (acts as "no objection from this tier").
    - Among decisive proposals (non-`ALLOW`), the highest `priority` wins and vetoes
      all lower-priority decisive proposals.
    - If all proposals are `ALLOW`, the highest-priority `ALLOW` wins and stage holds.
    """
    if not proposals:
        noop = PolicyProposal(
            policy_name="DefaultNoOp",
            priority=PolicyPriority.LLM_PLANNER,
            action=PolicyAction.HOLD,
            target_stage=current_stage,
            reason="no_proposals",
        )
        return PolicyArbitrationResult(
            winning_proposal=noop,
            final_stage=current_stage,
            stage_changed=False,
        )

    indexed = list(enumerate(proposals))
    # Sort by priority descending, preserving original order for equal priorities
    sorted_pairs = sorted(indexed, key=lambda pair: (-int(pair[1].priority), pair[0]))
    ordered = [p for _, p in sorted_pairs]

    decisive = [p for p in ordered if p.action != PolicyAction.ALLOW]
    winner = decisive[0] if decisive else ordered[0]
    rejected = [p for p in ordered if p is not winner and p.action != PolicyAction.ALLOW]

    veto_log: List[str] = []
    for rej in rejected:
        veto_log.append(
            f"[P{winner.priority}:{winner.policy_name}({winner.action.value})] "
            f"vetoed [P{rej.priority}:{rej.policy_name}({rej.action.value})]"
            + (f" — {winner.reason}" if winner.reason else "")
        )

    final_stage = current_stage
    if winner.action in (PolicyAction.TRANSITION, PolicyAction.ROLLBACK) and winner.target_stage is not None:
        final_stage = winner.target_stage
    elif winner.target_stage is not None and winner.action in (PolicyAction.HOLD, PolicyAction.BLOCK):
        final_stage = winner.target_stage

    stage_changed = final_stage != current_stage
    hitl_triggered = winner.action == PolicyAction.HITL_HANDOFF

    # Collect events and notes from winner (plus non-conflicting ALLOW notes if any)
    events: List[AnyDialogueEvent] = list(winner.events)
    notes: List[str] = list(winner.system_notes)
    for p in ordered:
        if p is not winner and p.action == PolicyAction.ALLOW:
            for ev in p.events:
                events.append(ev)
            for n in p.system_notes:
                if n not in notes:
                    notes.append(n)

    return PolicyArbitrationResult(
        winning_proposal=winner,
        rejected_proposals=rejected,
        final_stage=final_stage,
        stage_changed=stage_changed,
        events=events,
        system_notes=notes,
        hitl_triggered=hitl_triggered,
        hitl_decision=winner.hitl_decision,
        veto_log=veto_log,
    )


# ── P4: GuardrailPolicy ───────────────────────────────────────────────

_FINANCIAL_PROMISE_RE_WORDS = (
    "零首付包批",
    "100%免息",
    "保底回购",
    "保值回购承诺",
    "绝对最低价",
    "违约我赔",
)


def evaluate_guardrail_policy(
    sess: SessionState,
    user_message: str,
    *,
    injection_detected: bool = False,
    compliance_flagged: bool = False,
    circuit_breaker_trip: Optional[Any] = None,
    hitl_dec: Optional[HITLDecision] = None,
    turn_id: int = 0,
) -> PolicyProposal:
    """P4 (highest): Safety, prompt injection, prohibited financial promise, circuit breaker, HITL."""
    msg = (user_message or "").strip()

    if injection_detected:
        note = "[安全护栏拦截] 检测到潜在提示词注入或越权指令，已阻断越权状态变更并保持当前阶段。"
        return PolicyProposal(
            policy_name="GuardrailPolicy",
            priority=PolicyPriority.GUARDRAIL,
            action=PolicyAction.BLOCK,
            target_stage=sess.stage,
            reason="prompt_injection_detected",
            events=[SystemNoteAdded(turn_id=turn_id, source="GuardrailPolicy", note=note)],
            system_notes=[note],
        )

    if any(kw in msg for kw in _FINANCIAL_PROMISE_RE_WORDS):
        note = "[合规护栏拦截] 禁止对金融贴息、保值回购或绝对底价作出未经授权的承诺，请以门店官方金融方案为准。"
        return PolicyProposal(
            policy_name="GuardrailPolicy",
            priority=PolicyPriority.GUARDRAIL,
            action=PolicyAction.BLOCK,
            target_stage=sess.stage,
            reason="prohibited_financial_promise",
            events=[SystemNoteAdded(turn_id=turn_id, source="GuardrailPolicy", note=note)],
            system_notes=[note],
        )

    dec = hitl_dec or evaluate_hitl_trigger(sess, msg, compliance_flagged=compliance_flagged)
    if dec.triggered:
        return PolicyProposal(
            policy_name="GuardrailPolicy",
            priority=PolicyPriority.GUARDRAIL,
            action=PolicyAction.HITL_HANDOFF,
            target_stage=sess.stage,
            reason=dec.reason.value if dec.reason else "hitl_triggered",
            hitl_decision={
                "reason": dec.reason.value if dec.reason else "",
                "severity": dec.severity,
                "detail": dec.detail,
            },
            system_notes=[f"[HITL人工接管] {dec.detail}"] if dec.detail else [],
        )

    if circuit_breaker_trip is not None:
        note = getattr(circuit_breaker_trip, "intervention_note", "[熔断器触发] 保持当前阶段并引导澄清。")
        return PolicyProposal(
            policy_name="GuardrailPolicy",
            priority=PolicyPriority.GUARDRAIL,
            action=PolicyAction.HOLD,
            target_stage=sess.stage,
            reason=str(getattr(circuit_breaker_trip, "reason", "circuit_breaker_trip")),
            events=[SystemNoteAdded(turn_id=turn_id, source="GuardrailPolicy", note=note)],
            system_notes=[note],
        )

    return PolicyProposal(
        policy_name="GuardrailPolicy",
        priority=PolicyPriority.GUARDRAIL,
        action=PolicyAction.ALLOW,
        reason="guardrail_clear",
    )


# ── P3: ActiveLoopPolicy ──────────────────────────────────────────────


def evaluate_active_loop_policy(
    sess: SessionState,
    turn_cls: TurnIntentClassification,
    user_message: str,
    *,
    slot_confidence: Optional[float] = None,
    candidate_slot: Optional[str] = None,
    candidate_value: Any = None,
    turn_id: int = 0,
) -> PolicyProposal:
    """
    P3: Deterministic Active Form Loop policy.

    Handles:
    1. Side-QA interruption (`is_interrupted=True`) -> 1-turn side-QA allowance with recovery hook.
    2. Recovery after side-QA -> deterministic `next_missing_slot()` prompt.
    3. Deterministic Python validation (phone format, business hours) -> retry count & error prompt.
    4. Two-Stage Fallback (`0.4 <= conf < 0.8` -> `pending_confirmation`; `<0.4` or `>=2` failures -> options/HITL).
    """
    loop = ensure_active_loop_for_stage(sess)
    if loop is None:
        return PolicyProposal(
            policy_name="ActiveLoopPolicy",
            priority=PolicyPriority.ACTIVE_LOOP,
            action=PolicyAction.ALLOW,
            reason="no_active_loop",
        )

    # 1. Side-QA interruption during an active form
    if turn_cls.is_interrupt and not turn_cls.is_constraint_change:
        loop.is_interrupted = True
        missing = next_missing_slot(sess, loop)
        recovery_hint = build_slot_prompt(missing) if missing else ""
        note = (
            "[ActiveLoop 侧问允许] 请先基于检索事实准确回答客户当前疑问；"
            + (f"回答完毕后顺带引导回表单：{recovery_hint}" if recovery_hint else "")
        )
        return PolicyProposal(
            policy_name="ActiveLoopPolicy",
            priority=PolicyPriority.ACTIVE_LOOP,
            action=PolicyAction.SIDE_QA_ALLOW,
            target_stage=sess.stage,
            reason="side_qa_interruption_with_recovery_hook",
            events=[
                ActiveLoopUpdated(turn_id=turn_id, source="ActiveLoopPolicy", active_loop=loop.model_dump()),
                SystemNoteAdded(turn_id=turn_id, source="ActiveLoopPolicy", note=note),
            ],
            system_notes=[note],
            metadata={"missing_slot": missing or "", "recovery_prompt": recovery_hint},
        )

    # 2. Deterministic slot validation on already-filled slots in the active loop
    for slot_path in loop.required_slots:
        val = None
        target: Any = sess
        for part in slot_path.split("."):
            target = getattr(target, part, None) if target is not None else None
        val = target
        if val is not None and str(val).strip() != "":
            ok, err_msg = validate_slot_value(slot_path, val)
            if not ok:
                loop.retry_counts[slot_path] = int(loop.retry_counts.get(slot_path, 0)) + 1
                fb = evaluate_two_stage_fallback(slot_path, val, 0.2, loop)
                if fb.trigger_hitl:
                    return PolicyProposal(
                        policy_name="ActiveLoopPolicy",
                        priority=PolicyPriority.ACTIVE_LOOP,
                        action=PolicyAction.HITL_HANDOFF,
                        target_stage=sess.stage,
                        reason=f"slot_validation_exhausted:{slot_path}",
                        events=[
                            ActiveLoopUpdated(turn_id=turn_id, source="ActiveLoopPolicy", active_loop=loop.model_dump()),
                        ],
                        hitl_decision={
                            "reason": "active_loop_validation_exhausted",
                            "severity": "medium",
                            "detail": err_msg or fb.directive,
                        },
                        system_notes=[fb.directive],
                    )
                note = f"[表单校验失败] {err_msg} {fb.directive}".strip()
                return PolicyProposal(
                    policy_name="ActiveLoopPolicy",
                    priority=PolicyPriority.ACTIVE_LOOP,
                    action=PolicyAction.FALLBACK_OPTIONS if loop.retry_counts[slot_path] >= 2 else PolicyAction.PROMPT_SLOT,
                    target_stage=sess.stage,
                    reason=f"invalid_slot:{slot_path}",
                    events=[
                        # Clear invalid slot value deterministically
                        SlotUpdated(turn_id=turn_id, source="ActiveLoopPolicy", field_path=slot_path, value=""),
                        ActiveLoopUpdated(turn_id=turn_id, source="ActiveLoopPolicy", active_loop=loop.model_dump()),
                        SystemNoteAdded(turn_id=turn_id, source="ActiveLoopPolicy", note=note),
                    ],
                    system_notes=[note],
                    metadata={"options": fb.structured_options, "invalid_slot": slot_path},
                )

    # 3. Two-Stage Fallback for low-confidence candidate slot
    if candidate_slot and slot_confidence is not None and slot_confidence < 0.8:
        fb = evaluate_two_stage_fallback(candidate_slot, candidate_value, slot_confidence, loop)
        if fb.trigger_hitl:
            return PolicyProposal(
                policy_name="ActiveLoopPolicy",
                priority=PolicyPriority.ACTIVE_LOOP,
                action=PolicyAction.HITL_HANDOFF,
                target_stage=sess.stage,
                reason=f"low_confidence_hitl:{candidate_slot}",
                hitl_decision={
                    "reason": "active_loop_low_confidence",
                    "severity": "medium",
                    "detail": fb.directive,
                },
                system_notes=[fb.directive],
            )
        if fb.stage == 1:
            loop.pending_confirmation = dict(fb.pending_confirmation)
            return PolicyProposal(
                policy_name="ActiveLoopPolicy",
                priority=PolicyPriority.ACTIVE_LOOP,
                action=PolicyAction.CONFIRM_SLOT,
                target_stage=sess.stage,
                reason=f"two_stage_fallback_confirm:{candidate_slot}",
                events=[
                    ActiveLoopUpdated(turn_id=turn_id, source="ActiveLoopPolicy", active_loop=loop.model_dump()),
                    PendingConfirmationUpdated(
                        turn_id=turn_id,
                        source="ActiveLoopPolicy",
                        pending_confirmation=fb.pending_confirmation,
                    ),
                    SystemNoteAdded(turn_id=turn_id, source="ActiveLoopPolicy", note=fb.directive),
                ],
                system_notes=[fb.directive],
            )
        if fb.stage == 2:
            loop.retry_counts[candidate_slot] = int(loop.retry_counts.get(candidate_slot, 0)) + 1
            return PolicyProposal(
                policy_name="ActiveLoopPolicy",
                priority=PolicyPriority.ACTIVE_LOOP,
                action=PolicyAction.FALLBACK_OPTIONS,
                target_stage=sess.stage,
                reason=f"two_stage_fallback_options:{candidate_slot}",
                events=[
                    ActiveLoopUpdated(turn_id=turn_id, source="ActiveLoopPolicy", active_loop=loop.model_dump()),
                    SystemNoteAdded(turn_id=turn_id, source="ActiveLoopPolicy", note=fb.directive),
                ],
                system_notes=[fb.directive],
                metadata={"options": fb.structured_options},
            )

    # 4. Recovery after side-QA interruption -> deterministic next_missing_slot() prompt
    if loop.is_interrupted:
        loop.is_interrupted = False
        missing = next_missing_slot(sess, loop)
        if missing:
            prompt = build_slot_prompt(missing, retry_count=int(loop.retry_counts.get(missing, 0)))
            loop.last_prompted_slot = missing
            note = f"[ActiveLoop 打断恢复] 请继续引导客户补全当前缺失槽位（{missing}）：{prompt}"
            return PolicyProposal(
                policy_name="ActiveLoopPolicy",
                priority=PolicyPriority.ACTIVE_LOOP,
                action=PolicyAction.PROMPT_SLOT,
                target_stage=sess.stage,
                reason=f"recover_missing_slot:{missing}",
                events=[
                    ActiveLoopUpdated(turn_id=turn_id, source="ActiveLoopPolicy", active_loop=loop.model_dump()),
                    SystemNoteAdded(turn_id=turn_id, source="ActiveLoopPolicy", note=note),
                ],
                system_notes=[note],
                metadata={"missing_slot": missing, "prompt": prompt},
            )

    # Form complete or no interruption -> allow P2 StageFSMRulePolicy to advance
    return PolicyProposal(
        policy_name="ActiveLoopPolicy",
        priority=PolicyPriority.ACTIVE_LOOP,
        action=PolicyAction.ALLOW,
        reason="active_loop_satisfied_or_ready",
    )


# ── P2: StageFSMRulePolicy ────────────────────────────────────────────


def evaluate_stage_fsm_rule_policy(
    sess: SessionState,
    turn_cls: TurnIntentClassification,
    *,
    has_multi_slots: bool = False,
    turn_id: int = 0,
) -> PolicyProposal:
    """
    P2: Hard business FSM preconditions & lossless rollback rules.

    Enforces:
    - `stage_hold` -> HOLD for 1 turn
    - `constraint_update` -> ROLLBACK with `TurnReverted` event
    - Forward `STAGE_TRANSITIONS` + `TRANSITION_GUARDS` + `VerificationEvidenceLedger`
    """
    old_stage = sess.stage

    if sess.stage_hold:
        return PolicyProposal(
            policy_name="StageFSMRulePolicy",
            priority=PolicyPriority.STAGE_FSM_RULE,
            action=PolicyAction.HOLD,
            target_stage=old_stage,
            reason="stage_hold_active",
            events=[SlotUpdated(turn_id=turn_id, source="StageFSMRulePolicy", field_path="stage_hold", value=False)],
        )

    if turn_cls.is_interrupt and not turn_cls.is_constraint_change and not turn_cls.is_multi_intent:
        return PolicyProposal(
            policy_name="StageFSMRulePolicy",
            priority=PolicyPriority.STAGE_FSM_RULE,
            action=PolicyAction.SIDE_QA_ALLOW,
            target_stage=old_stage,
            reason="side_qa_stage_anchor",
        )

    if turn_cls.is_interrupt and turn_cls.is_constraint_change:
        rb_prop = propose_rollback(sess, reason="turn_classifier_constraint_update")
        if rb_prop is not None:
            verdict = arbitrate(sess, rb_prop)
            if verdict.accepted:
                target_turn = max(1, turn_id - 1) if turn_id > 1 else 1
                notes = [verdict.system_note] if verdict.system_note else []
                return PolicyProposal(
                    policy_name="StageFSMRulePolicy",
                    priority=PolicyPriority.STAGE_FSM_RULE,
                    action=PolicyAction.ROLLBACK,
                    target_stage=verdict.stage,
                    reason="constraint_change_rollback",
                    events=[
                        TurnReverted(
                            turn_id=turn_id,
                            source="StageFSMRulePolicy",
                            target_turn_id=target_turn,
                            reason="constraint_change_rollback",
                        ),
                        StageTransitioned(
                            turn_id=turn_id,
                            source="StageFSMRulePolicy",
                            from_stage=old_stage,
                            to_stage=verdict.stage,
                            reason="constraint_change_rollback",
                            policy_name="StageFSMRulePolicy",
                        ),
                        *(
                            [SystemNoteAdded(turn_id=turn_id, source="StageFSMRulePolicy", note=verdict.system_note)]
                            if verdict.system_note
                            else []
                        ),
                    ],
                    system_notes=notes,
                )

    forward = propose_forward(sess)
    proposals = [forward] if forward is not None else []
    auto_multi = has_multi_slots or (
        turn_cls.is_multi_intent
        or len(turn_cls.extracted_slots_hint) >= 2
        or (len(sess.last_patch) >= 2 and any("needs.explicit" in k for k in sess.last_patch))
        or (
            sess.stage in (Stage.WELCOME, Stage.PROFILE_ANALYSIS)
            and bool(sess.needs.explicit.price)
            and should_advance_to_car_selection(sess.needs)
        )
        or (
            sess.stage in (Stage.CAR_SELECTION, Stage.RESERVATION_4S)
            and should_advance_to_confirmation(sess.reservation)
        )
    )
    verdict = advance_adaptive(sess, proposals) if auto_multi else advance(sess, proposals)

    if verdict.accepted and verdict.stage != old_stage:
        notes = [verdict.system_note] if verdict.system_note else []
        return PolicyProposal(
            policy_name="StageFSMRulePolicy",
            priority=PolicyPriority.STAGE_FSM_RULE,
            action=PolicyAction.TRANSITION,
            target_stage=verdict.stage,
            reason=verdict.proposal.reason or "fsm_guard_passed",
            events=[
                StageTransitioned(
                    turn_id=turn_id,
                    source="StageFSMRulePolicy",
                    from_stage=old_stage,
                    to_stage=verdict.stage,
                    reason=verdict.proposal.reason or "fsm_guard_passed",
                    policy_name="StageFSMRulePolicy",
                ),
                *(
                    [SystemNoteAdded(turn_id=turn_id, source="StageFSMRulePolicy", note=n) for n in notes]
                ),
            ],
            system_notes=notes,
        )

    if not verdict.accepted and verdict.rejection:
        notes = [verdict.system_note] if verdict.system_note else []
        return PolicyProposal(
            policy_name="StageFSMRulePolicy",
            priority=PolicyPriority.STAGE_FSM_RULE,
            action=PolicyAction.BLOCK,
            target_stage=old_stage,
            reason=verdict.rejection,
            events=[
                SystemNoteAdded(turn_id=turn_id, source="StageFSMRulePolicy", note=n) for n in notes
            ],
            system_notes=notes,
        )

    return PolicyProposal(
        policy_name="StageFSMRulePolicy",
        priority=PolicyPriority.STAGE_FSM_RULE,
        action=PolicyAction.ALLOW,
        reason="no_fsm_transition",
    )


# ── P1: LLMPlannerPolicy ──────────────────────────────────────────────


def evaluate_llm_planner_policy(
    sess: SessionState,
    proposed_stage: Optional[Stage] = None,
    reason: str = "",
    *,
    turn_id: int = 0,
) -> PolicyProposal:
    """
    P1 (lowest): Free LLM planning within the deterministic cage.
    Can only suggest transitions; any conflict with P2/P3/P4 is vetoed.
    """
    if proposed_stage is not None and proposed_stage != sess.stage:
        verdict = arbitrate(
            sess,
            TransitionProposal(target=proposed_stage, source=ProposalSource.LLM, reason=reason),
        )
        if verdict.accepted:
            return PolicyProposal(
                policy_name="LLMPlannerPolicy",
                priority=PolicyPriority.LLM_PLANNER,
                action=PolicyAction.TRANSITION,
                target_stage=verdict.stage,
                reason=reason or "llm_proposed_transition",
                events=[
                    StageTransitioned(
                        turn_id=turn_id,
                        source="LLMPlannerPolicy",
                        from_stage=sess.stage,
                        to_stage=verdict.stage,
                        reason=reason or "llm_proposed_transition",
                        policy_name="LLMPlannerPolicy",
                    )
                ],
            )
        return PolicyProposal(
            policy_name="LLMPlannerPolicy",
            priority=PolicyPriority.LLM_PLANNER,
            action=PolicyAction.BLOCK,
            target_stage=sess.stage,
            reason=verdict.rejection,
            system_notes=[verdict.system_note] if verdict.system_note else [],
        )

    return PolicyProposal(
        policy_name="LLMPlannerPolicy",
        priority=PolicyPriority.LLM_PLANNER,
        action=PolicyAction.ALLOW,
        reason="llm_planner_stay",
    )
