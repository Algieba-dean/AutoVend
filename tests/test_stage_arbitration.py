"""
Tests for stage arbitration: graph enforcement, guards, and rollback.

The property under test is that **no path** through the code can move the
conversation along an edge the graph does not declare, or past a guard that
refuses. Before this module existed the graph was decorative — `can_transition`
was called only from tests while the runtime used an if-else chain — so these
assert the enforcement, not just the data.
"""

import pytest

from src.agent.schemas import (
    ExplicitNeeds,
    ReservationInfo,
    SessionState,
    Stage,
    UserProfile,
    VehicleNeeds,
)
from src.agent.stages import (
    ROLLBACK_TARGET,
    STAGE_TRANSITIONS,
    ProposalSource,
    TransitionProposal,
    advance,
    arbitrate,
    can_transition,
    clear_stage_outputs,
    handle_constraint_change,
    is_rollback,
    propose_forward,
    propose_rollback,
)


def _state(stage=Stage.WELCOME, **kwargs):
    return SessionState(session_id="s", stage=stage, **kwargs)


def _full_profile():
    return UserProfile(name="张伟", age="35", family_size="3")


def _full_needs(prize="30,000 ~ 40,000"):
    return VehicleNeeds(explicit=ExplicitNeeds(prize=prize, vehicle_category_bottom="Mid-Size SUV"))


def _full_reservation():
    return ReservationInfo(
        test_driver="张伟",
        reservation_date="2026-08-01",
        reservation_time="14:00",
        reservation_location="上海徐汇店",
        reservation_phone_number="13800000000",
    )


class TestGraphIntegrity:
    def test_every_edge_targets_a_known_stage(self):
        for source, targets in STAGE_TRANSITIONS.items():
            assert isinstance(source, Stage)
            for target in targets:
                assert isinstance(target, Stage)

    def test_farewell_is_terminal(self):
        assert STAGE_TRANSITIONS[Stage.FAREWELL] == set()

    def test_every_stage_except_the_first_is_reachable(self):
        reachable = {t for targets in STAGE_TRANSITIONS.values() for t in targets}
        for stage in Stage:
            if stage is Stage.WELCOME:
                continue
            assert stage in reachable, f"{stage.value} is unreachable"

    def test_rollback_edges_exist_where_the_flow_needs_them(self):
        """A customer revising needs after seeing cars must not have to restart."""
        assert can_transition(Stage.CAR_SELECTION, Stage.NEEDS_ANALYSIS)
        assert can_transition(Stage.RESERVATION_4S, Stage.CAR_SELECTION)
        assert can_transition(Stage.RESERVATION_CONFIRMATION, Stage.RESERVATION_4S)

    def test_is_rollback_distinguishes_direction(self):
        assert is_rollback(Stage.CAR_SELECTION, Stage.NEEDS_ANALYSIS)
        assert not is_rollback(Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION)


class TestGraphEnforcement:
    def test_illegal_edge_is_refused(self):
        """The case the old if-else chain could not express at all."""
        state = _state(Stage.WELCOME, profile=_full_profile())

        verdict = arbitrate(state, TransitionProposal(target=Stage.FAREWELL))

        assert not verdict.accepted
        assert verdict.stage is Stage.WELCOME
        assert "不存在" in verdict.rejection

    def test_illegal_edge_names_the_legal_ones(self):
        verdict = arbitrate(_state(Stage.WELCOME), TransitionProposal(target=Stage.CAR_SELECTION))

        assert "profile_analysis" in verdict.rejection

    def test_refusal_produces_a_note_for_the_generator(self):
        """A blocked transition must not stall the conversation silently."""
        verdict = arbitrate(_state(Stage.WELCOME), TransitionProposal(target=Stage.FAREWELL))

        assert verdict.system_note
        assert verdict.system_note.startswith("[系统]")

    def test_proposing_the_current_stage_is_a_no_op(self):
        verdict = arbitrate(
            _state(Stage.NEEDS_ANALYSIS), TransitionProposal(target=Stage.NEEDS_ANALYSIS)
        )

        assert not verdict.accepted
        assert not verdict.rejection


