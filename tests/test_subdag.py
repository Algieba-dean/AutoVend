"""
Tests for Sub-DAG Workflow Engine and Stage Sub-DAGs (CAR_SELECTION & RESERVATION_4S).

Verifies:
1. Top-level sales FSM compliance is retained.
2. Sub-DAG topology execution (nodes, condition branching, handles, API calls).
3. Stage.CAR_SELECTION multi-car spec comparison Sub-DAG.
4. Stage.RESERVATION_4S qualification preliminary check & dealer inventory Sub-DAG.
5. Integration with SessionState & SalesAgent turn execution.
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
from src.agent.stages import STAGE_TRANSITIONS, can_transition
from src.agent.subdag import (
    APINode,
    BaseSubDAGNode,
    ConditionNode,
    DecisionNode,
    EndNode,
    StartNode,
    SubDAGContext,
    SubDAGExecutor,
    SubDAGGraph,
    create_car_selection_dag,
    create_reservation_4s_dag,
    get_stage_subdag,
    run_stage_subdag,
)


class TestTopLevelFSMCompliance:
    """Ensure top-level Sales FSM remains unchanged and compliant."""

    def test_fsm_stage_transitions_structure(self):
        assert Stage.CAR_SELECTION in STAGE_TRANSITIONS[Stage.NEEDS_ANALYSIS]
        assert Stage.RESERVATION_4S in STAGE_TRANSITIONS[Stage.CAR_SELECTION]
        assert Stage.RESERVATION_CONFIRMATION in STAGE_TRANSITIONS[Stage.RESERVATION_4S]

    def test_can_transition_compliance(self):
        assert can_transition(Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION)
        assert can_transition(Stage.CAR_SELECTION, Stage.RESERVATION_4S)
        assert not can_transition(Stage.WELCOME, Stage.RESERVATION_4S)  # Illegal skip


class TestSubDAGGraphAndContext:
    """Test SubDAGGraph topology sorting and SubDAGContext variable resolution."""

    def test_context_variable_resolution(self):
        state = SessionState(
            session_id="s123",
            stage=Stage.CAR_SELECTION,
            profile=UserProfile(name="李雷", phone_number="13900001111"),
            matched_cars=[{"model_name": "AutoVend Model 7", "brand": "AutoVend"}],
        )
        ctx = SubDAGContext(session_state=state, user_message="想了解更多")

        assert ctx.get_variable("profile.name") == "李雷"
        assert ctx.get_variable("matched_cars[0].model_name") == "AutoVend Model 7"
        assert ctx.resolve_template("客户: {{profile.name}}, 意向: {{matched_cars[0].model_name}}") == "客户: 李雷, 意向: AutoVend Model 7"

    def test_dag_topo_sort(self):
        nodes = [
            {"id": "n1", "type": "start"},
            {"id": "n2", "type": "api"},
            {"id": "n3", "type": "end"},
        ]
        edges = [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
        ]
        graph = SubDAGGraph(nodes, edges)
        topo = graph.get_topo_sort()
        assert topo == ["n1", "n2", "n3"]


class TestCarSelectionSubDAG:
    """Test CAR_SELECTION stage multi-car contrast Sub-DAG."""

    def test_car_selection_subdag_execution(self):
        state = SessionState(
            session_id="cs1",
            stage=Stage.CAR_SELECTION,
            matched_cars=[
                {"model_name": "AutoVend EV7", "price_range": "30-35万", "powertrain": "纯电"},
                {"model_name": "AutoVend Hybrid9", "price_range": "35-40万", "powertrain": "插混"},
            ],
        )

        updated = run_stage_subdag(state, user_message="对比一下这两款车")

        # Verify Sub-DAG completed and recorded in subdag_state
        assert "car_selection_confirmation" in updated.subdag_state
        subdag_res = updated.subdag_state["car_selection_confirmation"]
        assert subdag_res["completed"] is True
        assert "fetch_specs" in subdag_res["outputs"]

        # Verify API returned specs
        specs = subdag_res["outputs"]["fetch_specs"]["body"]["specs"]
        assert len(specs) == 2
        assert specs[0]["model_name"] == "AutoVend EV7"

        # Verify multi-car contrast system note was injected
        notes_str = " ".join(updated.system_notes)
        assert "多车对比分析" in notes_str


class TestReservation4SSubDAG:
    """Test RESERVATION_4S stage qualification preliminary check & 4S stock Sub-DAG."""

    def test_reservation_4s_subdag_execution(self):
        state = SessionState(
            session_id="res1",
            stage=Stage.RESERVATION_4S,
            profile=UserProfile(name="王芳", phone_number="13811112222"),
            matched_cars=[{"model_name": "AutoVend EV7"}],
            reservation=ReservationInfo(test_driver="王芳"),
        )

        updated = run_stage_subdag(state, user_message="我想预约本周末试驾")

        # Verify Sub-DAG completed
        assert "reservation4s" in updated.subdag_state
        subdag_res = updated.subdag_state["reservation4s"]
        assert subdag_res["completed"] is True

        # Verify qualification check API output
        qual = subdag_res["outputs"]["verify_qualification"]["body"]
        assert qual["eligible"] is True

        # Verify 4S stock check API output
        stock = subdag_res["outputs"]["check_dealer_stock"]["body"]
        assert stock["in_stock"] is True
        assert stock["dealer_name"] == "AutoVend Flagship 4S Experience Center"

        # Verify 4S location pre-filled into reservation info
        assert updated.reservation.reservation_location == "AutoVend 旗舰 4S 体验中心"
        assert updated.reservation.salesman == "高级销售顾问 Alex"

        # Verify system note injected
        notes_str = " ".join(updated.system_notes)
        assert "4S资质初审与库存查询" in notes_str
