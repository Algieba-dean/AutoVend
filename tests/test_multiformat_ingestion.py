"""
Comprehensive unit and integration test suite for AutoVend Multi-Format Enterprise Ingestion.
Tests:
1. Format Autodetection (Magic bytes & extensions)
2. Excel Parser (Multi-sheet, merged cells, formulas, formatting, TableBlocks)
3. Word Parser (Hierarchical headings H1-H4, complex tables with cell spans, lists, callouts, footnotes)
4. PowerPoint Parser (Slide sequence, spatial reading order, embedded tables, speaker notes)
5. Image Parser & Diagnostics (Dimensions, DPI, aspect ratio, blur/contrast, EXIF, pluggable OCR)
6. Structured & Plain Text (CSV/TSV, Markdown, HTML, JSON, TOML, RTF)
7. Edge Cases (0-byte empty files, single cell, large tables, special characters, corrupted files)
8. Pipeline & Retrieval Integration (HierarchicalChunker, ParentChildRetriever, IncrementalIngestion, Freshness)
"""

import datetime
import tempfile
import time
from pathlib import Path

import openpyxl
import pytest
from PIL import Image

from src.filter.vehicle_db import VehicleDB
from src.ingestion.freshness import DataFreshnessEngine, FreshnessStatus
from src.ingestion.hierarchical_chunker import ChunkType, HierarchicalChunker
from src.ingestion.layout_parser import BoundingBox
from src.ingestion.multiformat_parser import (
    BaseOCREngine,
    CsvTsvParser,
    DocumentFormat,
    ExcelParser,
    ImageParser,
    MultiFormatParser,
    OCRLine,
    OCRResult,
    OfflineMockOCREngine,
    PowerPointParser,
    StructuredTextParser,
    TableCell,
    VisionAPIOCREngine,
    WordParser,
    extract_exif_metadata,
    extract_image_diagnostics,
    extract_ole2_text,
)
from src.ingestion.pipeline import IncrementalIngestionPipeline
from src.retrieval.parent_child_retriever import ParentChildRetriever

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_specs"


# ── 1. Format Autodetection Tests ────────────────────────────────────────


def test_format_autodetection():
    parser = MultiFormatParser()

    assert parser.detect_format(SAMPLE_DIR / "Xiaomi_SU7_Trims.xlsx") == DocumentFormat.EXCEL
    assert parser.detect_format(SAMPLE_DIR / "Zeekr_001_Service_Manual.docx") == DocumentFormat.WORD
    assert parser.detect_format(SAMPLE_DIR / "NIO_ET9_Launch_Deck.pptx") == DocumentFormat.POWERPOINT
    assert parser.detect_format(SAMPLE_DIR / "Aito_M9_Spec_Sheet.png") == DocumentFormat.IMAGE
    assert parser.detect_format(SAMPLE_DIR / "Battery_Degradation_4680.csv") == DocumentFormat.CSV
    assert parser.detect_format(SAMPLE_DIR / "xiaomi_su7_ultra_specs.pdf") == DocumentFormat.PDF

    # Magic byte inspection for PNG and JPEG without extension
    with tempfile.NamedTemporaryFile(suffix="") as tmp:
        tmp.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        tmp.flush()
        assert parser.detect_format(Path(tmp.name)) == DocumentFormat.IMAGE

    with tempfile.NamedTemporaryFile(suffix="") as tmp:
        tmp.write(b"%PDF-1.7\n%...")
        tmp.flush()
        assert parser.detect_format(Path(tmp.name)) == DocumentFormat.PDF


# ── 2. Excel Parsing Tests ───────────────────────────────────────────────


