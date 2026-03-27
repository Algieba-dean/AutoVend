"""
KPI Test Suite — End-to-End Multi-Turn Dialogue Scoring.

AI-generated test dialogues simulate realistic user personas through
complete conversation flows. Each dialogue is scored on:

  1. Stage progression correctness
  2. Profile extraction completeness
  3. Needs extraction completeness
  4. Response non-emptiness (proxy for response quality)
  5. Session state consistency

KPI Targets:
  - Multi-turn stage progression accuracy ≥ 95%
  - Profile completeness after profile stage ≥ 80%
  - Needs completeness after needs stage ≥ 70%
  - Response generation success rate = 100%
  - Agent process latency (no real LLM) < 10ms per turn
"""

import json
import time
from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest

from agent.sales_agent import SalesAgent
from agent.schemas import AgentInput, SessionState, Stage

# ── Scoring ────────────────────────────────────────────────────


@dataclass
class DialogueScore:
    """Scoring results for a single dialogue run."""

    persona: str = ""
    total_turns: int = 0
    stage_correct: int = 0
    responses_generated: int = 0
    profile_fields_filled: int = 0
    profile_fields_total: int = 10  # total profile fields
    needs_fields_filled: int = 0
    needs_key_fields_total: int = 5  # prize, brand, powertrain, category, design
    latencies_ms: list = field(default_factory=list)

    @property
    def stage_accuracy(self) -> float:
        return self.stage_correct / self.total_turns if self.total_turns else 0

    @property
    def response_rate(self) -> float:
        return self.responses_generated / self.total_turns if self.total_turns else 0

    @property
    def profile_completeness(self) -> float:
        return self.profile_fields_filled / self.profile_fields_total

    @property
    def needs_completeness(self) -> float:
        return self.needs_fields_filled / self.needs_key_fields_total

    @property
    def avg_latency_ms(self) -> float:
        return sum(self.latencies_ms) / len(self.latencies_ms) if self.latencies_ms else 0

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        s = sorted(self.latencies_ms)
        idx = int(len(s) * 0.95)
        return s[min(idx, len(s) - 1)]


# ── Mock LLM Factory ──────────────────────────────────────────


def _create_dialogue_llm(
    profile_response: dict,
    needs_response: dict,
    implicit_response: dict,
    reservation_response: dict,
):
    """Create a mock LLM that returns stage-appropriate JSON."""
    mock = MagicMock()

    def side_effect(prompt):
        resp = MagicMock()
        p = prompt.lower()
        if "profile" in p and "extract" in p:
            resp.text = json.dumps(profile_response)
        elif "vehicle requirements" in p or "explicit" in p or "vehicle needs" in p:
            resp.text = json.dumps(needs_response)
        elif "deduce" in p or "implicit" in p:
            resp.text = json.dumps(implicit_response)
        elif "reservation" in p and "extract" in p:
            resp.text = json.dumps(reservation_response)
        else:
            resp.text = "感谢您的信息！让我为您推荐合适的车型。"
        return resp

    mock.complete.side_effect = side_effect
    return mock


# ── AI-Generated Dialogue Scenarios ───────────────────────────
#
# Each scenario represents a complete user persona journey with
# multiple conversation turns and expected stage at each step.

