"""
Unit tests for Hierarchical & Semantic Chunker (src/ingestion/hierarchical_chunker.py).
Verifies:
- Table independent chunking (atomic table preservation, no context mixture)
- Context enrichment (structured header metadata injection: model, section, bbox, page)
- Parent-child document splitting (parent ~1000 tokens, child ~200 tokens)
- Bidirectional linkage between parent and child chunks
- Multi-row table child generation with column headers
"""

from pathlib import Path
import pytest

from src.ingestion.hierarchical_chunker import (
    Chunk,
    ChunkType,
    HierarchicalChunker,
)
from src.ingestion.layout_parser import (
    BoundingBox,
    LayoutAwareParser,
    ParsedDocument,
    TableBlock,
    TextSection,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_SAMPLE_PATH = _PROJECT_ROOT / "data" / "sample_specs" / "xiaomi_su7_ultra_specs.pdf"


def test_token_estimation():
    text_cn = "小米SU7 Ultra搭载三电机动力总成，综合马力达到1548匹。"
    tokens_cn = Chunk.estimate_tokens(text_cn)
    assert 20 <= tokens_cn <= 45

    text_en = "Xiaomi SU7 Ultra features triple electric motors with 1548 horsepower."
    tokens_en = Chunk.estimate_tokens(text_en)
    assert 10 <= tokens_en <= 25

    assert Chunk.estimate_tokens("") == 0


def test_table_independent_chunking_and_context_enrichment():
    tbl = TableBlock(
        page_num=1,
        bbox=BoundingBox(50, 100, 500, 300, page=1),
        rows=[
            ["车型版本", "电机配置", "百公里加速", "最高车速"],
            ["SU7 Ultra", "三电机 (V8s+V8s+V6s)", "1.98s", "350km/h"],
            ["SU7 Max", "双电机 (V6s+V6)", "2.78s", "265km/h"],
        ],
        title="动力与加速对比表",
    )

    doc = ParsedDocument(
        title="小米SU7技术规格白皮书",
        vehicle_model="小米SU7 Ultra",
        tables=[tbl],
    )

    chunker = HierarchicalChunker(parent_max_tokens=1000, child_max_tokens=200)
    result = chunker.chunk_document(doc)

    # 1. Verify table chunk is atomic
    assert len(result["tables"]) == 1
    t_chunk = result["tables"][0]
    assert t_chunk.chunk_type == ChunkType.TABLE

    # 2. Verify Context Enrichment header injection
    content = t_chunk.content
    assert "【结构化元数据】" in content
    assert "• 车型/文档主题: 小米SU7 Ultra" in content
    assert "• 所属章节/功能模块: 动力与加速对比表" in content
    assert "• 所在页码: 第 1 页" in content
    assert "• 边框坐标 BBox: [50.0, 100.0, 500.0, 300.0]" in content
    assert "| 车型版本 | 电机配置 | 百公里加速 | 最高车速 |" in content
    assert "| SU7 Ultra | 三电机 (V8s+V8s+V6s) | 1.98s | 350km/h |" in content

    # 3. Verify Metadata fields
    assert t_chunk.metadata["is_table"] is True
    assert t_chunk.metadata["vehicle_model"] == "小米SU7 Ultra"
    assert t_chunk.metadata["row_count"] == 3
    assert t_chunk.metadata["col_count"] == 4

    # 4. Table acts as parent and has child chunks
    assert t_chunk in result["parents"]
    assert len(t_chunk.child_ids) > 0

    # 5. Verify child chunk contains column headers and rows
    table_children = [c for c in result["children"] if c.parent_id == t_chunk.chunk_id]
    assert len(table_children) > 0
    c0 = table_children[0]
    assert "表头: 车型版本 | 电机配置 | 百公里加速 | 最高车速" in c0.content
    assert "SU7 Ultra" in c0.content


def test_parent_child_text_chunking():
    # Construct a long text section with multiple paragraphs
    paras = [
        f"这是关于智能座舱与车机互联系统的详细说明段落第{i}段。采用高通骁龙8295旗舰座舱芯片，配备16.1英寸3K超清中控大屏，支持五屏联动交互系统及小米澎湃OS底层生态无缝流转体验。"
        for i in range(12)
    ]
    long_content = "\n\n".join(paras)

    sec = TextSection(
        title="智能座舱与生态互联",
        content=long_content,
        level=2,
        page_num=3,
    )
    doc = ParsedDocument(
        title="技术说明书",
        vehicle_model="小米SU7",
        sections=[sec],
    )

    chunker = HierarchicalChunker(
        parent_max_tokens=600,
        child_max_tokens=150,
        child_overlap_tokens=30,
    )
    res = chunker.chunk_document(doc)

    parents = res["parents"]
    children = res["children"]

    assert len(parents) >= 1
    assert len(children) > len(parents)

    # Check parent content and metadata
    p = parents[0]
    assert p.chunk_type == ChunkType.PARENT
    assert "【章节: 智能座舱与生态互联 | 车型: 小米SU7 | 级别: H2】" in p.content
    assert p.metadata["vehicle_model"] == "小米SU7"
    assert p.metadata["is_table"] is False

    # Check child linkage to parent
    parent_ids = {parent.chunk_id for parent in parents}
    for c in children:
        assert c.chunk_type == ChunkType.CHILD
        assert c.parent_id in parent_ids
        parent_obj = next(parent for parent in parents if parent.chunk_id == c.parent_id)
        assert c.chunk_id in parent_obj.child_ids
        assert c.token_count <= 250  # small chunk guarantee


def test_chunking_real_pdf_document():
    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(PDF_SAMPLE_PATH)

    chunker = HierarchicalChunker(parent_max_tokens=800, child_max_tokens=200)
    res = chunker.chunk_document(doc)

    parents = res["parents"]
    children = res["children"]
    tables = res["tables"]

    assert len(tables) >= 2
    assert len(parents) >= 3
    assert len(children) >= len(parents)

    # Every child must point to a valid existing parent
    parent_ids = {p.chunk_id for p in parents}
    for c in children:
        assert c.parent_id in parent_ids


def test_english_text_chunking_and_sentence_splitting():
    # Multi-sentence English technical paragraphs without Chinese punctuation
    english_sentences = [
        f"Paragraph {i}: The quad-motor powertrain architecture delivers exceptional torque vectoring capabilities across all four wheels with millisecond-level reaction times."
        for i in range(10)
    ]
    english_text = " ".join(english_sentences)

    sec = TextSection(title="Powertrain Architecture", content=english_text, level=1)
    doc = ParsedDocument(title="Engineering Manual", vehicle_model="Yangwang U9", sections=[sec])

    chunker = HierarchicalChunker(parent_max_tokens=600, child_max_tokens=150)
    res = chunker.chunk_document(doc)

    children = res["children"]
    assert len(children) >= 2, "English text should be split into multiple child chunks using English sentence boundaries"
    for c in children:
        assert c.token_count <= 250


def test_long_unbroken_sentence_subdivision():
    # Very long single sentence without periods, but with commas/semicolons
    long_clause = (
        "这是一段非常冗长且连续的技术规格说明文本，包含了关于高压碳化硅电控模块的详细参数，"
        "同时集成了双枪快充升压充电技术与全主动悬架阻尼调节机构，"
        "并且在高速行驶过程中通过主动尾翼与扩散器协同工作产生高达280公斤的下压力以保持车辆抓地力，"
        "此外还配备了由碳陶瓷制动盘和六活塞卡钳组成的高性能制动总成以保证连续赛道圈速下的抗热衰退表现。"
    )
    long_text = long_clause * 2  # ~300+ tokens in one unbroken sentence

    sec = TextSection(title="极端长句测试", content=long_text, level=2)
    doc = ParsedDocument(title="测试文档", vehicle_model="测试车型", sections=[sec])

    chunker = HierarchicalChunker(parent_max_tokens=800, child_max_tokens=120)
    res = chunker.chunk_document(doc)

    children = res["children"]
    assert len(children) >= 2, "Long sentences should be subdivided into ~120-token child chunks"
    for c in children:
        assert c.token_count <= 200, f"Child chunk {c.chunk_id} exceeded max token limit: {c.token_count}"


def test_table_with_none_bbox_graceful_handling():
    tbl = TableBlock(
        page_num=1,
        bbox=None,  # Intentionally None
        rows=[["Param", "Value"], ["A", "1"]],
        title="无坐标表",
    )
    doc = ParsedDocument(title="测试", tables=[tbl])

    chunker = HierarchicalChunker()
    # Must not throw AttributeError: 'NoneType' object has no attribute 'x0'
    res = chunker.chunk_document(doc)
    assert len(res["tables"]) == 1
    t_chunk = res["tables"][0]
    assert "未提供" in t_chunk.content or "None" in str(t_chunk.metadata.get("bbox"))


def test_byd_yangwang_u9_hierarchical_chunking():
    u9_path = _PROJECT_ROOT / "data" / "sample_specs" / "byd_yangwang_u9_specs.pdf"
    assert u9_path.exists()

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(u9_path)

    chunker = HierarchicalChunker(parent_max_tokens=800, child_max_tokens=200)
    res = chunker.chunk_document(doc)

    assert len(res["tables"]) >= 2
    assert len(res["parents"]) >= 3
    assert len(res["children"]) > len(res["parents"])

    # Verify context enrichment contains Yangwang U9
    for t_chunk in res["tables"]:
        assert "仰望U9" in t_chunk.content or "Yangwang U9" in t_chunk.content
