"""
Stage machine: a directed graph with arbitration, guards and rollback.

The conversation is not steered by an if-else chain or by asking the model
nicely in a system prompt. It is a directed graph whose edges are declared in
`STAGE_TRANSITIONS`, and **every** stage change is arbitrated against that
graph before it takes effect.

That is a deliberate correction. The graph existed before this module was
rewritten, but nothing consulted it: `determine_next_stage` was a chain of ifs
and `can_transition` was called only from tests. The graph asserted a shape the
runtime did not enforce.

## Propose and decide

Stage changes arrive as *proposals*, never as decisions:

- `RULE` — the slot-filling heuristics below. Cheap, deterministic, the default.
- `LLM` — the model may emit `transition_to(stage=...)` when it judges the
  current step complete (see `transition_proposer.py`).
- `INTERRUPT` — the user contradicted an earlier constraint, so the dialog
  manager proposes a rollback.

Python arbitrates. A proposal is accepted only if the edge exists in the graph
*and* the guard on that edge passes. Nothing the model can emit will move the
conversation to a stage the graph does not allow — the model proposes, the
process decides.

## Guards

Each edge may carry a guard: a hardcoded business check that inspects state and
returns a rejection reason, or None to allow. A rejected proposal does not
silently stall; it produces a `system_note` that is injected into the next
generation prompt, so the model is told *why* it may not advance and what to
ask for instead.

## Rollback

Backward edges are first-class members of the graph (CAR_SELECTION ->
NEEDS_ANALYSIS, RESERVATION_CONFIRMATION -> RESERVATION_4S). When the user
revises a constraint mid-flow, the interrupt path walks one of those edges,
clears the state the abandoned stage had produced, and injects a note so the
reply acknowledges the change rather than restarting cold.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Set, Tuple

from src.agent.schemas import (
    ReservationInfo,
    SessionState,
    Stage,
    UserProfile,
    VehicleNeeds,
)

logger = logging.getLogger(__name__)

# ── The graph ─────────────────────────────────────────────────────────

#: Valid stage transitions: current stage -> allowed next stages.
#: Backward edges are intentional: a customer who revises their needs after
#: seeing recommendations must be able to go back, not be told to start over.
STAGE_TRANSITIONS: Dict[Stage, Set[Stage]] = {
    Stage.WELCOME: {Stage.PROFILE_ANALYSIS},
    Stage.PROFILE_ANALYSIS: {Stage.NEEDS_ANALYSIS},
    Stage.NEEDS_ANALYSIS: {Stage.CAR_SELECTION, Stage.PROFILE_ANALYSIS},
    Stage.CAR_SELECTION: {Stage.RESERVATION_4S, Stage.NEEDS_ANALYSIS},
    Stage.RESERVATION_4S: {Stage.RESERVATION_CONFIRMATION, Stage.CAR_SELECTION},
    Stage.RESERVATION_CONFIRMATION: {Stage.FAREWELL, Stage.RESERVATION_4S},
    Stage.FAREWELL: set(),
}

#: Ordered list of all stages, used to tell forward edges from rollbacks.
STAGE_ORDER: List[Stage] = [
    Stage.WELCOME,
    Stage.PROFILE_ANALYSIS,
    Stage.NEEDS_ANALYSIS,
    Stage.CAR_SELECTION,
    Stage.RESERVATION_4S,
    Stage.RESERVATION_CONFIRMATION,
    Stage.FAREWELL,
]

_STAGE_INDEX: Dict[Stage, int] = {stage: i for i, stage in enumerate(STAGE_ORDER)}


def can_transition(current: Stage, target: Stage) -> bool:
    """Whether an edge from `current` to `target` exists in the graph."""
    return target in STAGE_TRANSITIONS.get(current, set())


def is_rollback(current: Stage, target: Stage) -> bool:
    """Whether the edge walks backwards through the SOP."""
    return _STAGE_INDEX.get(target, 0) < _STAGE_INDEX.get(current, 0)


# ── Proposals and verdicts ────────────────────────────────────────────


class ProposalSource(str, Enum):
    """Who asked for the transition. Recorded so rejections are attributable."""

    RULE = "rule"
    LLM = "llm"
    INTERRUPT = "interrupt"


@dataclass(frozen=True)
class TransitionProposal:
    """A request to change stage. Not a decision."""

    target: Stage
    source: ProposalSource = ProposalSource.RULE
    reason: str = ""


@dataclass(frozen=True)
class TransitionVerdict:
    """The arbiter's answer."""

    accepted: bool
    stage: Stage
    proposal: TransitionProposal
    rejection: str = ""
    system_note: str = ""

    @property
    def changed(self) -> bool:
        return self.accepted and self.stage != self.proposal.target or self.accepted

    def as_dict(self) -> Dict:
        return {
            "accepted": self.accepted,
            "stage": self.stage.value,
            "target": self.proposal.target.value,
            "source": self.proposal.source.value,
            "rejection": self.rejection,
        }


