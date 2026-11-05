"""
Unit and integration tests for Truth Engine, MIIT Platform, Reliability Repository,
Price Valuation, and Agent Tool Integration.
(tests/test_truth_engine.py)
"""

import pytest

from src.agent.plugins.pipeline import AgentPluginPipeline
from src.agent.schemas import (
    ExplicitNeeds,
    SessionState,
    Stage,
    UserProfile,
    UserRole,
    VehicleNeeds,
)
from src.agent.tools import dispatch, is_allowed
from src.core.truth_engine import TruthEngineFacade
from src.truth_engine.miit_platform import MIITSpecsPlatform
from src.truth_engine.price_valuation import PriceValuationEngine
from src.truth_engine.reliability_cases import ReliabilityCaseRepository
from src.truth_engine.service import TruthEngineService


class TestMIITPlatform:
    """Test MIIT declaration specifications and national standards mapping."""

    @pytest.fixture
    def miit_platform(self):
        return MIITSpecsPlatform.get_instance()

    def test_find_specs_known_models(self, miit_platform):
        for name in ["小米SU7 Max", "比亚迪汉EV", "特斯拉Model 3", "问界M9 EV", "极氪001"]:
            spec = miit_platform.find_specs(name)
            assert spec is not None, f"Failed to find specs for {name}"
            assert spec.curb_weight_kg > 1500
            assert spec.battery_net_weight_kg > 200
            assert spec.battery_mass_ratio > 0.1
            assert spec.motor_peak_power_kw > 100
            assert spec.motor_rated_power_kw > 50

    def test_deconstruct_parameters(self, miit_platform):
        spec = miit_platform.find_specs("小米SU7 Max")
        assert spec is not None
        decon = miit_platform.deconstruct_parameters(spec)
        assert decon["car_model"] == "小米SU7 Max"
        assert decon["battery_mass_ratio_pct"] > 25.0
        assert decon["rated_power_ratio_pct"] < 50.0  # rated is ~34% of peak
        assert len(decon["analysis_points"]) >= 2
        assert len(decon["standards_deconstruction"]) >= 3
        # Check GB standards mapped
        standards_text = " ".join(decon["standards_deconstruction"])
        assert "GB 38031-2020" in standards_text
        assert "GB 7258-2017" in standards_text
        assert "GB/T 18386.1-2021" in standards_text

    def test_format_deconstruction_markdown(self, miit_platform):
        md = miit_platform.format_deconstruction_markdown("小米SU7 Max")
        assert "工信部申报参数与国标拆解" in md
        assert "整备质量" in md
        assert "持续额定" in md
        assert "国家标准底线与现实差距" in md


class TestReliabilityCases:
    """Test owner reliability, controversies, and crash tests repository."""

    @pytest.fixture
    def repo(self):
        return ReliabilityCaseRepository.get_instance()

    def test_infotainment_reliability(self, repo):
        info = repo.find_infotainment_record("小米SU7")
        assert info is not None
        assert "8295" in info.soc_chip
        assert info.screen_blackout_rate_per_year > 0
        assert len(info.ota_negative_regressions) >= 1

    def test_battery_safety_and_standards(self, repo):
        batt = repo.find_battery_safety("小米SU7 Max")
        assert batt is not None
        assert "三元锂" in batt.battery_chemistry
        assert "GB 38031-2020" in batt.gb_38031_compliance
        assert "托底" in batt.puncture_and_impact_reality

    def test_brake_and_chassis_controversies(self, repo):
        controversies = repo.get_chassis_brake_controversies("刹车踏板踩断")
        assert len(controversies) >= 1
        pedal_case = next(c for c in controversies if "刹车踏板" in c.topic)
        assert "PA66-GF30" in pedal_case.engineering_fact
        assert "溃缩" in pedal_case.engineering_fact
        assert "防断腿" in pedal_case.engineering_fact or "脚踝" in pedal_case.engineering_fact

        onebox_case = next(c for c in repo.get_chassis_brake_controversies() if "One-Box" in c.topic)
        assert "液压" in onebox_case.engineering_fact
        assert "GB 7258" in onebox_case.material_and_standards

    def test_crash_test_ratings(self, repo):
        crash = repo.find_crash_test("小米SU7")
        assert crash is not None
        assert "中保研" in crash.evaluator
        assert "G" in crash.occupant_safety
        assert "A柱" in crash.small_overlap_25_result


