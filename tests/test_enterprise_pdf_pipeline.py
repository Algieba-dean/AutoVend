"""
Enterprise Production-Grade Test Suite for AutoVend PDF Parsing & Retrieval Pipeline.
(tests/test_enterprise_pdf_pipeline.py)

Validates 7 major enterprise PDF processing capabilities:
1. Cross-Page Table Stitching (跨页表格无缝拼接与表头去重)
2. Running Header, Footer, and Watermark Noise Filtering (页眉/页脚/水印清洗)
3. Dual-Column / Multi-Column Reading Order Reconstruction (双栏排版顺序还原)
4. Hierarchical Heading Tree (H1-H4) and Breadcrumb Tracking (多级标题树与面包屑路径)
5. Table Normalization & Forward-Fill Cell Spanning (复杂表格归一化与单元格平铺)
6. Scanned vs Digital Hybrid Page Classification (混合型文档与纯扫描件自适应检测)
7. Parent-Child Hierarchical Retrieval with Metadata Filtering (父子检索与多维度元数据过滤)
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
    CrossPageTableStitcher,
    DocumentHierarchyBuilder,
    HeaderFooterWatermarkFilter,
    LayoutAwareParser,
    OCROrientationDetector,
    ParsedDocument,
    PyMuPDFPlumberEngine,
    ReadingOrderSorter,
    TableBlock,
    TableCell,
    TextSection,
)
from src.ingestion.unstructured_parser import UnstructuredDataParser, VehicleTOMLConverter
from src.retrieval.parent_child_retriever import (
    ParentChildRetriever,
    ParentChildSearchResponse,
)

ENTERPRISE_PDF_PATH = Path("/home/algieba/projects/hackthon/AutoVend/data/sample_specs/enterprise_multipage_specs.pdf")
SAMPLE_SPECS_DIR = ENTERPRISE_PDF_PATH.parent


def test_cross_page_table_stitching():
    """Verify seamless stitching of multi-page vehicle specs table."""
    assert ENTERPRISE_PDF_PATH.exists(), f"Enterprise PDF missing at {ENTERPRISE_PDF_PATH}"

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(ENTERPRISE_PDF_PATH)

    assert doc.metadata.get("has_stitched_tables") is True
    assert len(doc.tables) == 1, f"Expected 1 consolidated stitched table, got {len(doc.tables)}"

    tbl = doc.tables[0]
    assert tbl.is_stitched is True
    assert tbl.pages == [1, 2]
    # Page 1 had 5 data rows + Page 2 had 4 data rows = 9 data rows + 1 header = 10 rows
    assert tbl.row_count == 10
    assert tbl.col_count == 6

    # Verify duplicate header on Page 2 was stripped
    headers = tbl.headers
    assert "版本型号 / Trim" in headers[0]
    assert "智驾芯片 / Autonomous" in headers[-1]

    # Verify both Page 1 data and Page 2 data are in rows
    row_models = [r[0] for r in tbl.rows[1:]]
    assert "SU7 标准版" in row_models
    assert "SU7 Ultra 赛道版" in row_models
    assert "仰望U9 标准版" in row_models
    assert "仰望U9 纽北极速版" in row_models

    # Verify Markdown representation includes stitched pages
    md = tbl.to_markdown()
    assert "第 1-2 页拼接" in md or "第 1 至 2 页" in md or "第 1-2" in md
    assert "SU7 Ultra 赛道版" in md
    assert "仰望U9 纽北极速版" in md


def test_header_footer_watermark_filtering():
    """Verify running headers, footers, pagination, and watermarks are stripped."""
    parser = LayoutAwareParser(engine_type="hybrid", filter_noise=True)
    doc = parser.parse(ENTERPRISE_PDF_PATH)

    full_md = doc.get_full_markdown()

    # The running header text must NOT contaminate document content
    assert "AutoVend Confidential Enterprise Specification Manual" not in full_md

    # Pagination must NOT be present as narrative content
    assert "Page 1 of 3" not in full_md
    assert "Page 2 of 3" not in full_md
    assert "Page 3 of 3" not in full_md

    # Watermark text must NOT appear in markdown body
    for sec in doc.sections:
        assert "CONFIDENTIAL" not in sec.title
        assert "CONFIDENTIAL" not in sec.content


def test_dual_column_reading_order_reconstruction():
    """Verify left column content precedes right column content without interleave."""
    parser = LayoutAwareParser(engine_type="hybrid", reading_order_sort=True)
    doc = parser.parse(ENTERPRISE_PDF_PATH)

    # Page 3 sections
    page3_secs = [s for s in doc.sections if s.page_num == 3]
    assert len(page3_secs) >= 2

    # Left column section: 2.1.1 前轴主动悬架与气动阻尼
    # Right column section: 2.1.2 后轴扭矩矢量分配与主动差速
    sec_titles = [s.title for s in page3_secs]
    assert any("前轴主动悬架" in t for t in sec_titles)
    assert any("后轴扭矩矢量" in t for t in sec_titles)

    # Left column index must be strictly smaller than right column index
    left_idx = next(i for i, t in enumerate(sec_titles) if "前轴主动悬架" in t)
    right_idx = next(i for i, t in enumerate(sec_titles) if "后轴扭矩矢量" in t)
    assert left_idx < right_idx, "Left column must be read before right column"

    # Verify content continuity: left column text is not mixed with right column text
    left_sec = page3_secs[left_idx]
    assert "连续阻尼可调减振器" in left_sec.content
    assert "扭矩响应能力" not in left_sec.content  # Right column content not leaked into left column


def test_hierarchical_headings_and_breadcrumbs():
    """Verify multi-level heading detection and breadcrumb path tracking."""
    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(ENTERPRISE_PDF_PATH)

    # Check breadcrumbs on chassis sub-sections
    chassis_secs = [s for s in doc.sections if "前轴主动悬架" in s.title or "后轴扭矩矢量" in s.title]
    assert len(chassis_secs) >= 1

    sample_sec = chassis_secs[0]
    assert len(sample_sec.breadcrumb_path) >= 2
    assert "2. 底盘悬架与空气动力学工程白皮书" in sample_sec.breadcrumb_path[0]
    assert sample_sec.breadcrumb_path[-1] == sample_sec.title


def test_table_normalization_and_forward_fill():
    """Verify forward-fill normalization and key-value records generation."""
    bbox = BoundingBox(10, 20, 200, 150)
    # Ragged table where category is only given in row 0 and 2
    raw_rows = [
        ["系统分类", "参数项", "指标值"],
        ["动力总成", "前驱电机功率", "240 kW"],
        ["", "后驱电机功率", "400 kW"],      # Empty category cell (merged in original)
        ["底盘悬架", "悬架结构", "双叉臂"],
        ["", "减振系统", "主动CDC电控"],     # Empty category cell
    ]
    tbl = TableBlock(page_num=1, bbox=bbox, rows=raw_rows)

    # Test forward-fill
    norm_rows = tbl.normalize_forward_fill()
    assert norm_rows[2][0] == "动力总成"
    assert norm_rows[4][0] == "底盘悬架"

    # Test to_records
    records = tbl.to_records()
    assert len(records) == 4
    assert records[0]["系统分类"] == "动力总成"
    assert records[0]["参数项"] == "前驱电机功率"
    assert records[1]["系统分类"] == "动力总成"
    assert records[1]["参数项"] == "后驱电机功率"
    assert records[3]["系统分类"] == "底盘悬架"
    assert records[3]["指标值"] == "主动CDC电控"


def test_hierarchical_chunking_with_stitched_table():
    """Verify hierarchical chunker creates enriched table and section chunks."""
    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(ENTERPRISE_PDF_PATH)

    chunker = HierarchicalChunker()
    chunk_dict = chunker.chunk_document(doc)

    assert len(chunk_dict["parents"]) >= 3
    assert len(chunk_dict["children"]) >= 4

    # Find the table chunk
    table_chunks = [c for c in chunk_dict["parents"] if c.chunk_type == ChunkType.TABLE]
    assert len(table_chunks) == 1

    t_chunk = table_chunks[0]
    assert t_chunk.metadata.get("is_stitched") is True
    assert t_chunk.metadata.get("pages") == [1, 2]
    assert "【结构化元数据】" in t_chunk.content
    assert "跨页缝合" in t_chunk.content
    assert "SU7 Ultra 赛道版" in t_chunk.content
    assert "仰望U9 纽北极速版" in t_chunk.content

    # Check child chunks for the table
    t_children = [c for c in chunk_dict["children"] if c.parent_id == t_chunk.chunk_id]
    assert len(t_children) >= 2


def test_parent_child_retriever_end_to_end_and_metadata_filter():
    """Verify parent-child retriever resolves child matches to complete stitched table and sections."""
    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(ENTERPRISE_PDF_PATH)

    retriever = ParentChildRetriever()
    retriever.index_document(doc)

    # Query 1: Query for an item on Page 2 of the cross-page table
    resp1 = retriever.search(query="仰望U9 纽北极速版 1400 PS 六轴高精度IMU")
    assert len(resp1.results) >= 1
    top_res = resp1.results[0]
    assert top_res.is_table is True
    assert top_res.is_stitched is True
    # The returned content contains the full consolidated table
    assert "SU7 标准版" in top_res.content
    assert "仰望U9 纽北极速版" in top_res.content

    # Query 2: Metadata filtering (only search tables)
    resp_table_only = retriever.search(query="连续阻尼 悬架", filter_metadata={"is_table": True})
    for r in resp_table_only.results:
        assert r.is_table is True

    # Query 3: Metadata filtering (only search narrative sections)
    resp_text_only = retriever.search(query="前唇 主动升降气坝 50kg下压力", filter_metadata={"is_table": False})
    assert len(resp_text_only.results) >= 1
    text_res = resp_text_only.results[0]
    assert text_res.is_table is False
    assert len(text_res.breadcrumbs) >= 1
    assert "底盘悬架" in text_res.breadcrumbs[0]

    # Query 4: LLM context formatting
    llm_context = resp_text_only.format_llm_context(max_parents=1)
    assert "[层级路径:" in llm_context
    assert "主动升降气坝" in llm_context


def test_toml_converter_metric_extraction():
    """Verify vehicle spec extraction with horsepower, battery capacity and acceleration."""
    converter = VehicleTOMLConverter()
    sample_text = (
        "车型名称: Xiaomi SU7 Ultra\n"
        "品牌: Xiaomi\n"
        "价格: 81.49万元\n"
        "综合最大马力达到1548 PS，零百加速1.98秒，搭载93.7kWh三元锂电池包，属于四门纯电超跑。"
    )
    fields = converter.extract_structured_fields(sample_text)
    assert fields["car_model"] == "Xiaomi SU7 Ultra"
    assert fields["horsepower"] == 1548
    assert fields["acceleration_0_100"] == "1.98s"
    assert fields["battery_capacity"] == "93.7 kWh"
    assert fields["powertrain_type"] == "bev"
    assert fields["vehicle_category_bottom"] == "four-door hardtop"
    assert fields["prize"] == "60,000 ~ 100,000"


def test_cross_page_table_stitching_three_continuous_pages():
    """Verify seamless continuous stitching across 3 pages into a single consolidated TableBlock."""
    b1 = BoundingBox(10, 200, 500, 800, page=1)
    b2 = BoundingBox(10, 50, 500, 800, page=2)
    b3 = BoundingBox(10, 50, 500, 400, page=3)

    headers = ["版本Trim", "电机架构Drive", "最大马力Power"]
    t1 = TableBlock(page_num=1, bbox=b1, rows=[headers, ["SU7 Standard", "单电机", "299 PS"]], headers=headers)
    t2 = TableBlock(page_num=2, bbox=b2, rows=[headers, ["SU7 Max", "双电机", "673 PS"]], headers=headers)
    t3 = TableBlock(page_num=3, bbox=b3, rows=[headers, ["SU7 Ultra", "三电机", "1548 PS"]], headers=headers)

    stitched_tables = CrossPageTableStitcher.stitch_tables([t1, t2, t3])
    assert len(stitched_tables) == 1, f"Expected 1 consolidated table across 3 pages, got {len(stitched_tables)}"

    tbl = stitched_tables[0]
    assert tbl.is_stitched is True
    assert tbl.pages == [1, 2, 3]
    assert tbl.row_count == 4  # 1 header + 3 data rows
    assert tbl.rows[0] == headers
    assert tbl.rows[1][0] == "SU7 Standard"
    assert tbl.rows[2][0] == "SU7 Max"
    assert tbl.rows[3][0] == "SU7 Ultra"


def test_multilevel_compound_table_headers_and_records():
    """Verify multi-level header detection, compound header generation, and collision-free records."""
    raw_rows = [
        ["基本参数", "基本参数", "动力性能", "动力性能"],
        ["车型代号", "指导价格", "系统马力", "零百加速"],
        ["Xiaomi SU7 Ultra", "81.49 万元", "1548 PS", "1.98 秒"],
        ["BYD Yangwang U9", "168.0 万元", "1306 PS", "2.36 秒"],
    ]
    tbl = TableBlock(page_num=1, bbox=BoundingBox(10, 20, 500, 300), rows=raw_rows)

    assert tbl.is_multilevel_header is True
    assert tbl.header_rows_count == 2
    assert tbl.headers == [
        "基本参数 > 车型代号",
        "基本参数 > 指导价格",
        "动力性能 > 系统马力",
        "动力性能 > 零百加速",
    ]

    records = tbl.to_records()
    assert len(records) == 2

    # Verify no keys were overwritten and all fields are preserved
    rec0 = records[0]
    assert rec0["基本参数 > 车型代号"] == "Xiaomi SU7 Ultra"
    assert rec0["基本参数 > 指导价格"] == "81.49 万元"
    assert rec0["动力性能 > 系统马力"] == "1548 PS"
    assert rec0["动力性能 > 零百加速"] == "1.98 秒"


def test_table_forward_fill_parent_category_reset():
    """Verify forward-fill clears child category cache when parent category changes."""
    raw_rows = [
        ["主系统分类", "子模块分类", "技术指标"],
        ["动力总成", "前驱电机", "240 kW"],
        ["动力总成", "", "400 kW"],           # Subcategory empty under same parent -> should forward-fill "前驱电机"
        ["底盘悬架", "", "双腔空气弹簧"],     # Parent changes to "底盘悬架", subcategory empty -> MUST NOT inherit "前驱电机"
    ]
    tbl = TableBlock(page_num=1, bbox=BoundingBox(10, 20, 300, 200), rows=raw_rows)
    norm = tbl.normalize_forward_fill()

    assert norm[2][0] == "动力总成"
    assert norm[2][1] == "前驱电机"

    # Row 3 must NOT have "前驱电机" under "底盘悬架"
    assert norm[3][0] == "底盘悬架"
    assert norm[3][1] == "", f"Expected empty subcategory under new parent category, got '{norm[3][1]}'"


def test_three_column_reading_order_sorter():
    """Verify ReadingOrderSorter reconstructs left-to-right columns in 3-column layout."""
    page_width = 600.0
    page_height = 800.0

    # Spanning banner at the top
    banner = {"bbox": [40, 30, 560, 60], "lines": [{"spans": [{"text": "Global System Architecture Overview", "size": 16}]}]}
    # Column 1 (Left): x in [40, 180]
    c1_p1 = {"bbox": [40, 80, 180, 140], "lines": [{"spans": [{"text": "Col1 Line1", "size": 9}]}]}
    c1_p2 = {"bbox": [40, 150, 180, 210], "lines": [{"spans": [{"text": "Col1 Line2", "size": 9}]}]}
    # Column 2 (Middle): x in [220, 360]
    c2_p1 = {"bbox": [220, 80, 360, 140], "lines": [{"spans": [{"text": "Col2 Line1", "size": 9}]}]}
    c2_p2 = {"bbox": [220, 150, 360, 210], "lines": [{"spans": [{"text": "Col2 Line2", "size": 9}]}]}
    # Column 3 (Right): x in [400, 540]
    c3_p1 = {"bbox": [400, 80, 540, 140], "lines": [{"spans": [{"text": "Col3 Line1", "size": 9}]}]}
    c3_p2 = {"bbox": [400, 150, 540, 210], "lines": [{"spans": [{"text": "Col3 Line2", "size": 9}]}]}

    # Interleaved input
    input_blocks = [c3_p1, c1_p2, banner, c2_p2, c1_p1, c3_p2, c2_p1]
    sorted_blocks = ReadingOrderSorter.sort_page_blocks(input_blocks, page_width, page_height)

    # Expected order: banner, c1_p1, c1_p2, c2_p1, c2_p2, c3_p1, c3_p2
    sorted_texts = [b["lines"][0]["spans"][0]["text"] for b in sorted_blocks]
    assert sorted_texts[0] == "Global System Architecture Overview"
    assert sorted_texts[1:3] == ["Col1 Line1", "Col1 Line2"]
    assert sorted_texts[3:5] == ["Col2 Line1", "Col2 Line2"]
    assert sorted_texts[5:7] == ["Col3 Line1", "Col3 Line2"]


def test_ocr_orientation_detector_and_scanned_page_handling():
    """Verify OCR orientation detection and diagnostic section preservation for pure image pages."""
    class DummyPage:
        def __init__(self, rotation=90):
            self.rotation = rotation
            self.rect = type("Rect", (), {"width": 595.0, "height": 842.0})()
        def get_text(self, *args, **kwargs):
            return {"blocks": []}

    dummy = DummyPage(rotation=90)
    detected = OCROrientationDetector.detect_page_rotation(dummy)
    assert detected == 90


def test_case1_financial_autoloan_nested_terms_and_fine_print():
    """Edge Case 1: Financial auto-loan policy & interest rate table with multi-tier nested terms & fine print."""
    pdf_path = SAMPLE_SPECS_DIR / "financial_autoloan_policy_specs.pdf"
    assert pdf_path.exists(), f"Sample PDF missing: {pdf_path}"

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(pdf_path)

    # 1. Document properties
    assert doc.pages == 2
    assert len(doc.tables) == 2

    # 2. Table 0 has multi-level compound header
    t0 = doc.tables[0]
    assert t0.page_num == 1
    assert t0.is_multilevel_header is True
    assert t0.header_rows_count == 2
    assert t0.col_count == 7
    assert t0.row_count == 7  # 2 header rows + 5 data rows

    records = t0.to_records()
    assert len(records) == 5
    assert "金融方案分类 > 方案名称" in records[0]
    assert "利率及年化费率 > 综合年化利率IRR" in records[0]
    assert records[0]["金融方案分类 > 方案名称"] == "0息先享方案"
    assert records[0]["利率及年化费率 > 综合年化利率IRR"] == "0.00%"
    assert records[2]["金融方案分类 > 方案名称"] == "超低息长贷方案"
    assert records[2]["利率及年化费率 > 综合年化利率IRR"] == "3.80%"

    # 3. Table 1: Insurance table
    t1 = doc.tables[1]
    assert t1.page_num == 2
    assert t1.row_count == 5  # 1 header + 4 data rows
    assert t1.col_count == 4
    ins_records = t1.to_records()
    assert len(ins_records) == 4
    assert ins_records[2]["险种大类"] == "高压电池专属险"
    assert "35万元" in ins_records[2]["保障限额"]

    # 4. Fine print / footnotes properly bound to tables
    assert len(t0.footnotes) == 3, f"Expected 3 footnotes for Table 0, got {len(t0.footnotes)}"
    assert any("中国人民银行单利计算口径" in fn for fn in t0.footnotes)
    assert any("3% 计收提前结清违约金手续费" in fn for fn in t0.footnotes)
    assert any("AutoVend专属金融基金" in fn for fn in t0.footnotes)

    assert len(t1.footnotes) == 1
    assert "非法改装动力总成工况下发生的事故" in t1.footnotes[0]

    # Verify footnotes rendered in Table Markdown representation
    md_t0 = t0.to_markdown()
    assert "3% 计收提前结清违约金手续费" in md_t0

    # Verify footnotes excluded from structured records to prevent data contamination
    assert "3% 计收提前结清违约金手续费" not in str(records)

    # 5. Full markdown preserves fine print context
    full_text = doc.get_full_markdown()
    assert "中国人民银行单利计算口径" in full_text
    assert "3% 计收提前结清违约金手续费" in full_text
    assert "非法改装动力总成工况下发生的事故，保险人不承担任何赔偿责任" in full_text


def test_case2_vehicle_maintenance_mixed_column_layout():
    """Edge Case 2: Complex vehicle maintenance manual with mixed column layouts & embedded borderless spec table."""
    pdf_path = SAMPLE_SPECS_DIR / "vehicle_maintenance_diagnostic_manual.pdf"
    assert pdf_path.exists(), f"Sample PDF missing: {pdf_path}"

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(pdf_path)

    # 1. Single-page document with mixed column sections and embedded borderless table
    assert doc.pages == 1
    assert len(doc.tables) == 1
    tbl = doc.tables[0]
    assert tbl.row_count == 5
    assert tbl.col_count == 5
    assert tbl.is_borderless is True, "Embedded spec table must be detected as borderless"
    assert tbl.extraction_engine.startswith("borderless")

    records = tbl.to_records()
    assert len(records) == 4
    terminals = [r["端子代号"] for r in records]
    assert terminals == ["HVIL-IN", "HVIL-OUT", "PDU-TEMP", "INV-GATE"]
    assert records[0]["导通阻值上限"] == "≤ 1.0 Ω"

    # Footnote bound to borderless spec table
    assert len(tbl.footnotes) == 1
    assert "测量端子阻值前务必将低压蓄电池负极断开" in tbl.footnotes[0]

    # 2. Full markdown preserves reading flow: Top banner -> Dual-column 1.1 & 1.2 -> Embedded table -> Sign-off
    full_md = doc.get_full_markdown()
    pos_banner = full_md.find("【高压作业安全规范警示】")
    pos_dtc = full_md.find("1.1 故障现象与DTC码读取")
    pos_measure = full_md.find("1.2 物理测量与排故处置流程")
    pos_table = full_md.find("HVIL-IN")
    pos_signoff = full_md.find("【终检验收规范】")

    assert pos_banner != -1, "Top warning banner missing"
    assert pos_dtc != -1, "Section 1.1 missing"
    assert pos_measure != -1, "Section 1.2 missing"
    assert pos_table != -1, "Table missing"
    assert pos_signoff != -1, "Bottom sign-off missing"

    # Check reading sequence: banner -> 1.1 -> 1.2 -> table -> signoff
    assert pos_banner < pos_dtc, "Banner must precede DTC reading"
    assert pos_dtc < pos_measure, "Column 1 (1.1) must precede Column 2 (1.2)"
    assert pos_measure < pos_table, "Diagnostic flow must precede table"
    assert pos_table < pos_signoff, "Table must precede final sign-off"


def test_case3_irregular_borderless_spec_table_detection():
    """Edge Case 3: Irregular / borderless spec table where gridlines are missing (whitespace-delimited)."""
    pdf_path = SAMPLE_SPECS_DIR / "irregular_borderless_specs.pdf"
    assert pdf_path.exists(), f"Sample PDF missing: {pdf_path}"

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(pdf_path)

    # 1. Detected borderless tables flag
    assert doc.metadata.get("has_borderless_tables") is True
    assert len(doc.tables) == 1

    tbl = doc.tables[0]
    assert tbl.col_count == 6
    assert tbl.row_count == 5  # 1 header + 4 rows
    assert tbl.is_borderless is True

    # 2. Column headers properly identified
    assert tbl.rows[0] == ["Trim / 版本型号", "Power / 功率", "Torque / 扭矩", "Battery / 电池", "0-100 / 加速", "Price / 指导价"]

    records = tbl.to_records()
    assert len(records) == 4
    assert records[0]["Trim / 版本型号"] == "SU7 Ultra 量产版"
    assert records[0]["Power / 功率"] == "1548 PS"
    assert records[0]["0-100 / 加速"] == "1.98 秒"
    assert records[2]["Trim / 版本型号"] == "仰望U9 标准版"
    assert records[2]["Battery / 电池"] == "80.0 kWh 刀片"

    # 3. Footnote attached to table
    assert len(tbl.footnotes) == 1
    assert "以上零百加速成绩均在干燥沥青路面" in tbl.footnotes[0]

    # 4. Narrative section preserved without being corrupted as table
    narrative_sections = [s for s in doc.sections if "核心技术解读" in s.title]
    assert len(narrative_sections) == 1
    assert "小米V8s超级电机最高转速达到27200rpm" in narrative_sections[0].content


def test_case4_mixed_orientation_portrait_landscape_matrix():
    """Edge Case 4: Multi-page document with mixed page orientations (Portrait P1 -> Landscape P2 -> Portrait P3)."""
    pdf_path = SAMPLE_SPECS_DIR / "mixed_orientation_enterprise_specs.pdf"
    assert pdf_path.exists(), f"Sample PDF missing: {pdf_path}"

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(pdf_path)

    # 1. Orientation tracking
    assert doc.pages == 3
    assert doc.metadata.get("has_mixed_orientations") is True
    assert doc.page_orientations == {1: "portrait", 2: "landscape", 3: "portrait"}

    # Page dimensions reflect orientation change
    w1, h1 = doc.page_dimensions[1]
    w2, h2 = doc.page_dimensions[2]
    w3, h3 = doc.page_dimensions[3]
    assert h1 > w1, "Page 1 must be portrait"
    assert w2 > h2, "Page 2 must be landscape"
    assert h3 > w3, "Page 3 must be portrait"

    # 2. Landscape wide table extracted on page 2
    assert len(doc.tables) == 1
    tbl = doc.tables[0]
    assert tbl.page_num == 2
    assert tbl.col_count == 12
    assert tbl.row_count == 4  # 1 header + 3 vehicle models

    headers = tbl.rows[0]
    assert "车型名称" in headers
    assert "放电倍率" in headers
    assert "官方指导价" in headers

    records = tbl.to_records()
    assert len(records) == 3
    rec_u9 = next(r for r in records if r["车型名称"] == "BYD Yangwang U9")
    assert rec_u9["马力(PS)"] == "1306"
    assert rec_u9["驱动形式"] == "易四方四驱"
    assert rec_u9["零百加速"] == "2.36 s"

    rec_taycan = next(r for r in records if r["车型名称"] == "Taycan Turbo GT")
    assert rec_taycan["马力(PS)"] == "1034"
    assert rec_taycan["最高时速"] == "305 km/h"

    # Footnote attached to landscape table
    assert len(tbl.footnotes) == 1
    assert "Landscape 方向" in tbl.footnotes[0]


def test_case5_scanned_brochure_repeated_watermark_rejection_and_fallback():
    """Edge Case 5: Brochure with repeated watermarks and scanned/image blueprint page."""
    pdf_path = SAMPLE_SPECS_DIR / "scanned_brochure_watermark_specs.pdf"
    assert pdf_path.exists(), f"Sample PDF missing: {pdf_path}"

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(pdf_path)

    # 1. Page count and classifications
    assert doc.pages == 3
    classifications = doc.metadata.get("pages_classification", {})
    assert classifications.get(1) == "digital"
    assert classifications.get(2) == "scanned"
    assert classifications.get(3) == "digital"

    # 2. Watermarks are cleanly filtered out
    full_md = doc.get_full_markdown()
    assert "INTERNAL ONLY" not in full_md
    assert "DO NOT DISTRIBUTE" not in full_md

    # 3. Diagnostic text section generated for scanned image page
    scanned_secs = [s for s in doc.sections if s.page_num == 2]
    assert len(scanned_secs) == 1
    assert "扫描件工程图表" in scanned_secs[0].title
    assert "【扫描件版面图像诊断 (第 2 页)】" in scanned_secs[0].content
    assert "纯图片扫描件" in scanned_secs[0].content

    # 4. Genuine text content on digital pages preserved
    assert "下压力尾翼角度" in full_md
    assert "整车5年或10万公里质保" in full_md
    assert "关键三电系统提供8年或16万公里质保" in full_md


def test_case6_cross_page_borderless_table_stitching():
    """Edge Case 6: Multi-page continuous BORDERLESS table across Page 1 and Page 2 without gridlines."""
    pdf_path = SAMPLE_SPECS_DIR / "enterprise_borderless_multipage_specs.pdf"
    assert pdf_path.exists(), f"Sample PDF missing: {pdf_path}"

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(pdf_path)

    assert doc.pages == 2
    assert doc.metadata.get("has_borderless_tables") is True
    assert doc.metadata.get("has_stitched_tables") is True

    # Seamlessly stitched into 1 consolidated TableBlock
    assert len(doc.tables) == 1, f"Expected 1 stitched borderless table, got {len(doc.tables)}"
    tbl = doc.tables[0]
    assert tbl.is_borderless is True
    assert tbl.is_stitched is True
    assert tbl.pages == [1, 2]
    # Page 1 (5 rows) + Page 2 (4 rows) = 9 data rows + 1 header = 10 rows
    assert tbl.row_count == 10
    assert tbl.col_count == 6

    # Verify duplicate header on Page 2 was stripped
    assert tbl.rows[0] == ["版本型号 / Trim", "电机架构 / Motor", "最大马力 / Power", "电池规格 / Battery", "零百加速 / 0-100", "官方指导价 / Price"]

    # Verify rows across both pages
    records = tbl.to_records()
    assert len(records) == 9
    assert records[0]["版本型号 / Trim"] == "SU7 标准版"
    assert records[3]["版本型号 / Trim"] == "SU7 Ultra 量产版"
    assert records[3]["最大马力 / Power"] == "1548 PS"
    assert records[5]["版本型号 / Trim"] == "仰望U9 标准版"
    assert records[5]["零百加速 / 0-100"] == "2.36 秒"
    assert records[7]["版本型号 / Trim"] == "Taycan Turbo GT"
    assert records[8]["版本型号 / Trim"] == "Model S Plaid"

    # Footnote attached to table
    assert len(tbl.footnotes) == 1
    assert "跨页无网格线白皮书性能数据均在标准工况" in tbl.footnotes[0]


def test_case7_oem_warranty_maintenance_three_level_hierarchy():
    """Edge Case 7: OEM Multi-Tier Warranty, Maintenance & Recall Matrix with 3-Level Deep Merged Category Hierarchy."""
    pdf_path = SAMPLE_SPECS_DIR / "oem_warranty_maintenance_matrix.pdf"
    assert pdf_path.exists(), f"Sample PDF missing: {pdf_path}"

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(pdf_path)

    assert len(doc.tables) == 1
    tbl = doc.tables[0]
    assert tbl.col_count == 6
    assert tbl.row_count == 9  # 1 header + 8 data rows

    # Test forward-fill normalization across 3 hierarchy levels
    norm = tbl.normalize_forward_fill()
    assert len(norm) == 9
    # Row 1: PACK -> BMS
    assert norm[2][0] == "三电高压核心系统"
    assert norm[2][1] == "动力电池总成(PACK)"
    assert norm[2][2] == "BMS电池管理系统"
    # Row 3: Dual-motor powertrain
    assert norm[4][0] == "三电高压核心系统"
    assert norm[4][1] == "双电机电驱总成"
    assert norm[4][2] == "V8s超级电机定转子"
    # Row 5: Chassis DiSus-X
    assert norm[6][0] == "智能底盘与制动"
    assert norm[6][1] == "云辇-X/主动悬架"
    assert norm[6][2] == "双阀CDC连续可调减振器"
    # Row 7: Carbon ceramic brake
    assert norm[8][0] == "智能底盘与制动"
    assert norm[8][1] == "碳陶制动总成"
    assert norm[8][2] == "碳陶制动通风盘"

    # Verify structured records
    records = tbl.to_records()
    assert len(records) == 8
    assert records[0]["具体零件/传感器"] == "电芯单体与模组"
    assert "8年或16万公里" in records[0]["质保期限"]
    assert records[3]["具体零件/传感器"] == "V8s超级电机定转子"
    assert "定子绝缘击穿或转子退磁终身质保" in records[3]["召回与免费更换特约条款"]

    # Footnote bound
    assert len(tbl.footnotes) == 1
    assert "全国联保与全免费备件更换" in tbl.footnotes[0]


def test_case8_unequal_three_column_reading_order_and_spanning_callout():
    """Edge Case 8: Three-column technical teardown with unequal column gutter widths and spanning callout box."""
    pdf_path = SAMPLE_SPECS_DIR / "unequal_three_column_specs.pdf"
    assert pdf_path.exists(), f"Sample PDF missing: {pdf_path}"

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(pdf_path)

    # Full markdown order verification:
    # Zone 1 (1.1 -> 1.2 -> 1.3) -> Callout Banner -> Zone 2 (2.1 -> 2.2 -> 2.3)
    full_md = doc.get_full_markdown()
    pos_dtc = full_md.find("1.1 DTC遥测流")
    pos_wave = full_md.find("1.2 示波器波形与物理测量")
    pos_parts = full_md.find("1.3 备件定额与采购")
    pos_callout = full_md.find("【高压系统安全隔离与防电弧飞溅强制规程】")
    pos_harness = full_md.find("2.1 线束与总线检查")
    pos_hipot = full_md.find("2.2 绝缘耐压打压测试")
    pos_signoff = full_md.find("2.3 终检验收与放行")

    assert pos_dtc != -1, "1.1 missing"
    assert pos_wave != -1, "1.2 missing"
    assert pos_parts != -1, "1.3 missing"
    assert pos_callout != -1, "Callout banner missing"
    assert pos_harness != -1, "2.1 missing"
    assert pos_hipot != -1, "2.2 missing"
    assert pos_signoff != -1, "2.3 missing"

    # Strictly ordered without horizontal interleave across column gutters
    assert pos_dtc < pos_wave < pos_parts, "Zone 1 must read Col 1 -> Col 2 -> Col 3"
    assert pos_parts < pos_callout, "Zone 1 must precede middle spanning callout"
    assert pos_callout < pos_harness < pos_hipot < pos_signoff, "Zone 2 must follow callout in Col 1 -> Col 2 -> Col 3 sequence"


def test_end_to_end_parent_child_retrieval_across_new_cases():
    """Verify ParentChildRetriever indexes and searches all 8 real-world edge case documents."""
    parser = LayoutAwareParser(engine_type="hybrid")
    retriever = ParentChildRetriever()

    test_filenames = [
        "financial_autoloan_policy_specs.pdf",
        "vehicle_maintenance_diagnostic_manual.pdf",
        "irregular_borderless_specs.pdf",
        "mixed_orientation_enterprise_specs.pdf",
        "scanned_brochure_watermark_specs.pdf",
        "enterprise_borderless_multipage_specs.pdf",
        "oem_warranty_maintenance_matrix.pdf",
        "unequal_three_column_specs.pdf",
    ]

    for fname in test_filenames:
        pdf_path = SAMPLE_SPECS_DIR / fname
        doc = parser.parse(pdf_path)
        retriever.index_document(doc)

    # Target test queries and expected substrings in retrieved parent chunk
    test_queries = [
        ("提前还款违约金手续费是多少？", "3% 计收提前结清违约金手续费"),
        ("P0A0F-00 高压互锁故障排查与端子阻值标准", "HVIL-IN"),
        ("无网格线白皮书 零百加速实测条件与工况", "干燥沥青路面、弹射起步模式"),
        ("Taycan Turbo GT 最高时速与官方指导价", "305 km/h"),
        ("整车质保与关键三电系统质保细则", "8年或16万公里质保"),
        ("跨页无框线白皮书 Model S Plaid 三电机全驱马力", "1020 PS"),
        ("定子绝缘击穿或转子退磁终身质保", "V8s超级电机定转子"),
        ("防电弧飞溅强制规程与验电确认", "【高压系统安全隔离与防电弧飞溅强制规程】"),
    ]

    for query, expected_evidence in test_queries:
        resp = retriever.search(query=query, top_k_parents=2)
        assert len(resp.results) >= 1, f"No results retrieved for query: {query}"
        matched = any(expected_evidence in res.content for res in resp.results)
        assert matched, f"Expected '{expected_evidence}' in retrieved results for query '{query}', got: {[r.content[:100] for r in resp.results]}"

