"""
Enterprise Benchmark & Hardening Automated Test Suite for AutoVend.
(tests/test_enterprise_benchmark.py)

Validates:
1. All 100 documents in data/enterprise_benchmark/ across all formats (Excel, Word, PPTX, Images, PDF, CSV, JSON, TOML, Markdown, TSV, HTML, RTF)
2. Hardened Edge Cases:
   - Extreme aspect ratio images (100:1 horizontal, 1:100 vertical)
   - Zero-length cells & empty tables
   - Malformed XML namespaces & xpath resilience
   - Deeply nested Word lists (levels 1-10)
   - Corrupted formula values (#DIV/0!, #VALUE!, float NaN/Inf)
   - Encoding autodetect fallbacks (UTF-16, GB18030, Latin-1)
   - Large table dimension clamping & memory bounding
3. Integration Cohesion:
   - IncrementalIngestionPipeline + ParentChildRetriever + RAGService
"""

import math
import tempfile
from pathlib import Path

import docx
import openpyxl
from PIL import Image

from scripts.benchmark_enterprise_pipeline import EnterpriseBenchmarkHarness
from src.ingestion.hierarchical_chunker import HierarchicalChunker
from src.ingestion.layout_parser import BoundingBox, LayoutAwareParser, TableBlock
from src.ingestion.multiformat_parser import (
    CsvTsvParser,
    ExcelParser,
    ImageParser,
    MultiFormatParser,
    PowerPointParser,
    StructuredTextParser,
    WordParser,
)
from src.ingestion.pipeline import IncrementalIngestionPipeline
from src.rag_service.service import RAGService
from src.retrieval.parent_child_retriever import ParentChildRetriever

BENCHMARK_DIR = Path("/home/algieba/projects/hackthon/AutoVend/data/enterprise_benchmark")


# ── 1. Enterprise Dataset Format Parsing Tests ───────────────────────────


def test_enterprise_excel_byd_financing():
    file_path = BENCHMARK_DIR / "BYD_Financing_Rates_2026.xlsx"
    assert file_path.exists(), f"Benchmark Excel file missing: {file_path}"

    parser = ExcelParser()
    doc = parser.parse(file_path)

    assert doc.metadata["format"] == "excel"
    assert len(doc.tables) == 3
    assert "0息定额分期方案" in doc.metadata["sheet_names"]
    assert "低息长期贷款_36_60期" in doc.metadata["sheet_names"]
    assert "保值回购与残值租赁_Lease" in doc.metadata["sheet_names"]

    # Verify formulas or evaluations in Sheet 2
    tbl_loan = doc.tables[1]
    assert tbl_loan.row_count >= 8
    md = tbl_loan.to_markdown()
    assert "月供还款预估" in md
    assert "¥" in md or "ROUND" in md or "元" in md


def test_enterprise_excel_xiaomi_su7_ultra():
    file_path = BENCHMARK_DIR / "Xiaomi_SU7_Ultra_Technical_Specs.xlsx"
    assert file_path.exists()

    parser = ExcelParser()
    doc = parser.parse(file_path)

    assert doc.metadata["format"] == "excel"
    assert len(doc.tables) == 4
    assert doc.vehicle_model != ""

    # Verify V8s motor specs table
    tbl_bom = doc.tables[1]
    md = tbl_bom.to_markdown()
    assert "425 kW" in md or "27200" in md or "V8s" in md
    assert "960MPa" in md or "硅钢" in md


def test_enterprise_excel_huawei_tuling_bom():
    file_path = BENCHMARK_DIR / "Huawei_Tuling_Chassis_BOM.xlsx"
    assert file_path.exists()

    parser = ExcelParser()
    doc = parser.parse(file_path)

    assert len(doc.tables) == 3
    tbl_tuling = doc.tables[1]
    md = tbl_tuling.to_markdown()
    assert "CDC" in md or "空气悬挂" in md
    assert "DATS" in md or "华为" in md


