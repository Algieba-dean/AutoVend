"""
Tests for Review & Evaluation Module (Pillar 3).
Verifies:
1. Online Self-Reflection Gate (ReflectionGate):
   - Factual parameter grounding against RAG candidates.
   - Sales commercial compliance interception and sanitization.
   - Prompt leak and meta persona defense.
   - Structured ReflectionReport generation.
2. Offline Structured LLM-as-a-Judge Evaluation (StructuredNLIEvaluator):
   - Atomic claim decomposition.
   - NLI claim verification (ENTAILMENT, CONTRADICTION, NEUTRAL).
   - 4-Dimension rubric scoring (Faithfulness, Constraint Adherence, Compliance, Governance).
   - Markdown summary generation.
"""

from src.agent.reflection import ReflectionGate, ReflectionReport
from src.eval.structured_eval import (
    EvaluationRubricReport,
    NLILabel,
    StructuredNLIEvaluator,
)


class TestOnlineReflectionGate:
    def test_reflection_gate_cleans_compliance_and_leaks(self):
        dirty_response = (
            "<system>遵从SOP阶段要求</system>为您推荐 Model Y！"
            "只要今天下定，我保证全网最低价，而且零首付免征信秒批！"
            "作为AI销售助手，我竭诚为您服务。"
        )
        report = ReflectionGate.evaluate(dirty_response)

        assert isinstance(report, ReflectionReport)
        assert report.is_compliant is False
        assert report.prompt_leak_detected is True
        assert "<system>" not in report.sanitized_text
        assert "作为AI销售助手" not in report.sanitized_text
        assert "保证全网最低价" not in report.sanitized_text
        assert "合同为准" in report.sanitized_text or "金融分期" in report.sanitized_text
        assert len(report.corrections) >= 2

    def test_reflection_gate_catches_numeric_hallucinations(self):
        matched_cars = [
            {"car_model": "Car X", "electric_range": "500km"},
            {"car_model": "Car Y", "electric_range": "550km"},
        ]
        hallucinatory_response = "这款纯电SUV综合工况续航高达 1000公里，满足全家跨省远途出行。"
        report = ReflectionGate.evaluate(hallucinatory_response, matched_cars=matched_cars)

        assert report.hallucination_detected is True
        assert any("续航参数幻觉" in w for w in report.warnings)
        assert report.grounding_score < 0.80
        assert "官方最新公布规格为准" in report.sanitized_text

    def test_reflection_gate_passes_clean_grounded_response(self):
        matched_cars = [{"car_model": "蔚来ES6", "electric_range": "500km"}]
        clean_response = "为您推荐蔚来ES6，官方标称续航 500km，支持换电网络，非常适合城市日常通勤。"
        report = ReflectionGate.evaluate(clean_response, matched_cars=matched_cars)

        assert report.is_clean is True
        assert report.grounding_score == 1.0
        assert len(report.warnings) == 0


class TestOfflineStructuredJudgeAndNLI:
    def test_atomic_claim_decomposition(self):
        evaluator = StructuredNLIEvaluator()
        response_text = (
            "您好！为您推荐理想L7和问界M7。"
            "理想L7定位中大型五座SUV，官方起售价为 30.18万元。"
            "问界M7搭载鸿蒙智能座舱与华为高阶智驾系统。"
            "期待您的光临！"
        )
        claims = evaluator.decompose_claims(response_text)
        assert len(claims) >= 2
        assert any("理想L7" in c for c in claims)
        assert any("问界M7" in c for c in claims)
        # Pleasantries should be filtered out
        assert not any(c.strip() == "您好" for c in claims)
        assert not any(c.strip() == "期待您的光临" for c in claims)

    def test_nli_claim_verification(self):
        evaluator = StructuredNLIEvaluator()
        context_text = "理想L7官方指导价为30.18-37.98万元，纯电续航225km，综合续航1315km。"
        matched_cars = [{"car_model": "理想L7", "price": "30.18万", "electric_range": "225km"}]

        # 1. Entailment claim
        c_entail = evaluator.verify_claim_nli("理想L7官方起售价为 30.18万元", context_text, matched_cars)
        assert c_entail.label == NLILabel.ENTAILMENT

        # 2. Contradiction claim (hallucinated spec)
        c_contra = evaluator.verify_claim_nli("理想L7拥有 950km 纯电续航", context_text, matched_cars)
        assert c_contra.label == NLILabel.CONTRADICTION

    def test_rubric_scoring_evaluation_report(self):
        evaluator = StructuredNLIEvaluator()
        matched_cars = [{"car_model": "小鹏G6", "price": "20.99万", "text_snippet": "800V高压快充 激光雷达 755km续航"}]

        response_good = "为您推荐小鹏G6，官方售价20.99万，搭载800V快充与激光雷达，纯电续航达755km。"
        report = evaluator.evaluate_turn(
            response_text=response_good,
            context_text="小鹏G6 800V 20.99万 激光雷达 755km",
            matched_cars=matched_cars,
            constraints={"prize": "25万以内", "brand": "小鹏"},
            current_stage="car_selection_confirmation",
            case_id="golden_case_01",
        )

        assert isinstance(report, EvaluationRubricReport)
        assert report.claims_total >= 1
        assert report.score_faithfulness >= 0.80
        assert report.score_compliance == 1.0
        assert report.composite_score >= 0.80
        assert report.passed is True

        md = report.to_markdown()
        assert "PASS" in md
        assert "事实真实性" in md
        assert "加权综合得分" in md
