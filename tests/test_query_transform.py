"""
Unit tests for Advanced Query Transformation Engine (src/retrieval/query_transform.py).
"""

from src.retrieval.query_transform import QueryTransformationEngine


def test_query_rewriting_coreference():
    """Test coreference resolution and noise stripping in query rewriting."""
    engine = QueryTransformationEngine()
    history = "User: 我想看特斯拉 Model Y\nAssistant: 为您推荐 Model Y"
    raw_query = "请问麻烦问一下它后备箱多大？"

    rewritten = engine.rewrite_query(raw_query, history)
    assert "特斯拉" in rewritten or "Model Y" in rewritten or "它" not in rewritten
    assert "麻烦问一下" not in rewritten


def test_query_expansion():
    """Test query expansion with automotive domain synonyms."""
    engine = QueryTransformationEngine()
    expanded = engine.expand_query("我想找一款适合家的奶爸车")
    assert "大空间" in expanded or "SUV" in expanded or "家庭" in expanded


def test_hyde_document_generation():
    """Test HyDE hypothetical document generation."""
    # Without active LLM, returns None to avoid hallucination poisoning
    engine_no_llm = QueryTransformationEngine()
    assert engine_no_llm.generate_hyde_doc("20万左右 纯电SUV") is None

    # With active LLM, returns generated hypothetical spec doc
    class MockLLM:
        def is_available(self):
            return True

        def complete(self, prompt):
            return "【目标车型规格文档】 预算20万纯电SUV车型推荐，具备高压快充与大空间。"

    engine_with_llm = QueryTransformationEngine(llm=MockLLM())
    hyde_doc = engine_with_llm.generate_hyde_doc("20万左右 纯电SUV")
    assert hyde_doc is not None
    assert "20万" in hyde_doc or "纯电" in hyde_doc


def test_multi_query_generation():
    """Test multi-query variation generation."""
    engine = QueryTransformationEngine()
    queries = engine.generate_multi_queries("德系 豪华轿车")
    assert len(queries) >= 2
    assert any("详细配置" in q for q in queries)


def test_sub_query_decomposition():
    """Test sub-query decomposition for comparative queries."""
    engine = QueryTransformationEngine()
    sub_qs = engine.decompose_sub_queries("对比理想L7和问界M7的续航与售价")
    assert len(sub_qs) == 2
    assert "理想L7" in sub_qs[0]
    assert "问界M7" in sub_qs[1]


def test_transform_all_pipeline():
    """Test transform_all master entry point."""
    engine = QueryTransformationEngine()
    res = engine.transform_all("对比理想L7和问界M7", "User: 选车")
    assert "rewritten_query" in res
    assert "hyde_document" in res
    assert "multi_queries" in res
    assert "sub_queries" in res
    assert len(res["sub_queries"]) == 2


def test_comparative_query_entity_isolation():
    """Test that comparative queries isolate entities and never collapse into self-comparison."""
    engine = QueryTransformationEngine()

    # Case 1: Single car in history, comparison query with two pronouns
    # MUST NOT replace both with Xiaomi SU7
    history_single = "User: 我刚看了小米SU7\nAssistant: 小米SU7性能很出色"
    query1 = "刚才提到的那款车和它相比，哪个续航更长？"
    rewritten1 = engine.rewrite_query(query1, history_single)
    # The comparison intent must NOT be collapsed into "小米SU7...和小米SU7相比"
    assert "小米SU7那款车和小米SU7相比" not in rewritten1
    assert "相比" in rewritten1

    # Case 2: Query already mentions Model Y explicitly, history mentions Model Y and 小米SU7
    # MUST NOT replace pronoun with Model Y (causing Model Y vs Model Y)
    history_two = "User: 特斯拉Model Y 怎么样？\nAssistant: Model Y空间很大。\nUser: 那小米SU7呢？"
    query2 = "特斯拉Model Y和它相比，哪个加速更快？"
    rewritten2 = engine.rewrite_query(query2, history_two)
    assert "特斯拉Model Y和特斯拉Model Y相比" not in rewritten2
    assert "小米SU7" in rewritten2

    # Case 3: Two distinct cars in history, two distinct pronouns
    history_distinct = "User: 上次看的蔚来ES6不错\nUser: 刚才看的小米SU7也很强"
    query3 = "上一款和刚才提到的那台相比，哪个后备箱更大？"
    rewritten3 = engine.rewrite_query(query3, history_distinct)
    assert "蔚来ES6" in rewritten3
    assert "小米SU7" in rewritten3
