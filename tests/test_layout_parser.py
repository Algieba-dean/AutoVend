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
    LayoutAwareParser,
    MinerUDoclingEngine,
    ParsedDocument,
    PyMuPDFPlumberEngine,
    TableBlock,
    TableCell,
    TextSection,
    UnstructuredEngine,
)

PDF_SAMPLE_PATH = Path("/home/algieba/projects/hackthon/AutoVend/data/sample_specs/xiaomi_su7_ultra_specs.pdf")


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
    u9_path = Path("/home/algieba/projects/hackthon/AutoVend/data/sample_specs/byd_yangwang_u9_specs.pdf")
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
