"""
Unit tests for the 7 Code Review fixes (/boost).
"""

import pytest


# ---------------------------------------------------------------------------
# 1. onnx_reranker: Token-overlap lexical heuristic description & scoring
# ---------------------------------------------------------------------------
def test_onnx_reranker_lexical_fallback_and_honesty():
    from src.rag_service.onnx_reranker import OnnxCrossEncoderReranker

    reranker = OnnxCrossEncoderReranker()
    scores = reranker.score_pairs("纯电SUV", ["Tesla Model Y 纯电SUV 大空间", "柴油重卡"])
    assert len(scores) == 2
    assert 0.0 <= scores[0] <= 1.0
    assert 0.0 <= scores[1] <= 1.0
    assert scores[0] > scores[1]

    # Verify docstring honesty (no 'calibrated cross-attention' claims)
    assert "cross-attention" not in reranker.score_pairs.__doc__.lower()
    assert "lexical heuristic" in reranker.score_pairs.__doc__.lower()


# ---------------------------------------------------------------------------
# 2. embeddings: Explicit EmbeddingDegradedError instead of silent [1.0, 0...]
# ---------------------------------------------------------------------------
def test_dummy_sentence_transformer_raises_degraded_error():
    from src.rag.embeddings import EmbeddingDegradedError, _DummySentenceTransformer

    dummy = _DummySentenceTransformer(dimension=1024)
    with pytest.raises(EmbeddingDegradedError) as exc_info:
        dummy.encode("测试文本")
    assert "silent cosine distance poisoning" in str(exc_info.value) or "degraded" in str(exc_info.value).lower()

    with pytest.raises(EmbeddingDegradedError):
        dummy._generate_vector("测试文本")


def test_hybrid_pipeline_fast_cuts_to_bm25_when_degraded():
    from unittest.mock import MagicMock

    from src.filter.filter_engine import FilterResult
    from src.models.vehicle import PreciseLabels, Vehicle
    from src.retrieval.hybrid_pipeline import HybridPipeline, HybridPipelineResult

    class DegradedRetriever:
        class FakeEmbedding:
            is_degraded = True
        embedding_model = FakeEmbedding()

    class MockSparseIndex:
        def search(self, query, top_k=5):
            return [("Tesla-Model Y", 8.5)]

    mock_db = MagicMock()
    mock_db.get_vehicle.return_value = Vehicle(
        car_model="Tesla-Model Y",
        precise_labels=PreciseLabels(price="30万"),
    )

    pipeline = HybridPipeline(
        db=mock_db,
        retriever=DegradedRetriever(),
        sparse_index=MockSparseIndex(),
    )
    res = HybridPipelineResult()
    filter_res = FilterResult(car_models=["Tesla-Model Y"], applied_query={}, degrade_level=0, total_candidates=1)
    pipeline._semantic_rerank("纯电SUV", filter_res, top_k=5, result=res)
    assert res.search_response is not None
    assert res.sparse_result_count == 1
    assert res.search_response.total_count == 1


# ---------------------------------------------------------------------------
# 3. query_transform: Comparison query entity isolation & pronoun preservation
# ---------------------------------------------------------------------------
def test_query_transform_comparison_pronoun_isolation():
    from src.retrieval.query_transform import QueryTransformationEngine

    engine = QueryTransformationEngine()

    # Case A: Single car in history, comparison query with two pronouns
    history = "User: 我想看小米SU7\nAssistant: 为您推荐 小米SU7"
    raw = "刚才提到的那款车和它相比，哪个续航更长？"
    rewritten = engine.rewrite_query(raw, history)
    # MUST NOT collapse both into Xiaomi SU7
    assert "小米SU7那款车和小米SU7相比" not in rewritten
    assert "相比" in rewritten

    # Case B: Query already has Model Y explicitly
    history_b = "User: 看下Model Y\nUser: 又看下小米SU7"
    raw_b = "Model Y和它相比哪个提速更快？"
    rewritten_b = engine.rewrite_query(raw_b, history_b)
    assert "Model Y和Model Y相比" not in rewritten_b
    assert "小米SU7" in rewritten_b