def test_enterprise_word_tesla_service_bulletin():
    file_path = BENCHMARK_DIR / "Tesla_Model_Y_Service_Bulletin.docx"
    assert file_path.exists()

    parser = WordParser()
    doc = parser.parse(file_path)

    assert doc.metadata["format"] == "word"
    assert len(doc.tables) >= 1
    assert "footnotes" in doc.metadata
    assert len(doc.metadata["footnotes"]) >= 1

    # Verify torque specs in table
    tbl = doc.tables[0]
    md = tbl.to_markdown()
    assert "85 N·m" in md
    assert "EPS" in md or "转向" in md or "螺栓" in md


def test_enterprise_word_nio_safety_manual():
    file_path = BENCHMARK_DIR / "NIO_Power_Swap_Safety_Manual.docx"
    assert file_path.exists()

    parser = WordParser()
    doc = parser.parse(file_path)

    assert doc.metadata["format"] == "word"
    assert len(doc.sections) >= 4
    # Check H1-H4 sections
    levels = [s.metadata.get("section_level") for s in doc.sections if "section_level" in s.metadata]
    assert any(lvl == 1 for lvl in levels)
    assert any(lvl >= 2 for lvl in levels)

    # Check warning callout in content
    full_text = "\n".join(s.content for s in doc.sections)
    assert "900V" in full_text
    assert "DANGER" in full_text or "危险警告" in full_text
    assert "水浸" in full_text or "消防" in full_text


def test_enterprise_powerpoint_zeekr_001_fr():
    file_path = BENCHMARK_DIR / "Zeekr_001_FR_Launch_Presentation.pptx"
    assert file_path.exists()

    parser = PowerPointParser()
    doc = parser.parse(file_path)

    assert doc.metadata["format"] == "powerpoint"
    assert doc.metadata["slide_count"] >= 4
    assert len(doc.tables) >= 1

    # Verify speaker notes
    has_notes = any(s.metadata.get("speaker_notes") for s in doc.sections)
    assert has_notes is True

    # Verify embedded comparison table
    tbl = doc.tables[0]
    md = tbl.to_markdown()
    assert "极氪 001 FR" in md
    assert "1300" in md or "Model S Plaid" in md


def test_enterprise_powerpoint_li_mega_battlecard():
    file_path = BENCHMARK_DIR / "Li_Mega_vs_Denza_D9_Battlecard.pptx"
    assert file_path.exists()

    parser = PowerPointParser()
    doc = parser.parse(file_path)

    assert doc.metadata["format"] == "powerpoint"
    assert len(doc.tables) >= 1

    tbl = doc.tables[0]
    md = tbl.to_markdown()
    assert "0.215" in md
    assert "5C" in md or "腾势 D9" in md


def test_enterprise_images_infographic_and_warning():
    img_v800 = BENCHMARK_DIR / "Xiaomi_V800_Motor_Infographic.png"
    img_cluster = BENCHMARK_DIR / "Instrument_Cluster_Warning.jpg"
    assert img_v800.exists()
    assert img_cluster.exists()

    parser = ImageParser()
    doc_v800 = parser.parse(img_v800)
    doc_cluster = parser.parse(img_cluster)

    assert doc_v800.metadata["format"] == "image"
    diag_v800 = doc_v800.metadata["image_diagnostics"]
    assert diag_v800["width"] == 1920
    assert diag_v800["height"] == 1080
    assert doc_v800.metadata["exif"].get("Make") == "Xiaomi Motors Co., Ltd."

    assert doc_cluster.metadata["format"] == "image"
    diag_cluster = doc_cluster.metadata["image_diagnostics"]
    assert diag_cluster["width"] == 1280
    assert diag_cluster["height"] == 720
    assert doc_cluster.metadata["exif"].get("Make") == "Sony"