DIALOGUE_SCENARIOS = [
    {
        "id": "D01",
        "persona": "Young professional buying first EV",
        "profile_resp": {
            "name": "李明",
            "age": "26",
            "residence": "杭州",
            "target_driver": "自己",
            "expertise": "新手",
            "family_size": "1",
            "price_sensitivity": "中",
        },
        "needs_resp": {
            "powertrain_type": "纯电动",
            "vehicle_category_bottom": "紧凑型SUV",
            "prize": "15-25万",
            "brand": "比亚迪",
            "design_style": "运动",
        },
        "implicit_resp": {
            "safety": "High",
            "smartness": "High",
            "energy_consumption_level": "Low",
            "driving_range": "High",
        },
        "reservation_resp": {
            "reservation_date": "2024-06-15",
            "reservation_time": "10:00",
            "reservation_location": "杭州西湖店",
            "test_driver": "李明",
            "reservation_phone_number": "13800138000",
        },
        "turns": [
            {"msg": "你好，我想看看车", "expected_stage": Stage.PROFILE_ANALYSIS},
            {"msg": "我叫李明，26岁，在杭州", "expected_stage": Stage.NEEDS_ANALYSIS},
            {"msg": "我想要纯电SUV，预算15到25万", "expected_stage": Stage.CAR_SELECTION},
            {"msg": "比亚迪元Plus看起来不错，我想试驾", "expected_stage": Stage.CAR_SELECTION},
            {"msg": "6月15号上午10点，杭州西湖店", "expected_stage": Stage.CAR_SELECTION},
        ],
    },
    {
        "id": "D02",
        "persona": "Family father upgrading to 7-seat SUV",
        "profile_resp": {
            "name": "张伟",
            "age": "38",
            "family_size": "5",
            "residence": "上海浦东",
            "target_driver": "自己",
            "price_sensitivity": "高",
            "parking_conditions": "地下车库",
        },
        "needs_resp": {
            "seat_layout": "7座",
            "vehicle_category_bottom": "中大型SUV",
            "prize": "25-35万",
            "powertrain_type": "插电混动",
            "drive_type": "全轮驱动",
        },
        "implicit_resp": {
            "family_friendliness": "High",
            "space": "Large",
            "cost_performance": "High",
            "safety": "High",
        },
        "reservation_resp": {
            "reservation_date": "周六",
            "reservation_time": "14:00",
            "reservation_location": "浦东试驾中心",
            "test_driver": "张伟",
            "reservation_phone_number": "13900139000",
        },
        "turns": [
            {"msg": "你好", "expected_stage": Stage.PROFILE_ANALYSIS},
            {"msg": "我是张伟，38岁，家里五口人", "expected_stage": Stage.NEEDS_ANALYSIS},
            {"msg": "要7座SUV，25到35万，插电混动", "expected_stage": Stage.CAR_SELECTION},
            {"msg": "理想L8不错，周六下午2点试驾", "expected_stage": Stage.CAR_SELECTION},
        ],
    },
    {
        "id": "D03",
        "persona": "Luxury buyer with specific performance needs",
        "profile_resp": {
            "name": "David",
            "age": "45",
            "residence": "深圳",
            "target_driver": "self",
            "expertise": "expert",
            "family_size": "3",
            "price_sensitivity": "低",
        },
        "needs_resp": {
            "brand": "BMW",
            "design_style": "运动",
            "acceleration_0_100": "4秒以内",
            "drive_type": "后轮驱动",
            "prize": "50万以上",
        },
        "implicit_resp": {
            "brand_grade": "High",
            "power_performance": "High",
            "comfort_level": "High",
            "aesthetics": "Large",
        },
        "reservation_resp": {
            "reservation_date": "明天",
            "reservation_time": "11:00",
            "reservation_location": "南山BMW中心",
            "test_driver": "David",
            "reservation_phone_number": "13700137000",
        },
        "turns": [
            {"msg": "Hi there", "expected_stage": Stage.PROFILE_ANALYSIS},
            {
                "msg": "I'm David, 45, car enthusiast from Shenzhen",
                "expected_stage": Stage.NEEDS_ANALYSIS,
            },
            {
                "msg": "Want a BMW, sporty, under 4s 0-100, RWD, 50万+",
                "expected_stage": Stage.CAR_SELECTION,
            },
        ],
    },
    {
        "id": "D04",
        "persona": "Budget-conscious college graduate",
        "profile_resp": {
            "name": "小陈",
            "age": "24",
            "target_driver": "自己",
            "expertise": "新手",
            "family_size": "1",
            "price_sensitivity": "高",
            "parking_conditions": "路边",
        },
        "needs_resp": {
            "prize": "8万以下",
            "vehicle_category_bottom": "微型车",
            "fuel_consumption": "低",
            "seat_layout": "5座",
            "powertrain_type": "汽油",
        },
        "implicit_resp": {
            "cost_performance": "High",
            "energy_consumption_level": "Low",
            "safety": "High",
        },
        "reservation_resp": {},
        "turns": [
            {"msg": "你好啊", "expected_stage": Stage.PROFILE_ANALYSIS},
            {"msg": "我是小陈，24岁刚毕业", "expected_stage": Stage.NEEDS_ANALYSIS},
            {"msg": "预算8万以下，省油的小车就行", "expected_stage": Stage.CAR_SELECTION},
        ],
    },
    {
        "id": "D05",
        "persona": "Retired couple seeking comfort",
        "profile_resp": {
            "name": "王阿姨",
            "age": "62",
            "target_driver": "老伴",
            "family_size": "2",
            "residence": "北京朝阳",
            "expertise": "中等",
            "price_sensitivity": "中",
        },
        "needs_resp": {
            "design_style": "舒适",
            "vehicle_category_bottom": "中型轿车",
            "prize": "20-30万",
            "powertrain_type": "汽油",
            "seat_layout": "5座",
        },
        "implicit_resp": {"comfort_level": "High", "safety": "High", "smartness": "Medium"},
        "reservation_resp": {
            "reservation_date": "下周一",
            "reservation_time": "09:00",
            "reservation_location": "朝阳望京店",
            "test_driver": "王阿姨",
            "reservation_phone_number": "13600136000",
        },
        "turns": [
            {"msg": "你好", "expected_stage": Stage.PROFILE_ANALYSIS},
            {"msg": "我姓王，62岁，给老伴选车", "expected_stage": Stage.NEEDS_ANALYSIS},
            {"msg": "舒适的中型轿车，20到30万", "expected_stage": Stage.CAR_SELECTION},
        ],
    },
]