class TestPriceValuationEngine:
    """Test depreciation valuation and drive-away price calculator."""

    @pytest.fixture
    def price_engine(self):
        return PriceValuationEngine.get_instance()

    def test_depreciation_rates(self, price_engine):
        dep = price_engine.get_depreciation_data("小米SU7 Max")
        assert dep is not None
        assert 0.70 <= dep.one_year_residual_rate <= 0.85
        assert 0.45 <= dep.three_year_residual_rate <= 0.65
        assert "万元" in dep.current_retail_price_range_wan

    def test_calculate_drive_away_price_standard(self, price_engine):
        calc = price_engine.calculate_drive_away_price(
            car_model="小米SU7 Max",
            msrp_wan=29.99,
            cash_discount_wan=1.0,
            perks_discount_wan=0.6,
            trade_in_subsidy_wan=1.5,
        )
        # Net car price = 29.99 - 1.0 - 0.6 - 1.5 = 26.89万
        assert abs(calc.net_car_price_wan - 26.89) < 0.01
        # Net car < 33.9万, EV purchase tax is 0
        assert calc.purchase_tax_wan == 0.0
        # Total price includes insurance + registration
        assert calc.total_drive_away_price_wan > calc.net_car_price_wan
        assert len(calc.hidden_fee_warnings) >= 3

    def test_calculate_drive_away_price_high_end_tax(self, price_engine):
        """Test EV exceeding 30,000 RMB exemption limit gets taxed on the difference."""
        calc = price_engine.calculate_drive_away_price(
            car_model="问界M9",
            msrp_wan=50.0,
            cash_discount_wan=0.0,
            perks_discount_wan=0.0,
            trade_in_subsidy_wan=0.0,
        )
        assert calc.net_car_price_wan == 50.0
        # Taxable base = 50.0 / 1.13 = 44.247万, normal tax = 4.425万. Exemption = 3.0万, so tax ~ 1.42万
        assert calc.purchase_tax_wan > 1.0
        assert calc.total_drive_away_price_wan > 51.0

    def test_hidden_fee_warnings(self, price_engine):
        md = price_engine.format_price_and_depreciation_markdown("小米SU7 Max")
        assert "金融服务费警告" in md
        assert "出库费" in md
        assert "装潢包" in md


class TestTruthEngineFacade:
    """Test facade and unified service."""

    @pytest.fixture
    def facade(self):
        return TruthEngineFacade.get_instance()

    def test_facade_deconstruct_specs(self, facade):
        res = facade.deconstruct_vehicle_specs("小米SU7 Max")
        assert res["found_in_miit"] is True
        assert "整备质量" in res["summary_markdown"]

    def test_facade_uncover_marketing_fluff(self, facade):
        res = facade.uncover_marketing_fluff("这款混动车支持加92号汽油", car_model="比亚迪汉DM-i")
        assert res["detected_fluff_count"] >= 1
        assert "92号" in res["summary_markdown"]

    def test_facade_get_safety_cases(self, facade):
        res = facade.get_real_owner_feedback_and_safety_cases("小米SU7", query_filter="刹车踏板")
        assert "真实车主体验" in res["summary_markdown"]
        assert "刹车踏板" in res["summary_markdown"]

    def test_facade_generate_truth_sales_note(self, facade):
        note = facade.generate_truth_sales_note("听说刹车踏板会踩断，真的假的？", car_model="小米SU7")
        assert note is not None
        assert "AUTO-VEND CONSUMER TRUTH DIRECTIVE" in note
        assert "PA66-GF30" in note
        assert "溃缩" in note

    def test_build_full_truth_report(self):
        service = TruthEngineService.get_instance()
        report = service.build_full_truth_report("小米SU7 Max")
        assert report.car_model == "小米SU7 Max"
        assert report.miit_specs is not None
        assert report.range_gap is not None
        assert report.battery_safety is not None
        assert report.depreciation is not None
        assert report.drive_away_price is not None