class TestGuards:
    def test_budget_guard_blocks_recommendation(self):
        """
        The guard the propose-and-decide split exists for: two need fields but
        no price range. The model would happily call this done.
        """
        needs = VehicleNeeds(
            explicit=ExplicitNeeds(brand="Tesla", powertrain_type="Battery Electric Vehicle")
        )
        state = _state(Stage.NEEDS_ANALYSIS, profile=_full_profile(), needs=needs)

        verdict = arbitrate(state, TransitionProposal(target=Stage.CAR_SELECTION))

        assert not verdict.accepted
        assert "预算" in verdict.rejection
        assert "预算" in verdict.system_note

    def test_budget_guard_allows_once_the_price_is_known(self):
        state = _state(Stage.NEEDS_ANALYSIS, profile=_full_profile(), needs=_full_needs())

        assert arbitrate(state, TransitionProposal(target=Stage.CAR_SELECTION)).accepted

    def test_budget_alone_is_not_enough(self):
        needs = VehicleNeeds(explicit=ExplicitNeeds(prize="30,000 ~ 40,000"))
        state = _state(Stage.NEEDS_ANALYSIS, profile=_full_profile(), needs=needs)

        verdict = arbitrate(state, TransitionProposal(target=Stage.CAR_SELECTION))

        assert not verdict.accepted
        assert "需求信息不足" in verdict.rejection

    def test_profile_guard_blocks_empty_profile(self):
        verdict = arbitrate(
            _state(Stage.PROFILE_ANALYSIS), TransitionProposal(target=Stage.NEEDS_ANALYSIS)
        )

        assert not verdict.accepted
        assert "画像" in verdict.rejection

    def test_reservation_guard_requires_a_matched_car(self):
        state = _state(Stage.CAR_SELECTION, matched_cars=[])

        verdict = arbitrate(state, TransitionProposal(target=Stage.RESERVATION_4S))

        assert not verdict.accepted
        assert "车型" in verdict.rejection

    def test_confirmation_guard_names_the_missing_slots(self):
        state = _state(
            Stage.RESERVATION_4S,
            reservation=ReservationInfo(reservation_date="2026-08-01"),
        )

        verdict = arbitrate(state, TransitionProposal(target=Stage.RESERVATION_CONFIRMATION))

        assert not verdict.accepted
        assert "时间" in verdict.rejection and "门店" in verdict.rejection
        assert "日期" not in verdict.rejection, "already provided, should not be listed"

    def test_rollback_edges_carry_no_guard(self):
        """
        A rollback exists precisely to escape a stage whose forward guard
        cannot be satisfied; guarding it too would trap the conversation.
        """
        state = _state(Stage.CAR_SELECTION, matched_cars=[{"car_model": "BMW-X3"}])

        assert arbitrate(state, TransitionProposal(target=Stage.NEEDS_ANALYSIS)).accepted


class TestAdvance:
    def test_defaults_to_the_rule_proposer(self):
        state = _state(Stage.WELCOME)

        verdict = advance(state)

        assert verdict.accepted
        assert verdict.stage is Stage.PROFILE_ANALYSIS
        assert verdict.proposal.source is ProposalSource.RULE

    def test_first_accepted_proposal_wins(self):
        state = _state(Stage.NEEDS_ANALYSIS, profile=_full_profile(), needs=_full_needs())
        proposals = [
            TransitionProposal(target=Stage.FAREWELL, source=ProposalSource.LLM),  # illegal
            TransitionProposal(target=Stage.CAR_SELECTION, source=ProposalSource.RULE),
        ]

        verdict = advance(state, proposals)

        assert verdict.accepted
        assert verdict.proposal.source is ProposalSource.RULE

    def test_last_rejection_surfaces_when_none_pass(self):
        needs = VehicleNeeds(explicit=ExplicitNeeds(brand="Tesla", powertrain_type="BEV"))
        state = _state(Stage.NEEDS_ANALYSIS, profile=_full_profile(), needs=needs)

        verdict = advance(state)

        assert not verdict.accepted
        assert verdict.stage is Stage.NEEDS_ANALYSIS
        assert "预算" in verdict.rejection

    def test_terminal_stage_produces_no_proposal(self):
        verdict = advance(_state(Stage.FAREWELL, reservation=_full_reservation()))

        assert not verdict.accepted
        assert verdict.stage is Stage.FAREWELL

    def test_propose_forward_returns_none_at_the_end(self):
        assert propose_forward(_state(Stage.FAREWELL)) is None