# ── Guards ────────────────────────────────────────────────────────────

#: A guard inspects state and returns a rejection reason, or None to allow.
Guard = Callable[[SessionState], Optional[str]]


def _guard_needs_profile(state: SessionState) -> Optional[str]:
    """Do not discuss requirements before knowing who is buying."""
    if not should_advance_to_needs(state.profile):
        return (
            "用户画像为空：尚未获得姓名、年龄、家庭结构或用车人中的任何一项。"
            "请继续了解客户基本情况，不要进入需求分析。"
        )
    return None


def _guard_needs_budget(state: SessionState) -> Optional[str]:
    """
    The recommendation stage is meaningless without a budget.

    This is the guard the whole propose-and-decide split exists for: a model
    that has had a pleasant conversation will happily declare the requirements
    complete without ever having asked the price range.
    """
    explicit = state.needs.explicit
    if not explicit.prize:
        return "缺少预算信息：客户尚未说明价格区间。请拒绝进入推荐阶段，先向客户询问预算范围。"
    if not should_advance_to_car_selection(state.needs):
        return (
            "需求信息不足：除预算外至少还需要一项明确需求"
            "（车型类别 / 品牌 / 动力形式 / 座位布局等）。请继续澄清。"
        )
    return None


def _guard_reservation_needs_car(state: SessionState) -> Optional[str]:
    if not should_advance_to_reservation(state.matched_cars):
        return "尚无匹配车型：请先完成车型推荐并让客户确认意向车型，再安排试驾。"
    return None


def _guard_confirmation_needs_slots(state: SessionState) -> Optional[str]:
    reservation = state.reservation
    missing = [
        label
        for label, value in (
            ("日期", reservation.reservation_date),
            ("时间", reservation.reservation_time),
            ("门店", reservation.reservation_location),
        )
        if not value
    ]
    if missing:
        return f"预约信息不完整，缺少：{'、'.join(missing)}。请补齐后再进入确认环节。"
    return None


def _guard_farewell_needs_full_reservation(state: SessionState) -> Optional[str]:
    if not should_advance_to_farewell(state.reservation):
        return "预约尚未完全确认（需要试驾人、日期、时间、门店、联系电话）。请补齐后再结束对话。"
    return None


#: Guards keyed by edge. Edges without a guard are allowed whenever the graph
#: permits them — rollbacks in particular, since the point of a rollback is to
#: escape a state whose forward guard cannot yet be satisfied.
TRANSITION_GUARDS: Dict[Tuple[Stage, Stage], Guard] = {
    (Stage.PROFILE_ANALYSIS, Stage.NEEDS_ANALYSIS): _guard_needs_profile,
    (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION): _guard_needs_budget,
    (Stage.CAR_SELECTION, Stage.RESERVATION_4S): _guard_reservation_needs_car,
    (Stage.RESERVATION_4S, Stage.RESERVATION_CONFIRMATION): _guard_confirmation_needs_slots,
    (Stage.RESERVATION_CONFIRMATION, Stage.FAREWELL): _guard_farewell_needs_full_reservation,
}


# ── Arbitration ───────────────────────────────────────────────────────