def test_excel_multi_sheet_and_merged_cells():
    excel_file = SAMPLE_DIR / "Xiaomi_SU7_Trims.xlsx"
    assert excel_file.exists(), f"Sample Excel file missing at {excel_file}"

    parser = ExcelParser()
    doc = parser.parse(excel_file)

    assert doc.metadata["format"] == "excel"
    assert len(doc.tables) == 3, f"Expected 3 sheets/tables, found {len(doc.tables)}"
    assert len(doc.sections) == 3

    # Check sheet names
    sheet_names = doc.metadata["sheet_names"]
    assert "Standard_标准版" in sheet_names
    assert "Pro_超长续航版" in sheet_names
    assert "Max_高性能版" in sheet_names

    # Check merged cell resolution on standard sheet table
    t_std = doc.tables[0]
    assert t_std.metadata["sheet_name"] == "Standard_标准版"
    # Category "动力与底盘总成" was merged across rows 3-6 column A
    # Verify that in rows 2, 3, 4, 5 (0-indexed: row 2 to 5), column 0 is non-empty and correctly propagated
    norm_rows = t_std.rows
    for r_idx in range(2, 6):
        assert norm_rows[r_idx][0] == "动力与底盘总成", (
            f"Row {r_idx} Col 0 failed merged propagation: {norm_rows[r_idx][0]}"
        )

    # Check formula evaluation or formula string preservation
    # Row 14 (15th row, index 14) has formula for net price
    pricing_row = norm_rows[14]
    assert "实际购车裸车总价" in pricing_row[1]
    assert pricing_row[2] != "", "Pricing formula calculation/fallback should not be empty"

    # Markdown and HTML conversions
    md = t_std.to_markdown()
    assert "动力与底盘总成" in md
    assert "驱动电机型式" in md
    assert "后置单电机 (后驱)" in md

    html = t_std.to_html()
    assert '<table border="1" class="autovend-table">' in html


def test_excel_empty_sheet_and_formatting():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "DataSheet"
    ws1["A1"] = "售价 (万)"
    ws1["B1"] = 29.9000
    ws1["A2"] = "发布日期"
    ws1["B2"] = datetime.date(2025, 3, 28)

    # Empty sheet
    wb.create_sheet(title="EmptySheet")
    wb.save(tmp_path)

    parser = ExcelParser()
    doc = parser.parse(tmp_path)

    assert len(doc.tables) == 1
    assert len(doc.sections) == 2  # Includes empty sheet section
    assert doc.sections[1].metadata.get("is_empty") is True
    assert "2025-03-28" in doc.tables[0].to_markdown()

    tmp_path.unlink()


# ── 3. Word Parsing Tests ────────────────────────────────────────────────


def test_word_heading_hierarchy_and_complex_tables():
    docx_file = SAMPLE_DIR / "Zeekr_001_Service_Manual.docx"
    assert docx_file.exists(), f"Sample DOCX file missing at {docx_file}"

    parser = WordParser()
    doc = parser.parse(docx_file)

    assert doc.metadata["format"] == "word"
    assert "极氪" in doc.vehicle_model or "001" in doc.vehicle_model
    assert len(doc.tables) >= 1

    # Check heading levels and breadcrumb paths
    sec_titles = [s.title for s in doc.sections]
    assert any("动力电池与高压电驱系统维保规程" in t for t in sec_titles)
    assert any("冷却回路与防冻液更换周期" in t for t in sec_titles)

    # Check breadcrumbs of sub-heading
    sub_sec = next(s for s in doc.sections if "冷却回路" in s.title)
    assert sub_sec.level == 2
    assert len(sub_sec.breadcrumb_path) >= 2

    # Check warning callout extraction (format `> `)
    all_content = "\n\n".join(s.content for s in doc.sections)
    assert "> 【高压维保重大安全警告】" in all_content or "重大安全警告" in all_content

    # Check torque table with merged cell resolution
    table = doc.tables[0]
    assert table.row_count == 6
    assert table.col_count == 5

    # Check vertical merge: "前悬挂双叉臂总成" in rows 1 and 2
    assert table.rows[1][0] == "前悬挂双叉臂总成"
    assert table.rows[2][0] == "前悬挂双叉臂总成"

    # Check multi-paragraph cell resolution
    row1_method = table.rows[1][3]
    assert "扭矩法" in row1_method
    assert "90°" in row1_method

    # Check Markdown representation
    md = table.to_markdown()
    assert "| 前悬挂双叉臂总成 |" in md
    assert "达克罗涂层螺栓" in md


