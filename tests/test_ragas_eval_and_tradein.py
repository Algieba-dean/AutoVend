"""
Tests for Route A (LlamaIndex removal), Used-Car Trade-In Valuation Tool,
and RAGAS evaluation wrapper.
"""

import importlib
import inspect
import json
from types import SimpleNamespace

import pytest


class TestRouteACleanup:
    def test_deprecated_llamaindex_modules_removed(self):
        for mod_name in (
            "backend.app.rag.query_engine",
            "backend.app.rag.vehicle_index",
            "src.llm.llamaindex_adapter",
            "src.agent.memory",
        ):
            with pytest.raises(ModuleNotFoundError):
                importlib.import_module(mod_name)

    def test_bge_embedding_model_decoupled_from_llamaindex(self):
        from src.rag.embeddings import BGEEmbeddingModel

        bases = [b.__name__ for b in BGEEmbeddingModel.__mro__]
        assert "BaseEmbedding" not in bases
        for method_name in (
            "get_text_embedding",
            "get_query_embedding",
            "aget_query_embedding",
            "get_text_embedding_batch",
        ):
            assert hasattr(BGEEmbeddingModel, method_name)


class TestTradeInValuationTool:
    def test_estimate_trade_in_valuation_known_model(self):
        from src.agent.langchain_tools import estimate_trade_in_valuation_tool

        raw = estimate_trade_in_valuation_tool.invoke(
            {"car_model": "Model Y", "vehicle_age_years": 2.0, "mileage_wan_km": 3.5}
        )
        data = json.loads(raw)
        assert data["found"] is True
        assert 0.0 < data["one_year_residual_rate"] <= 1.0
        assert 0.0 < data["three_year_residual_rate"] <= 1.0
        assert data["vehicle_age_years"] == 2.0
        assert data["mileage_wan_km"] == 3.5
        assert data["wholesale_price_range_wan"]
        assert data["retail_price_range_wan"]

    def test_estimate_trade_in_valuation_empty_or_invalid(self):
        from src.agent.langchain_tools import estimate_trade_in_valuation_tool

        raw = estimate_trade_in_valuation_tool.invoke({"car_model": "   "})
        data = json.loads(raw)
        assert data["found"] is False

    def test_pricing_finance_skill_includes_trade_in_and_respects_cap(self):
        from src.agent.voice_skills import VOICE_SKILLS, route_voice_skill

        skill = VOICE_SKILLS["pricing_finance"]
        assert "estimate_trade_in_valuation" in skill.tool_names
        assert len(skill.tool_names) <= 4

        routed = route_voice_skill("我有一台老车想置换估价，大概能值多少钱")
        assert routed.skill.name == "pricing_finance"

    def test_voice_mode_defaults_preserved(self):
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        from src.agent.langgraph_agent import LangGraphSalesAgent
        from src.agent.voice.pipeline import VoicePipeline

        agent = LangGraphSalesAgent(llm=FakeListChatModel(responses=["ok"]))
        assert agent.voice_mode is False

        src_pipeline = inspect.getsource(VoicePipeline)
        assert "voice_mode=True" in src_pipeline


class TestRagasEvalWrapper:
    def test_summarize_splits_scored_and_nan(self):
        import pandas as pd

        from src.eval.ragas_eval import summarize

        fake_df = pd.DataFrame(
            {
                "user_input": ["q1", "q2"],
                "retrieved_contexts": [["c1"], ["c2"]],
                "response": ["a1", "a2"],
                "reference": ["r1", "r2"],
                "faithfulness": [0.9, float("nan")],
                "answer_relevancy": [0.8, 0.6],
                "context_recall": [float("nan"), float("nan")],
            }
        )
        fake_res = SimpleNamespace(to_pandas=lambda: fake_df)
        summary = summarize(fake_res)

        assert summary["faithfulness"]["score"] == pytest.approx(0.9)
        assert summary["faithfulness"]["n_scored"] == 1
        assert summary["faithfulness"]["n_failed"] == 1
        assert summary["answer_relevancy"]["score"] == pytest.approx(0.7)
        assert summary["context_recall"]["score"] is None
        assert summary["context_recall"]["n_failed"] == 2

    def test_benchmark_ragas_mock_mode(self, tmp_path):
        from scripts.benchmark_ragas import run_benchmark

        out_file = tmp_path / "ragas_mock.json"
        report = run_benchmark(sample_limit=3, system_name="fusion", use_mock=True, out_path=out_file)

        assert out_file.exists()
        assert report["mode"] == "mock"
        assert report["n_samples"] == 3
        for metric in ("faithfulness", "answer_relevancy", "context_recall"):
            assert metric in report["scores"]
            assert len(report["scores"][metric]["ci_95"]) == 2