# ---------------------------------------------------------------------------
# 4. adapters: No KV structured pollution in natural language query
# ---------------------------------------------------------------------------
def test_adapters_clean_natural_language_query():
    from types import SimpleNamespace

    from src.retrieval.adapters import needs_to_filters, needs_to_query_text

    explicit = SimpleNamespace(
        vehicle_category_bottom="中型SUV",
        powertrain_type="纯电动",
        brand="蔚来",
        price="30-40万",
    )
    implicit = SimpleNamespace(
        comfort_level="High",
        smartness="Advanced",
        space="Large",
        family_friendliness="High",
    )

    query_text = needs_to_query_text(explicit, implicit)
    # Absolutely NO raw KV pair pollution like "comfort_level:High" in query text
    assert "comfort_level:High" not in query_text
    assert "smartness:Advanced" not in query_text
    assert ":" not in query_text
    assert "中型SUV" in query_text
    assert "纯电动" in query_text
    assert "蔚来" in query_text

    # Structured metadata should be accessible via needs_to_filters
    filters = needs_to_filters(explicit, implicit)
    assert filters["comfort_level"] == "High"
    assert filters["smartness"] == "Advanced"
    assert filters["brand"] == "蔚来"


# ---------------------------------------------------------------------------
# 5. vehicle: Typo cleaning & robust price range matching
# ---------------------------------------------------------------------------
def test_vehicle_clean_schema_and_price_range():
    from src.models.vehicle import PreciseLabels, Vehicle

    # 1. Pydantic schema is clean without typo fields
    labels = PreciseLabels(
        brand="小米",
        car_model="SU7",
        passenger_space_volume="3.5~4.5 cubic meter",
        voice_interaction="Yes",
        passability="High",
        cold_resistance="High",
        price="21.59-29.99万",
    )
    assert labels.passenger_space_volume == "3.5~4.5 cubic meter"
    assert labels.voice_interaction == "Yes"
    assert labels.passability == "High"
    assert labels.cold_resistance == "High"
    assert not hasattr(labels, "passenger_sapce_volume")
    assert not hasattr(labels, "voice_interfaction")

    # 2. Hyphen price range (21.59-29.99万)
    v_hyphen = Vehicle(car_model="SU7", precise_labels=labels)
    assert v_hyphen.get_price_range() == (215900, 299900)
    assert v_hyphen.matches_price_range(250000) is True
    assert v_hyphen.matches_price_range(25.0) is True  # in 万元
    assert v_hyphen.matches_price_range(100000) is False

    # 3. '到' price range (20万到30万)
    v_dao = Vehicle(car_model="SU7", precise_labels=PreciseLabels(price="20万到30万"))
    assert v_dao.get_price_range() == (200000, 300000)
    assert v_dao.matches_price_range(250000) is True

    # 4. '~' price range (30,000~40,000)
    v_tilde = Vehicle(car_model="Audi-A1", precise_labels=PreciseLabels(price="30,000~40,000"))
    assert v_tilde.get_price_range() == (30000, 40000)

    # 5. Silent pass-through bug fix: Missing price MUST return False, not True
    v_empty = Vehicle(car_model="NoPrice", precise_labels=PreciseLabels(price=""))
    assert v_empty.get_price_range() is None
    assert v_empty.matches_price_range(250000) is False
    assert v_empty.matches_price_range(25.0) is False


# ---------------------------------------------------------------------------
# 6. query_engine: Deprecation notice and backward compatibility
# ---------------------------------------------------------------------------
def test_legacy_query_engine_deprecation_notice():
    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        import importlib

        import backend.app.rag.query_engine
        importlib.reload(backend.app.rag.query_engine)
        assert any(
            "deprecated" in str(item.message).lower() for item in w
        )


# ---------------------------------------------------------------------------
# 7. tiered_engine: Fast-path colloquial spoken intent matching
# ---------------------------------------------------------------------------
def test_tiered_engine_colloquial_fast_path():
    from src.retrieval.tiered_engine import SpecIntentClassifier, TieredRetrievalEngine

    # SpecIntentClassifier handles colloquial queries without fragile regex failure
    res_acc1 = SpecIntentClassifier.classify("这车多久能到一百码")
    assert res_acc1 is not None and res_acc1[0] == "acceleration_0_100"

    res_acc2 = SpecIntentClassifier.classify("起步猛不猛")
    assert res_acc2 is not None and res_acc2[0] == "acceleration_0_100"

    res_price = SpecIntentClassifier.classify("这车多少钱能拿下来")
    assert res_price is not None and res_price[0] == "price"

    res_range = SpecIntentClassifier.classify("充满电能跑多远")
    assert res_range is not None and res_range[0] == "electric_range"

    res_charging = SpecIntentClassifier.classify("充到80%要几分钟")
    assert res_charging is not None and res_charging[0] == "charging_tech"

    # End-to-end Tier 0 fast path
    engine = TieredRetrievalEngine()
    t0_res = engine.search_tier0("SU7 Max多久能到一百码")
    assert t0_res is not None
    assert t0_res.tier == 0
    assert "2.78秒" in t0_res.facts_summary


