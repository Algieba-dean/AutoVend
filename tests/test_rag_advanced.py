"""
Tests for Advanced RAG Module (Pillar 1).
Verifies:
1. Query rewriting with coreference resolution and implicit scenario intent enrichment.
2. Multi-perspective and multi-entity sub-query decomposition.
3. Context compression and hallucination-grounded fluff pruning.
4. Tabular spec reranking with budget penalty/reward and dynamic intent weighting.
5. Integration with RAGService.
"""

from src.rag_service.reranker import RankRefiner, parse_budget_limit, parse_numeric_price_range
from src.rag_service.schemas import VehicleSearchResult
from src.retrieval.compression import CompressedContext, ContextCompressor
from src.retrieval.query_transform import QueryTransformationEngine


class TestAdvancedQueryTransformation:
    def test_coreference_and_implicit_enrichment(self):
        engine = QueryTransformationEngine()
        history = "User: 我正在看蔚来ES6和理想L7\nAssistant: 蔚来ES6是纯电SUV，理想L7是增程式SUV。"

        # Test coreference pronoun resolution
        raw_query = "请问这车适合二胎家庭跑长途吗？"
        rewritten = engine.rewrite_query(raw_query, history)
        assert "理想L7" in rewritten or "蔚来ES6" in rewritten
        assert "请问" not in rewritten
        # Implicit intent scenario enrichment
        assert "大空间" in rewritten or "6座" in rewritten or "长续航" in rewritten

    def test_winter_and_camping_implicit_enrichment(self):
        engine = QueryTransformationEngine()
        res_winter = engine.rewrite_query("在东北冬天开着省心吗")
        assert "热泵空调" in res_winter or "电池低温加热" in res_winter or "四驱" in res_winter

        res_camp = engine.rewrite_query("打算周末去露营野营")
        assert "对外放电" in res_camp or "后备箱" in res_camp

    def test_multi_entity_comparison_decomposition(self):
        engine = QueryTransformationEngine()
        sub_qs = engine.decompose_sub_queries("对比Model Y、蔚来ES6和极氪001的续航与售价")
        assert len(sub_qs) >= 3
        assert any("Model Y" in q for q in sub_qs)
        assert any("蔚来ES6" in q for q in sub_qs)
        assert any("极氪001" in q for q in sub_qs)

    def test_multi_perspective_decomposition(self):
        engine = QueryTransformationEngine()
        query = "预算25万适合家用二胎、经常自驾游且注重智驾的新能源车"
        perspectives = engine.decompose_multi_perspective(query)
        assert len(perspectives) >= 3

        p_types = [p["perspective"] for p in perspectives]
        assert "space_and_comfort" in p_types
        assert "range_and_energy" in p_types
        assert "intelligent_driving" in p_types
        assert "budget_and_value" in p_types


class TestContextCompressionAndPruning:
    def test_marketing_fluff_pruning(self):
        noisy_text = "遥遥领先！地表最强底盘配置。官方指导价24.98万元，CLTC纯电续航650km。极致奢华，降维打击同级！"
        cleaned = ContextCompressor.clean_marketing_fluff(noisy_text)
        assert "遥遥领先" not in cleaned
        assert "地表最强" not in cleaned
        assert "极致奢华" not in cleaned
        assert "24.98万元" in cleaned
        assert "650km" in cleaned

    def test_compress_snippet_preserves_factual_specs(self):
        raw_snippet = (
            "这款车拥有秒杀同级的无敌奢华体验！"
            "搭载双电机四驱系统，百公里加速仅需 3.8秒。"
            "配备 100kWh 大电池包，CLTC 综合续航达到 702km。"
            "全系标配激光雷达与双 Orin-X 芯片，支持城市高阶 NOA 辅助驾驶。"
            "售价区间为 22.99-29.99万元。买到就是赚到，绝对保值！"
        )
        compressed = ContextCompressor.compress_snippet(
            raw_snippet,
            query_text="续航和智驾怎么样",
            max_length=150,
        )
        assert isinstance(compressed, CompressedContext)
        assert compressed.compressed_length <= 150
        assert "702km" in compressed.compressed_text or "激光雷达" in compressed.compressed_text
        assert "买到就是赚到" not in compressed.compressed_text
        assert "秒杀同级" not in compressed.compressed_text
        assert compressed.compression_ratio < 1.0


class TestTabularSpecReranking:
    def test_price_range_and_budget_parsing(self):
        min_p, max_p = parse_numeric_price_range("21.59-29.99万元")
        assert min_p == 21.59
        assert max_p == 29.99

        b_limit = parse_budget_limit("25万以内")
        assert b_limit == 25.0

    def test_spec_score_reward_and_penalty(self):
        # Car A within budget (21.59万 vs 25万 budget)
        car_a = VehicleSearchResult(
            car_model="Car A",
            score=0.8,
            price="21.59万",
            powertrain_type="纯电动",
            metadata={"price": "21.59万", "powertrain_type": "纯电", "seat_layout": "5座"},
        )
        # Car B heavily exceeds budget (45万 vs 25万 budget)
        car_b = VehicleSearchResult(
            car_model="Car B",
            score=0.8,
            price="45.00万",
            powertrain_type="纯电动",
            metadata={"price": "45.00万", "powertrain_type": "纯电", "seat_layout": "5座"},
        )

        score_a = RankRefiner.calculate_spec_score(car_a, "25万以内 纯电", {"prize": "25万以内"})
        score_b = RankRefiner.calculate_spec_score(car_b, "25万以内 纯电", {"prize": "25万以内"})

        assert score_a > score_b
        assert score_b < 0.50

    def test_refine_reranks_candidates_by_spec_fit(self):
        car_cheap = VehicleSearchResult(
            car_model="Budget Match",
            score=0.04,  # Lower RRF rank score
            price="22万",
            metadata={"price": "22万", "seat_layout": "6座", "powertrain_type": "插电混动"},
            text_snippet="6座大空间 插电混动",
        )
        car_expensive = VehicleSearchResult(
            car_model="Pricey Car",
            score=0.08,  # Higher initial RRF score
            price="60万",
            metadata={"price": "60万", "seat_layout": "5座", "powertrain_type": "燃油"},
            text_snippet="燃油轿跑 5座",
        )

        reranked = RankRefiner.refine(
            query_text="25万左右 6座 混动",
            results=[car_expensive, car_cheap],
            top_k=2,
            constraints={"prize": "25万左右", "seat_layout": "6座"},
        )

        # Budget & 6-seat match should win top rank
        assert reranked[0].car_model == "Budget Match"