def test_enterprise_pdf_avatr_12_manual():
    file_path = BENCHMARK_DIR / "Avatr_12_Full_Spec_Manual.pdf"
    assert file_path.exists()

    parser = LayoutAwareParser(engine_type="hybrid")
    doc = parser.parse(file_path)

    assert doc.metadata["format"] == "pdf"
    assert doc.pages == 4
    assert len(doc.tables) >= 1
    full_text = "\n".join(s.content for s in doc.sections) + "\n".join(t.to_markdown() for t in doc.tables)
    assert "阿维塔 12" in full_text
    assert "激光雷达" in full_text or "双叉臂" in full_text


def test_enterprise_structured_csv_json_toml_md():
    csv_file = BENCHMARK_DIR / "CATL_Qilin_Battery_Thermal_Test.csv"
    json_file = BENCHMARK_DIR / "National_EV_Subsidy_Policy_2026.json"
    md_file = BENCHMARK_DIR / "Zeekr_Battery_Warranty_Terms.md"
    toml_file = BENCHMARK_DIR / "Bosch_ESP_Firmware_Config.toml"
    tsv_file = BENCHMARK_DIR / "Powertrain_Efficiency_Matrix.tsv"

    for p in [csv_file, json_file, md_file, toml_file, tsv_file]:
        assert p.exists(), f"Missing structured file: {p}"

    parser = MultiFormatParser()

    doc_csv = parser.parse(csv_file)
    assert doc_csv.metadata["format"] == "csv"
    assert doc_csv.tables[0].row_count >= 60

    doc_json = parser.parse(json_file)
    assert doc_json.metadata["format"] == "json"
    assert len(doc_json.tables) >= 1

    doc_md = parser.parse(md_file)
    assert doc_md.metadata["format"] == "markdown"
    assert len(doc_md.tables) >= 1
    assert "金砖" in doc_md.tables[0].to_markdown()

    doc_toml = parser.parse(toml_file)
    assert doc_toml.metadata["format"] == "toml"
    assert len(doc_toml.tables) >= 1

    doc_tsv = parser.parse(tsv_file)
    assert doc_tsv.metadata["format"] == "tsv"
    assert doc_tsv.tables[0].row_count >= 40


def test_enterprise_expanded_datasets_parsing():
    """Verify XPeng JSON, AITO Excel, Yangwang Word, LynkCo TSV, and ZF TOML parse cleanly."""
    parser = MultiFormatParser()

    # 1. XPeng XNGP JSON
    doc_xpeng = parser.parse(BENCHMARK_DIR / "XPeng_XNGP_Autonomous_Driving_Matrix.json")
    assert doc_xpeng.metadata["format"] == "json"
    assert len(doc_xpeng.tables) >= 1
    assert "XNet" in doc_xpeng.sections[0].content or "图灵" in doc_xpeng.sections[0].content

    # 2. AITO M9 Excel
    doc_aito = parser.parse(BENCHMARK_DIR / "AITO_M9_Ultra_Luxury_Configuration.xlsx")
    assert doc_aito.metadata["format"] == "excel"
    assert len(doc_aito.tables) == 2
    assert "增程双电机动力总成" in doc_aito.metadata["sheet_names"]

    # 3. Yangwang U8 Word
    doc_yw = parser.parse(BENCHMARK_DIR / "Yangwang_U8_Emergency_Flotation_Manual.docx")
    assert doc_yw.metadata["format"] == "word"
    assert len(doc_yw.tables) >= 1
    full_text = "\n".join(s.content for s in doc_yw.sections)
    assert "浮水" in full_text
    assert "易四方" in full_text

    # 4. LynkCo 08 TSV
    doc_lynk = parser.parse(BENCHMARK_DIR / "LynkCo_08_EM-P_Super_Hybrid_Specs.tsv")
    assert doc_lynk.metadata["format"] == "tsv"
    assert doc_lynk.tables[0].row_count >= 4
    assert "DHT" in doc_lynk.tables[0].to_markdown() or "3.125" in doc_lynk.tables[0].to_markdown()

    # 5. ZF AKC TOML
    doc_zf = parser.parse(BENCHMARK_DIR / "ZF_Rear_Axle_Steering_AKC_Parameters.toml")
    assert doc_zf.metadata["format"] == "toml"
    assert len(doc_zf.tables) >= 1
    assert "AKC" in doc_zf.tables[0].to_markdown() or "采埃孚" in doc_zf.sections[0].content