def arbitrate(state: SessionState, proposal: TransitionProposal) -> TransitionVerdict:
    """
    Decide whether a proposed transition may take effect.

    Two checks, in order: the edge must exist in the graph, and its guard must
    pass. A rejection carries a `system_note` written for the model, not for a
    log — it is injected into the next generation prompt so the reply asks for
    what is missing instead of stalling silently.
    """
    current = state.stage
    target = proposal.target

    if target == current:
        return TransitionVerdict(accepted=False, stage=current, proposal=proposal)

    if not can_transition(current, target):
        legal = sorted(s.value for s in STAGE_TRANSITIONS.get(current, set())) or "无"
        rejection = f"图中不存在 {current.value} → {target.value} 的边（合法目标：{legal}）"
        logger.warning(f"Transition rejected [{proposal.source.value}]: {rejection}")
        return TransitionVerdict(
            accepted=False,
            stage=current,
            proposal=proposal,
            rejection=rejection,
            system_note=(
                f"[系统] 当前阶段（{current.value}）不允许跳转到 {target.value}，"
                "请继续完成当前阶段的任务。"
            ),
        )

    guard = TRANSITION_GUARDS.get((current, target))
    if guard is not None:
        rejection = guard(state)
        if rejection:
            logger.info(f"Transition blocked by guard [{proposal.source.value}]: {rejection}")
            return TransitionVerdict(
                accepted=False,
                stage=current,
                proposal=proposal,
                rejection=rejection,
                system_note=f"[系统] {rejection}",
            )

    note = ""
    if is_rollback(current, target):
        note = (
            f"[系统] 客户修改了先前的需求，对话已从 {current.value} 回退到 "
            f"{target.value}。请自然地承接这个变化，不要从头开始，"
            "直接就改动的部分继续沟通。"
        )
        logger.info(f"Rollback accepted: {current.value} → {target.value}")
    else:
        logger.info(
            f"Transition accepted [{proposal.source.value}]: {current.value} → {target.value}"
        )

    return TransitionVerdict(accepted=True, stage=target, proposal=proposal, system_note=note)


# ── Rule-based proposer (the default) ─────────────────────────────────


def should_advance_to_needs(profile: UserProfile) -> bool:
    """Enough profile collected to move on. Any identifying field will do."""
    return any([profile.name, profile.age, profile.target_driver, profile.family_size])


def should_advance_to_car_selection(needs: VehicleNeeds) -> bool:
    """At least two explicit need fields filled."""
    explicit = needs.explicit
    filled_count = sum(
        1
        for v in [
            explicit.prize,
            explicit.brand,
            explicit.powertrain_type,
            explicit.vehicle_category_bottom,
            explicit.design_style,
            explicit.seat_layout,
        ]
        if v
    )
    return filled_count >= 2


def should_advance_to_reservation(matched_cars: list) -> bool:
    """At least one car matched."""
    return len(matched_cars) > 0


def should_advance_to_confirmation(reservation: ReservationInfo) -> bool:
    """Date, time and location present."""
    return all(
        [
            reservation.reservation_date,
            reservation.reservation_time,
            reservation.reservation_location,
        ]
    )


def should_advance_to_farewell(reservation: ReservationInfo) -> bool:
    """Every reservation field present."""
    return all(
        [
            reservation.test_driver,
            reservation.reservation_date,
            reservation.reservation_time,
            reservation.reservation_location,
            reservation.reservation_phone_number,
        ]
    )


#: The single forward target for each stage. Rule-based proposals only ever
#: move forward; going back is the interrupt path's job, because only the
#: dialog manager knows the user contradicted themselves.
_FORWARD_TARGET: Dict[Stage, Optional[Stage]] = {
    Stage.WELCOME: Stage.PROFILE_ANALYSIS,
    Stage.PROFILE_ANALYSIS: Stage.NEEDS_ANALYSIS,
    Stage.NEEDS_ANALYSIS: Stage.CAR_SELECTION,
    Stage.CAR_SELECTION: Stage.RESERVATION_4S,
    Stage.RESERVATION_4S: Stage.RESERVATION_CONFIRMATION,
    Stage.RESERVATION_CONFIRMATION: Stage.FAREWELL,
    Stage.FAREWELL: None,
}


def propose_forward(state: SessionState) -> Optional[TransitionProposal]:
    """The rule-based proposer: always suggest the next stage in the SOP."""
    target = _FORWARD_TARGET.get(state.stage)
    if target is None:
        return None
    return TransitionProposal(
        target=target, source=ProposalSource.RULE, reason="slot-filling heuristics"
    )


def advance(
    state: SessionState,
    proposals: Optional[List[TransitionProposal]] = None,
) -> TransitionVerdict:
    """
    Run one arbitration round.

    Proposals are tried in order and the first accepted one wins; the rejection
    of the last one is what surfaces if none pass, so the note the model sees
    describes the transition it most recently wanted.

    Defaults to the rule-based forward proposal, which is what the FSM did
    before proposals existed.
    """
    candidates = proposals if proposals is not None else []
    if not candidates:
        forward = propose_forward(state)
        candidates = [forward] if forward else []

    if not candidates:
        return TransitionVerdict(
            accepted=False,
            stage=state.stage,
            proposal=TransitionProposal(target=state.stage, source=ProposalSource.RULE),
        )

    verdict = None
    for proposal in candidates:
        verdict = arbitrate(state, proposal)
        if verdict.accepted:
            return verdict
    return verdict