# ── 4. PowerPoint Parsing Tests ──────────────────────────────────────────


def test_powerpoint_slides_spatial_and_notes():
    pptx_file = SAMPLE_DIR / "NIO_ET9_Launch_Deck.pptx"
    assert pptx_file.exists(), f"Sample PPTX file missing at {pptx_file}"

    parser = PowerPointParser()
    doc = parser.parse(pptx_file)

    assert doc.metadata["format"] == "powerpoint"
    assert doc.pages == 4
    assert len(doc.sections) == 4
    assert len(doc.tables) == 1

    # Slide 1 Title
    assert "蔚来 ET9" in doc.sections[0].title or "蔚来 ET9" in doc.sections[0].content

    # Slide 2 Spatial layout and speaker notes
    s2 = doc.sections[1]
    assert "全域900V高压" in s2.title or "核心技术架构" in s2.title
    assert "925V" in s2.content
    assert "神玑 NX9031" in s2.content
    assert "天行智能全主动底盘" in s2.content
    assert s2.metadata.get("speaker_notes") != "", "Slide 2 speaker notes should be captured"
    assert "> **演讲者备注**" in s2.content

    # Slide 3 Embedded table
    t3 = doc.tables[0]
    assert t3.row_count == 6
    assert t3.col_count == 4
    assert "蔚来 ET9" in t3.headers[1]
    assert "全主动集成液压悬挂" in t3.to_markdown()

    # Slide 4 Deep speaker notes
    s4 = doc.sections[3]
    assert "香槟塔" in s4.content
    assert "微秒级" in s4.metadata.get("speaker_notes", "")


# ── 5. Image Diagnostics & OCR Tests ─────────────────────────────────────


def test_image_diagnostics_and_exif():
    img_file = SAMPLE_DIR / "Aito_M9_Spec_Sheet.png"
    assert img_file.exists(), f"Sample Image missing at {img_file}"

    img = Image.open(str(img_file))
    diag = extract_image_diagnostics(img)

    assert diag.width == 1200
    assert diag.height == 900
    assert diag.aspect_ratio == pytest.approx(1.333, abs=0.01)
    assert diag.mode == "RGB"
    assert diag.channels == 3
    assert diag.contrast_score > 0.0
    assert diag.blur_score > 0.0
    assert isinstance(diag.is_blurry, bool)

    # EXIF tags
    exif = extract_exif_metadata(img)
    assert exif.get("Make") == "AutoVend Enterprise Camera"
    assert exif.get("Model") == "Aito-M9-Scanner-Pro"
    assert exif.get("Software") == "AutoVend Image Engine 2.0"


def test_image_parser_with_ocr():
    img_file = SAMPLE_DIR / "Aito_M9_Spec_Sheet.png"
    mock_lines = [
        ("问界 M9 旗舰车型配置规格表 (AITO M9 Spec Sheet)", 40, 50, 720, 80),
        ("车身尺寸: 5230mm × 1999mm × 1800mm, 轴距: 3110mm", 40, 100, 680, 125),
        ("动力总成: 前后双电机智能四驱系统, 最大总功率 365kW / 390kW", 40, 140, 710, 165),
        ("纯电续航: CLTC 综合工况 630km (纯电版) / 综合续航 1402km (增程版)", 40, 180, 740, 205),
        ("智驾系统: 华为乾崑智驾 ADS 3.0 高阶智能驾驶辅助", 40, 220, 650, 245),
        ("指导售价: 46.98 万元 - 56.98 万元 (增程Max/Ultra, 纯电Max/Ultra)", 40, 260, 700, 285),
    ]
    parser = ImageParser(ocr_engine=OfflineMockOCREngine(mock_lines=mock_lines))
    doc = parser.parse(img_file)

    assert doc.metadata["format"] == "image"
    assert "问界" in doc.vehicle_model or "M9" in doc.vehicle_model
    assert len(doc.sections) == 1
    assert "问界 M9" in doc.sections[0].content
    assert "5230mm" in doc.sections[0].content

    # Structured table created from parameter lines
    assert len(doc.tables) >= 1
    t = doc.tables[0]
    assert t.row_count >= 3
    assert "车身尺寸" in t.to_markdown()
    assert "华为乾崑智驾" in t.to_markdown()