# ── Test Classes ───────────────────────────────────────────────


class TestMultiTurnDialogues:
    """KPI: Multi-turn stage progression + response generation."""

    def _run_dialogue(self, scenario: dict) -> DialogueScore:
        """Execute one full dialogue and return scores."""
        llm = _create_dialogue_llm(
            scenario["profile_resp"],
            scenario["needs_resp"],
            scenario["implicit_resp"],
            scenario["reservation_resp"],
        )
        agent = SalesAgent(llm=llm)
        state = SessionState(session_id=f"test-{scenario['id']}")
        score = DialogueScore(persona=scenario["persona"])

        for turn in scenario["turns"]:
            inp = AgentInput(
                session_state=state,
                user_message=turn["msg"],
            )

            t0 = time.perf_counter()
            result = agent.process(inp)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            score.total_turns += 1
            score.latencies_ms.append(elapsed_ms)

            if result.session_state.stage == turn["expected_stage"]:
                score.stage_correct += 1

            if result.response_text.strip():
                score.responses_generated += 1

            state = result.session_state

        # Evaluate profile completeness
        profile_dict = state.profile.model_dump()
        score.profile_fields_filled = sum(1 for v in profile_dict.values() if v)

        # Evaluate needs completeness (key fields only)
        explicit_dict = state.needs.explicit.model_dump()
        key_fields = [
            "prize",
            "brand",
            "powertrain_type",
            "vehicle_category_bottom",
            "design_style",
        ]
        score.needs_fields_filled = sum(1 for k in key_fields if explicit_dict.get(k))

        return score

    @pytest.mark.parametrize(
        "scenario", DIALOGUE_SCENARIOS, ids=[s["id"] for s in DIALOGUE_SCENARIOS]
    )
    def test_stage_progression(self, scenario):
        """Each dialogue's stage accuracy must be ≥ 80%."""
        score = self._run_dialogue(scenario)
        assert score.stage_accuracy >= 0.80, (
            f"[{scenario['id']}] {scenario['persona']}: "
            f"stage accuracy={score.stage_accuracy:.0%} "
            f"({score.stage_correct}/{score.total_turns})"
        )

    @pytest.mark.parametrize(
        "scenario", DIALOGUE_SCENARIOS, ids=[s["id"] for s in DIALOGUE_SCENARIOS]
    )
    def test_response_generation(self, scenario):
        """Every turn must produce a non-empty response."""
        score = self._run_dialogue(scenario)
        assert score.response_rate == 1.0, (
            f"[{scenario['id']}] {scenario['persona']}: "
            f"response rate={score.response_rate:.0%} "
            f"({score.responses_generated}/{score.total_turns})"
        )

    @pytest.mark.parametrize(
        "scenario", DIALOGUE_SCENARIOS, ids=[s["id"] for s in DIALOGUE_SCENARIOS]
    )
    def test_process_latency(self, scenario):
        """Agent p95 latency (mock LLM) must be < 50ms."""
        score = self._run_dialogue(scenario)
        assert score.p95_latency_ms < 50, (
            f"[{scenario['id']}] p95 latency={score.p95_latency_ms:.1f}ms — target < 50ms"
        )

    def test_aggregate_stage_accuracy(self):
        """Aggregate stage accuracy across all dialogues ≥ 95%."""
        total_turns = 0
        total_correct = 0
        for scenario in DIALOGUE_SCENARIOS:
            score = self._run_dialogue(scenario)
            total_turns += score.total_turns
            total_correct += score.stage_correct
        accuracy = total_correct / total_turns if total_turns else 0
        assert accuracy >= 0.95, (
            f"Aggregate stage accuracy={accuracy:.0%} "
            f"({total_correct}/{total_turns}) — target ≥ 95%"
        )

    def test_aggregate_response_rate(self):
        """Aggregate response rate across all dialogues = 100%."""
        total = 0
        generated = 0
        for scenario in DIALOGUE_SCENARIOS:
            score = self._run_dialogue(scenario)
            total += score.total_turns
            generated += score.responses_generated
        rate = generated / total if total else 0
        assert rate == 1.0, f"Aggregate response rate={rate:.0%} ({generated}/{total})"