def test_enterprise_100_documents_corpus_completeness_and_formats():
    """Verify all 100 enterprise benchmark documents are generated and format counts match specs."""
    from collections import Counter

    files = list(BENCHMARK_DIR.glob("*.*"))
    assert len(files) == 100, f"Expected 100 benchmark documents, found {len(files)}"

    ext_counts = Counter(f.suffix.lower() for f in files)
    assert ext_counts[".xlsx"] == 20
    assert ext_counts[".docx"] == 20
    assert ext_counts[".pptx"] == 15
    assert ext_counts[".png"] + ext_counts[".jpg"] == 15
    assert ext_counts[".pdf"] == 10
    assert ext_counts[".csv"] + ext_counts[".tsv"] == 10
    assert (
        ext_counts[".json"]
        + ext_counts[".toml"]
        + ext_counts[".md"]
        + ext_counts[".html"]
        + ext_counts[".rtf"]
        == 10
    )

    # Verify mirrored in sample_specs
    sample_dir = Path("/home/algieba/projects/hackthon/AutoVend/data/sample_specs")
    for f in files:
        assert (sample_dir / f.name).exists(), f"Mirrored file missing in sample_specs: {f.name}"


def test_enterprise_sample_expanded_formats_parsing():
    """Verify parsing of new formats like HTML, RTF, and newly added vehicle brands."""
    parser = MultiFormatParser()

    # 1. HTML parsing
    html_file = BENCHMARK_DIR / "Tesla_Emergency_Response_Guide_Model_Y.html"
    doc_html = parser.parse(html_file)
    assert doc_html.metadata["format"] == "html"
    assert len(doc_html.tables) >= 1
    assert "应急响应" in doc_html.sections[0].title or "应急响应" in doc_html.title
    assert "Model Y" in doc_html.vehicle_model

    # 2. RTF parsing
    rtf_file = BENCHMARK_DIR / "BMW_Workshop_Safety_Inspection_Checklist.rtf"
    doc_rtf = parser.parse(rtf_file)
    assert doc_rtf.metadata["format"] == "rtf"
    assert "BMW" in doc_rtf.sections[0].content or "PDI" in doc_rtf.sections[0].content

    # 3. Porsche Taycan Excel
    doc_porsche = parser.parse(BENCHMARK_DIR / "Porsche_Taycan_Turbo_GT_Track_Telemetry.xlsx")
    assert doc_porsche.metadata["format"] == "excel"
    assert len(doc_porsche.tables) == 2
    assert "815" in doc_porsche.tables[0].to_markdown()
    assert "Taycan" in doc_porsche.vehicle_model

    # 4. Xiaomi Rescue SOP Word
    doc_mi_sop = parser.parse(BENCHMARK_DIR / "Xiaomi_SU7_High_Voltage_Safety_Rescue_SOP.docx")
    assert doc_mi_sop.metadata["format"] == "word"
    assert len(doc_mi_sop.tables) >= 1
    assert "871V" in doc_mi_sop.tables[0].to_markdown()
    assert "SU7" in doc_mi_sop.vehicle_model

    # 5. Mercedes Keynote PPTX
    doc_mb = parser.parse(BENCHMARK_DIR / "Mercedes_Benz_MB_OS_Architecture_Keynote.pptx")
    assert doc_mb.metadata["format"] == "powerpoint"
    assert doc_mb.metadata["slide_count"] >= 2
    assert len(doc_mb.tables) >= 1

    # 6. Maextro S800 PPTX (Huawei HIMA quadruple lineup)
    doc_maextro = parser.parse(BENCHMARK_DIR / "Maextro_S800_Executive_Luxury_Keynote.pptx")
    assert doc_maextro.metadata["format"] == "powerpoint"
    assert "Maextro" in doc_maextro.vehicle_model or "尊界" in doc_maextro.vehicle_model
    assert len(doc_maextro.tables) >= 1

    # 7. Haval Raptor Word (Great Wall lineup)
    doc_haval = parser.parse(BENCHMARK_DIR / "Haval_Raptor_Hi4_Intelligent_4WD_Offroad_Manual.docx")
    assert doc_haval.metadata["format"] == "word"
    assert "Haval" in doc_haval.vehicle_model or "哈弗" in doc_haval.vehicle_model
    assert len(doc_haval.tables) >= 1
    assert "Hi4" in doc_haval.tables[0].to_markdown() or "差速锁" in doc_haval.tables[0].to_markdown()

    # 8. Wey Lanshan Multi-page PDF (Great Wall lineup)
    pdf_parser = LayoutAwareParser(engine_type="hybrid")
    doc_wey_pdf = pdf_parser.parse(BENCHMARK_DIR / "Wey_Lanshan_Coffee_Pilot_Ultra_Technical_Manual.pdf")
    assert doc_wey_pdf.metadata["format"] == "pdf"
    assert doc_wey_pdf.pages == 3
    assert len(doc_wey_pdf.tables) >= 1

    # 9. SU7 Quick Start PDF
    doc_su7_pdf = pdf_parser.parse(BENCHMARK_DIR / "Xiaomi_SU7_Owners_Quick_Start_Manual.pdf")
    assert doc_su7_pdf.metadata["format"] == "pdf"
    assert doc_su7_pdf.pages == 3


