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
        assert compressed.compression_ratio < 1.0

    def test_markdown_table_preserved_without_shredding(self):
        """Markdown tables must NOT be split by pipe characters into isolated cell fragments."""
        table_snippet = (
            "以下是两款配置的核心技术规格：\n"
            "| 车型 | 纯电续航 | 零百加速 | 指导价 |\n"
            "| 小米SU7 标准版 | 700km | 5.28s | 21.59万 |\n"
            "| 小米SU7 Max | 800km | 2.78s | 29.99万 |\n"
            "全系标配高通8295智能座舱芯片。"
        )
        sentences = ContextCompressor.split_sentences(table_snippet)
        # Table rows must be preserved as whole rows, not shredded by '|'
        assert any("| 车型 | 纯电续航 | 零百加速 | 指导价 |" in s for s in sentences)
        assert any("| 小米SU7 标准版 | 700km | 5.28s | 21.59万 |" in s for s in sentences)
        assert any("| 小米SU7 Max | 800km | 2.78s | 29.99万 |" in s for s in sentences)

        compressed = ContextCompressor.compress_snippet(
            table_snippet,
            query_text="续航和零百加速",
            max_length=300,
        )
        assert "| 小米SU7" in compressed.compressed_text
        assert "700km" in compressed.compressed_text

    def test_marketing_fluff_grammar_preservation(self):
        """Marketing cleaning must not leave ungrammatical dangling clauses."""
        text = "搭载了华为被业界誉为遥遥领先的鸿蒙座舱，整体操作非常流畅。"
        cleaned = ContextCompressor.clean_marketing_fluff(text)
        assert "遥遥领先" not in cleaned
        assert "被业界誉为的" not in cleaned  # Ungrammatical fragment eliminated
        assert "搭载了华为鸿蒙座舱" in cleaned or "鸿蒙座舱" in cleaned

    def test_marketing_fluff_preserved_when_explicitly_queried(self):
        """When query explicitly searches for a marketing term, evidence must not be discarded."""
        text = "发布会上宣布该车型在智能驾驶领域遥遥领先，并且配备了双Orin-X芯片。"
        # Query specifically mentions 遥遥领先
        cleaned = ContextCompressor.clean_marketing_fluff(text, query_text="哪款车自称遥遥领先")
        assert "遥遥领先" in cleaned  # Kept as key search evidence
        assert "双Orin-X芯片" in cleaned



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

        score_a = RankRefiner.calculate_spec_score(car_a, "25万以内 纯电", {"price": "25万以内"})
        score_b = RankRefiner.calculate_spec_score(car_b, "25万以内 纯电", {"price": "25万以内"})

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
            constraints={"price": "25万左右", "seat_layout": "6座"},
        )

        # Budget & 6-seat match should win top rank
        assert reranked[0].car_model == "Budget Match"