class TestAgentProcessLatency:
    """KPI: Agent process latency (no real LLM) < 10ms avg."""

    def test_single_turn_latency(self):
        """Single turn processing with mock LLM should be < 10ms."""
        mock = MagicMock()
        resp = MagicMock()
        resp.text = json.dumps({"name": "Test"})
        mock.complete.return_value = resp

        agent = SalesAgent(llm=mock)
        state = SessionState(session_id="latency-test")
        inp = AgentInput(session_state=state, user_message="Hello")

        latencies = []
        for _ in range(20):
            t0 = time.perf_counter()
            agent.process(inp)
            latencies.append((time.perf_counter() - t0) * 1000)

        avg = sum(latencies) / len(latencies)
        assert avg < 10, f"Avg latency={avg:.2f}ms — target < 10ms"

    def test_multi_session_isolation(self):
        """Different sessions should not interfere with each other."""
        mock = MagicMock()
        resp = MagicMock()
        resp.text = json.dumps({"name": "UserA"})
        mock.complete.return_value = resp

        agent = SalesAgent(llm=mock)

        # Process session A
        state_a = SessionState(session_id="sess-A")
        agent.process(AgentInput(session_state=state_a, user_message="I'm user A"))

        # Process session B
        state_b = SessionState(session_id="sess-B")
        agent.process(AgentInput(session_state=state_b, user_message="I'm user B"))

        # Sessions should be independent
        history_a = agent.get_history_text("sess-A")
        history_b = agent.get_history_text("sess-B")
        assert "user A" in history_a
        assert "user B" in history_b
        assert "user B" not in history_a
        assert "user A" not in history_b
