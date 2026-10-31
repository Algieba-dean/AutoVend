"""
Unit and integration tests for Marketing De-biasing & Anti-Fluff Engine.
(tests/test_marketing_debiaser.py)
"""

import pytest

from src.truth_engine.debiaser import MarketingDebiaser
from src.truth_engine.models import FluffCategory, FluffSeverity


@pytest.fixture
def debiaser():
    return MarketingDebiaser.get_instance()


class TestMarketingDebiaser:
    """Test marketing fluff detection and nominal-vs-real calculations."""

    def test_singleton_instance(self, debiaser):
        instance2 = MarketingDebiaser.get_instance()
        assert debiaser is instance2

    def test_detect_92_octane_fluff(self, debiaser):
        """Verify '支持加92号汽油' is exposed as standard hybrid tech, not exclusive innovation."""
        queries = [
            "这款车最大的亮点是支持加92号油，太省心了",
            "能加92号汽油吗？听说有独家技术支持吃粗粮",
            "92号油",
        ]
        for q in queries:
            items = debiaser.inspect_text_for_fluff(q)
            assert len(items) >= 1
            fluff = next(item for item in items if item.category == FluffCategory.STANDARD_TECH_AS_BREAKTHROUGH)
            assert "92号" in fluff.claim
            assert "阿特金森" in fluff.debiasing_explanation or "混动" in fluff.debiasing_explanation
            assert "无效宣传" in fluff.debiasing_explanation or "硬宣传" in fluff.debiasing_explanation

    def test_detect_full_stack_self_developed_myth(self, debiaser):
        """Verify '全栈自研' exposes Tier-1 supplier hardware integration."""
        text = "官方宣称整车从底盘到三电全部全栈自研，是不是真的很牛？"
        items = debiaser.inspect_text_for_fluff(text)
        assert len(items) >= 1
        fluff = next(item for item in items if item.category == FluffCategory.TIER1_AS_SELF_DEVELOPED)
        assert fluff.severity == FluffSeverity.HIGH
        assert "博世" in fluff.debiasing_explanation or "Tier-1" in fluff.reality
        assert "高通" in fluff.debiasing_explanation or "宁德时代" in fluff.debiasing_explanation

    def test_detect_supercar_acceleration_thermal_throttling(self, debiaser):
        """Verify '超跑级加速' identifies lack of thermal throttling disclosure."""
        text = "这台车拥有超跑级加速，百公里加速2.78秒，能天天当跑车开吗？"
        items = debiaser.inspect_text_for_fluff(text)
        assert len(items) >= 1
        fluff = next(item for item in items if item.category == FluffCategory.THERMAL_THROTTLE_OMISSION)
        assert "热衰减" in fluff.reality or "热保护" in fluff.debiasing_explanation
        assert "额定" in fluff.debiasing_explanation or "持续功率" in fluff.debiasing_explanation

    def test_detect_brake_pedal_breaking_claim(self, debiaser):
        """Verify brake pedal snapping panic is addressed with structural engineering fact."""
        text = "听说网上有人说急刹车时刹车踏板踩断了，塑料刹车踏板靠谱吗？"
        items = debiaser.inspect_text_for_fluff(text)
        assert len(items) >= 1
        fluff = next(item for item in items if item.category == FluffCategory.SAFETY_AND_CHASSIS_MYTH)
        assert "PA66-GF30" in fluff.debiasing_explanation or "玻纤" in fluff.debiasing_explanation
        assert "溃缩" in fluff.debiasing_explanation or "解耦" in fluff.debiasing_explanation
        assert "防断腿" in fluff.debiasing_explanation or "脚踝" in fluff.debiasing_explanation

    def test_detect_lifetime_warranty_restrictions(self, debiaser):
        """Verify lifetime warranty fine-print restrictions are surfaced."""
        text = "销售说提供三电终身质保，是不是以后不管怎么开都保修？"
        items = debiaser.inspect_text_for_fluff(text)
        assert len(items) >= 1
        fluff = next(item for item in items if item.category == FluffCategory.FINE_PRINT_RESTRICTION)
        assert "首任车主" in fluff.debiasing_explanation
        assert "4S店" in fluff.debiasing_explanation

    def test_detect_adas_overpromise(self, debiaser):
        """Verify L3/autonomous driving overpromising is grounded in L2 legal reality."""
        text = "宣传支持L3级自动驾驶，全场景零接管，真的可以解放双手睡觉吗？"
        items = debiaser.inspect_text_for_fluff(text)
        assert len(items) >= 1
        fluff = next(item for item in items if item.category == FluffCategory.ADAS_OVERPROMISE)
        assert "L2" in fluff.reality
        assert "驾驶员" in fluff.debiasing_explanation

    def test_nominal_vs_real_winter_and_highway_range(self, debiaser):
        """Verify winter low-temp range (50-65%) and highway 120km/h fulfillment rates."""
        models_to_test = ["小米SU7 Max", "小米SU7 标准版", "比亚迪汉EV", "特斯拉Model 3", "极氪001"]
        for model in models_to_test:
            gap = debiaser.get_range_gap(model)
            assert gap is not None
            assert gap.cltc_range_km > 0
            # Winter fulfillment rate should be within realistic 50%~65%
            assert 0.45 <= gap.winter_achievement_rate <= 0.65
            assert gap.winter_low_temp_range_km < gap.cltc_range_km
            # Highway fulfillment rate should be within realistic 60%~72%
            assert 0.58 <= gap.highway_achievement_rate <= 0.72
            assert gap.highway_120_range_km < gap.cltc_range_km
            assert len(gap.reasons) >= 1

    def test_peak_charging_vs_average_power_curve(self, debiaser):
        """Verify peak charging power drops and realistic 10%-80% duration is accurate."""
        ch = debiaser.get_charging_curve_reality("小米SU7 Max")
        assert ch is not None
        assert ch.nominal_peak_power_kw >= 300.0
        assert ch.average_power_10_to_80_kw < ch.nominal_peak_power_kw
        assert 15.0 <= ch.real_time_10_to_80_min <= 25.0
        assert ch.winter_cold_charge_penalty_min > 0

    def test_generate_debiasing_summary_formatting(self, debiaser):
        """Verify comprehensive Markdown debiasing summary generation."""
        summary = debiaser.generate_debiasing_summary(
            query_text="支持加92号汽油吗？冬天开暖风续航打几折？峰值充电能跑多快？",
            car_model="小米SU7 Max",
        )
        assert "营销去魅与硬宣传剥离" in summary
        assert "92号" in summary
        assert "标称 vs 真实物理工况差异" in summary
        assert "CLTC标称续航" in summary
        assert "达成率" in summary
        assert "充电标称峰值 vs 现实均值" in summary

    def test_empty_and_benign_text(self, debiaser):
        """Verify empty and neutral text does not generate false alarms."""
        assert debiaser.inspect_text_for_fluff("") == []
        assert debiaser.inspect_text_for_fluff("今天天气不错，早上好") == []

    def test_detect_800v_and_charging_fluff(self, debiaser):
        """Verify pseudo-800V and exaggerated 5-min 200km charging claims."""
        text_800v = "这台车宣传是标配全域800V高压架构，是不是真800V？"
        items_800v = debiaser.inspect_text_for_fluff(text_800v)
        assert len(items_800v) >= 1
        assert any("800V" in item.claim for item in items_800v)

        text_charge = "充电5分钟续航200公里，真的能达到吗？"
        items_charge = debiaser.inspect_text_for_fluff(text_charge)
        assert len(items_charge) >= 1
        assert any("5分钟" in item.claim for item in items_charge)

    def test_detect_zero_fire_and_gigacasting_fluff(self, debiaser):
        """Verify zero-spontaneous-combustion and gigacasting cost fluff."""
        text_fire = "销售说搭载了绝对不起火不爆炸的零自燃电池，是不是刀枪不入？"
        items_fire = debiaser.inspect_text_for_fluff(text_fire)
        assert len(items_fire) >= 1
        assert any("零自燃" in item.claim or "不起火" in item.claim for item in items_fire)

        text_casting = "采用了一体化大压铸车身，刚度航母级"
        items_casting = debiaser.inspect_text_for_fluff(text_casting)
        assert len(items_casting) >= 1
        assert any("一体化" in item.claim for item in items_casting)

        text_1000km = "号称续航超过1000公里，真正能跑多远？"
        items_1000km = debiaser.inspect_text_for_fluff(text_1000km)
        assert len(items_1000km) >= 1
        assert any("1000公里" in item.claim for item in items_1000km)

    def test_free_text_does_not_hallucinate_car_model(self, debiaser):
        """Verify that questioning generic fluff without vehicle model does not fabricate a bogus car name."""
        summary = debiaser.generate_debiasing_summary("支持加92号汽油吗？")
        assert "支持加92号汽油吗？" not in summary
        assert "CLTC标称续航" not in summary

        # But when a known model is mentioned in the question, it is auto-extracted
        summary_model = debiaser.generate_debiasing_summary("小米SU7支持加92号油吗？冬天续航怎么样？")
        assert "小米SU7" in summary_model
        assert "CLTC标称续航" in summary_model


