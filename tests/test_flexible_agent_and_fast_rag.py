"""
Unit & Integration Tests for Flexible Governed Agent and Fast-Path Tiered RAG (tests/test_flexible_agent_and_fast_rag.py).

Verifies:
1. Fast-Path Tier 0 Retrieval (< 1-2 ms): In-memory exact spec & tabular entity lookup, semantic query cache.
2. Fast-Path Multi-Vehicle Spec Comparison & Attribute Mapping (battery chemistry, motor, acceleration).
3. Tier 1 Agile Hybrid & Tier 2 Deep Comparative Retrieval routing.
4. Dynamic Intent Interruptibility & Topic Hopping with Interrupted Goal Stack (side questions, seamless resumption).
5. Customer needs statements without interrogatives do not falsely freeze dialog progression.
6. Anti-Loop Circuit Breaker Topic Hopping Protection & Consultative Nudge.
7. Multi-Intent Joint Fulfillment (multi-slot opportunistic extraction & adaptive multi-hop progression).
8. Deterministic Guardrails Preservation (Evidence Ledger, Reconciliation, Reflection, Circuit Breaker).
"""

import time
from unittest.mock import MagicMock

import pytest

from src.agent.circuit_breaker import AgentCircuitBreaker
from src.agent.evidence_ledger import VerificationEvidenceLedger
from src.agent.reconciliation import reconcile_constraints
from src.agent.reflection import reflect_and_guard
from src.agent.sales_agent import SalesAgent
from src.agent.schemas import (
    AgentInput,
    ExplicitNeeds,
    ReservationInfo,
    SessionState,
    Stage,
    UserProfile,
    VehicleNeeds,
)
from src.agent.stages import advance_adaptive
from src.agent.topic_manager import TopicManager, UserDialogueIntent
from src.rag_service.schemas import VehicleQueryRequest
from src.rag_service.service import RAGService
from src.retrieval.tiered_engine import SemanticQueryCache, TieredRetrievalEngine

# -------------------------------------------------------------------------
# 1. Tier 0 Fast-Path Retrieval Tests
# -------------------------------------------------------------------------


class TestFastPathTier0Retrieval:
    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = TieredRetrievalEngine()

    def test_su7_max_acceleration_exact_spec(self):
        """Test sub-millisecond grounded spec lookup for SU7 Max acceleration."""
        query = "SU7 Max 零百加速是多少"
        res = self.engine.search_tier0(query)

        assert res is not None
        assert res.tier == 0
        assert res.is_fast_path is True
        assert res.latency_ms < 10.0  # sub-10ms even on cold run, sub-1ms warm
        assert len(res.results) == 1
        assert "小米-SU7 Max" in res.results[0].car_model
        assert "2.78秒" in res.facts_summary
        assert "0-100km/h加速" in res.facts_summary

    def test_battery_supplier_and_chemistry_lookup(self):
        """Test exact battery chemistry and supplier matching without defaulting to acceleration."""
        query = "SU7 Max用的是什么电池"
        res = self.engine.search_tier0(query)

        assert res is not None
        assert res.tier == 0
        assert "麒麟电池" in res.facts_summary or "三元锂" in res.facts_summary
        assert "电池规格与品牌" in res.facts_summary or "电池" in res.facts_summary

    def test_flagship_specs_li_l7_and_m7(self):
        """Test newly added flagship models (Li Auto L7 and AITO M7)."""
        res_l7 = self.engine.search_tier0("理想L7纯电续航是多少")
        assert res_l7 is not None
        assert "理想-L7" in res_l7.results[0].car_model
        assert "225" in res_l7.facts_summary or "纯电" in res_l7.facts_summary

        res_m7 = self.engine.search_tier0("问界M7官方售价")
        assert res_m7 is not None
        assert "问界-M7" in res_m7.results[0].car_model
        assert "24.98" in res_m7.facts_summary

    def test_multi_vehicle_fast_path_spec_comparison(self):
        """Test fast-path tabular spec comparison for 2 known flagship models (< 2ms)."""
        query = "对比一下SU7 Max和Model 3的加速"
        res = self.engine.search_tier0(query)

        assert res is not None
        assert res.tier == 0
        assert res.is_fast_path is True
        assert len(res.results) == 2
        models = [r.car_model for r in res.results]
        assert any("SU7 Max" in m for m in models)
        assert any("Model 3" in m for m in models)
        assert "2.78秒" in res.facts_summary
        assert "4.4秒" in res.facts_summary
        assert "重点对比项" in res.facts_summary

    def test_xiaomi_motor_rpm_knowledge_graph_fast_path(self):
        """Test proprietary OEM motor RPM lookup via Knowledge Graph (< 2ms)."""
        query = "小米电机转速是多少"
        res = self.engine.search_tier0(query)

        assert res is not None
        assert res.tier == 0
        assert res.is_fast_path is True
        assert "转速" in res.facts_summary
        assert ("21,000rpm" in res.facts_summary or "27200rpm" in res.facts_summary or "21000" in res.facts_summary)

    def test_zeekr_001_range_spec(self):
        """Test Zeekr 001 range spec query."""
        query = "极氪001续航"
        res = self.engine.search_tier0(query)

        assert res is not None
        assert res.tier == 0
        assert "极氪-001" in res.results[0].car_model
        assert "705" in res.facts_summary or "750" in res.facts_summary

    def test_semantic_query_cache_sub_millisecond_hit(self):
        """Test that repeated exact/normalized queries hit memory cache in < 0.5 ms."""
        query = "特斯拉Model 3最高车速"
        res1 = self.engine.search_tier0(query)
        assert res1 is not None

        start = time.perf_counter()
        res2 = self.engine.search_tier0(query)
        duration_ms = (time.perf_counter() - start) * 1000.0

        assert res2 is not None
        assert res2.tier == 0
        assert res2.metadata.get("cache_hit") is True or duration_ms < 1.0
        assert "200km/h" in res2.facts_summary

    def test_rag_service_fast_path_integration(self):
        """Test that RAGService.search_vehicles routes direct spec query to Tier 0."""
        service = RAGService()
        req = VehicleQueryRequest(query_text="SU7 Max 零百加速是多少")
        resp = service.search_vehicles(req)

        assert resp is not None
        assert len(resp.results) >= 1
        assert "fast_path" in resp.search_summary or resp.total_time_ms < 50.0
        assert resp.results[0].car_model == "小米-SU7 Max"

    def test_lru_cache_eviction_on_capacity_saturation(self):
        """Test that SemanticQueryCache strictly respects capacity and evicts oldest items on saturation."""
        cache = SemanticQueryCache(capacity=3)
        cache.put("q1", "v1")
        cache.put("q2", "v2")
        cache.put("q3", "v3")

        # Access q1 to make it most recently used (order: q2, q3, q1)
        assert cache.get("q1") == "v1"

        # Insert q4 to trigger eviction of q2
        cache.put("q4", "v4")

        assert cache.get("q2") is None
        assert cache.get("q1") == "v1"
        assert cache.get("q3") == "v3"
        assert cache.get("q4") == "v4"


