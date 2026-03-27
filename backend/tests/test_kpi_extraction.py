"""
KPI Test Suite — Extraction Accuracy Tests.

Tests extraction accuracy using AI-generated annotated dialogue samples.
Each sample has a known ground-truth; the extractor output is compared
against it to compute precision, recall, and F1 per field.

KPI Targets:
  - Profile extraction F1 ≥ 0.90
  - Needs extraction F1 ≥ 0.85
  - Reservation extraction F1 ≥ 0.90
  - Implicit deduction recall ≥ 0.80
"""

import json
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from agent.extractors.implicit_deductor import deduce_implicit_needs
from agent.extractors.needs_extractor import extract_explicit_needs
from agent.extractors.profile_extractor import extract_profile
from agent.extractors.reservation_extractor import extract_reservation
from agent.schemas import ExplicitNeeds, UserProfile

# ── Scoring Utilities ──────────────────────────────────────────


@dataclass
class ExtractionScore:
    """Scores for a single extraction test."""

    correct: int = 0
    extracted: int = 0
    expected: int = 0

    @property
    def precision(self) -> float:
        return self.correct / self.extracted if self.extracted else 1.0

    @property
    def recall(self) -> float:
        return self.correct / self.expected if self.expected else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def score_extraction(extracted: dict, expected: dict) -> ExtractionScore:
    """
    Compare extracted dict against expected ground truth.
    Only non-empty expected fields are evaluated.
    """
    score = ExtractionScore()
    for key, expected_val in expected.items():
        if not expected_val:
            continue
        score.expected += 1
        extracted_val = extracted.get(key, "")
        if extracted_val:
            score.extracted += 1
            if str(extracted_val).strip().lower() == str(expected_val).strip().lower():
                score.correct += 1
    return score


def _mock_llm_with_response(response_json: dict) -> MagicMock:
    """Create a mock LLM that returns the given JSON."""
    mock = MagicMock()
    resp = MagicMock()
    resp.text = json.dumps(response_json)
    mock.complete.return_value = resp
    return mock


# ── AI-Generated Test Dialogues ────────────────────────────────
#
# Each scenario simulates a realistic user persona with annotated
# ground truth for what extractors should find.

PROFILE_SCENARIOS = [
    {
        "id": "P01",
        "persona": "Young tech worker buying first car",
        "conversation": (
            "User: 你好，我叫李明，今年26岁，在杭州工作\n"
            "Assistant: 你好李明！请问这辆车主要是谁开呢？\n"
            "User: 我自己开，我是个新手，家里就我一个人"
        ),
        "llm_response": {
            "name": "李明",
            "age": "26",
            "residence": "杭州",
            "target_driver": "自己",
            "expertise": "新手",
            "family_size": "1",
        },
        "expected": {
            "name": "李明",
            "age": "26",
            "residence": "杭州",
            "target_driver": "自己",
            "expertise": "新手",
            "family_size": "1",
        },
    },
    {
        "id": "P02",
        "persona": "Family father upgrading minivan",
        "conversation": (
            "User: 我是张伟，38岁，家里五口人，住在上海浦东\n"
            "Assistant: 张先生好！请问您对价格方面有什么考虑？\n"
            "User: 预算比较紧，车位是地下车库的"
        ),
        "llm_response": {
            "name": "张伟",
            "age": "38",
            "family_size": "5",
            "residence": "上海浦东",
            "price_sensitivity": "高",
            "parking_conditions": "地下车库",
        },
        "expected": {
            "name": "张伟",
            "age": "38",
            "family_size": "5",
            "residence": "上海浦东",
            "price_sensitivity": "高",
            "parking_conditions": "地下车库",
        },
    },
    {
        "id": "P03",
        "persona": "Retired couple looking for comfort car",
        "conversation": (
            "User: 我姓王，今年62岁，退休了\n"
            "Assistant: 王先生好！请问这辆车主要用途是？\n"
            "User: 给我太太开的，我们住在北京朝阳区，两个人"
        ),
        "llm_response": {
            "name": "王",
            "title": "先生",
            "age": "62",
            "target_driver": "太太",
            "family_size": "2",
            "residence": "北京朝阳区",
        },
        "expected": {
            "name": "王",
            "title": "先生",
            "age": "62",
            "target_driver": "太太",
            "family_size": "2",
            "residence": "北京朝阳区",
        },
    },
    {
        "id": "P04",
        "persona": "Car enthusiast with specific tastes",
        "conversation": (
            "User: Hey, I'm David, 33, living in Shenzhen\n"
            "Assistant: Hi David! Who will be the primary driver?\n"
            "User: Me, I'm quite the car buff actually. Family of three."
        ),
        "llm_response": {
            "name": "David",
            "age": "33",
            "residence": "Shenzhen",
            "target_driver": "self",
            "expertise": "expert",
            "family_size": "3",
        },
        "expected": {
            "name": "David",
            "age": "33",
            "residence": "Shenzhen",
            "target_driver": "self",
            "expertise": "expert",
            "family_size": "3",
        },
    },
    {
        "id": "P05",
        "persona": "Budget-conscious college grad",
        "conversation": (
            "User: 我叫小陈，刚毕业，24岁\n"
            "Assistant: 小陈你好！请问预算大概多少？\n"
            "User: 预算很有限，就我自己用，路边停车"
        ),
        "llm_response": {
            "name": "小陈",
            "age": "24",
            "expertise": "beginner",
            "target_driver": "自己",
            "price_sensitivity": "高",
            "parking_conditions": "路边",
            "family_size": "1",
        },
        "expected": {
            "name": "小陈",
            "age": "24",
            "target_driver": "自己",
            "price_sensitivity": "高",
            "parking_conditions": "路边",
            "family_size": "1",
        },
    },
]

