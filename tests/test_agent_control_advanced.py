"""
Tests for Advanced Agent Deterministic Control & Reconciliation (Pillar 2).
Verifies:
1. Anti-loop circuit breaker (stage dwell timeout, guard rejection deadlock, oscillation inhibition).
2. Evidence-ledger stage transition validation.
3. Hard vs soft slot constraint reconciliation and proactive trade-off matrix generation.
4. Transactional rollback with savepoints and error recovery hints.
"""

from src.agent.circuit_breaker import AgentCircuitBreaker
from src.agent.evidence_ledger import VerificationEvidenceLedger
from src.agent.reconciliation import reconcile_constraints
from src.agent.schemas import ReservationInfo, SessionState, Stage
from src.agent.stages import ProposalSource, TransitionProposal, arbitrate
from src.agent.tools import dispatch_all


class TestAgentCircuitBreaker:
    def test_rejection_loop_budget_deadlock(self):
        cb = AgentCircuitBreaker(max_rejections=2)
        sid = "sess_cb_budget"

        # Turn 1: Budget missing
        trip1 = cb.record_turn(sid, Stage.NEEDS_ANALYSIS, rejection_reason="缺少预算信息：客户尚未说明价格区间")
        assert trip1 is None

        # Turn 2: Budget missing again -> circuit breaker trips!
        trip2 = cb.record_turn(sid, Stage.NEEDS_ANALYSIS, rejection_reason="缺少预算信息：客户尚未说明价格区间")
        assert trip2 is not None
        assert trip2.trip_type == "REJECTION_LOOP"
        assert "断路器干预 - 预算死锁解除" in trip2.intervention_note
        assert "阶梯选项" in trip2.intervention_note

    def test_stage_oscillation_inhibition(self):
        cb = AgentCircuitBreaker()
        sid = "sess_osc"

        cb.record_turn(sid, Stage.NEEDS_ANALYSIS)
        cb.record_turn(sid, Stage.CAR_SELECTION)
        cb.record_turn(sid, Stage.NEEDS_ANALYSIS)
        trip = cb.record_turn(sid, Stage.CAR_SELECTION)

        assert trip is not None
        assert trip.trip_type == "OSCILLATION_LOOP"
        assert "阶段振荡抑制" in trip.intervention_note

    def test_stage_dwell_timeout(self):
        cb = AgentCircuitBreaker(max_dwell=4)
        sid = "sess_dwell"

        for _ in range(3):
            assert cb.record_turn(sid, Stage.NEEDS_ANALYSIS) is None

        trip = cb.record_turn(sid, Stage.NEEDS_ANALYSIS)
        assert trip is not None
        assert trip.trip_type == "DWELL_LOOP"
        assert "需求分析停留超时" in trip.intervention_note


class TestEvidenceLedgerStageGovernance:
    def test_evidence_ledger_validates_budget(self):
        ledger = VerificationEvidenceLedger()
        assert ledger.verify_budget("25万以内") is True
        assert ledger.verify_budget("300000元") is True
        assert ledger.verify_budget("随便") is False

    def test_evidence_ledger_blocks_car_selection_without_budget(self):
        state = SessionState(stage=Stage.NEEDS_ANALYSIS)
        state.needs.explicit.brand = "比亚迪"
        # Budget is empty

        prop = TransitionProposal(target=Stage.CAR_SELECTION, source=ProposalSource.RULE)
        verdict = arbitrate(state, prop)
        assert verdict.accepted is False
        assert "缺少预算" in verdict.rejection or "BUDGET_VERIFIED" in verdict.rejection

    def test_evidence_ledger_blocks_confirmation_without_verified_store(self):
        ledger = VerificationEvidenceLedger()
        state = SessionState(stage=Stage.RESERVATION_4S)
        # Reservation without store
        state.reservation = ReservationInfo(
            reservation_date="2026-10-20",
            reservation_time="14:00",
            reservation_location="",
        )

        allowed, missing = ledger.validate_stage_transition(Stage.RESERVATION_4S, Stage.RESERVATION_CONFIRMATION, state)
        assert allowed is False
        assert any("STORE_VERIFIED" in m for m in missing)


class TestAdvancedConstraintReconciliation:
    def test_hard_vs_soft_conflict_classification(self):
        # Hard conflict: Budget vs Luxury brand
        state_hard = SessionState()
        state_hard.needs.explicit.prize = "15万"
        state_hard.needs.explicit.brand = "保时捷"

        conflicts_hard = reconcile_constraints(state_hard)
        assert len(conflicts_hard) >= 1
        assert conflicts_hard[0].severity == "HARD"
        assert len(conflicts_hard[0].trade_off_options) >= 2
        assert "HARD级别" in conflicts_hard[0].to_system_note()

        # Hard conflict: Budget vs LiDAR/NOA
        state_tech = SessionState()
        state_tech.needs.explicit.prize = "12万"
        state_tech.needs.explicit.design_style = "激光雷达 城市NOA高阶智驾"
        conflicts_tech = reconcile_constraints(state_tech)
        assert any(c.conflict_type == "BUDGET_VS_TECH" and c.severity == "HARD" for c in conflicts_tech)

        # Soft conflict: Pure EV in extreme cold
        state_soft = SessionState()
        state_soft.needs.explicit.powertrain_type = "纯电动"
        state_soft.profile.residence = "哈尔滨 极寒东北地区"
        conflicts_soft = reconcile_constraints(state_soft)
        assert any(c.conflict_type == "POWERTRAIN_VS_USAGE" and c.severity == "SOFT" for c in conflicts_soft)


class TestTransactionalSavepointRollback:
    def test_savepoint_rollback_reverts_only_post_savepoint_patches(self):
        state = SessionState(session_id="tx_sp_session", stage=Stage.PROFILE_ANALYSIS)
        calls = [
            # 1. Successfully record user profile
            {"tool": "record_profile", "args": {"fields": {"name": "张经理", "phone_number": "13800138000"}}},
            # 2. Establish savepoint "sp_profile"
            {"tool": "savepoint", "args": {"name": "sp_profile"}},
            # 3. Modify age
            {"tool": "record_profile", "args": {"fields": {"age": "40"}}},
            # 4. Attempt illegal tool with savepoint rollback request
            {
                "tool": "select_vehicle",
                "args": {"car_model": "Tesla Model Y"},
                "rollback_to_savepoint": "sp_profile",
            },
        ]

        results = dispatch_all(state, calls, atomic=True)
        assert len(results) == 4
        # Failed step
        assert results[3].ok is False
        assert results[3].rolled_back is True
        assert "回滚至保存点 'sp_profile'" in results[3].message
        assert results[3].recovery_hint != ""

        # Pre-savepoint profile persists!
        assert state.profile.name == "张经理"
        assert state.profile.phone_number == "13800138000"
        # Post-savepoint modification was rolled back!
        assert state.profile.age == ""