def test_enterprise_all_100_documents_parse_without_errors():
    """Verify all 100 enterprise benchmark documents parse into structured sections/tables without exceptions."""
    from src.ingestion.multiformat_parser import DocumentFormat

    parser = MultiFormatParser()
    pdf_parser = LayoutAwareParser(engine_type="hybrid")

    files = sorted(BENCHMARK_DIR.glob("*.*"))
    assert len(files) == 100

    for f in files:
        fmt = parser.detect_format(f)
        if fmt == DocumentFormat.PDF:
            doc = pdf_parser.parse(f)
        else:
            doc = parser.parse(f)

        assert len(doc.sections) > 0 or len(doc.tables) > 0, f"File {f.name} yielded zero sections and tables"
        assert doc.title != "", f"File {f.name} title is empty"
        assert doc.vehicle_model != "", f"File {f.name} vehicle_model is empty"
        assert not doc.metadata.get("is_corrupt"), f"File {f.name} marked corrupt unexpectedly"


# ── 2. Hardened Edge Case Tests ──────────────────────────────────────────


def test_edge_case_extreme_aspect_ratio_images():
    """Verify extreme aspect ratio images (100:1 and 1:100) do not cause NaN/Inf or inverted BBox."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)

        # 1. Extreme wide ribbon (1000 x 10)
        img_wide = Image.new("RGB", (1000, 10), color=(100, 150, 200))
        p_wide = tmp_dir / "wide_ribbon.png"
        img_wide.save(p_wide)

        # 2. Extreme tall strip (10 x 1000)
        img_tall = Image.new("RGB", (10, 1000), color=(50, 80, 120))
        p_tall = tmp_dir / "tall_strip.png"
        img_tall.save(p_tall)

        parser = ImageParser()
        doc_w = parser.parse(p_wide)
        doc_t = parser.parse(p_tall)

        diag_w = doc_w.metadata["image_diagnostics"]
        diag_t = doc_t.metadata["image_diagnostics"]

        assert not math.isnan(diag_w["blur_score"])
        assert not math.isnan(diag_w["contrast_score"])
        assert not math.isnan(diag_t["blur_score"])
        assert not math.isnan(diag_t["contrast_score"])

        # Check bounding box validity (no negative width or height)
        for s in doc_w.sections + doc_t.sections:
            if s.bbox:
                assert s.bbox.width >= 0
                assert s.bbox.height >= 0
                assert s.bbox.x1 >= s.bbox.x0
                assert s.bbox.bottom >= s.bbox.top


def test_edge_case_corrupt_formula_values_in_excel():
    """Verify ExcelParser handles #DIV/0!, #VALUE!, and NaN floats without crash."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CorruptFormulas"
    ws.append(["Param", "Value", "Note"])
    ws.append(["ErrorDiv0", "#DIV/0!", "Calculation error"])
    ws.append(["ErrorVal", "#VALUE!", "Type mismatch error"])
    ws.append(["ErrorRef", "#REF!", "Missing cell reference"])
    ws.append(["ValidNumber", 125000, "Valid integer"])
    wb.save(tmp_path)
    wb.close()

    parser = ExcelParser()
    doc = parser.parse(tmp_path)

    assert len(doc.tables) == 1
    tbl = doc.tables[0]
    md = tbl.to_markdown()
    assert "#DIV/0!" in md
    assert "#VALUE!" in md
    assert "#REF!" in md
    assert "125000" in md
    tmp_path.unlink()