class TestAgentToolIntegration:
    """Test integration of truth tools in agent tools dispatch and stage permissions."""

    @pytest.fixture
    def initial_state(self):
        return SessionState(
            session_id="test_truth_session",
            user_role=UserRole.CUSTOMER,
            stage=Stage.NEEDS_ANALYSIS,
            profile=UserProfile(name="张先生", family_size="3口之家"),
            needs=VehicleNeeds(explicit=ExplicitNeeds(price="25-30万")),
        )

    def test_tools_allowed_in_stages(self):
        for stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
            assert is_allowed(stage, "deconstruct_vehicle_specs")
            assert is_allowed(stage, "uncover_marketing_fluff")
            assert is_allowed(stage, "get_real_owner_feedback_and_safety_cases")

    def test_dispatch_deconstruct_vehicle_specs(self, initial_state):
        result = dispatch(
            initial_state,
            "deconstruct_vehicle_specs",
            {"car_model": "小米SU7 Max"},
        )
        assert result.ok is True
        assert "小米SU7 Max" in result.message
        assert len(initial_state.system_notes) >= 1
        assert "工信部申报参数与国标拆解" in initial_state.system_notes[0]

    def test_dispatch_uncover_marketing_fluff(self, initial_state):
        result = dispatch(
            initial_state,
            "uncover_marketing_fluff",
            {"claim_or_feature": "可加92号油，超跑级百公里加速", "car_model": "比亚迪汉"},
        )
        assert result.ok is True
        assert len(initial_state.system_notes) >= 1
        combined_notes = " ".join(initial_state.system_notes)
        assert "营销去魅" in combined_notes or "物理工况差异" in combined_notes

    def test_dispatch_get_real_owner_feedback_and_safety_cases(self, initial_state):
        result = dispatch(
            initial_state,
            "get_real_owner_feedback_and_safety_cases",
            {"car_model": "小米SU7", "query_filter": "刹车踏板"},
        )
        assert result.ok is True
        assert len(initial_state.system_notes) >= 1
        assert "刹车踏板" in initial_state.system_notes[0]


class TestPluginPipelineIntegration:
    """Test TruthDebiaserPlugin inside AgentPluginPipeline."""

    def test_plugin_pipeline_triggers_truth_note(self):
        pipeline = AgentPluginPipeline()
        state = SessionState(
            session_id="test_plugin_truth",
            stage=Stage.NEEDS_ANALYSIS,
            matched_cars=[{"car_model": "小米SU7"}],
        )
        context = {
            "user_input": "这车支持加92号油吗？急刹车刹车踏板会不会被踩断？",
        }
        pipeline.run_before_response(state, context)
        assert context.get("truth_debiasing_triggered") is True
        assert len(state.system_notes) >= 1
        notes_str = " ".join(state.system_notes)
        assert "AUTO-VEND CONSUMER TRUTH DIRECTIVE" in notes_str
        assert "92号" in notes_str
        assert "踏板" in notes_str


class TestDisambiguationAndEdgeCases:
    """Test edge cases, empty input handling, and vehicle disambiguation."""

    def test_empty_strings_handled_gracefully(self):
        miit = MIITSpecsPlatform.get_instance()
        repo = ReliabilityCaseRepository.get_instance()
        price_engine = PriceValuationEngine.get_instance()

        assert miit.find_specs("") is None
        assert miit.find_specs("   ") is None
        assert miit.extract_model_name_from_text("") is None
        assert miit.extract_model_name_from_text("   ") is None
        assert miit.extract_model_name_from_text("今天天气真好") is None

        assert repo.find_infotainment_record("") is None
        assert repo.find_infotainment_record("   ") is None
        assert repo.find_battery_safety("") is None
        assert repo.find_crash_test("") is None

        assert price_engine.get_depreciation_data("") is None
        assert price_engine.get_depreciation_data("   ") is None

    def test_model_disambiguation_accuracy(self):
        miit = MIITSpecsPlatform.get_instance()

        # BYD Seagull vs BYD Han EV
        seagull = miit.find_specs("比亚迪海鸥")
        assert seagull is not None
        assert seagull.car_model == "比亚迪海鸥"
        assert seagull.curb_weight_kg < 1300.0
        assert seagull.curb_weight_kg != 2100.0  # Not Han EV

        # Tesla Model Y vs Model 3
        modely = miit.find_specs("特斯拉Model Y")
        assert modely is not None
        assert modely.car_model == "特斯拉Model Y"

        # Xiaomi SU7 Ultra vs Max
        su7ultra = miit.find_specs("小米SU7 Ultra")
        assert su7ultra is not None
        assert su7ultra.car_model == "小米SU7 Ultra"
        assert su7ultra.motor_peak_power_kw > 1000.0

        # AITO Wenjie M7 vs M9
        m7 = miit.find_specs("问界M7")
        assert m7 is not None
        assert m7.car_model == "问界M7"