class TestAdversarialMarketingFluffMatrix:
    """Comprehensive adversarial marketing claim detection across diverse EV/PHEV brands."""

    ADVERSARIAL_CASES = [
        # BYD (比亚迪)
        ("比亚迪DM-i支持加92号汽油，不挑油品吃粗粮省钱利器", FluffCategory.STANDARD_TECH_AS_BREAKTHROUGH, "92号"),
        ("比亚迪宣称搭载绝对不起火不爆炸的零自燃刀片电池", FluffCategory.SAFETY_AND_CHASSIS_MYTH, "零自燃"),
        # Tesla (特斯拉)
        ("特斯拉宣传一体化大压铸后地板航母级刚度，出了事故维修要多少钱？", FluffCategory.FINE_PRINT_RESTRICTION, "一体化"),
        ("特斯拉宣称FSD全场景自动驾驶零接管可以解放双手睡觉", FluffCategory.ADAS_OVERPROMISE, "自动驾驶"),
        # Xiaomi (小米)
        ("小米官方宣称从底盘到三电全部全栈自研，是不是真的很牛？", FluffCategory.TIER1_AS_SELF_DEVELOPED, "全栈自研"),
        ("小米SU7宣称超跑级百公里加速2.78秒狂暴模式天天当跑车开", FluffCategory.THERMAL_THROTTLE_OMISSION, "超跑"),
        ("网上说小米急刹车时塑料刹车踏板踩断是真的假的？", FluffCategory.SAFETY_AND_CHASSIS_MYTH, "踏板"),
        # Huawei HIMA / AITO (华为鸿蒙智行/问界)
        ("华为智驾全场景L3级自动驾驶零接管可以解放双手睡觉吗？", FluffCategory.ADAS_OVERPROMISE, "自动驾驶"),
        ("问界M9宣传采用潜艇级高强钢扭转刚度50000，撞车真的一点不变形吗？", FluffCategory.FINE_PRINT_RESTRICTION, "刚度"),
        # NIO (蔚来)
        ("蔚来宣传整车软硬件全栈自研神玑芯片，三电到底是不是纯血自研？", FluffCategory.TIER1_AS_SELF_DEVELOPED, "自研"),
        ("蔚来销售承诺三电终身质保终身免费保养，在外面小保养也保吗？", FluffCategory.FINE_PRINT_RESTRICTION, "终身质保"),
        # XPeng (小鹏)
        ("小鹏宣传标配全域800V高压架构，是不是真800V还是伪800V？", FluffCategory.STANDARD_TECH_AS_BREAKTHROUGH, "800V"),
        ("小鹏宣传充电5分钟续航200公里，真的能达到吗？", FluffCategory.NOMINAL_VS_REAL_GAP, "5分钟"),
        ("小鹏XNGP宣称全国都能开的自动驾驶零接管免责套路是什么？", FluffCategory.ADAS_OVERPROMISE, "自动驾驶"),
        # Zeekr (极氪)
        ("极氪浩瀚架构宣称打造绝对不起火零自燃神仙电池", FluffCategory.SAFETY_AND_CHASSIS_MYTH, "零自燃"),
        ("极氪001FR号称百公里加速2秒级秒杀超跑，持续激烈驾驶会不会热衰减？", FluffCategory.THERMAL_THROTTLE_OMISSION, "超跑"),
        # Li Auto (理想)
        ("理想L7宣传增程器能加92号油吃粗粮跑长途，是不是独家技术？", FluffCategory.STANDARD_TECH_AS_BREAKTHROUGH, "92号"),
        ("理想宣称纯电千里续航突破1000公里，真正能跑多远？", FluffCategory.NOMINAL_VS_REAL_GAP, "1000公里"),
    ]

    @pytest.mark.parametrize("query,expected_category,claim_keyword", ADVERSARIAL_CASES)
    def test_adversarial_marketing_fluff_detection(self, debiaser, query, expected_category, claim_keyword):
        items = debiaser.inspect_text_for_fluff(query)
        assert len(items) >= 1, f"Failed to detect fluff in: {query}"
        matching = [item for item in items if item.category == expected_category]
        assert len(matching) >= 1, f"Expected category {expected_category} not found for {query}"
        assert any(
            claim_keyword in item.claim or claim_keyword in item.reality or claim_keyword in item.debiasing_explanation
            for item in matching
        )