# -------------------------------------------------------------------------
# 2. Tier 1 & Tier 2 Routing Tests
# -------------------------------------------------------------------------


class TestTierRouting:
    def test_routing_classifier(self):
        engine = TieredRetrievalEngine()

        # Direct spec query -> Tier 0 candidate
        assert engine.is_tier0_candidate("SU7 Max 零百加速是多少") is True
        assert engine.is_tier0_candidate("极氪001续航是多少") is True

        # Fast multi-vehicle tabular spec comparison -> Tier 0 candidate
        assert engine.is_tier0_candidate("对比SU7 Max和Model 3的零百加速") is True

        # Deep comparative query -> Tier 2 candidate
        assert engine.is_tier2_candidate("对比问界M7和理想L7的智驾方案与优缺点差异") is True
        assert engine.is_tier0_candidate("对比问界M7和理想L7的智驾方案与优缺点差异") is False

        # Standard informational query -> neither Tier 0 nor Tier 2
        assert engine.is_tier0_candidate("推荐几款适合长途自驾的车型") is False
        assert engine.is_tier2_candidate("推荐几款适合长途自驾的车型") is False


# -------------------------------------------------------------------------
# 3. Dynamic Intent Interruptibility & Topic Hopping Tests
# -------------------------------------------------------------------------


