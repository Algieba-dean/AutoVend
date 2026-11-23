"""
Tests for Red Flag 1 (LangGraph modularization & legacy glue retirement) and
Red Flag 2 (real NLI/embedding/DB-backed upgrades replacing TOY IMPLEMENTATIONs).
"""

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from src.agent.battlecards import Battlecard, BattlecardStore, match_battlecards
from src.agent.graph import AgentGraphState
from src.agent.langgraph_agent import LangGraphSalesAgent
from src.agent.reflection import (
    ClaimVerdict,
    FaithfulnessAuditOutput,
    ReflectionGate,
    audit_response_against_evidence,
    verify_numeric_hallucinations,
)
from src.agent.sales_agent import SalesAgent
from src.core.compression import ContextCompressor
from src.rag_service.eval_monitor import RAGEvalMonitor


class TestRedFlag1Modularization:
    def test_langgraph_sales_agent_and_facade_exports(self):
        assert LangGraphSalesAgent is not None
        assert AgentGraphState is not None
        assert not hasattr(SalesAgent, "observe"), "Legacy observe() should be retired"
        assert not hasattr(SalesAgent, "respond"), "Legacy respond() should be retired"

    def test_sales_agent_delegates_to_langgraph(self):
        fake_llm = MagicMock()
        agent = SalesAgent(llm=fake_llm)
        assert isinstance(agent.langgraph, LangGraphSalesAgent)
        assert agent.get_history_text("nonexistent-session") == ""


class TestRedFlag2ReflectionAuditor:
    def test_multi_attribute_numeric_hallucination_checks(self):
        cars = [
            {
                "car_model": "TestEV",
                "electric_range": "500km",
                "battery_capacity": "75kWh",
                "acceleration_0_100": "5.8",
            }
        ]
        # Battery hallucination (150kWh vs 75kWh)
        warnings = verify_numeric_hallucinations("该车搭载 150kWh 超大电池包，3.0秒破百。", cars)
        assert any("电池容量幻觉" in w for w in warnings)
        assert any("零百加速参数幻觉" in w for w in warnings)

    def test_nli_scorer_entailment_and_contradiction(self):
        cars = [{"car_model": "Model X", "price_wan": 25.0, "electric_range": "600km"}]
        report = ReflectionGate.evaluate(
            "Model X 纯电续航 600km，非常适合城市通勤。该车支持免费终身换电。",
            matched_cars=cars,
            nli_scorer=lambda premise, hyp: 0.9 if "600km" in hyp else 0.1,
        )
        assert report.faithfulness_method == "cross_encoder_nli"
        assert report.hallucination_detected is True
        assert any(v.label == "CONTRADICTED" for v in report.claim_verdicts)

    def test_auditor_llm_structured_nli(self):
        fake_auditor = MagicMock()
        structured = MagicMock()
        structured.invoke.return_value = FaithfulnessAuditOutput(
            claim_verdicts=[
                ClaimVerdict(claim="续航 600km", label="ENTAILED", reason="matches evidence"),
                ClaimVerdict(claim="标配空气悬架", label="UNSUPPORTED", reason="not in evidence"),
            ],
            overall_faithful=False,
        )
        fake_auditor.with_structured_output.return_value = structured

        cars = [{"car_model": "Model X", "price_wan": 25.0, "electric_range": "600km"}]
        report = audit_response_against_evidence(
            "Model X 续航 600km，全系标配空气悬架。",
            matched_cars=cars,
            auditor_llm=fake_auditor,
        )
        assert report.faithfulness_method == "llm_nli"
        assert report.hallucination_detected is True
        assert report.grounding_score == 0.5


class TestRedFlag2DynamicBattlecards:
    def test_cms_upsert_and_match(self, tmp_path: Path):
        cms_file = tmp_path / "battlecards.json"
        store = BattlecardStore(cms_path=cms_file)
        store.upsert_battlecard(
            Battlecard(
                name="小米 SU7",
                category="纯电中大型轿跑",
                target_competitors=["小米su7", "su7"],
                strengths=["生态互联", "外观运动"],
                counter_points=["对比二排头部空间与家庭实用性"],
            ),
            persist=True,
        )
        reloaded = BattlecardStore(cms_path=cms_file)
        cards = match_battlecards("我在看小米SU7，怎么样？", store=reloaded)
        assert len(cards) == 1
        assert cards[0].name == "小米 SU7"
        assert cms_file.exists()


class TestRedFlag2SemanticCompression:
    def test_semantic_and_info_density_scoring(self):
        def fake_embed(texts):
            # First text is query, second is relevant spec, third is fluff
            out = []
            for t in texts:
                if "续航" in t or "700" in t:
                    out.append([1.0, 0.0, 0.0])
                else:
                    out.append([0.0, 1.0, 0.0])
            return np.asarray(out, dtype=np.float32)

        s_spec = ContextCompressor.score_sentence(
            "CLTC纯电续航702km，支持800V高压快充。",
            query_text="续航多少",
            embed_fn=fake_embed,
        )
        s_fluff = ContextCompressor.score_sentence(
            "这款车外观非常好看，开出去很有面子。",
            query_text="续航多少",
            embed_fn=fake_embed,
        )
        assert s_spec > s_fluff

    def test_markdown_table_preservation(self):
        table = (
            "| 车型 | 价格 | 续航 |\n"
            "|---|---|---|\n"
            "| Model A | 22万 | 600km |\n"
            "| Model B | 25万 | 700km |\n"
            "此外该车还拥有非常舒适的氛围灯和多种驾驶模式可供日常切换体验。"
        )
        res = ContextCompressor.compress_snippet(table, query_text="续航", max_length=120)
        assert "|---|---|---|" in res.compressed_text


class TestRedFlag2EmbeddingOODMonitor:
    def test_embedding_centroid_ood_detection(self):
        def fake_embed(texts):
            vecs = []
            for t in texts:
                if any(k in t for k in ("车", "SUV", "续航", "试驾", "预算", "Model")):
                    vecs.append([1.0, 0.0, 0.0])
                else:
                    vecs.append([0.0, 0.0, 1.0])
            return np.asarray(vecs, dtype=np.float32)

        monitor = RAGEvalMonitor(embed_fn=fake_embed, ood_similarity_threshold=0.5)
        assert monitor._detect_out_of_domain("预算20万买什么SUV", top1_score=0.8, result_count=3) is False
        assert monitor._detect_out_of_domain("明天股票会涨吗", top1_score=0.1, result_count=0) is True

    def test_distributional_fallback_without_embedder(self):
        monitor = RAGEvalMonitor()
        assert monitor._detect_out_of_domain("20万纯电SUV续航对比", top1_score=0.75, result_count=3) is False
        assert monitor._detect_out_of_domain("帮我写一段Python快排代码", top1_score=0.05, result_count=0) is True