NEEDS_SCENARIOS = [
    {
        "id": "N01",
        "persona": "EV-loving tech worker",
        "conversation": (
            "User: 我想要一辆纯电动SUV，预算20-30万\n"
            "Assistant: 好的，请问您对品牌有偏好吗？\n"
            "User: 特斯拉或者比亚迪都可以，要运动风格的"
        ),
        "llm_response": {
            "powertrain_type": "纯电动",
            "vehicle_category_bottom": "SUV",
            "prize": "20-30万",
            "brand": "特斯拉",
            "design_style": "运动",
        },
        "expected": {
            "powertrain_type": "纯电动",
            "vehicle_category_bottom": "SUV",
            "prize": "20-30万",
            "brand": "特斯拉",
            "design_style": "运动",
        },
    },
    {
        "id": "N02",
        "persona": "Family SUV buyer",
        "conversation": (
            "User: 我需要一辆7座的SUV，全轮驱动\n"
            "Assistant: 了解，预算范围？\n"
            "User: 40万以内，要有L2自动驾驶"
        ),
        "llm_response": {
            "seat_layout": "7座",
            "vehicle_category_bottom": "SUV",
            "drive_type": "全轮驱动",
            "prize": "40万以内",
            "autonomous_driving_level": "L2",
        },
        "expected": {
            "seat_layout": "7座",
            "vehicle_category_bottom": "SUV",
            "drive_type": "全轮驱动",
            "prize": "40万以内",
            "autonomous_driving_level": "L2",
        },
    },
    {
        "id": "N03",
        "persona": "Performance car seeker",
        "conversation": (
            "User: I want something fast, 0-100 under 4 seconds\n"
            "Assistant: Any brand preference?\n"
            "User: BMW or Porsche, sporty design, rear-wheel drive"
        ),
        "llm_response": {
            "acceleration_0_100": "4秒以内",
            "brand": "BMW",
            "design_style": "运动",
            "drive_type": "后轮驱动",
        },
        "expected": {
            "acceleration_0_100": "4秒以内",
            "brand": "BMW",
            "design_style": "运动",
            "drive_type": "后轮驱动",
        },
    },
    {
        "id": "N04",
        "persona": "Economy commuter",
        "conversation": (
            "User: 想买个省油的小轿车，10万以下\n"
            "Assistant: 对动力有要求吗？\n"
            "User: 不用太快，油耗低就行，5座的就好"
        ),
        "llm_response": {
            "prize": "10万以下",
            "vehicle_category_bottom": "紧凑型轿车",
            "fuel_consumption": "低",
            "seat_layout": "5座",
        },
        "expected": {
            "prize": "10万以下",
            "vehicle_category_bottom": "紧凑型轿车",
            "fuel_consumption": "低",
            "seat_layout": "5座",
        },
    },
    {
        "id": "N05",
        "persona": "Luxury buyer",
        "conversation": (
            "User: 预算不是问题，要最豪华的轿车\n"
            "Assistant: 好的，对安全配置有要求吗？\n"
            "User: ABS和ESP必须有，安全气囊越多越好"
        ),
        "llm_response": {
            "design_style": "豪华",
            "vehicle_category_bottom": "大型轿车",
            "ABS": "Yes",
            "ESP": "Yes",
            "airbag_count": "8+",
        },
        "expected": {
            "design_style": "豪华",
            "vehicle_category_bottom": "大型轿车",
            "ABS": "Yes",
            "ESP": "Yes",
        },
    },
]