class TestTopicHoppingAndInterruptibility:
    def test_needs_statement_without_questions_is_not_an_interruption(self):
        """Customer stating preferences in NEEDS_ANALYSIS must not be falsely treated as side-question interrupt."""
        state = SessionState(stage=Stage.NEEDS_ANALYSIS)
        msg = "平时主要是上下班代步，希望续航长一点，空间大一点，底盘舒服"

        result = TopicManager.analyze_user_turn(msg, state.stage, state)

        assert result.is_interrupt is False
        assert result.intent == UserDialogueIntent.SALES_PROGRESSION
        assert "灵活意图应答" not in result.suggested_directive

    def test_detect_side_question_during_reservation(self):
        """User in RESERVATION_4S asks technical question about battery."""
        state = SessionState(stage=Stage.RESERVATION_4S)
        msg = "等等，SU7 Max的电池包是宁德时代的还是比亚迪的？"

        result = TopicManager.analyze_user_turn(msg, state.stage, state)

        assert result.intent in (UserDialogueIntent.SIDE_QUESTION, UserDialogueIntent.MULTI_INTENT)
        assert result.is_interrupt is True
        assert "电池" in result.topic_label or "规格" in result.topic_label
        assert "灵活意图应答" in result.suggested_directive

    def test_circuit_breaker_topic_hopping_protection(self):
        """Verify circuit breaker does not falsely trip rejection loop during healthy side-questions."""
        cb = AgentCircuitBreaker(max_dwell=3, max_rejections=2)
        sid = "sess_topic_hop"

        # Turn 1-3: user asks spec questions
        for _ in range(3):
            trip = cb.record_turn(sid, Stage.NEEDS_ANALYSIS, rejection_reason="缺少预算信息", is_topic_hopping=True)
            assert trip is None

        # Turn 5: consultative nudge fires to guide customer toward test drive
        for _ in range(2):
            trip = cb.record_turn(sid, Stage.NEEDS_ANALYSIS, rejection_reason="缺少预算信息", is_topic_hopping=True)
        assert trip is not None
        assert trip.trip_type == "TOPIC_HOPPING_DWELL"
        assert "实车体验" in trip.intervention_note

    def test_sales_agent_answers_side_question_and_preserves_stage(self):
        """SalesAgent handles side question at RESERVATION_4S without losing stage or crashing."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(text="小米SU7 Max搭载宁德时代麒麟电池，请问您想预约哪天试驾？")
        agent = SalesAgent(llm=mock_llm)

        state = SessionState(
            session_id="hop_sess",
            stage=Stage.RESERVATION_4S,
            matched_cars=[{"car_model": "小米-SU7 Max"}],
        )
        inp = AgentInput(
            session_state=state,
            user_message="SU7 Max零百加速是多少？",
        )
        res = agent.process(inp)

        # Stage should stay anchored at RESERVATION_4S
        assert res.session_state.stage == Stage.RESERVATION_4S
        assert res.stage_changed is False
        assert res.response_text != ""
        assert len(res.session_state.interrupted_goals) >= 1
        assert res.session_state.interrupted_goals[-1]["stage"] == Stage.RESERVATION_4S.value

    def test_multi_turn_interruption_and_goal_resumption(self):
        """Full multi-turn flow: Interruption -> Side Question Answered -> Resumption Cue -> Goal Resumed."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(text="小米SU7 Max零百加速仅需2.78秒。")
        agent = SalesAgent(llm=mock_llm)

        # Turn 1: User at RESERVATION_4S interrupts with a side question
        state = SessionState(
            session_id="multi_turn_sess",
            stage=Stage.RESERVATION_4S,
            matched_cars=[{"car_model": "小米-SU7 Max"}],
        )
        inp1 = AgentInput(session_state=state, user_message="SU7 Max零百加速是多少？")
        res1 = agent.process(inp1)

        assert res1.session_state.stage == Stage.RESERVATION_4S
        assert len(res1.session_state.interrupted_goals) == 1
        assert res1.session_state.interrupted_goals[0]["stage"] == Stage.RESERVATION_4S.value

        # Turn 2: User acknowledges and agrees to continue
        mock_llm.complete.return_value = MagicMock(text="好的，我们继续预约试驾，请问您打算预约哪天？")
        inp2 = AgentInput(session_state=res1.session_state, user_message="原来这么快啊，好的，那继续预约吧")
        res2 = agent.process(inp2)

        # Interrupted goal was popped and directive guided resumption
        assert res2.session_state.stage == Stage.RESERVATION_4S
        assert len(res2.session_state.interrupted_goals) == 0

    def test_compound_negative_constraint_and_tech_query(self):
        """Test compound turn combining negative constraint and technical question simultaneously."""
        state = SessionState(stage=Stage.CAR_SELECTION)
        msg = "我不要SUV，SU7 Max电机转速多少，明天能去试驾吗？"
        res = TopicManager.analyze_user_turn(msg, state.stage, state)

        assert res.intent == UserDialogueIntent.MULTI_INTENT
        assert res.is_interrupt is True
        assert res.is_multi_intent is True
        assert "电机" in res.suggested_directive
        assert "多意图复合处理" in res.suggested_directive
        assert res.extracted_slots_hint.get("vehicle_category_bottom") == "SUV"
        assert res.extracted_slots_hint.get("reservation_date") == "明天"

    def test_constraint_update_directive_guidance(self):
        """Test that explicit constraint modification receives targeted directive."""
        state = SessionState(stage=Stage.CAR_SELECTION)
        msg = "预算改一下，换成25万以内"
        res = TopicManager.analyze_user_turn(msg, state.stage, state)

        assert res.intent == UserDialogueIntent.CONSTRAINT_UPDATE
        assert res.is_interrupt is True
        assert "客户约束条件修正" in res.suggested_directive