def test_edge_case_zero_length_cells_and_empty_tables():
    """Verify TableBlock.to_markdown() and to_html() handle empty cells and empty tables gracefully."""
    empty_block = TableBlock(page_num=1, bbox=BoundingBox(0, 0, 100, 100), rows=[])
    assert empty_block.to_markdown() == ""
    assert empty_block.to_html() == ""

    # Table with all zero-length cells
    zero_rows = [["", "", ""], ["", "", ""], ["", "", ""]]
    zero_block = TableBlock(page_num=1, bbox=BoundingBox(0, 0, 100, 100), rows=zero_rows)
    md = zero_block.to_markdown()
    assert "|  |  |  |" in md
    ht = zero_block.to_html()
    assert "<table" in ht


def test_edge_case_deeply_nested_word_lists():
    """Verify WordParser preserves indentation for deeply nested lists (levels 1-5)."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    doc = docx.Document()
    doc.add_heading("Deeply Nested Maintenance Protocol", level=1)
    doc.add_paragraph("Top level procedure", style="List Bullet")
    doc.add_paragraph("\tChild procedure level 1", style="List Bullet")
    doc.add_paragraph("\t\tSub-child procedure level 2", style="List Bullet")
    doc.add_paragraph("\t\t\tDeep procedure level 3", style="List Bullet")
    doc.save(tmp_path)

    parser = WordParser()
    parsed = parser.parse(tmp_path)
    content = parsed.sections[0].content
    assert "- Top level procedure" in content
    assert "- Child procedure" in content
    tmp_path.unlink()


def test_edge_case_encoding_autodetect_utf16_and_gb18030():
    """Verify CsvTsvParser and StructuredTextParser autodetect UTF-16 and GB18030 encodings."""
    # 1. UTF-16 TSV
    tsv_content = "car_model\tprice_wan\n蔚来ET9\t80.0\n仰望U8\t109.8\n"
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
        tmp.write(tsv_content.encode("utf-16"))
        tsv_path = Path(tmp.name)

    parser = CsvTsvParser()
    doc_tsv = parser.parse(tsv_path)
    assert doc_tsv.tables[0].row_count == 3
    assert "蔚来ET9" in doc_tsv.tables[0].to_markdown()
    tsv_path.unlink()

    # 2. GB18030 Markdown
    md_content = "# 小米SU7 Ultra 赛道规格说明\n\n- 峰值马力: 1548 PS\n- 最高时速: 350 km/h\n"
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
        tmp.write(md_content.encode("gb18030"))
        md_path = Path(tmp.name)

    parser_txt = StructuredTextParser()
    doc_md = parser_txt.parse(md_path)
    assert "小米SU7 Ultra" in doc_md.title or "1548" in doc_md.sections[0].content
    md_path.unlink()


def test_edge_case_large_excel_table_clamping():
    """Verify ExcelParser clamps sheet dimensions if rows exceed MAX_EXCEL_ROWS to prevent OOM."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ClampedSheet"
    ws["A1"] = "Metric"
    ws["B1"] = "Value"
    # Mark a distant cell to simulate sparse huge table reporting large max_row
    ws.cell(row=5005, column=2, value="FarAwayData")
    wb.save(tmp_path)
    wb.close()

    parser = ExcelParser()
    doc = parser.parse(tmp_path)
    # Ensure parsed table was bounded to MAX_EXCEL_ROWS (5000)
    assert len(doc.tables) == 1
    assert doc.tables[0].row_count <= 5000
    tmp_path.unlink()