def test_offline_mock_ocr_honest_degradation_when_no_mock_lines():
    """Verify that OfflineMockOCREngine honestly degrades instead of matching filename substrings."""
    img_file = SAMPLE_DIR / "Aito_M9_Spec_Sheet.png"
    engine = OfflineMockOCREngine()
    res = engine.extract_text_and_boxes(img_file)
    assert res.metadata.get("is_degraded") is True
    assert res.full_text == ""
    assert res.lines == []


def test_ocr_custom_adapter():
    class CustomTestOCREngine(BaseOCREngine):
        def extract_text_and_boxes(self, image_path):
            line = "测试车型: 超级纯电MPV\n最大续航: 1000km"
            bbox = BoundingBox(0, 0, 100, 50)
            ocr_line = OCRLine(text="测试车型: 超级纯电MPV", bbox=bbox, confidence=0.99)
            return OCRResult(full_text=line, lines=[ocr_line], confidence=0.99, metadata={"engine": "custom"})

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_p = Path(tmp.name)
    Image.new("RGB", (100, 100), color="white").save(tmp_p)

    parser = ImageParser(ocr_engine=CustomTestOCREngine())
    doc = parser.parse(tmp_p)

    assert "超级纯电MPV" in doc.sections[0].content
    assert doc.metadata["ocr_confidence"] == 0.99
    tmp_p.unlink()


# ── 6. Structured & Plain Text Tests ─────────────────────────────────────


def test_csv_tsv_parser():
    csv_file = SAMPLE_DIR / "Battery_Degradation_4680.csv"
    assert csv_file.exists()

    parser = CsvTsvParser()
    doc = parser.parse(csv_file)

    assert doc.metadata["format"] == "csv"
    assert doc.metadata["delimiter"] == ","
    assert len(doc.tables) == 1

    tbl = doc.tables[0]
    assert "Cycle_Number" in tbl.headers[0]
    assert "Capacity_Retention_Percent" in tbl.headers[1]
    assert tbl.row_count > 15
    assert "SEI Formation Stabilization" in tbl.to_markdown()

    # TSV parsing
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write("Model\tPrice\tRange\nModel3\t23.19\t606km\nModelY\t24.99\t554km\n")
        tsv_path = Path(tmp.name)

    tsv_doc = parser.parse(tsv_path)
    assert tsv_doc.metadata["format"] == "tsv"
    assert tsv_doc.metadata["delimiter"] == "\t"
    assert tsv_doc.tables[0].row_count == 3
    tsv_path.unlink()