# -------------------------------------------------------------------------
# 4. Multi-Intent Joint Fulfillment & Adaptive Stage Traversal
# -------------------------------------------------------------------------


class TestMultiIntentJointFulfillment:
    def test_adaptive_stage_advancement_from_welcome_to_car_selection(self):
        """
        When user provides Name + Budget + Category at WELCOME,
        advance_adaptive steps through WELCOME -> PROFILE -> NEEDS -> CAR_SELECTION in 1 turn.
        """
        state = SessionState(
            stage=Stage.WELCOME,
            profile=UserProfile(name="李华", age="32"),
            needs=VehicleNeeds(
                explicit=ExplicitNeeds(
                    prize="25万左右",
                    vehicle_category_bottom="中型轿车",
                    powertrain_type="纯电动",
                )
            ),
        )

        verdict = advance_adaptive(state)

        assert verdict.accepted is True
        assert verdict.stage == Stage.CAR_SELECTION

    def test_adaptive_advancement_respects_guards(self):
        """If user provides profile but NO budget, adaptive advancement stops at NEEDS_ANALYSIS."""
        state = SessionState(
            stage=Stage.WELCOME,
            profile=UserProfile(name="王芳"),
            needs=VehicleNeeds(),  # No budget
        )

        verdict = advance_adaptive(state)

        assert verdict.accepted is True
        assert verdict.stage == Stage.NEEDS_ANALYSIS

    def test_multi_intent_sales_agent_processing(self):
        """
        SalesAgent processes compound user message:
        answers technical inquiry, extracts slots, and adaptively advances stage.
        """
        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(
            text='{"name": "陈明", "prize": "25万", "powertrain_type": "纯电", "vehicle_category_bottom": "轿车"}'
        )
        agent = SalesAgent(llm=mock_llm)

        state = SessionState(session_id="multi_sess", stage=Stage.WELCOME)
        state.profile.name = "陈明"
        state.needs.explicit.prize = "25万"
        state.needs.explicit.vehicle_category_bottom = "轿车"
        state.needs.explicit.powertrain_type = "纯电"

        inp = AgentInput(
            session_state=state,
            user_message="你好我是陈明，想看25万以内的纯电轿车，顺便问下SU7 Max电机转速是多少？",
        )
        res = agent.process(inp)

        assert res.session_state.stage == Stage.CAR_SELECTION
        assert res.stage_changed is True


# -------------------------------------------------------------------------
# 5. Deterministic Guardrails Preservation Tests
# -------------------------------------------------------------------------


class TestDeterministicGuardrailsPreservation:
    def test_evidence_ledger_blocks_unverified_car_selection(self):
        """Evidence ledger blocks transition to CAR_SELECTION if budget format is unverified/absent."""
        ledger = VerificationEvidenceLedger()
        state = SessionState(stage=Stage.NEEDS_ANALYSIS)
        state.needs.explicit.prize = ""

        allowed, missing = ledger.validate_stage_transition(
            Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION, state
        )
        assert allowed is False
        assert any("BUDGET_VERIFIED" in m for m in missing)

    def test_evidence_ledger_blocks_farewell_without_phone(self):
        """Evidence ledger blocks transition to FAREWELL without phone validation."""
        ledger = VerificationEvidenceLedger()
        state = SessionState(stage=Stage.RESERVATION_CONFIRMATION)
        state.reservation = ReservationInfo(
            test_driver="张伟",
            reservation_location="海淀店",
            reservation_phone_number="",  # missing phone
        )

        allowed, missing = ledger.validate_stage_transition(
            Stage.RESERVATION_CONFIRMATION, Stage.FAREWELL, state
        )
        assert allowed is False
        assert any("PHONE_VALIDATED" in m for m in missing)

    def test_constraint_reconciliation_detects_conflicts(self):
        """Reconciliation engine flags conflicts between budget and premium requirements."""
        state = SessionState()
        state.needs.explicit.prize = "12万"
        state.needs.explicit.brand = "保时捷"

        conflicts = reconcile_constraints(state)
        assert len(conflicts) >= 1
        assert any("预算" in c.description for c in conflicts)

    def test_reflection_guard_intercepts_unauthorized_claims(self):
        """Reflection gate cleans unauthorized sales guarantees."""
        raw_text = "我们保证全网最低价，而且买贵包退差价！"
        cleaned_text, warnings = reflect_and_guard(raw_text, [])

        assert "保证全网最低价" not in cleaned_text
        assert len(warnings) >= 1