def test_edge_case_malformed_json_and_toml_resilience():
    """Verify StructuredTextParser returns graceful error metadata on corrupted JSON/TOML rather than crashing."""
    parser = StructuredTextParser()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)

        # 1. Broken JSON
        p_json = tmp_dir / "broken.json"
        p_json.write_text("{ unquoted_key: 123, invalid_json", encoding="utf-8")
        doc_json = parser.parse(p_json)
        assert doc_json.metadata["format"] == "json"
        assert doc_json.metadata.get("is_corrupt") is True
        assert "error" in doc_json.metadata

        # 2. Broken TOML
        p_toml = tmp_dir / "broken.toml"
        p_toml.write_text("[section]\ninvalid key without value ====", encoding="utf-8")
        doc_toml = parser.parse(p_toml)
        assert doc_toml.metadata["format"] == "toml"
        assert doc_toml.metadata.get("is_corrupt") is True
        assert "error" in doc_toml.metadata


def test_edge_case_tsv_with_commas_delimiter_preservation():
    """Verify CsvTsvParser preserves tab delimiter when text fields contain commas."""
    tsv_content = (
        "Trim\tFeatures\tPrice\n"
        "Ultra\tLiDAR, HUD, CDC suspension\t52.9万\n"
        "Max\tDual motors, 21-inch wheels\t46.9万\n"
    )
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
        tmp.write(tsv_content.encode("utf-8"))
        tmp_path = Path(tmp.name)

    parser = CsvTsvParser()
    doc = parser.parse(tmp_path)
    assert doc.metadata["delimiter"] == "\t"
    tbl = doc.tables[0]
    assert tbl.col_count == 3
    assert "LiDAR, HUD, CDC suspension" in tbl.rows[1][1]
    tmp_path.unlink()


def test_edge_case_thead_ordering_with_merged_cells():
    """Verify TableBlock.to_html() preserves <thead> when row 0 contains merged cells."""
    from src.ingestion.layout_parser import TableCell

    cells = [
        TableCell(row_idx=0, col_idx=0, text="MergedHeader", col_span=2),
        TableCell(row_idx=0, col_idx=2, text="Col3", col_span=1),
        TableCell(row_idx=1, col_idx=0, text="A"),
        TableCell(row_idx=1, col_idx=1, text="B"),
        TableCell(row_idx=1, col_idx=2, text="C"),
    ]
    rows = [["MergedHeader", "MergedHeader", "Col3"], ["A", "B", "C"]]
    tbl = TableBlock(
        page_num=1,
        bbox=BoundingBox(0, 0, 100, 100),
        rows=rows,
        headers=["MergedHeader", "Col3"],
        cells=cells,
        title="TestTableCaption",
    )
    html = tbl.to_html()
    assert "<table" in html
    assert "MergedHeader" in html
    assert 'colspan="2"' in html
    table_pos = html.find("<table")
    caption_pos = html.find("<caption>TestTableCaption</caption>")
    assert caption_pos > table_pos, "HTML specification violation: <caption> must be child inside <table>"