class TestRefactoredArchitectureSolutions:
    """
    Verification tests for production-grade refactor solutions from
    docs/rag/04_architecture_refactor_solutions.md:
    Phase 1 (P0): HyDE poisoning cut, DLQ error recording, Idempotent Doc ID, SQLite FTS5 BM25.
    Phase 2 (P1): 3-tier caching entity check, Entity-Scoped Context Retrieval, NumPy Vectorized Cosine.
    Phase 3 (P2): ONNX Cross-Encoder Sigmoid calibration, Gaussian smooth decay price fit.
    Phase 4 (P3): Pydantic V2 schema governance, Audit sampling & RAGAS eval judge monitoring.
    """

    def test_hyde_strict_llm_prevents_poisoning(self):
        engine = QueryTransformationEngine(llm=None)
        # Without LLM, returns None unconditionally to prevent semantic hallucination poisoning
        assert engine.generate_hyde_doc("五菱宏光Mini 买菜车") is None
        assert engine.generate_hyde_doc("五菱宏光Mini 买菜车", strict_llm=True) is None

    def test_dlq_recording_on_embedding_failure(self, tmp_path):
        import json
        from src.rag.index_builder import IndexDLQ

        dlq_dir = str(tmp_path / "dlq")
        dlq = IndexDLQ(dlq_dir=dlq_dir)
        dlq.record_failure(
            task_type="VECTOR_EMBEDDING",
            payload={"batch_index": 2, "texts": ["test text"]},
            error_msg="Connection reset by peer",
        )

        dlq_file = tmp_path / "dlq" / "index_builder_dlq.jsonl"
        assert dlq_file.exists()
        with open(dlq_file, "r", encoding="utf-8") as f:
            line = f.readline()
            data = json.loads(line)
            assert data["task_type"] == "VECTOR_EMBEDDING"
            assert "Connection reset" in data["error_msg"]

    def test_idempotent_doc_id_generation(self):
        from src.rag.vector_store import generate_vehicle_doc_id

        id1 = generate_vehicle_doc_id("Tesla-Model Y")
        id2 = generate_vehicle_doc_id("Tesla-Model Y")
        id3 = generate_vehicle_doc_id("BMW-X3")

        assert id1 == id2
        assert id1.startswith("veh_")
        assert len(id1) == 20  # "veh_" (4) + 16 hex chars
        assert id1 != id3

    def test_sqlite_fts5_bm25_search(self):
        from src.filter.vehicle_db import VehicleDB
        from src.retrieval.bm25_index import SQLiteFTS5Index

        db = VehicleDB()
        fts_index = SQLiteFTS5Index(db=db)
        results = fts_index.search("SUV", top_k=5)
        # Should return non-empty valid list of (car_model, score) pairs
        assert isinstance(results, list)
        assert len(results) > 0
        assert isinstance(results[0][0], str)
        assert isinstance(results[0][1], float)
        assert results[0][1] >= 0.0

    def test_vectorized_cosine_search(self):
        import numpy as np
        import pytest
        from src.retrieval.parent_child_retriever import vectorized_cosine_search

        q = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        m = np.array(
            [
                [1.0, 0.0, 0.0],  # index 0: similarity = 1.0
                [0.0, 1.0, 0.0],  # index 1: similarity = 0.0
                [0.7071, 0.7071, 0.0],  # index 2: similarity ≈ 0.707
            ],
            dtype=np.float32,
        )

        ranked = vectorized_cosine_search(q, m, top_k=2)
        assert len(ranked) == 2
        assert ranked[0][0] == 0
        assert pytest.approx(ranked[0][1], 0.01) == 1.0
        assert ranked[1][0] == 2
        assert pytest.approx(ranked[1][1], 0.01) == 0.707

    def test_entity_scoped_context_isolation(self):
        from src.ingestion.hierarchical_chunker import Chunk, ChunkType
        from src.retrieval.parent_child_retriever import (
            format_isolated_llm_context,
            retrieve_multi_vehicle_context,
        )

        class MockParentChildRetriever:
            def search(self, query, filter_metadata=None, top_k_parents=2):
                model = filter_metadata.get("car_model") if filter_metadata else "Default"
                chunk = Chunk(
                    chunk_id=f"chk_{model}",
                    content=f"这是【{model}】的专属电池与动力系统测评报告。",
                    chunk_type=ChunkType.PARENT,
                    parent_id=f"par_{model}",
                    metadata={"car_model": model},
                )
                return [chunk]

        scoped = retrieve_multi_vehicle_context(
            query="电池寿命",
            car_models=["Tesla-Model Y", "Xiaomi-SU7"],
            parent_child_retriever=MockParentChildRetriever(),
            top_k_per_vehicle=1,
        )

        assert "Tesla-Model Y" in scoped
        assert "Xiaomi-SU7" in scoped
        assert len(scoped["Tesla-Model Y"]) == 1
        assert "Tesla-Model Y" in scoped["Tesla-Model Y"][0].content

        formatted_md = format_isolated_llm_context(scoped)
        assert "### 车型: 【Tesla-Model Y】专属参考资料:" in formatted_md
        assert "### 车型: 【Xiaomi-SU7】专属参考资料:" in formatted_md

    def test_onnx_cross_encoder_and_gaussian_fit(self):
        from src.rag_service.onnx_reranker import OnnxCrossEncoderReranker
        from src.rag_service.reranker import calculate_gaussian_price_fit

        reranker = OnnxCrossEncoderReranker()
        scores = reranker.score_pairs("纯电SUV", ["Tesla Model Y 纯电SUV 大空间", "柴油重卡"])
        assert len(scores) == 2
        assert 0.0 <= scores[0] <= 1.0
        assert scores[0] > scores[1]

        # Gaussian budget decay tests
        # 1. On or under budget -> exactly 1.0
        assert calculate_gaussian_price_fit(20.0, 25.0) == 1.0
        assert calculate_gaussian_price_fit(25.0, 25.0) == 1.0

        # 2. Over budget 10% (27.5万 vs 25万) -> smooth decay ~0.85
        fit_10pct = calculate_gaussian_price_fit(27.5, 25.0)
        assert 0.80 < fit_10pct < 0.90

        # 3. Over budget 50% (37.5万 vs 25万) -> non-linear cliff decay < 0.05
        fit_50pct = calculate_gaussian_price_fit(37.5, 25.0)
        assert fit_50pct < 0.05

    def test_precise_labels_schema_governance(self):
        from src.models.vehicle import PreciseLabels

        labels = PreciseLabels(
            brand="特斯拉",
            car_model="Model 3 焕新版",
            vehicle_category_bottom="中型车",
            powertrain_type="纯电动",
            price="23.19-27.19万",
            wheelbase="2875",
            horsepower="299",
            zero_to_one_hundred_km_h_acceleration_time="6.1秒",
            driving_range="606km",
        )

        assert labels.price_min_wan == 23.19
        assert labels.price_max_wan == 27.19
        assert labels.wheelbase_mm == 2875
        assert labels.horsepower_ps == 299
        assert labels.acceleration_0_100_s == 6.1
        assert labels.electric_range_km == 606

    def test_rag_eval_monitor_audit_queue_and_ragas(self):
        from src.rag_service.eval_monitor import RAGEvalMonitor

        # 100% sample rate for unit test verification
        monitor = RAGEvalMonitor(audit_sample_rate=1.0)
        alerts = monitor.record_retrieval(
            query_text="请问蔚来ES6续航多少",
            results=[{"car_model": "NIO-ES6", "score": 0.88}],
            candidate_count=5,
            latency_ms=15.0,
        )

        assert len(monitor.audit_queue) == 1
        audit_entry = monitor.audit_queue[0]
        assert audit_entry["query_text"] == "请问蔚来ES6续航多少"
        assert "NIO-ES6" in audit_entry["result_models"]

        # RAGAS metrics evaluation
        ragas_result = monitor.evaluate_ragas_sample(
            query="蔚来ES6 纯电续航",
            retrieved_contexts=["蔚来ES6搭载100kWh电池，CLTC纯电续航625km。"],
            response="蔚来ES6的CLTC纯电续航为625公里。",
            candidate_models=["NIO-ES6"],
        )
        assert ragas_result["faithfulness"] >= 0.8
        assert ragas_result["context_relevancy"] >= 0.8
        assert ragas_result["contamination_detected"] is False

    def test_ragas_detects_cross_entity_contamination_and_alerts(self):
        from src.rag_service.eval_monitor import RAGEvalMonitor

        monitor = RAGEvalMonitor()
        # Mismatched context: query & candidate is Xiaomi-SU7, but retrieved context has Tesla Model Y
        contaminated_sample = monitor.evaluate_ragas_sample(
            query="小米SU7 续航与价格",
            retrieved_contexts=["Tesla Model Y 搭载双电机全轮驱动，百公里加速3.7秒。"],
            response="小米SU7百公里加速3.7秒。",
            candidate_models=["Xiaomi-SU7"],
        )
        assert contaminated_sample["contamination_detected"] is True
        assert len(contaminated_sample["alerts"]) == 1
        assert contaminated_sample["alerts"][0].alert_type == "CROSS_ENTITY_CONTAMINATION"

    def test_semantic_cache_entity_isolation(self):
        import numpy as np
        from src.retrieval.tiered_engine import SemanticQueryCache

        class MockEmbeddingModel:
            def encode(self, text):
                # Returns identical vector to simulate very high cosine similarity (1.0)
                return np.array([1.0, 0.0, 0.0], dtype=np.float32)

        cache = SemanticQueryCache(similarity_threshold=0.96, embedding_model=MockEmbeddingModel())
        cache.put("小米SU7 续航是多少", "SU7_CACHE_VALUE")

        # Query for Model 3 has cosine similarity 1.0, but entity differs (Model 3 vs SU7) -> MUST NOT HIT!
        miss_res = cache.get("特斯拉Model 3 续航是多少")
        assert miss_res is None

        # Query for SU7 with different phrasing has same entity -> SHOULD HIT!
        hit_res = cache.get("SU7 续航多少公里")
        assert hit_res == "SU7_CACHE_VALUE"

    def test_rank_refiner_batch_cross_encoder_scoring(self):
        from src.rag_service.onnx_reranker import OnnxCrossEncoderReranker
        from src.rag_service.reranker import RankRefiner
        from src.rag_service.schemas import VehicleSearchResult

        reranker = OnnxCrossEncoderReranker()
        results = [
            VehicleSearchResult(
                car_model="Tesla-Model Y",
                score=0.10,
                brand="特斯拉",
                text_snippet="Tesla Model Y 纯电SUV 大空间",
            ),
            VehicleSearchResult(
                car_model="Dongfeng-Truck",
                score=0.10,
                brand="东风",
                text_snippet="柴油重卡 载重30吨",
            ),
        ]

        refined = RankRefiner.refine("纯电SUV", results, top_k=2, cross_encoder=reranker)
        assert len(refined) == 2
        assert refined[0].car_model == "Tesla-Model Y"
        assert refined[0].score > refined[1].score