class TestNewTruthToolsDispatch:
    """Test calculate_real_drive_away_price and explain_automotive_term tools."""

    @pytest.fixture
    def initial_state(self):
        return SessionState(
            session_id="test_new_tools_session",
            user_role=UserRole.CUSTOMER,
            stage=Stage.NEEDS_ANALYSIS,
            profile=UserProfile(name="李女士"),
            needs=VehicleNeeds(explicit=ExplicitNeeds(price="20-30万")),
        )

    def test_dispatch_calculate_real_drive_away_price(self, initial_state):
        res = dispatch(
            initial_state,
            "calculate_real_drive_away_price",
            {
                "car_model": "小米SU7 Max",
                "msrp_wan": 29.99,
                "cash_discount": 1.0,
                "perks_discount": 0.5,
                "trade_in_subsidy": 1.0,
            },
        )
        assert res.ok is True
        assert "落地价" in res.message
        assert res.request["type"] == "drive_away_price"
        assert len(initial_state.system_notes) >= 1
        note = " ".join(initial_state.system_notes)
        assert "全包落地价" in note
        assert "金融服务费警告" in note

    def test_dispatch_calculate_price_missing_car_model(self, initial_state):
        res = dispatch(initial_state, "calculate_real_drive_away_price", {"car_model": ""})
        assert res.ok is False
        assert "缺少" in res.message

    def test_dispatch_explain_automotive_term_known(self, initial_state):
        res = dispatch(initial_state, "explain_automotive_term", {"term": "800V"})
        assert res.ok is True
        assert "800V" in res.message
        assert len(initial_state.system_notes) >= 1
        note = " ".join(initial_state.system_notes)
        assert "汽车技术名词解析" in note

    def test_dispatch_explain_automotive_term_fluff_fallback(self, initial_state):
        res = dispatch(initial_state, "explain_automotive_term", {"term": "支持加92号油"})
        assert res.ok is True
        assert len(initial_state.system_notes) >= 1
        note = " ".join(initial_state.system_notes)
        assert "92号" in note

    def test_dispatch_explain_automotive_term_unknown(self, initial_state):
        res = dispatch(initial_state, "explain_automotive_term", {"term": "xyz_completely_unknown_999"})
        assert res.ok is False
        assert "未收录" in res.message

    def test_stage_permissions_for_new_tools(self):
        # explain_automotive_term allowed in WELCOME, PROFILE_ANALYSIS, NEEDS_ANALYSIS, CAR_SELECTION
        assert is_allowed(Stage.WELCOME, "explain_automotive_term")
        assert is_allowed(Stage.PROFILE_ANALYSIS, "explain_automotive_term")
        assert is_allowed(Stage.NEEDS_ANALYSIS, "explain_automotive_term")
        assert is_allowed(Stage.CAR_SELECTION, "explain_automotive_term")

        # calculate_real_drive_away_price allowed in NEEDS_ANALYSIS, CAR_SELECTION, RESERVATION_4S
        assert is_allowed(Stage.NEEDS_ANALYSIS, "calculate_real_drive_away_price")
        assert is_allowed(Stage.CAR_SELECTION, "calculate_real_drive_away_price")
        assert is_allowed(Stage.RESERVATION_4S, "calculate_real_drive_away_price")