def test_markdown_and_html_parser():
    parser = StructuredTextParser()

    # Markdown with tables and headers
    md_content = """# 小米汽车产品白皮书

## 1. 核心技术架构
小米汽车全系标配澎湃OS车载操作系统。

| 车型 | 指导价 (万) | 续航 (km) |
| --- | --- | --- |
| SU7 标准版 | 21.59 | 700 |
| SU7 Max | 29.99 | 800 |

## 2. 补能网络
支持 800V 超充。
"""
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(md_content)
        md_path = Path(tmp.name)

    doc_md = parser.parse(md_path)
    assert doc_md.metadata["format"] == "markdown"
    assert len(doc_md.sections) >= 2
    assert len(doc_md.tables) == 1
    assert doc_md.tables[0].headers == ["车型", "指导价 (万)", "续航 (km)"]
    md_path.unlink()

    # HTML with table
    html_content = """<!DOCTYPE html>
<html>
<body>
  <h1>新能源乘用车购车补贴名录</h1>
  <table>
    <caption>2026年新能源免征购置税车型</caption>
    <tr><th>品牌</th><th>车型名称</th><th>电池类型</th></tr>
    <tr><td>蔚来</td><td>ET9</td><td>46105三元锂</td></tr>
  </table>
</body>
</html>"""
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(html_content)
        html_path = Path(tmp.name)

    doc_html = parser.parse(html_path)
    assert doc_html.metadata["format"] == "html"
    assert len(doc_html.tables) == 1
    assert "2026年新能源免征购置税车型" in doc_html.tables[0].title
    html_path.unlink()


def test_json_and_toml_parser():
    parser = StructuredTextParser()

    # JSON specifications
    json_data = [
        {"trim": "Standard", "motor": "Single", "hp": 299},
        {"trim": "Max", "motor": "Dual", "hp": 673},
    ]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as tmp:
        import json
        json.dump(json_data, tmp)
        json_path = Path(tmp.name)

    doc_json = parser.parse(json_path)
    assert doc_json.metadata["format"] == "json"
    assert len(doc_json.tables) == 1
    assert doc_json.tables[0].headers == ["trim", "motor", "hp"]
    json_path.unlink()

    # TOML specifications
    toml_content = """
    [vehicle]
    car_model = "SU7 Max"
    brand = "xiaomi"
    price = 29.99
    horsepower = 673
    """
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(toml_content)
        toml_path = Path(tmp.name)

    doc_toml = parser.parse(toml_path)
    assert doc_toml.metadata["format"] == "toml"
    assert len(doc_toml.tables) == 1
    assert "vehicle.car_model" in doc_toml.tables[0].to_markdown()
    toml_path.unlink()


# ── 7. Edge Cases & Robustness Tests ─────────────────────────────────────


def test_edge_case_empty_files():
    parser = MultiFormatParser()

    # 0-byte file with various extensions
    for ext in [".txt", ".csv", ".tsv", ".json", ".md", ".html"]:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_p = Path(tmp.name)

        doc = parser.parse(tmp_p)
        assert doc.metadata.get("is_empty") is True or len(doc.tables) == 0
        tmp_p.unlink()


def test_edge_case_nonexistent_file():
    parser = MultiFormatParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(Path("/nonexistent/path/spec.xlsx"))


def test_edge_case_large_table():
    parser = CsvTsvParser()
    rows = [["ID", "Voltage", "Current", "Temp"]]
    for i in range(250):
        rows.append([str(i), f"{3.7 + i*0.001:.3f}", "10.5", "25.2"])

    content = "\n".join([",".join(r) for r in rows])
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_p = Path(tmp.name)

    doc = parser.parse(tmp_p)
    assert doc.tables[0].row_count == 251
    tmp_p.unlink()


def test_edge_case_special_unicode_and_characters():
    parser = StructuredTextParser()
    content = """# 车型特殊字符测试 ⚡ 🚗

| 符号参数 | 转义实体 & 状态 | 备注说明 |
| --- | --- | --- |
| 电机转速 > 21,000 rpm | <tag>测试 & 验证</tag> | 包含 | 管道符与双引号 "OK" |
"""
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_p = Path(tmp.name)

    doc = parser.parse(tmp_p)
    assert len(doc.tables) == 1
    md = doc.tables[0].to_markdown()
    assert "21,000 rpm" in md
    tmp_p.unlink()


# ── 8. Integration: Chunker, Retriever & Pipeline ────────────────────────


