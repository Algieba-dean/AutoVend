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
    engine = QueryTransformationEngine()
    hyde_doc = engine.generate_hyde_doc("20万左右 纯电SUV")
    assert "【目标车型规格文档】" in hyde_doc
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