class TestTruthAPIRoutes:
    """Test REST API endpoints mounted under /api/truth."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from backend.app.main import app

        return TestClient(app)

    def test_deconstruct_specs_endpoint(self, client):
        resp = client.get("/api/truth/deconstruct?car_model=小米SU7 Max")
        assert resp.status_code == 200
        data = resp.json()
        assert data["car_model"] == "小米SU7 Max"
        assert data["found_in_miit"] is True
        assert "工信部申报参数与国标拆解" in data["summary_markdown"]

    def test_deconstruct_specs_endpoint_empty_param(self, client):
        resp = client.get("/api/truth/deconstruct?car_model=")
        assert resp.status_code == 400

    def test_debias_endpoint(self, client):
        resp = client.post(
            "/api/truth/debias",
            json={"claim": "支持加92号汽油，超跑级加速", "car_model": "比亚迪汉DM-i"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["detected_fluff_count"] >= 1
        assert "营销去魅" in data["summary_markdown"]

    def test_reliability_endpoint(self, client):
        resp = client.get("/api/truth/reliability?car_model=小米SU7&query_filter=刹车踏板")
        assert resp.status_code == 200
        data = resp.json()
        assert data["car_model"] == "小米SU7"
        assert "刹车踏板" in data["summary_markdown"]

    def test_pricing_endpoint(self, client):
        resp = client.post(
            "/api/truth/pricing",
            json={
                "car_model": "小米SU7 Max",
                "msrp_wan": 29.99,
                "cash_discount": 1.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "calculation" in data
        assert data["calculation"]["total_drive_away_price_wan"] > 28.0

    def test_standards_endpoint(self, client):
        resp = client.get("/api/truth/standards")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 4
        assert "GB 38031-2020" in data["standards"]

    def test_models_endpoint(self, client):
        resp = client.get("/api/truth/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 15
        assert "小米SU7 Max" in data["models"]

    def test_full_report_endpoint(self, client):
        resp = client.get("/api/truth/report/小米SU7 Max")
        assert resp.status_code == 200
        data = resp.json()
        assert data["car_model"] == "小米SU7 Max"
        assert "全维度真实拆解报告" in data["report_markdown"]


class TestNationalStandardsComplianceAndDeconstruction:
    """Parametric evaluation of National Standards mapping and engineering reality gap deconstruction."""

    STANDARDS_CASES = [
        (
            "GB 38031-2020",
            "动力蓄电池安全要求",
            "5分钟内不起火不爆炸",
            "5分钟安全逃生时间是国家法规的'底线及格线'",
            "穿透",
        ),
        (
            "GB 7258-2017",
            "机动车运行安全技术条件",
            "应急制动效能",
            "One-Box",
            "PA66-GF30",
        ),
        (
            "GB/T 18386.1-2021",
            "电动汽车能量消耗量和续驶里程试验方法",
            "CLTC-P",
            "28.96 km/h",
            "50%~65%",
        ),
        (
            "GB/T 31498-2021",
            "电动汽车碰撞后安全要求",
            "4秒内泄放至安全电压",
            "HVIL",
            "防撞梁",
        ),
    ]

    @pytest.mark.parametrize(
        "standard_code,title_keyword,mandatory_clause_kw,deconstruction_kw1,deconstruction_kw2",
        STANDARDS_CASES,
    )
    def test_national_standards_content_and_gaps(
        self,
        standard_code,
        title_keyword,
        mandatory_clause_kw,
        deconstruction_kw1,
        deconstruction_kw2,
    ):
        from src.truth_engine.miit_platform import NATIONAL_STANDARDS_MAPPING

        assert standard_code in NATIONAL_STANDARDS_MAPPING, f"Standard {standard_code} not found in mapping"
        item = NATIONAL_STANDARDS_MAPPING[standard_code]
        assert title_keyword in item["title"]
        assert mandatory_clause_kw in item["key_mandatory_clause"]
        gap = item["engineering_reality_gap"]
        assert deconstruction_kw1 in gap
        assert deconstruction_kw2 in gap


class TestMIITRegulatoryParameterCrossVerification:
    """Parametric regulatory parameter cross-verification across 15+ models in MIIT database."""

    MIIT_MODELS = [
        "小米SU7 Ultra",
        "小米SU7 Max",
        "小米SU7 Pro",
        "小米SU7 标准版",
        "比亚迪汉EV",
        "比亚迪汉DM-i",
        "比亚迪秦PLUS DM-i",
        "比亚迪海豹EV",
        "比亚迪海鸥",
        "问界M9 EV",
        "问界M9 增程版",
        "问界M7",
        "特斯拉Model 3",
        "特斯拉Model Y",
        "极氪001",
        "极氪007",
        "理想L7",
        "理想L8",
        "理想L9",
    ]

    @pytest.mark.parametrize("car_model", MIIT_MODELS)
    def test_miit_declaration_physics_parameters(self, car_model):
        from src.truth_engine.miit_platform import MIITSpecsPlatform

        platform = MIITSpecsPlatform.get_instance()
        spec = platform.find_specs(car_model)
        assert spec is not None, f"Failed to retrieve MIIT declaration for {car_model}"

        # 1. Mass checks
        assert spec.curb_weight_kg > 1000.0
        assert spec.gross_weight_kg > spec.curb_weight_kg
        assert spec.battery_net_weight_kg > 100.0
        # Battery mass ratio is realistically 10%~35% of curb weight
        assert 0.10 <= spec.battery_mass_ratio <= 0.35

        # 2. Motor power checks (Continuous rated power must strictly reflect reality: <= 50% of peak)
        assert spec.motor_peak_power_kw > 50.0
        assert spec.motor_rated_power_kw > 20.0
        assert spec.motor_rated_power_kw < spec.motor_peak_power_kw
        assert 0.25 <= spec.rated_to_peak_power_ratio <= 0.50

        # 3. Speed & standards checks
        assert spec.top_speed_kmh >= 130.0
        assert len(spec.relevant_national_standards) >= 2
        assert "GB 38031-2020" in spec.relevant_national_standards
        assert "GB 7258-2017" in spec.relevant_national_standards


class TestSafetyControversiesAndCrashTestsMatrix:
    """Parametric evaluation of safety controversies, infotainment reliability, and crash tests."""

    CONTROVERSY_CASES = [
        ("刹车踏板踩断", "PA66-GF30", "溃缩", "脚踝"),
        ("塑料刹车踏板", "PA66-GF30", "1200N", "Euro-NCAP"),
        ("One-Box线控制动失灵", "博世", "机械液压", "GB 7258-2017"),
        ("电子刹车踩不动", "常开", "应急制动", "ASIL-D"),
        ("悬架球头脱落", "整备质量", "铝合金", "扭矩"),
        ("电池托底穿刺", "GB 38031-2020", "吸能", "5分钟"),
        ("底盘磕碰电池穿透", "高强钢", "热失控", "逃生"),
    ]

    @pytest.mark.parametrize("query,kw1,kw2,kw3", CONTROVERSY_CASES)
    def test_chassis_and_brake_controversy_retrieval(self, query, kw1, kw2, kw3):
        from src.truth_engine.reliability_cases import ReliabilityCaseRepository

        repo = ReliabilityCaseRepository.get_instance()
        controversies = repo.get_chassis_brake_controversies(query)
        assert len(controversies) >= 1, f"No controversies found for query: {query}"
        combined_text = " ".join([c.engineering_fact + " " + c.material_and_standards for c in controversies])
        assert kw1 in combined_text
        assert kw2 in combined_text
        assert kw3 in combined_text

    INFOTAINMENT_MODELS = [
        ("小米SU7", "8295", 1.2),
        ("特斯拉Model 3", "Ryzen", 0.8),
        ("比亚迪汉", "DiLink", 1.8),
        ("问界M9", "HarmonyOS", 0.4),
        ("极氪001", "8295", 1.5),
        ("问界M7", "HarmonyOS", 0.5),
        ("特斯拉Model Y", "Ryzen", 0.7),
        ("比亚迪海豹", "DiLink", 1.4),
        ("小鹏G6", "8155", 0.8),
    ]

    @pytest.mark.parametrize("model,chip_or_os_kw,max_blackout_rate", INFOTAINMENT_MODELS)
    def test_infotainment_reliability_matrix(self, model, chip_or_os_kw, max_blackout_rate):
        from src.truth_engine.reliability_cases import ReliabilityCaseRepository

        repo = ReliabilityCaseRepository.get_instance()
        info = repo.find_infotainment_record(model)
        assert info is not None, f"No infotainment record for {model}"
        assert chip_or_os_kw in info.soc_chip or chip_or_os_kw in info.reboot_frequency
        assert 0.0 < info.screen_blackout_rate_per_year <= max_blackout_rate + 0.1
        assert len(info.ota_negative_regressions) >= 1

    CRASH_TEST_MODELS = [
        ("小米SU7", "中保研", "A柱"),
        ("特斯拉Model 3", "中保研", "小偏置"),
        ("特斯拉Model Y", "中保研", "乘员舱"),
        ("比亚迪汉", "中保研", "热成型钢"),
    ]

    @pytest.mark.parametrize("model,evaluator_kw,structural_kw", CRASH_TEST_MODELS)
    def test_crash_test_matrix(self, model, evaluator_kw, structural_kw):
        from src.truth_engine.reliability_cases import ReliabilityCaseRepository

        repo = ReliabilityCaseRepository.get_instance()
        crash = repo.find_crash_test(model)
        assert crash is not None, f"No crash test for {model}"
        assert evaluator_kw in crash.evaluator
        assert crash.occupant_safety.startswith("G")
        assert len(crash.structural_defect_notes) >= 1
        combined_notes = crash.small_overlap_25_result + " " + " ".join(crash.structural_defect_notes)
        assert structural_kw in combined_notes