def test_hierarchical_chunker_integration():
    parser = MultiFormatParser()
    chunker = HierarchicalChunker()

    # Excel document chunking
    doc_excel = parser.parse(SAMPLE_DIR / "Xiaomi_SU7_Trims.xlsx")
    chunks_excel = chunker.chunk_document(doc_excel)

    assert len(chunks_excel["tables"]) == 3
    assert len(chunks_excel["parents"]) >= 3
    assert len(chunks_excel["children"]) > 10

    # Ensure table parent chunks have format metadata
    for t_chunk in chunks_excel["tables"]:
        assert t_chunk.chunk_type == ChunkType.TABLE
        assert t_chunk.metadata.get("is_table") is True
        assert "工作表名称" in t_chunk.content

    # Word document chunking
    doc_word = parser.parse(SAMPLE_DIR / "Zeekr_001_Service_Manual.docx")
    chunks_word = chunker.chunk_document(doc_word)
    assert len(chunks_word["tables"]) == 1
    assert len(chunks_word["parents"]) >= 3

    # PowerPoint document chunking
    doc_pptx = parser.parse(SAMPLE_DIR / "NIO_ET9_Launch_Deck.pptx")
    chunks_pptx = chunker.chunk_document(doc_pptx)
    assert len(chunks_pptx["tables"]) == 1
    assert len(chunks_pptx["parents"]) >= 4


def test_parent_child_retriever_multi_format():
    parser = MultiFormatParser()
    retriever = ParentChildRetriever()

    # Index Excel & Word & PPTX
    doc_excel = parser.parse(SAMPLE_DIR / "Xiaomi_SU7_Trims.xlsx")
    doc_word = parser.parse(SAMPLE_DIR / "Zeekr_001_Service_Manual.docx")
    doc_pptx = parser.parse(SAMPLE_DIR / "NIO_ET9_Launch_Deck.pptx")

    retriever.index_document(doc_excel)
    retriever.index_document(doc_word)
    retriever.index_document(doc_pptx)

    # Query 1: Search Excel Specs
    res_excel = retriever.search("SU7 Pro 续航里程与电池容量", top_k_parents=2)
    assert len(res_excel.results) > 0
    formatted_ctx = res_excel.format_llm_context(max_parents=1)
    assert "830 km" in formatted_ctx or "94.3 kWh" in formatted_ctx

    # Query 2: Search Word Torque Specs
    res_word = retriever.search("双叉臂 前下摆臂 紧固力矩", top_k_parents=2)
    assert len(res_word.results) > 0
    formatted_word = res_word.format_llm_context(max_parents=1)
    assert "120" in formatted_word or "前悬挂双叉臂" in formatted_word

    # Query 3: Search PPTX Architecture
    res_pptx = retriever.search("ET9 全域900V 与 神玑芯片", top_k_parents=2)
    assert len(res_pptx.results) > 0
    formatted_pptx = res_pptx.format_llm_context(max_parents=1)
    assert "925V" in formatted_pptx or "神玑" in formatted_pptx


def test_incremental_pipeline_and_freshness_engine(tmp_path):
    freshness = DataFreshnessEngine()
    test_db = VehicleDB(db_path=str(tmp_path / "freshness_test.db"))
    pipeline = IncrementalIngestionPipeline(db=test_db, freshness_engine=freshness)

    csv_path = SAMPLE_DIR / "Battery_Degradation_4680.csv"

    # Ingest file first time
    s1 = pipeline.ingest_file(csv_path)
    assert s1.created_count == 1
    assert s1.unchanged_count == 0

    # Ingest file second time (unmodified -> unchanged)
    s2 = pipeline.ingest_file(csv_path)
    assert s2.created_count == 0
    assert s2.unchanged_count == 1

    # Check freshness tracking
    f_status, diag = freshness.assess_document_freshness(csv_path.name)
    assert f_status == FreshnessStatus.FRESH
    assert diag["ttl_days"] == 180
    assert diag["metadata"]["table_count"] == 1

    # Simulate aged document reaching TTL threshold
    old_ts = time.time() - (190 * 86400)
    freshness.register_document_freshness("Aged_Spec.xlsx", last_modified_ts=old_ts, ttl_days=180)
    expired_status, exp_diag = freshness.assess_document_freshness("Aged_Spec.xlsx")
    assert expired_status == FreshnessStatus.EXPIRED
    assert exp_diag["age_days"] >= 180