class TestRollback:
    def test_clears_what_the_abandoned_stage_produced(self):
        """
        Without this the rollback is cosmetic: the conversation says it is
        re-examining requirements while still holding the recommendations the
        superseded requirements produced.
        """
        state = _state(Stage.CAR_SELECTION, matched_cars=[{"car_model": "BMW-X3"}])

        cleared = clear_stage_outputs(state, Stage.CAR_SELECTION)

        assert cleared == ["matched_cars"]
        assert state.matched_cars == []

    def test_clearing_is_idempotent_when_nothing_was_produced(self):
        state = _state(Stage.CAR_SELECTION, matched_cars=[])

        assert clear_stage_outputs(state, Stage.CAR_SELECTION) == []

    def test_constraint_change_rolls_back_and_clears(self):
        state = _state(
            Stage.CAR_SELECTION,
            profile=_full_profile(),
            needs=_full_needs(),
            matched_cars=[{"car_model": "BMW-X3"}],
        )

        outcome = handle_constraint_change(state, reason="user changed budget")

        assert outcome is not None and outcome.rolled_back
        assert state.stage is Stage.NEEDS_ANALYSIS
        assert state.previous_stage == Stage.CAR_SELECTION.value
        assert outcome.cleared_fields == ["matched_cars"]
        assert state.matched_cars == []

    def test_rollback_note_tells_the_model_not_to_restart(self):
        state = _state(Stage.CAR_SELECTION, matched_cars=[{"car_model": "X"}])

        outcome = handle_constraint_change(state)

        assert "回退" in outcome.verdict.system_note
        assert "不要从头开始" in outcome.verdict.system_note

    def test_reservation_rollback_clears_the_booking(self):
        state = _state(
            Stage.RESERVATION_CONFIRMATION,
            reservation=_full_reservation(),
            matched_cars=[{"car_model": "X"}],
        )

        outcome = handle_constraint_change(state)

        assert outcome.rolled_back
        assert state.stage is Stage.RESERVATION_4S
        assert not any(state.reservation.model_dump().values())

    @pytest.mark.parametrize("stage", [Stage.WELCOME, Stage.PROFILE_ANALYSIS, Stage.NEEDS_ANALYSIS])
    def test_no_rollback_target_early_in_the_flow(self, stage):
        """Revising requirements while still gathering them needs no rollback."""
        assert propose_rollback(_state(stage)) is None
        assert handle_constraint_change(_state(stage)) is None

    def test_every_rollback_target_is_a_legal_edge(self):
        for source, target in ROLLBACK_TARGET.items():
            assert can_transition(source, target), f"{source.value} -> {target.value} not in graph"
            assert is_rollback(source, target)


class TestStageHold:
    """
    A rollback must survive the same turn that caused it.

    "我想改一下预算" announces a change without stating the new value, so the
    superseded budget is still in state and the forward guard still passes.
    Without the hold the FSM steps back to needs analysis and returns to
    recommendations in the same turn, re-running retrieval against exactly the
    constraints the customer just disowned.
    """

    def test_rollback_sets_the_hold(self):
        state = _state(Stage.CAR_SELECTION, needs=_full_needs(), matched_cars=[{"car_model": "X"}])

        handle_constraint_change(state)

        assert state.stage_hold is True
        assert state.stage is Stage.NEEDS_ANALYSIS

    def test_forward_guard_would_otherwise_allow_the_return(self):
        """Proves the hold is load-bearing, not defensive."""
        state = _state(Stage.NEEDS_ANALYSIS, profile=_full_profile(), needs=_full_needs())

        assert arbitrate(state, TransitionProposal(target=Stage.CAR_SELECTION)).accepted

    def test_no_hold_when_there_was_no_rollback(self):
        assert _state(Stage.CAR_SELECTION).stage_hold is False