def determine_next_stage(
    current_stage: Stage,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: list,
    reservation: ReservationInfo,
) -> Stage:
    """
    Backwards-compatible wrapper returning only the resulting stage.

    Prefer `advance()`, which also returns *why* a transition was refused —
    the rejection note is what stops a blocked conversation from stalling
    silently.
    """
    state = SessionState(
        stage=current_stage,
        profile=profile,
        needs=needs,
        matched_cars=matched_cars,
        reservation=reservation,
    )
    return advance(state).stage


# ── Interrupts ────────────────────────────────────────────────────────

#: Stage-local state each stage produces. On rollback the abandoned stage's
#: output is cleared, so the conversation genuinely redoes the step instead of
#: resuming with stale conclusions attached.
STAGE_OUTPUTS: Dict[Stage, Tuple[str, ...]] = {
    Stage.CAR_SELECTION: ("matched_cars",),
    Stage.RESERVATION_4S: ("reservation",),
    Stage.RESERVATION_CONFIRMATION: ("reservation",),
}

#: Where a constraint change sends the conversation back to, per stage.
ROLLBACK_TARGET: Dict[Stage, Stage] = {
    Stage.CAR_SELECTION: Stage.NEEDS_ANALYSIS,
    Stage.RESERVATION_4S: Stage.CAR_SELECTION,
    Stage.RESERVATION_CONFIRMATION: Stage.RESERVATION_4S,
}


def propose_rollback(state: SessionState, reason: str = "") -> Optional[TransitionProposal]:
    """
    Propose the rollback for a constraint change, or None if there is nowhere
    to go back to (the user revised needs while still in needs analysis).
    """
    target = ROLLBACK_TARGET.get(state.stage)
    if target is None:
        return None
    return TransitionProposal(
        target=target,
        source=ProposalSource.INTERRUPT,
        reason=reason or "user revised an earlier constraint",
    )


def clear_stage_outputs(state: SessionState, stage: Stage) -> List[str]:
    """
    Drop the state `stage` produced, in place. Returns the fields cleared.

    Without this a rollback is cosmetic: the conversation says it is
    re-examining requirements while still holding the recommendations and the
    booking that the superseded requirements produced.
    """
    cleared: List[str] = []
    for name in STAGE_OUTPUTS.get(stage, ()):
        current = getattr(state, name, None)
        if name == "matched_cars":
            if current:
                state.matched_cars = []
                cleared.append(name)
        elif name == "reservation":
            if current and any(current.model_dump().values()):
                state.reservation = ReservationInfo()
                cleared.append(name)
    return cleared


@dataclass
class InterruptOutcome:
    """Result of handling a constraint-change interrupt."""

    verdict: TransitionVerdict
    cleared_fields: List[str] = field(default_factory=list)

    @property
    def rolled_back(self) -> bool:
        return self.verdict.accepted


def handle_constraint_change(state: SessionState, reason: str = "") -> Optional[InterruptOutcome]:
    """
    Roll the conversation back after the user contradicted an earlier constraint.

    Mutates `state` on success: the stage moves back along a legal edge and the
    abandoned stage's output is cleared. Returns None when the current stage has
    no rollback target — the user revised requirements while still gathering
    them, which needs no state change.
    """
    proposal = propose_rollback(state, reason)
    if proposal is None:
        return None

    from_stage = state.stage
    verdict = arbitrate(state, proposal)
    if not verdict.accepted:
        return InterruptOutcome(verdict=verdict)

    cleared = clear_stage_outputs(state, from_stage)
    state.previous_stage = from_stage.value
    state.stage = verdict.stage
    # Hold the new stage for one turn. The customer announced a change without
    # yet stating the new value, so the superseded constraint is still in state
    # and the forward guard would wave the conversation straight back.
    state.stage_hold = True
    logger.info(
        f"Interrupt rollback {from_stage.value} → {verdict.stage.value}; "
        f"cleared {cleared or 'nothing'}"
    )
    return InterruptOutcome(verdict=verdict, cleared_fields=cleared)