# ── 9. Advanced Format & Deep Edge Case Tests ────────────────────────────


def test_markdown_table_at_eof():
    parser = StructuredTextParser()
    content = "# 标题\n\n| 列A | 列B |\n| --- | --- |\n| 值1 | 值2 |"
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    doc = parser.parse(tmp_path)
    assert len(doc.tables) == 1, "Markdown table at EOF should be preserved"
    assert doc.tables[0].headers == ["列A", "列B"]
    assert doc.tables[0].rows[1] == ["值1", "值2"]
    tmp_path.unlink()


def test_html_hierarchical_sections_and_breadcrumbs():
    parser = StructuredTextParser()
    html_content = """<!DOCTYPE html>
<html>
<head><title>纯电超跑参数手册</title></head>
<body>
  <h1>极氪汽车</h1>
  <p>极氪智能科技官方文档。</p>
  <h2>极氪 001 FR</h2>
  <p>四电机分布式电驱系统。</p>
  <h3>热管理规程</h3>
  <p>PTC加热与热泵协同工作。</p>
</body>
</html>"""
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(html_content)
        tmp_path = Path(tmp.name)

    doc = parser.parse(tmp_path)
    assert len(doc.sections) >= 3
    sec_fr = next(s for s in doc.sections if "极氪 001 FR" in s.title)
    assert sec_fr.level == 2
    assert "极氪汽车" in sec_fr.breadcrumb_path
    sec_tm = next(s for s in doc.sections if "热管理规程" in s.title)
    assert sec_tm.level == 3
    assert len(sec_tm.breadcrumb_path) >= 2
    tmp_path.unlink()


def test_rtf_unicode_and_hex_decoding():
    parser = StructuredTextParser()
    rtf_content = r"{\rtf1\ansi\ansicpg936 \b \u26497?\u23458?001 \b0 \'b5\'e7\'bb\'fa}"
    with tempfile.NamedTemporaryFile(suffix=".rtf", delete=False, mode="w", encoding="latin1") as tmp:
        tmp.write(rtf_content)
        tmp_path = Path(tmp.name)

    doc = parser.parse(tmp_path)
    assert doc.metadata["format"] == "rtf"
    assert "极客001" in doc.raw_text or "极" in doc.raw_text
    tmp_path.unlink()


def test_json_union_keys_and_nested_dict():
    parser = StructuredTextParser()
    json_data = [
        {"model": "SU7", "specs": {"hp": 299, "range": 700}},
        {"model": "SU7 Max", "specs": {"hp": 673}, "track_mode": True},
    ]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as tmp:
        import json
        json.dump(json_data, tmp)
        tmp_path = Path(tmp.name)

    doc = parser.parse(tmp_path)
    assert len(doc.tables) == 1
    tbl = doc.tables[0]
    assert "model" in tbl.headers
    assert "specs.hp" in tbl.headers
    assert "specs.range" in tbl.headers
    assert "track_mode" in tbl.headers
    assert tbl.row_count == 3
    tmp_path.unlink()