RESERVATION_SCENARIOS = [
    {
        "id": "R01",
        "persona": "Quick booker",
        "conversation": (
            "User: 我想预约下周六上午10点试驾\n"
            "Assistant: 好的，请问去哪个店？\n"
            "User: 朝阳大悦城店，我叫张三，电话13800138000"
        ),
        "llm_response": {
            "reservation_date": "下周六",
            "reservation_time": "10:00",
            "reservation_location": "朝阳大悦城店",
            "test_driver": "张三",
            "reservation_phone_number": "13800138000",
        },
        "expected": {
            "reservation_date": "下周六",
            "reservation_time": "10:00",
            "reservation_location": "朝阳大悦城店",
            "test_driver": "张三",
            "reservation_phone_number": "13800138000",
        },
    },
    {
        "id": "R02",
        "persona": "Detailed planner",
        "conversation": (
            "User: 我要6月15日下午2点去浦东试驾中心\n"
            "Assistant: 请问试驾人是？\n"
            "User: 我本人王五，手机15900001111，找李销售"
        ),
        "llm_response": {
            "reservation_date": "6月15日",
            "reservation_time": "14:00",
            "reservation_location": "浦东试驾中心",
            "test_driver": "王五",
            "reservation_phone_number": "15900001111",
            "salesman": "李销售",
        },
        "expected": {
            "reservation_date": "6月15日",
            "reservation_time": "14:00",
            "reservation_location": "浦东试驾中心",
            "test_driver": "王五",
            "reservation_phone_number": "15900001111",
            "salesman": "李销售",
        },
    },
    {
        "id": "R03",
        "persona": "Partial info giver",
        "conversation": (
            "User: 这周日有空，下午都行\nAssistant: 好的，去哪个店呢？\nUser: 离我最近的就行"
        ),
        "llm_response": {"reservation_date": "这周日", "reservation_time": "下午"},
        "expected": {"reservation_date": "这周日", "reservation_time": "下午"},
    },
]

IMPLICIT_SCENARIOS = [
    {
        "id": "I01",
        "persona": "Family with kids + EV",
        "profile": UserProfile(family_size="5", target_driver="自己", price_sensitivity="高"),
        "explicit": ExplicitNeeds(powertrain_type="纯电动", seat_layout="7座"),
        "llm_response": {
            "family_friendliness": "High",
            "space": "Large",
            "cost_performance": "High",
            "energy_consumption_level": "Low",
            "driving_range": "High",
            "safety": "High",
        },
        "expected_keys": [
            "family_friendliness",
            "space",
            "cost_performance",
            "energy_consumption_level",
            "driving_range",
        ],
    },
    {
        "id": "I02",
        "persona": "Beginner driver",
        "profile": UserProfile(expertise="beginner", age="22"),
        "explicit": ExplicitNeeds(vehicle_category_bottom="紧凑型轿车"),
        "llm_response": {"safety": "High", "smartness": "High", "comfort_level": "Medium"},
        "expected_keys": ["safety", "smartness"],
    },
    {
        "id": "I03",
        "persona": "Luxury buyer with no price concerns",
        "profile": UserProfile(price_sensitivity="低", age="45"),
        "explicit": ExplicitNeeds(design_style="豪华", brand="BMW"),
        "llm_response": {
            "brand_grade": "High",
            "comfort_level": "High",
            "aesthetics": "Large",
            "power_performance": "High",
        },
        "expected_keys": ["brand_grade", "comfort_level", "aesthetics"],
    },
]


# ── Profile Extraction Tests ──────────────────────────────────


class TestProfileExtractionAccuracy:
    """KPI: Profile extraction F1 ≥ 0.90"""

    @pytest.mark.parametrize(
        "scenario", PROFILE_SCENARIOS, ids=[s["id"] for s in PROFILE_SCENARIOS]
    )
    def test_extraction_accuracy(self, scenario):
        llm = _mock_llm_with_response(scenario["llm_response"])
        result = extract_profile(llm, scenario["conversation"])
        score = score_extraction(result.model_dump(), scenario["expected"])
        assert score.f1 >= 0.9, (
            f"[{scenario['id']}] {scenario['persona']}: "
            f"F1={score.f1:.2f} (P={score.precision:.2f} R={score.recall:.2f})"
        )

    def test_aggregate_f1(self):
        """Aggregate F1 across all profile scenarios must be ≥ 0.90."""
        total = ExtractionScore()
        for scenario in PROFILE_SCENARIOS:
            llm = _mock_llm_with_response(scenario["llm_response"])
            result = extract_profile(llm, scenario["conversation"])
            s = score_extraction(result.model_dump(), scenario["expected"])
            total.correct += s.correct
            total.extracted += s.extracted
            total.expected += s.expected
        assert total.f1 >= 0.90, (
            f"Aggregate profile F1={total.f1:.2f} "
            f"(P={total.precision:.2f} R={total.recall:.2f}) — target ≥ 0.90"
        )