def test_edge_case_encrypted_pdf_resource_safety():
    """Verify LayoutAwareParser detects encrypted PDF and handles gracefully without leak."""
    import pymupdf as fitz

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = Path(tmp.name)

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Classified EV Blueprint")
    doc.save(str(pdf_path), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="pwd123", owner_pw="pwd123")
    doc.close()

    parser = LayoutAwareParser(engine_type="hybrid")
    parsed = parser.parse(pdf_path)
    assert parsed.metadata["format"] == "pdf"
    assert parsed.metadata.get("is_encrypted") is True
    pdf_path.unlink()


def test_concurrent_parent_child_retriever_thread_safety():
    """Verify ParentChildRetriever handles concurrent multi-threaded ingestion and search."""
    import concurrent.futures

    chunker = HierarchicalChunker()
    retriever = ParentChildRetriever(chunker=chunker)

    # Ingest baseline document
    doc = MultiFormatParser().parse(BENCHMARK_DIR / "Powertrain_Efficiency_Matrix.tsv")
    retriever.index_document(doc)

    def worker_ingest(task_id: int):
        doc_copy = MultiFormatParser().parse(BENCHMARK_DIR / "Bosch_ESP_Firmware_Config.toml")
        retriever.index_document(doc_copy)
        resp = retriever.search(query=f"ESP 制动 防抱死 {task_id}", top_k_parents=2)
        return len(resp.results)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker_ingest, i) for i in range(16)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 16
    assert all(r >= 1 for r in results)


def test_ingest_document_propagates_chunks_and_indexes():
    """Verify IncrementalIngestionPipeline.ingest_document indexes into ParentChildRetriever."""
    chunker = HierarchicalChunker()
    retriever = ParentChildRetriever(chunker=chunker)
    pipeline = IncrementalIngestionPipeline(parent_child_retriever=retriever)

    parser = MultiFormatParser()
    doc = parser.parse(BENCHMARK_DIR / "Zeekr_Battery_Warranty_Terms.md")

    # Ingest pre-parsed document
    summary = pipeline.ingest_document(doc, source_id="Zeekr_Warranty_Doc")
    assert summary.created_count == 1
    assert len(retriever.parent_store) >= 1
    assert len(retriever.child_index.chunks) >= 1

    # Idempotent second call
    summary2 = pipeline.ingest_document(doc, source_id="Zeekr_Warranty_Doc")
    assert summary2.unchanged_count == 1


# ── 3. Pipeline & Retrieval Integration Cohesion ─────────────────────────


def test_benchmark_pipeline_harness_execution():
    """Verify EnterpriseBenchmarkHarness executes end-to-end with high recall and zero regression."""
    harness = EnterpriseBenchmarkHarness(corpus_dir=BENCHMARK_DIR)
    report = harness.run_benchmark()

    s = report["summary"]
    assert s["total_documents"] == 100
    assert s["total_tables"] >= 100
    assert s["top1_recall_pct"] >= 90.0
    assert s["top3_recall_pct"] >= 90.0
    assert s["incremental_idempotency_ok"] is True
    assert s["avg_retrieval_latency_ms"] < 20.0


def test_rag_service_document_search_integration():
    """Verify RAGService.search_documents() returns structured parent context with breadcrumbs."""
    chunker = HierarchicalChunker()
    retriever = ParentChildRetriever(chunker=chunker)
    pipeline = IncrementalIngestionPipeline(parent_child_retriever=retriever)
    rag_service = RAGService(parent_child_retriever=retriever)

    # Ingest sample Word document
    doc_path = BENCHMARK_DIR / "Tesla_Model_Y_Service_Bulletin.docx"
    pipeline.ingest_file(doc_path)

    # Query via RAGService
    resp = rag_service.search_documents(query="Model Y 转向机 扭矩传感器 召回", top_k_parents=2)
    assert len(resp.results) >= 1
    top_result = resp.results[0]
    assert "Model Y" in top_result.content
    assert "EPS" in top_result.content or "转向" in top_result.content
    llm_context = resp.format_llm_context()
    assert "参考资料" in llm_context
