"""
Unit tests for Parent-Child Document Retriever (src/retrieval/parent_child_retriever.py).
Verifies:
- Child chunk precise matching expands to complete Parent chunk
- Atomic Markdown tables recalled without loss of structure or truncation
- Deduplication of parent documents across multiple matching children
- Rich context formatting for LLM generation
- End-to-end integration with LayoutAwareParser on real vehicle PDF
"""

from pathlib import Path
import pytest

from src.ingestion.hierarchical_chunker import (
    Chunk,
    ChunkType,
    HierarchicalChunker,
)
from src.ingestion.layout_parser import LayoutAwareParser, ParsedDocument
from src.retrieval.parent_child_retriever import (
    ParentChildRetriever,
    ParentChildSearchResponse,
    SimpleVectorIndex,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_SAMPLE_PATH = _PROJECT_ROOT / "data" / "sample_specs" / "xiaomi_su7_ultra_specs.pdf"


def test_parent_child_retrieval_flow():
    retriever = ParentChildRetriever()

    # Create synthetic parent and children
    p1 = Chunk(
        chunk_id="parent_powertrain_01",
        content="【章节: 动力性能 | 车型: 小米SU7 Ultra】\n全系标配三电机驱动，综合功率达到1138kW（1548马力）。配备自研V8s超级电机，转速高达27200rpm，0-100km/h加速时间为1.98秒，最高时速达到350km/h。采用全铝合金双叉臂独立前悬架与五连杆后悬架。",
        chunk_type=ChunkType.PARENT,
        metadata={"vehicle_model": "小米SU7 Ultra", "topic": "powertrain"},
    )
    c1 = Chunk(
        chunk_id="c_01",
        content="[小米SU7 Ultra > 动力性能]\n0-100km/h加速时间为1.98秒，最高时速达到350km/h，搭载三电机1548马力。",
        chunk_type=ChunkType.CHILD,
        parent_id="parent_powertrain_01",
        metadata={"vehicle_model": "小米SU7 Ultra"},
    )
    c2 = Chunk(
        chunk_id="c_02",
        content="[小米SU7 Ultra > 动力性能]\n配备自研V8s超级电机，转速高达27200rpm，全铝合金双叉臂悬架。",
        chunk_type=ChunkType.CHILD,
        parent_id="parent_powertrain_01",
        metadata={"vehicle_model": "小米SU7 Ultra"},
    )
    p1.child_ids = ["c_01", "c_02"]

    retriever.index_chunks({
        "parents": [p1],
        "children": [c1, c2],
    })

    # Search for "1.98秒" (present in child c1)
    response = retriever.search(query="小米SU7 Ultra 0-100加速 1.98秒", top_k_parents=2)

    assert isinstance(response, ParentChildSearchResponse)
    assert len(response.results) == 1

    top_result = response.results[0]
    assert top_result.parent_id == "parent_powertrain_01"
    # Returns the full parent context (~1000 tokens)
    assert "综合功率达到1138kW" in top_result.content
    assert "全铝合金双叉臂独立前悬架" in top_result.content
    assert top_result.score > 0.3

    # Matched children contains c1
    matched_ids = [m.chunk.chunk_id for m in top_result.matched_children]
    assert "c_01" in matched_ids


def test_parent_deduplication_and_diversity_bonus():
    retriever = ParentChildRetriever()

    p = Chunk(
        chunk_id="parent_battery_01",
        content="【章节: 电池技术 | 车型: 小米SU7 Ultra】\n宁德时代麒麟II电池，容量93.7kWh，支持5.2C超充，峰值放电1330kW，11分钟充至80%。",
        chunk_type=ChunkType.PARENT,
    )
    # Multiple children pointing to the same parent
    c1 = Chunk(
        chunk_id="c_bat_1",
        content="[小米SU7 Ultra > 电池] 麒麟II电池 5.2C超充 11分钟",
        chunk_type=ChunkType.CHILD,
        parent_id="parent_battery_01",
    )
    c2 = Chunk(
        chunk_id="c_bat_2",
        content="[小米SU7 Ultra > 电池] 容量93.7kWh 峰值放电1330kW",
        chunk_type=ChunkType.CHILD,
        parent_id="parent_battery_01",
    )
    p.child_ids = [c1.chunk_id, c2.chunk_id]

    retriever.index_chunks({"parents": [p], "children": [c1, c2]})

    # Query matching both children
    resp = retriever.search(query="麒麟II电池 5.2C超充 93.7kWh 容量")
    # Must deduplicate to exactly 1 parent result
    assert len(resp.results) == 1
    res = resp.results[0]
    assert res.parent_id == "parent_battery_01"
    assert len(res.matched_children) >= 2


def test_table_retrieval_returns_full_markdown():
    # End-to-end test on the actual PDF
    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(PDF_SAMPLE_PATH)

    retriever = ParentChildRetriever()
    retriever.index_document(doc)

    # Search for specific sensor "LiDAR"
    resp = retriever.search(query="LiDAR 128-beam Hesai AT128 激光雷达")

    assert len(resp.results) >= 1
    found_table = False
    for r in resp.results:
        if r.is_table and "LiDAR" in r.content:
            found_table = True
            # The returned context is the ENTIRE Markdown table including header & all rows!
            assert "| Sensor Type | Quantity | Detection Range | Key Supplier / Model |" in r.content
            assert "| --- | --- | --- | --- |" in r.content
            assert "NVIDIA DRIVE Orin-X" in r.content
            assert "Continental 4D mmWave" in r.content
            assert "【结构化元数据】" in r.content
            break

    assert found_table, "Expected query for LiDAR to retrieve full structured sensor table."


def test_llm_context_formatting():
    retriever = ParentChildRetriever()
    p1 = Chunk(
        chunk_id="p1",
        content="小米SU7 Ultra技术参数内容",
        chunk_type=ChunkType.PARENT,
        metadata={"is_table": False},
    )
    c1 = Chunk(chunk_id="c1", content="SU7 Ultra技术参数", chunk_type=ChunkType.CHILD, parent_id="p1")
    retriever.index_chunks({"parents": [p1], "children": [c1]})

    resp = retriever.search(query="SU7 Ultra")
    llm_context = resp.format_llm_context()

    assert "### [参考资料 1]" in llm_context
    assert "小米SU7 Ultra技术参数内容" in llm_context


def test_sentence_transformer_encode_support():
    class MockSentenceTransformer:
        def encode(self, texts):
            # Returns simple 3D mock embeddings
            if isinstance(texts, str):
                return [0.5, 0.5, 0.5]
            return [[0.1 * i, 0.2 * i, 0.3 * i] for i in range(len(texts))]

    mock_model = MockSentenceTransformer()
    index = SimpleVectorIndex(embedding_model=mock_model)

    c1 = Chunk(chunk_id="c1", content="易四方电机", chunk_type=ChunkType.CHILD, parent_id="p1")
    c2 = Chunk(chunk_id="c2", content="云辇系统", chunk_type=ChunkType.CHILD, parent_id="p1")
    index.add_chunks([c1, c2])

    assert len(index.embeddings) == 2
    # Second add with duplicate chunk should be skipped
    index.add_chunks([c1])
    assert len(index.embeddings) == 2

    results = index.search(query="易四方", top_k=2)
    assert len(results) == 2


def test_byd_yangwang_u9_retrieval_returns_full_markdown():
    u9_path = _PROJECT_ROOT / "data" / "sample_specs" / "byd_yangwang_u9_specs.pdf"
    assert u9_path.exists()

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(u9_path)

    retriever = ParentChildRetriever()
    retriever.index_document(doc)

    # Search for DiSus-X / 云辇-X
    resp = retriever.search(query="DiSus-X 云辇-X 2.36s 易四方四电机")

    assert len(resp.results) >= 1
    found_u9_table = False
    for r in resp.results:
        if r.is_table and ("DiSus-X" in r.content or "云辇-X" in r.content or "e4 Quad-Motor" in r.content):
            found_u9_table = True
            assert "| System / Module | Technical Specification | Rating / Value | Operating Regime |" in r.content
            assert "1306 PS" in r.content or "2.36 s" in r.content
            assert "【结构化元数据】" in r.content
            break

    assert found_u9_table, "Expected query to retrieve full un-truncated U9 powertrain/chassis markdown table."