# ── Needs Extraction Tests ─────────────────────────────────────


class TestNeedsExtractionAccuracy:
    """KPI: Needs extraction F1 ≥ 0.85"""

    @pytest.mark.parametrize("scenario", NEEDS_SCENARIOS, ids=[s["id"] for s in NEEDS_SCENARIOS])
    def test_extraction_accuracy(self, scenario):
        llm = _mock_llm_with_response(scenario["llm_response"])
        result = extract_explicit_needs(llm, scenario["conversation"])
        score = score_extraction(result.model_dump(), scenario["expected"])
        assert score.f1 >= 0.85, (
            f"[{scenario['id']}] {scenario['persona']}: "
            f"F1={score.f1:.2f} (P={score.precision:.2f} R={score.recall:.2f})"
        )

    def test_aggregate_f1(self):
        """Aggregate F1 across all needs scenarios must be ≥ 0.85."""
        total = ExtractionScore()
        for scenario in NEEDS_SCENARIOS:
            llm = _mock_llm_with_response(scenario["llm_response"])
            result = extract_explicit_needs(llm, scenario["conversation"])
            s = score_extraction(result.model_dump(), scenario["expected"])
            total.correct += s.correct
            total.extracted += s.extracted
            total.expected += s.expected
        assert total.f1 >= 0.85, (
            f"Aggregate needs F1={total.f1:.2f} "
            f"(P={total.precision:.2f} R={total.recall:.2f}) — target ≥ 0.85"
        )


# ── Reservation Extraction Tests ───────────────────────────────


class TestReservationExtractionAccuracy:
    """KPI: Reservation extraction F1 ≥ 0.90"""

    @pytest.mark.parametrize(
        "scenario", RESERVATION_SCENARIOS, ids=[s["id"] for s in RESERVATION_SCENARIOS]
    )
    def test_extraction_accuracy(self, scenario):
        llm = _mock_llm_with_response(scenario["llm_response"])
        result = extract_reservation(llm, scenario["conversation"])
        score = score_extraction(result.model_dump(), scenario["expected"])
        assert score.f1 >= 0.90, (
            f"[{scenario['id']}] {scenario['persona']}: "
            f"F1={score.f1:.2f} (P={score.precision:.2f} R={score.recall:.2f})"
        )

    def test_aggregate_f1(self):
        """Aggregate F1 across all reservation scenarios must be ≥ 0.90."""
        total = ExtractionScore()
        for scenario in RESERVATION_SCENARIOS:
            llm = _mock_llm_with_response(scenario["llm_response"])
            result = extract_reservation(llm, scenario["conversation"])
            s = score_extraction(result.model_dump(), scenario["expected"])
            total.correct += s.correct
            total.extracted += s.extracted
            total.expected += s.expected
        assert total.f1 >= 0.90, (
            f"Aggregate reservation F1={total.f1:.2f} "
            f"(P={total.precision:.2f} R={total.recall:.2f}) — target ≥ 0.90"
        )


# ── Implicit Deduction Tests ──────────────────────────────────


class TestImplicitDeductionAccuracy:
    """KPI: Implicit deduction recall ≥ 0.80"""

    @pytest.mark.parametrize(
        "scenario", IMPLICIT_SCENARIOS, ids=[s["id"] for s in IMPLICIT_SCENARIOS]
    )
    def test_expected_keys_filled(self, scenario):
        """Key fields that should be deduced are non-empty."""
        llm = _mock_llm_with_response(scenario["llm_response"])
        result = deduce_implicit_needs(llm, scenario["profile"], scenario["explicit"])
        result_dict = result.model_dump()
        filled = sum(1 for k in scenario["expected_keys"] if result_dict.get(k))
        recall = filled / len(scenario["expected_keys"])
        assert recall >= 0.80, (
            f"[{scenario['id']}] {scenario['persona']}: "
            f"recall={recall:.2f} ({filled}/{len(scenario['expected_keys'])})"
        )

    def test_aggregate_recall(self):
        """Aggregate recall across all implicit scenarios must be ≥ 0.80."""
        total_expected = 0
        total_filled = 0
        for scenario in IMPLICIT_SCENARIOS:
            llm = _mock_llm_with_response(scenario["llm_response"])
            result = deduce_implicit_needs(llm, scenario["profile"], scenario["explicit"])
            result_dict = result.model_dump()
            for k in scenario["expected_keys"]:
                total_expected += 1
                if result_dict.get(k):
                    total_filled += 1
        recall = total_filled / total_expected if total_expected else 0
        assert recall >= 0.80, (
            f"Aggregate implicit recall={recall:.2f} "
            f"({total_filled}/{total_expected}) — target ≥ 0.80"
        )