# ---------------------------------------------------------------------------
# 8. Edge cases: Price range qualifiers, abbreviation dedup, and cargo lookup
# ---------------------------------------------------------------------------
def test_vehicle_price_range_advanced_edge_cases():
    from src.models.vehicle import PreciseLabels, Vehicle
    from src.rag_service.reranker import parse_numeric_price_range

    # 1. Price range with '起' must preserve upper bound (not drop to val * 5)
    v_range_qi = Vehicle(car_model="SU7", precise_labels=PreciseLabels(price="21.59-29.99万起"))
    assert v_range_qi.get_price_range() == (215900, 299900)
    assert v_range_qi.matches_price_range(250000) is True
    assert v_range_qi.matches_price_range(400000) is False
    assert v_range_qi.matches_price_range(350000, tolerance=0.1) is False

    # 2. Mixed units (200000-25万) must convert before min/max so min <= max
    v_mixed = Vehicle(car_model="Mixed", precise_labels=PreciseLabels(price="200000-25万"))
    assert v_mixed.get_price_range() == (200000, 250000)
    assert v_mixed.matches_price_range(220000) is True

    # 3. Open-ended upper bound (Above 100,000) matches luxury budgets without artificial 500k cap
    v_above = Vehicle(car_model="Audi-A8", precise_labels=PreciseLabels(price="Above 100,000"))
    assert v_above.get_price_range() == (100000, 100_000_000)
    assert v_above.matches_price_range(800000) is True

    # 4. Single price with '起'
    v_single_qi = Vehicle(car_model="SingleQi", precise_labels=PreciseLabels(price="15.98万起"))
    assert v_single_qi.get_price_range() == (159800, 100_000_000)
    assert v_single_qi.matches_price_range(180000) is True

    # 5. Invalid target prices
    assert v_range_qi.matches_price_range(0) is False
    assert v_range_qi.matches_price_range(-10) is False

    # 6. parse_numeric_price_range in reranker.py
    assert parse_numeric_price_range("21.59-29.99万起") == (21.59, 29.99)
    assert parse_numeric_price_range("200000-25万") == (20.0, 25.0)
    assert parse_numeric_price_range("Below 10,000") == (0.0, 1.0)
    assert parse_numeric_price_range("Above 100,000") == (10.0, 10000.0)


def test_query_transform_canonical_model_coreference():
    from src.retrieval.query_transform import QueryTransformationEngine

    engine = QueryTransformationEngine()

    # History mentions '特斯拉 Model Y' and later abbreviation 'Model Y' -> same car, MUST NOT self-compare
    history_abbrev = "User: 特斯拉 Model Y 续航多少？\nAssistant: Model Y 续航 554km。"
    q = "刚才提到的那款车和它相比，哪个续航更长？"
    rewritten = engine.rewrite_query(q, history_abbrev)
    assert "特斯拉 Model Y那款车和Model Y相比" not in rewritten
    assert "特斯拉 Model Y和Model Y相比" not in rewritten
    assert "相比" in rewritten

    # Demonstratives '那款车' and '这款车'
    history_two = "User: 看了极氪001\nUser: 又看了一眼小鹏G6"
    q_two = "那款车和这款车相比，哪个续航更长？"
    rewritten_two = engine.rewrite_query(q_two, history_two)
    assert "极氪001" in rewritten_two
    assert "小鹏G6" in rewritten_two


def test_tiered_engine_fast_path_cargo_and_colloquial_specs():
    from src.retrieval.tiered_engine import FastSpecIndex, SpecIntentClassifier

    # 1. FastSpecIndex lookup_exact_spec correctly maps cargo_volume to trunk_volume
    index = FastSpecIndex()
    index.db_records["小米SU7"] = {"brand": "小米", "trunk_volume": "517L"}
    res = index.lookup_exact_spec("小米SU7", "cargo_volume")
    assert res is not None
    assert res[0] == "后备箱容积"
    assert res[1] == "517L"

    # 2. SpecIntentClassifier colloquial queries
    assert SpecIntentClassifier.classify("能开多少码")[0] == "max_speed"
    assert SpecIntentClassifier.classify("最高跑多少")[0] == "max_speed"
    assert SpecIntentClassifier.classify("能不能坐7个人")[0] == "seat_layout"
    assert SpecIntentClassifier.classify("小米SU7后备箱多大")[0] == "cargo_volume"
    assert SpecIntentClassifier.classify("百公里几个油")[0] == "fuel_consumption"
    assert SpecIntentClassifier.classify("百公里电耗多少")[0] == "electric_consumption"

