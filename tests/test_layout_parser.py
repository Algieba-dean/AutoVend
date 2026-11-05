"""
Unit tests for Layout-Aware Document & Table Parser (src/ingestion/layout_parser.py).
Verifies:
- Table extraction with precise BBox coordinates (x0, top, x1, bottom)
- Markdown Table & HTML Table conversions
- Multi-engine interfaces (PyMuPDFPlumber, Azure Document Intelligence, Unstructured, Docling/MinerU)
- Table boundary text exclusion
"""

from pathlib import Path
import pytest

from src.ingestion.layout_parser import (
    AzureDocumentIntelligenceEngine,
    BoundingBox,
    CrossPageTableStitcher,
    LayoutAwareParser,
    MinerUDoclingEngine,
    ParsedDocument,
    PyMuPDFPlumberEngine,
    TableBlock,
    TableCell,
    TextSection,
    UnstructuredEngine,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_SAMPLE_PATH = _PROJECT_ROOT / "data" / "sample_specs" / "xiaomi_su7_ultra_specs.pdf"


def test_bounding_box_geometry():
    bbox = BoundingBox(x0=36.0, top=100.5, x1=550.0, bottom=320.0, page=1)
    assert bbox.x0 == 36.0
    assert bbox.top == 100.5
    assert bbox.x1 == 550.0
    assert bbox.bottom == 320.0
    assert bbox.width == pytest.approx(514.0)
    assert bbox.height == pytest.approx(219.5)
    assert bbox.page == 1

    d = bbox.to_dict()
    assert d["x0"] == 36.0
    assert d["width"] == pytest.approx(514.0)


def test_table_block_markdown_and_html_conversion():
    bbox = BoundingBox(10, 20, 200, 150, page=1)
    rows = [
        ["配置项", "规格参数", "标配/选配"],
        ["电机类型", "三电机双V8s+V6s", "标配"],
        ["百公里加速", "1.98秒", "标配"],
    ]
    tbl = TableBlock(
        page_num=1,
        bbox=bbox,
        rows=rows,
        title="性能核心参数",
        extraction_engine="pdfplumber_test",
    )

    assert tbl.row_count == 3
    assert tbl.col_count == 3
    assert tbl.headers == ["配置项", "规格参数", "标配/选配"]

    # Markdown format validation
    md = tbl.to_markdown()
    assert "### 表格: 性能核心参数" in md
    assert "| 配置项 | 规格参数 | 标配/选配 |" in md
    assert "| --- | --- | --- |" in md
    assert "| 电机类型 | 三电机双V8s+V6s | 标配 |" in md
    assert "| 百公里加速 | 1.98秒 | 标配 |" in md

    # HTML format validation
    html = tbl.to_html()
    assert '<caption>性能核心参数</caption>' in html
    assert '<table border="1" class="autovend-table">' in html
    assert "<th>配置项</th>" in html
    assert "<td>1.98秒</td>" in html


def test_table_block_handles_irregular_rows():
    bbox = BoundingBox(0, 0, 100, 100)
    rows = [
        ["A", "B"],
        ["1", "2", "3"],  # Longer row
        ["4"],            # Shorter row
    ]
    tbl = TableBlock(page_num=1, bbox=bbox, rows=rows)
    md = tbl.to_markdown()
    assert "| A | B |" in md
    assert "| 1 | 2 | 3 |" in md


def test_extract_tables_from_sample_pdf():
    assert PDF_SAMPLE_PATH.exists(), f"Sample PDF missing at {PDF_SAMPLE_PATH}"

    engine = PyMuPDFPlumberEngine()
    tables = engine.extract_tables(PDF_SAMPLE_PATH)

    assert len(tables) >= 2, f"Expected at least 2 tables, found {len(tables)}"

    # Check first table coordinates & content
    t1 = tables[0]
    assert t1.page_num == 1
    assert t1.bbox.x0 > 0
    assert t1.bbox.x1 > t1.bbox.x0
    assert t1.bbox.bottom > t1.bbox.top
    assert t1.row_count >= 5

    # Check Markdown contains vehicle specs
    t1_md = t1.to_markdown()
    assert "Xiaomi SU7 Ultra" in t1_md or "1548 PS" in t1_md or "Powertrain" in t1_md

    # Check second page table (Sensors)
    t_sensors = [t for t in tables if any("LiDAR" in c or "Sensors" in c for row in t.rows for c in row)]
    assert len(t_sensors) >= 1
    assert t_sensors[0].page_num == 2


def test_layout_aware_parser_full_document():
    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(PDF_SAMPLE_PATH)

    assert isinstance(doc, ParsedDocument)
    assert len(doc.tables) >= 2
    assert len(doc.sections) >= 1

    # Verify table titles attributed
    for tbl in doc.tables:
        assert tbl.bbox is not None
        assert tbl.bbox.width > 100

    # Full markdown composition
    full_md = doc.get_full_markdown()
    assert len(full_md) > 500
    assert "| --- |" in full_md


def test_azure_document_intelligence_engine_adapter():
    # Test Azure adapter in local fallback / compat mode
    azure_engine = AzureDocumentIntelligenceEngine()
    assert not azure_engine.is_configured  # Env vars not set

    tables = azure_engine.extract_tables(PDF_SAMPLE_PATH)
    assert len(tables) >= 2
    assert tables[0].extraction_engine == "azure_doc_intelligence_local_compat"

    doc = azure_engine.parse(PDF_SAMPLE_PATH)
    assert doc.metadata["engine"] == "azure_document_intelligence_compat"


def test_unstructured_and_docling_adapters():
    unstructured_engine = UnstructuredEngine()
    tables = unstructured_engine.extract_tables(PDF_SAMPLE_PATH)
    assert len(tables) >= 2

    docling_engine = MinerUDoclingEngine(engine_name="docling")
    doc = docling_engine.parse(PDF_SAMPLE_PATH)
    assert "docling_adapter" in doc.metadata["engine"]


def test_table_lines_and_cells_extraction():
    engine = PyMuPDFPlumberEngine()
    tables = engine.extract_tables(PDF_SAMPLE_PATH)
    assert len(tables) >= 2

    t0 = tables[0]
    # Check TableLine extraction
    assert len(t0.lines) > 0, "Expected table boundary/grid lines to be extracted"
    for line in t0.lines:
        assert line.orientation in ["h", "v"]
        assert line.x1 >= line.x0
        assert line.bottom >= line.top
        assert line.page == t0.page_num

    # Check TableCell extraction
    assert len(t0.cells) > 0, "Expected table cells to be populated"
    sample_cell = t0.cells[0]
    assert sample_cell.row_idx == 0
    assert sample_cell.col_idx == 0
    assert sample_cell.text == "Specification"
    assert sample_cell.bbox is not None
    assert sample_cell.bbox.width > 0
    assert sample_cell.bbox.height > 0


def test_html_escaping_and_row_spans():
    bbox = BoundingBox(0, 0, 100, 100)
    cells = [
        TableCell(row_idx=0, col_idx=0, text="System", row_span=2),
        TableCell(row_idx=0, col_idx=1, text="Rating < 50ms & > 100kW"),
        TableCell(row_idx=1, col_idx=1, text="High Voltage"),
    ]
    tbl = TableBlock(
        page_num=1,
        bbox=bbox,
        rows=[
            ["System", "Rating < 50ms & > 100kW"],
            ["System", "High Voltage"],
        ],
        cells=cells,
        title="Escaped & Spanned Table",
    )

    html = tbl.to_html()
    # Check HTML entity escaping
    assert "&lt; 50ms &amp; &gt; 100kW" in html
    assert "<caption>Escaped &amp; Spanned Table</caption>" in html
    # Check rowspan attribute
    assert 'rowspan="2"' in html


def test_byd_yangwang_u9_pdf_extraction():
    u9_path = _PROJECT_ROOT / "data" / "sample_specs" / "byd_yangwang_u9_specs.pdf"
    assert u9_path.exists(), "Yangwang U9 sample PDF should exist"

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(u9_path)

    assert "仰望U9" in doc.vehicle_model or "Yangwang U9" in doc.vehicle_model
    assert len(doc.tables) >= 2
    assert len(doc.sections) >= 2

    # Check e4 and DiSus-X specs
    md = doc.get_full_markdown()
    assert "e4 Quad-Motor" in md or "易四方" in md
    assert "DiSus-X" in md or "云辇-X" in md
    assert "2.36 s" in md or "1306 PS" in md


def test_table_normalization_arbitrary_columns():
    """Verify normalize_forward_fill fills columns beyond column index 1 without min(2) truncation."""
    bbox = BoundingBox(0, 0, 100, 100)
    raw_rows = [
        ["一级分类", "二级分类", "三级模块", "参数项", "指标值"],
        ["动力总成", "电驱系统", "主驱电机", "峰值功率", "288 kW"],
        ["", "", "", "峰值扭矩", "420 N·m"],           # Columns 0, 1, 2 should all forward-fill
        ["", "热管理系统", "热泵", "工作温域", "-30~45 ℃"],  # Col 0 should keep 动力总成, 1 changes, 2 is 热泵
        ["", "", "压缩机", "排量", "34 cc"],             # Col 0 kept, Col 1 kept, Col 2 kept
    ]
    tbl = TableBlock(page_num=1, bbox=bbox, rows=raw_rows)

    filled = tbl.normalize_forward_fill()

    assert len(filled) == 5
    # Row 2 (index 2): col 0, 1, 2 filled from row 1
    assert filled[2][0] == "动力总成"
    assert filled[2][1] == "电驱系统"
    assert filled[2][2] == "主驱电机"
    assert filled[2][3] == "峰值扭矩"

    # Row 3 (index 3): col 0 kept, col 1 changed to 热管理系统, col 2 is 热泵
    assert filled[3][0] == "动力总成"
    assert filled[3][1] == "热管理系统"
    assert filled[3][2] == "热泵"

    # Row 4 (index 4): col 0 kept, col 1 kept, col 2 is 压缩机
    assert filled[4][0] == "动力总成"
    assert filled[4][1] == "热管理系统"
    assert filled[4][2] == "压缩机"


def test_table_normalization_index_column_preservation():
    """Verify that an incrementing sequence/index column (序号, 1, 2, 3...) does NOT wipe category caches."""
    bbox = BoundingBox(0, 0, 100, 100)
    raw_rows = [
        ["序号", "系统分类", "参数名称", "标配数值"],
        ["1", "动力系统", "电机最大转速", "21000 rpm"],
        ["2", "", "综合输出马力", "673 PS"],             # Index changed 1 -> 2, but category must NOT be cleared!
        ["3", "", "零百加速时间", "2.78 s"],             # Index changed 2 -> 3, category still 动力系统
        ["4", "底盘悬架", "空气弹簧腔室", "双腔闭式"],      # Category explicitly changes to 底盘悬架
        ["5", "", "CDC阻尼调节频率", "500 Hz"],          # Category forward-fills to 底盘悬架
    ]
    tbl = TableBlock(page_num=1, bbox=bbox, rows=raw_rows)

    filled = tbl.normalize_forward_fill()

    assert filled[1][1] == "动力系统"
    assert filled[2][1] == "动力系统", "Sequence column increment must not clear parent category cache"
    assert filled[3][1] == "动力系统", "Sequence column increment must not clear parent category cache"
    assert filled[4][1] == "底盘悬架"
    assert filled[5][1] == "底盘悬架", "Category must forward-fill under 底盘悬架"

    # Also verify with numeric column 0 without explicit '序号' header
    raw_rows_numeric = [
        ["No.", "Major Category", "Sub-Item", "Spec"],
        ["101", "Infotainment", "Screen Size", "16.1 inch"],
        ["102", "", "Resolution", "3K"],
        ["103", "", "Chipset", "Snapdragon 8295"],
    ]
    tbl_num = TableBlock(page_num=1, bbox=bbox, rows=raw_rows_numeric)
    filled_num = tbl_num.normalize_forward_fill()
    assert filled_num[2][1] == "Infotainment"
    assert filled_num[3][1] == "Infotainment"


def test_table_normalization_backward_and_bidirectional_fill():
    """Verify backward fill and bidirectional fill algorithms."""
    bbox = BoundingBox(0, 0, 100, 100)
    # Merged group where category is given at the bottom row (bottom-aligned merged cell)
    raw_rows = [
        ["分类", "参数", "数值"],
        ["", "前轴功率", "200 kW"],
        ["", "后轴功率", "300 kW"],
        ["电驱总成", "总功率", "500 kW"],
    ]
    tbl = TableBlock(page_num=1, bbox=bbox, rows=raw_rows)

    # Backward fill propagates upward
    b_filled = tbl.normalize_backward_fill()
    assert b_filled[1][0] == "电驱总成"
    assert b_filled[2][0] == "电驱总成"
    assert b_filled[3][0] == "电驱总成"

    # Bidirectional fill test: Top cell filled, middle blank, bottom-aligned group below
    bidirectional_rows = [
        ["分类", "参数", "数值"],
        ["外观配置", "车长", "4997 mm"],
        ["", "轴距", "3000 mm"],      # Filled forward from 外观配置
        ["", "前胎宽", "245 mm"],     # Filled backward from 底盘轮胎
        ["底盘轮胎", "后胎宽", "265 mm"],
    ]
    tbl_bi = TableBlock(page_num=1, bbox=bbox, rows=bidirectional_rows)
    bi_filled = tbl_bi.normalize_bidirectional_fill()
    assert bi_filled[1][0] == "外观配置"
    assert bi_filled[2][0] == "外观配置"
    assert bi_filled[3][0] == "底盘轮胎", "Row 3 must fill backward from bottom anchor 底盘轮胎"
    assert bi_filled[4][0] == "底盘轮胎"

    # Unified normalize_fill dispatcher
    f_res = tbl.normalize_fill(direction="forward")
    assert f_res[3][0] == "电驱总成"
    b_res = tbl.normalize_fill(direction="backward")
    assert b_res[1][0] == "电驱总成"
    bi_res = tbl.normalize_fill(direction="bidirectional")
    assert bi_res[1][0] == "电驱总成"

    with pytest.raises(ValueError, match="Invalid fill direction"):
        tbl.normalize_fill(direction="diagonal")


def test_cross_page_table_stitcher_column_width_variance():
    """Verify column width extraction and variance evaluation in CrossPageTableStitcher."""
    bbox1 = BoundingBox(x0=50.0, top=100.0, x1=550.0, bottom=700.0, page=1)
    bbox2 = BoundingBox(x0=50.0, top=50.0, x1=550.0, bottom=400.0, page=2)

    # Table 1 on page 1 with 3 columns: widths ~ 150, 200, 150
    cells1 = [
        TableCell(row_idx=0, col_idx=0, text="H1", bbox=BoundingBox(50, 100, 200, 130, page=1)),
        TableCell(row_idx=0, col_idx=1, text="H2", bbox=BoundingBox(200, 100, 400, 130, page=1)),
        TableCell(row_idx=0, col_idx=2, text="H3", bbox=BoundingBox(400, 100, 550, 130, page=1)),
        TableCell(row_idx=1, col_idx=0, text="V1", bbox=BoundingBox(50, 130, 200, 160, page=1)),
        TableCell(row_idx=1, col_idx=1, text="V2", bbox=BoundingBox(200, 130, 400, 160, page=1)),
        TableCell(row_idx=1, col_idx=2, text="V3", bbox=BoundingBox(400, 130, 550, 160, page=1)),
    ]
    t1 = TableBlock(
        page_num=1,
        bbox=bbox1,
        rows=[["H1", "H2", "H3"], ["V1", "V2", "V3"]],
        cells=cells1,
    )

    # Table 2 on page 2: Matching column widths (150, 200, 150)
    cells2_matching = [
        TableCell(row_idx=0, col_idx=0, text="H1", bbox=BoundingBox(50, 50, 200, 80, page=2)),
        TableCell(row_idx=0, col_idx=1, text="H2", bbox=BoundingBox(200, 50, 400, 80, page=2)),
        TableCell(row_idx=0, col_idx=2, text="H3", bbox=BoundingBox(400, 50, 550, 80, page=2)),
        TableCell(row_idx=1, col_idx=0, text="V4", bbox=BoundingBox(50, 80, 200, 110, page=2)),
        TableCell(row_idx=1, col_idx=1, text="V5", bbox=BoundingBox(200, 80, 400, 110, page=2)),
        TableCell(row_idx=1, col_idx=2, text="V6", bbox=BoundingBox(400, 80, 550, 110, page=2)),
    ]
    t2_matching = TableBlock(
        page_num=2,
        bbox=bbox2,
        rows=[["H1", "H2", "H3"], ["V4", "V5", "V6"]],
        cells=cells2_matching,
    )

    widths1 = CrossPageTableStitcher._compute_column_widths(t1)
    widths2 = CrossPageTableStitcher._compute_column_widths(t2_matching)
    assert len(widths1) == 3
    assert widths1[0] == pytest.approx(150.0)
    assert widths1[1] == pytest.approx(200.0)
    assert widths1[2] == pytest.approx(150.0)

    var_matching = CrossPageTableStitcher._compute_column_width_variance(widths1, widths2)
    assert var_matching == pytest.approx(0.0)

    stitched_ok = CrossPageTableStitcher.stitch_tables([t1, t2_matching])
    assert len(stitched_ok) == 1
    assert stitched_ok[0].is_stitched is True
    assert stitched_ok[0].row_count == 3  # Header + 2 data rows

    # Table 3 on page 2: Strongly divergent column widths: (300, 50, 150) -> diffs are (150, -150, 0) -> variance is 15000 >> 625
    cells3_divergent = [
        TableCell(row_idx=0, col_idx=0, text="H1", bbox=BoundingBox(50, 50, 350, 80, page=2)),
        TableCell(row_idx=0, col_idx=1, text="H2", bbox=BoundingBox(350, 50, 400, 80, page=2)),
        TableCell(row_idx=0, col_idx=2, text="H3", bbox=BoundingBox(400, 50, 550, 80, page=2)),
        TableCell(row_idx=1, col_idx=0, text="V7", bbox=BoundingBox(50, 80, 350, 110, page=2)),
        TableCell(row_idx=1, col_idx=1, text="V8", bbox=BoundingBox(350, 80, 400, 110, page=2)),
        TableCell(row_idx=1, col_idx=2, text="V9", bbox=BoundingBox(400, 80, 550, 110, page=2)),
    ]
    t3_divergent = TableBlock(
        page_num=2,
        bbox=bbox2,
        rows=[["H1", "H2", "H3"], ["V7", "V8", "V9"]],
        cells=cells3_divergent,
    )

    widths3 = CrossPageTableStitcher._compute_column_widths(t3_divergent)
    var_divergent = CrossPageTableStitcher._compute_column_width_variance(widths1, widths3)
    assert var_divergent > 625.0

    stitched_fail = CrossPageTableStitcher.stitch_tables([t1, t3_divergent])
    assert len(stitched_fail) == 2, "Tables with divergent column width variance must not stitch"


def test_non_index_numeric_column_not_treated_as_index():
    """Verify that numeric columns representing data (power, years, prices) are not misclassified as sequence index."""
    bbox = BoundingBox(0, 0, 100, 100)
    # Horsepower column with distinct fluctuating integers
    raw_rows_power = [
        ["马力", "车型", "加速"],
        ["400", "轿跑版", "3.5s"],
        ["300", "标准版", "4.8s"],
        ["500", "赛道版", "2.9s"],
    ]
    tbl_power = TableBlock(page_num=1, bbox=bbox, rows=raw_rows_power)
    assert tbl_power._is_index_column(0, 1) is False, "Horsepower values must not be classified as index column"

    # Year column with non-unit increments
    raw_rows_years = [
        ["款型年份", "车型", "版本"],
        ["2020", "Model S", "Long Range"],
        ["2022", "Model S", "Plaid"],
        ["2025", "Model S", "Ultra"],
    ]
    tbl_years = TableBlock(page_num=1, bbox=bbox, rows=raw_rows_years)
    assert tbl_years._is_index_column(0, 1) is False, "Years with non-unit increments must not be classified as index column"


def test_bidirectional_fill_with_multilevel_hierarchy_isolation():
    """Verify bidirectional fill isolates child column fills strictly within parent category boundaries."""
    bbox = BoundingBox(0, 0, 100, 100)
    raw_rows = [
        ["一级分类", "二级模块", "具体参数"],
        ["动力系统", "电机总成", "前驱200kW"],
        ["", "", "后驱300kW"],           # Forward-fills 电机总成 under 动力系统
        ["底盘系统", "", "前双叉臂"],        # Backward-fills 悬架总成 under 底盘系统; MUST NOT inherit 电机总成 from 动力系统!
        ["", "悬架总成", "后五连杆"],
    ]
    tbl = TableBlock(page_num=1, bbox=bbox, rows=raw_rows)
    filled = tbl.normalize_bidirectional_fill()

    assert filled[1][0] == "动力系统"
    assert filled[1][1] == "电机总成"

    assert filled[2][0] == "动力系统"
    assert filled[2][1] == "电机总成", "Row 2 must inherit 电机总成 from Row 1 within 动力系统"

    assert filled[3][0] == "底盘系统"
    assert filled[3][1] == "悬架总成", "Row 3 must inherit 悬架总成 backward from Row 4 within 底盘系统, not bleed from 动力系统"

    assert filled[4][0] == "底盘系统"
    assert filled[4][1] == "悬架总成"


def test_column_width_variance_with_unobserved_columns():
    """Verify column width variance computation ignores unobserved (0.0 width) columns instead of failing."""
    widths1 = [150.0, 0.0, 150.0]  # Column 1 had no single-span cell bboxes
    widths2 = [150.0, 200.0, 150.0]

    var = CrossPageTableStitcher._compute_column_width_variance(widths1, widths2)
    assert var == pytest.approx(0.0), "Missing cell bboxes in one column should not produce false huge variance"