def test_vision_api_ocr_engine_adapter():
    vision_engine = VisionAPIOCREngine()
    assert vision_engine.api_key is None or isinstance(vision_engine.api_key, str)

    img_file = SAMPLE_DIR / "Aito_M9_Spec_Sheet.png"
    res = vision_engine.extract_text_and_boxes(img_file)
    assert res.metadata["engine"] == "vision_api"
    assert res.metadata.get("is_degraded") is True
    assert res.full_text == ""

    class MockCompletions:
        def create(self, model, messages, **kwargs):
            class MockChoice:
                class MockMessage:
                    content = '{"text": "识别车型: 极氪001\\n电机功率: 400kW", "lines": [{"text": "识别车型: 极氪001", "box_2d": [10, 10, 30, 200]}]}'
                message = MockMessage()
            class MockResponse:
                choices = [MockChoice()]
            return MockResponse()

    class MockChat:
        completions = MockCompletions()

    class MockClient:
        chat = MockChat()

    custom_vision = VisionAPIOCREngine(api_key="mock_key", client=MockClient())
    res_custom = custom_vision.extract_text_and_boxes(img_file)
    assert "极氪001" in res_custom.full_text
    assert len(res_custom.lines) >= 1
    assert res_custom.metadata["engine"] == "vision_api"


def test_word_footnotes_and_captions_metadata():
    docx_file = SAMPLE_DIR / "Zeekr_001_Service_Manual.docx"
    parser = WordParser()
    doc = parser.parse(docx_file)

    assert "footnotes" in doc.metadata or "endnotes" in doc.metadata
    assert "captions" in doc.metadata
    for s in doc.sections:
        assert "页眉" not in s.title


def test_powerpoint_table_cell_spans():
    pptx_file = SAMPLE_DIR / "NIO_ET9_Launch_Deck.pptx"
    parser = PowerPointParser()
    doc = parser.parse(pptx_file)

    assert len(doc.tables) == 1
    tbl = doc.tables[0]
    assert len(tbl.cells) > 0
    first_cell = tbl.cells[0]
    assert isinstance(first_cell, TableCell)
    assert hasattr(first_cell, "row_span")
    assert hasattr(first_cell, "col_span")


def test_table_atomicity_in_chunker_no_raw_markdown_in_sections():
    excel_file = SAMPLE_DIR / "Xiaomi_SU7_Trims.xlsx"
    doc_excel = ExcelParser().parse(excel_file)
    for sec in doc_excel.sections:
        assert not sec.content.strip().startswith("|")
        assert "| --- |" not in sec.content

    chunker = HierarchicalChunker(child_max_tokens=100)
    chunks = chunker.chunk_document(doc_excel)
    for child in chunks["children"]:
        assert not (child.content.startswith("|") and child.content.endswith("|") and "\n|" not in child.content)


def test_legacy_ole2_fallback():
    header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    utf16_text = "极氪汽车服务技术手册".encode("utf-16le")
    ascii_text = b"AutoVend Legacy Binary Diagnostic Stream"
    payload = header + b"\x00" * 32 + utf16_text + b"\x00" * 32 + ascii_text

    with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)

    extracted = extract_ole2_text(tmp_path)
    assert "极氪汽车服务技术手册" in extracted or "AutoVend Legacy" in extracted

    parser = WordParser()
    doc = parser.parse(tmp_path)
    assert doc.sections[0].content != ""
    assert doc.metadata["format"] == "word"
    tmp_path.unlink()


def test_excel_parser_openpyxl_missing_graceful_fallback(monkeypatch, tmp_path):
    """Verify ExcelParser does not crash if openpyxl is not installed, gracefully falling back."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "openpyxl":
            raise ImportError("No module named 'openpyxl' (simulated missing dependency)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    # Legacy OLE2 fake excel file
    header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    utf16_text = "比亚迪汉EV参数表".encode("utf-16le")
    payload = header + b"\x00" * 32 + utf16_text
    test_xls = tmp_path / "test_missing_openpyxl.xls"
    test_xls.write_bytes(payload)

    parser = ExcelParser()
    # Must not raise ModuleNotFoundError or Crash!
    doc = parser.parse(test_xls)
    assert doc is not None
    assert doc.metadata["format"] == "excel"