class TestRealWorldPhysicsMatrix:
    """Parametric evaluation of real-world winter and highway physical fulfillment rates."""

    TEST_MODELS = [
        "小米SU7 Max",
        "小米SU7 Pro",
        "小米SU7 标准版",
        "小米SU7 Ultra",
        "比亚迪汉EV",
        "比亚迪海豹EV",
        "比亚迪海鸥",
        "特斯拉Model 3",
        "特斯拉Model Y",
        "问界M9 EV",
        "问界M7",
        "极氪001",
        "极氪007",
        "小鹏G6",
        "蔚来ET5",
    ]

    @pytest.mark.parametrize("car_model", TEST_MODELS)
    def test_nominal_vs_real_range_gap_parameters(self, debiaser, car_model):
        gap = debiaser.get_range_gap(car_model)
        assert gap is not None, f"No range gap data for {car_model}"
        assert gap.cltc_range_km > 0
        # Winter fulfillment must reflect real thermodynamic loss (0.45 ~ 0.65)
        assert 0.45 <= gap.winter_achievement_rate <= 0.65
        assert gap.winter_low_temp_range_km < gap.cltc_range_km
        # Highway fulfillment must reflect aerodynamic drag at 120km/h (0.58 ~ 0.72)
        assert 0.58 <= gap.highway_achievement_rate <= 0.72
        assert gap.highway_120_range_km < gap.cltc_range_km
        # Must provide physical thermodynamic, aerodynamic, or mechanical root causes
        assert len(gap.reasons) >= 1
        assert any(
            any(k in r for k in ("风阻", "阻", "能耗", "热泵", "PTC", "低温", "极寒", "电解液", "欧姆", "转速", "自重", "车重", "损耗", "质量"))
            for r in gap.reasons
        )


class TestChargingCurvePhysicsMatrix:
    """Parametric evaluation of nominal peak power vs sustained realistic charging power."""

    CHARGING_MODELS = [
        "小米SU7 Max",
        "小米SU7 Ultra",
        "小米SU7 标准版",
        "极氪001",
        "特斯拉Model 3",
        "特斯拉Model Y",
        "小鹏G6",
        "极氪007",
    ]

    @pytest.mark.parametrize("car_model", CHARGING_MODELS)
    def test_charging_curve_physics_realities(self, debiaser, car_model):
        curve = debiaser.get_charging_curve_reality(car_model)
        assert curve is not None, f"No charging reality curve for {car_model}"
        assert curve.nominal_peak_power_kw >= 140.0
        # Realistic 10-80% average power is strictly lower than nominal peak
        assert curve.average_power_10_to_80_kw < curve.nominal_peak_power_kw
        # 10%-80% duration is realistically between 10 and 35 minutes
        assert 10.0 <= curve.real_time_10_to_80_min <= 35.0
        # Winter cold charging penalty must be non-zero
        assert curve.winter_cold_charge_penalty_min >= 10.0
        assert len(curve.reality_analysis) > 20

