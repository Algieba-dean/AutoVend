"""
AutoVend Real Automotive Documents & Public Data Ingestion Test Suite.
======================================================================
Tests the parsing, chunking, indexing, and retrieval across 100% authentic,
real-world automotive documents acquired from public automotive archives,
regulatory safety authorities, OEM investor portals, and government registries.

Corpus files tested in data/real_enterprise_docs/:
1. Tesla_Q4_2023_Shareholder_Deck.pdf (Official Tesla IR Investor Deck)
2. NHTSA_Tesla_Autopilot_Recall_23V838.pdf (Official US DOT / NHTSA Part 573 Recall Report)
3. EPA_2024_Fuel_Economy_and_EV_Guide.pdf (Official US EPA / DOE EV Guide)
4. EuroNCAP_BYD_Seal_U_Rescue_Sheet.pdf (Official Euro NCAP / BYD Emergency Rescue Manual)
5. BYD_HKEX_Corporate_Filing.pdf (Official HKEX: 01211 BYD Corporate Announcement)
6. HEV_Powertrain_System_Requirements.docx (Authentic HEV Powertrain Specification)
7. ISO15118_CCS_EV_Charging_Protocol.docx (Authentic CCS / ISO 15118 EV Charging Manual)
8. Solar_Powered_Electric_Vehicle_Efficiency.pptx (Authentic 29-Slide Academic Engineering Deck)
9. Electric_Vehicle_Population_Real.csv (Real Washington State DOL EV Population Census)
10. Electric_Vehicle_Population_Data.xlsx (Comprehensive 150k-Row Official EV Registration Dataset)
11. Kia_Niro_EX_Touring_Monroney_Sticker.jpg (Authentic Monroney Window Sticker Photo, Denver Auto Show)
12. Kia_Sportage_Hybrid_Monroney_Sticker.jpg (Authentic Monroney Window Sticker Photo, Denver Auto Show)
13. BYD_Seal_EV_Real.jpg (Authentic Real Vehicle Exterior Photo)
14. Xiaomi_SU7_Yiche_Real_Catalog.json (Live Production Scraped Xiaomi SU7 Specs)
15. Tesla_Model_3_Yiche_Real_Catalog.json (Live Production Scraped Tesla Model 3 Specs)
16. BYD_Han_Yiche_Real_Catalog.json (Live Production Scraped BYD Han Specs)
"""

import time
from pathlib import Path

from scripts.fetch_real_automotive_docs import (
    MANIFEST,
    calculate_sha256,
    verify_real_documents,
)
from src.ingestion.hierarchical_chunker import ChunkType, HierarchicalChunker
from src.ingestion.layout_parser import LayoutAwareParser
from src.ingestion.multiformat_parser import (
    CsvTsvParser,
    DocumentFormat,
    ExcelParser,
    ImageParser,
    MultiFormatDocumentParser,
    MultiFormatParser,
    PowerPointParser,
    StructuredTextParser,
    WordParser,
)
from src.ingestion.pipeline import IncrementalIngestionPipeline
from src.retrieval.parent_child_retriever import ParentChildRetriever

import pytest

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "real_enterprise_docs"
pytestmark = pytest.mark.skipif(
    not CORPUS_DIR.exists() or not any(CORPUS_DIR.iterdir()) if CORPUS_DIR.exists() else True,
    reason="Real automotive documents not fetched; run scripts/fetch_real_automotive_docs.py to download.",
)


# ── 1. Corpus Integrity & Manifest Validation ────────────────────────────────


def test_real_corpus_presence_and_integrity():
    """Verify all 15 authentic real automotive documents exist and exceed minimum sizes."""
    assert CORPUS_DIR.exists(), f"Real documents directory missing: {CORPUS_DIR}"

    report = verify_real_documents(CORPUS_DIR)
    assert report["missing_count"] == 0, f"Missing files in real corpus: {report}"
    assert report["undersized_count"] == 0, f"Undersized files in real corpus: {report}"
    assert report["valid_count"] == len(MANIFEST)

    # Check SHA256 hashes are non-empty and unique
    seen_hashes = set()
    for item in MANIFEST:
        target = CORPUS_DIR / item["filename"]
        assert target.is_file(), f"Expected regular file at {target}"
        h = calculate_sha256(target)
        assert len(h) == 64
        seen_hashes.add(h)
    assert len(seen_hashes) == len(MANIFEST), "All authentic documents must have unique file content hashes"


# ── 2. Real PDF Document Parsing (LayoutAwareParser) ─────────────────────────


def test_real_pdf_nhtsa_recall():
    """Validate parsing official NHTSA safety recall report with real layout tables."""
    pdf_path = CORPUS_DIR / "NHTSA_Tesla_Autopilot_Recall_23V838.pdf"
    parser = LayoutAwareParser()
    doc = parser.parse(pdf_path)

    assert doc.pages == 5
    assert len(doc.sections) >= 3
    assert len(doc.tables) >= 5

    # Check table blocks contain real recall data
    all_table_text = " ".join(cell for t in doc.tables for row in t.rows for cell in row)
    assert "23V-838" in all_table_text or "23V-838" in doc.raw_text or any("23V-838" in s.title for s in doc.sections)


def test_real_pdf_byd_hkex_filing():
    """Validate parsing official BYD HKEX corporate disclosure."""
    pdf_path = CORPUS_DIR / "BYD_HKEX_Corporate_Filing.pdf"
    parser = LayoutAwareParser()
    doc = parser.parse(pdf_path)

    assert doc.pages == 2
    assert len(doc.sections) >= 1
    assert len(doc.raw_text) > 500


def test_real_pdf_euro_ncap_byd_rescue_sheet():
    """Validate parsing official Euro NCAP / BYD rescue manual with multi-page tables."""
    pdf_path = CORPUS_DIR / "EuroNCAP_BYD_Seal_U_Rescue_Sheet.pdf"
    parser = LayoutAwareParser()
    doc = parser.parse(pdf_path)

    assert doc.pages == 27
    assert len(doc.sections) >= 10
    assert len(doc.tables) >= 10
    # Check rescue content detected
    full_text = doc.raw_text.lower() + " ".join(s.content.lower() for s in doc.sections)
    assert "byd" in full_text or "seal" in full_text or "batería" in full_text or "primeros" in full_text


def test_real_pdf_tesla_shareholder_deck():
    """Validate parsing official Tesla Q4 investor deck with slide layouts."""
    pdf_path = CORPUS_DIR / "Tesla_Q4_2023_Shareholder_Deck.pdf"
    parser = LayoutAwareParser()
    doc = parser.parse(pdf_path)

    assert doc.pages == 32
    assert len(doc.sections) >= 20
    assert len(doc.tables) >= 10
    section_titles = [s.title for s in doc.sections]
    assert any("Highlights" in t or "Financial" in t or "Operational" in t or "Capacity" in t for t in section_titles)


def test_real_pdf_epa_fuel_economy_guide():
    """Validate parsing official 64-page EPA & DOE Fuel Economy & EV guide."""
    pdf_path = CORPUS_DIR / "EPA_2024_Fuel_Economy_and_EV_Guide.pdf"
    parser = LayoutAwareParser()
    doc = parser.parse(pdf_path)

    assert doc.pages == 64
    assert len(doc.sections) >= 50
    assert len(doc.tables) >= 100
    full_text = doc.raw_text + " ".join(s.content for s in doc.sections[:10])
    assert any(term in full_text for term in ["Fuel Economy", "MPGe", "Electric", "kWh", "EPA"])


# ── 3. Real Word Document Parsing (WordParser) ───────────────────────────────


def test_real_docx_hev_powertrain_spec():
    """Validate parsing real Hybrid Electric Vehicle requirements specification docx."""
    docx_path = CORPUS_DIR / "HEV_Powertrain_System_Requirements.docx"
    parser = WordParser()
    doc = parser.parse(docx_path)

    assert doc.metadata["format"] == "word"
    assert len(doc.sections) == 6
    section_titles = [s.title for s in doc.sections]
    assert "HEV Powertrain System Requirements" in section_titles
    assert "Overall System Requirements" in section_titles
    assert "Engine System Requirements" in section_titles
    assert "Fuel Consumption" in section_titles
    assert "Speed Controller Module Requirements" in section_titles

    # Verify engineering parameters in section contents
    overall_sec = next(s for s in doc.sections if s.title == "Overall System Requirements")
    assert "1325 kg" in overall_sec.content
    engine_sec = next(s for s in doc.sections if s.title == "Engine System Requirements")
    assert "ICE" in engine_sec.content


def test_real_docx_iso15118_ccs_charging():
    """Validate parsing real ISO 15118 / CCS EV charging protocol document."""
    docx_path = CORPUS_DIR / "ISO15118_CCS_EV_Charging_Protocol.docx"
    parser = WordParser()
    doc = parser.parse(docx_path)

    assert doc.metadata["format"] == "word"
    assert len(doc.sections) >= 1
    assert doc.pages >= 1


# ── 4. Real PowerPoint Parsing (PowerPointParser) ────────────────────────────


def test_real_pptx_solar_ev_efficiency():
    """Validate parsing 29-slide authentic engineering presentation deck."""
    pptx_path = CORPUS_DIR / "Solar_Powered_Electric_Vehicle_Efficiency.pptx"
    parser = PowerPointParser()
    doc = parser.parse(pptx_path)

    assert doc.metadata["format"] == "powerpoint"
    assert len(doc.sections) == 29, f"Expected 29 slides, got {len(doc.sections)}"
    assert doc.metadata["slide_count"] == 29

    # Check slide sequence and contents
    slide1 = doc.sections[0]
    assert "Advanced Monitoring System" in slide1.title or "Solar-Powered" in slide1.title
    assert "JAWAHARLAL NEHRU" in slide1.content

    slide3 = doc.sections[2]
    assert "OBJECTIVES" in slide3.title
    assert "photovoltaic" in slide3.content.lower()


# ── 5. Real CSV Census Dataset Parsing (CsvTsvParser) ─────────────────────────


def test_real_csv_ev_population():
    """Validate parsing real EV registration census data in CSV format."""
    csv_path = CORPUS_DIR / "Electric_Vehicle_Population_Real.csv"
    parser = CsvTsvParser()
    doc = parser.parse(csv_path)

    assert doc.metadata["format"] == "csv"
    assert doc.metadata["delimiter"] == ","
    assert len(doc.tables) == 1
    tbl = doc.tables[0]
    assert len(tbl.rows) >= 1000

    header = tbl.rows[0]
    assert "VIN (1-10)" in header
    assert "Make" in header
    assert "Model" in header
    assert "Electric Vehicle Type" in header
    assert "Base MSRP" in header

    # Verify real makes present
    makes = {row[header.index("Make")] for row in tbl.rows[1:50]}
    assert len(makes & {"TESLA", "HYUNDAI", "JEEP", "CHEVROLET", "NISSAN", "FORD"}) > 0


def test_real_excel_ev_population():
    """Validate parsing real 150,483-row multi-attribute EV population Excel dataset."""
    excel_path = CORPUS_DIR / "Electric_Vehicle_Population_Data.xlsx"
    parser = ExcelParser()
    t0 = time.time()
    doc = parser.parse(excel_path)
    elapsed = time.time() - t0

    assert elapsed < 5.0, f"ExcelParser should parse large workbook within 5s, took {elapsed:.2f}s"
    assert doc.metadata["format"] == "excel"
    assert len(doc.tables) == 1
    tbl = doc.tables[0]
    assert tbl.metadata["sheet_name"] == "Worksheet"
    assert len(tbl.rows) >= 1000

    header = tbl.rows[0]
    assert "VIN (1-10)" in header
    assert "Make" in header
    assert "Model" in header
    assert "Electric Vehicle Type" in header
    assert "Base MSRP" in header

    # Verify real makes present in Excel sheet
    makes = {row[header.index("Make")] for row in tbl.rows[1:50] if len(row) > header.index("Make")}
    assert len(makes & {"TESLA", "HYUNDAI", "JEEP", "CHEVROLET", "NISSAN", "FORD"}) > 0


# ── 6. Real Crawled OEM Catalog Specifications (StructuredTextParser) ────────


def test_real_crawled_xiaomi_su7_specs():
    """Validate parsing real scraped Xiaomi SU7 production specifications."""
    json_path = CORPUS_DIR / "Xiaomi_SU7_Yiche_Real_Catalog.json"
    parser = StructuredTextParser()
    doc = parser.parse(json_path)

    assert doc.metadata["format"] == "json"
    assert "Xiaomi SU7" in doc.title or "小米SU7" in doc.raw_text
    assert len(doc.sections) >= 1
    assert len(doc.tables) >= 1
    assert "720km" in doc.raw_text
    assert "21.99万" in doc.raw_text


def test_real_crawled_tesla_and_byd_specs():
    """Validate parsing real scraped Tesla Model 3 and BYD Han catalog specs."""
    parser = StructuredTextParser()

    tesla_doc = parser.parse(CORPUS_DIR / "Tesla_Model_3_Yiche_Real_Catalog.json")
    assert tesla_doc.metadata["format"] == "json"
    assert "Tesla" in tesla_doc.title or "特斯拉" in tesla_doc.raw_text or "Model 3" in tesla_doc.raw_text

    byd_doc = parser.parse(CORPUS_DIR / "BYD_Han_Yiche_Real_Catalog.json")
    assert byd_doc.metadata["format"] == "json"
    assert "比亚迪" in byd_doc.raw_text or "汉" in byd_doc.raw_text


# ── 7. Real Image Diagnostics & EXIF Metadata (ImageParser) ──────────────────


def test_real_image_kia_niro_monroney_exif():
    """Validate image diagnostics and EXIF metadata extraction from authentic Monroney photo."""
    img_path = CORPUS_DIR / "Kia_Niro_EX_Touring_Monroney_Sticker.jpg"
    parser = ImageParser()
    doc = parser.parse(img_path)

    assert doc.metadata["format"] == "image"
    diag = doc.metadata["image_diagnostics"]
    assert diag["width"] == 4032
    assert diag["height"] == 3024
    assert diag["is_blurry"] is False
    assert diag["blur_score"] > 200.0

    exif = doc.metadata["exif"]
    assert exif.get("Make") == "Apple"
    assert exif.get("Model") == "iPhone 13"
    assert "DateTimeOriginal" in exif


def test_real_image_kia_sportage_hybrid_exif():
    """Validate image diagnostics and EXIF metadata extraction from authentic Sportage Monroney photo."""
    img_path = CORPUS_DIR / "Kia_Sportage_Hybrid_Monroney_Sticker.jpg"
    parser = ImageParser()
    doc = parser.parse(img_path)

    assert doc.metadata["format"] == "image"
    diag = doc.metadata["image_diagnostics"]
    assert diag["width"] == 4032
    assert diag["height"] == 3024
    assert diag["is_blurry"] is False
    assert diag["blur_score"] > 200.0

    exif = doc.metadata["exif"]
    assert exif.get("Make") == "Apple"
    assert exif.get("Model") == "iPhone 13"
    assert "DateTimeOriginal" in exif


def test_real_image_byd_seal_exterior():
    """Validate vehicle exterior photo diagnostics."""
    img_path = CORPUS_DIR / "BYD_Seal_EV_Real.jpg"
    parser = ImageParser()
    doc = parser.parse(img_path)

    assert doc.metadata["format"] == "image"
    diag = doc.metadata["image_diagnostics"]
    assert diag["width"] > 500
    assert diag["height"] > 300
    assert diag["channels"] == 3


# ── 8. MultiFormat Autodetection on Real Corpus ───────────────────────────────


def test_multiformat_autodetection_real_corpus():
    """Validate format autodetection across all 16 authentic real documents."""
    parser = MultiFormatDocumentParser()

    expected_formats = {
        "Tesla_Q4_2023_Shareholder_Deck.pdf": DocumentFormat.PDF,
        "NHTSA_Tesla_Autopilot_Recall_23V838.pdf": DocumentFormat.PDF,
        "EPA_2024_Fuel_Economy_and_EV_Guide.pdf": DocumentFormat.PDF,
        "EuroNCAP_BYD_Seal_U_Rescue_Sheet.pdf": DocumentFormat.PDF,
        "BYD_HKEX_Corporate_Filing.pdf": DocumentFormat.PDF,
        "HEV_Powertrain_System_Requirements.docx": DocumentFormat.WORD,
        "ISO15118_CCS_EV_Charging_Protocol.docx": DocumentFormat.WORD,
        "Solar_Powered_Electric_Vehicle_Efficiency.pptx": DocumentFormat.POWERPOINT,
        "Electric_Vehicle_Population_Real.csv": DocumentFormat.CSV,
        "Electric_Vehicle_Population_Data.xlsx": DocumentFormat.EXCEL,
        "Kia_Niro_EX_Touring_Monroney_Sticker.jpg": DocumentFormat.IMAGE,
        "Kia_Sportage_Hybrid_Monroney_Sticker.jpg": DocumentFormat.IMAGE,
        "BYD_Seal_EV_Real.jpg": DocumentFormat.IMAGE,
        "Xiaomi_SU7_Yiche_Real_Catalog.json": DocumentFormat.JSON,
        "Tesla_Model_3_Yiche_Real_Catalog.json": DocumentFormat.JSON,
        "BYD_Han_Yiche_Real_Catalog.json": DocumentFormat.JSON,
    }

    for fname, exp_fmt in expected_formats.items():
        assert parser.detect_format(CORPUS_DIR / fname) == exp_fmt, f"Format mismatch for {fname}"


# ── 9. Hierarchical Chunking on Real Documents ───────────────────────────────


def test_hierarchical_chunking_real_documents():
    """Validate HierarchicalChunker extracts parents, children, and tables from real documents."""
    chunker = HierarchicalChunker(parent_max_tokens=1000, child_max_tokens=250)
    parser = MultiFormatParser()

    # Test NHTSA PDF Chunking
    nhtsa_doc = parser.parse(CORPUS_DIR / "NHTSA_Tesla_Autopilot_Recall_23V838.pdf")
    nhtsa_chunks = chunker.chunk_document(nhtsa_doc)
    assert len(nhtsa_chunks["parents"]) > 0
    assert len(nhtsa_chunks["children"]) > 0
    assert len(nhtsa_chunks["tables"]) > 0

    # Test HEV Docx Chunking
    hev_doc = parser.parse(CORPUS_DIR / "HEV_Powertrain_System_Requirements.docx")
    hev_chunks = chunker.chunk_document(hev_doc)
    assert len(hev_chunks["parents"]) >= 5
    for p in hev_chunks["parents"]:
        assert p.chunk_type == ChunkType.PARENT
        assert p.chunk_id is not None
        assert p.content is not None


# ── 10. Parent-Child Retrieval with Real Domain Queries ───────────────────────


def test_parent_child_retrieval_real_queries():
    """Validate indexing and semantic/lexical parent retrieval against real corpus."""
    parser = MultiFormatParser()
    retriever = ParentChildRetriever()

    # Index real documents of diverse formats
    docs = [
        parser.parse(CORPUS_DIR / "NHTSA_Tesla_Autopilot_Recall_23V838.pdf"),
        parser.parse(CORPUS_DIR / "HEV_Powertrain_System_Requirements.docx"),
        parser.parse(CORPUS_DIR / "Solar_Powered_Electric_Vehicle_Efficiency.pptx"),
        parser.parse(CORPUS_DIR / "Xiaomi_SU7_Yiche_Real_Catalog.json"),
        parser.parse(CORPUS_DIR / "Electric_Vehicle_Population_Data.xlsx", max_rows=500),
    ]

    for d in docs:
        stats = retriever.index_document(d)
        assert stats["parents_indexed"] > 0
        assert stats["children_indexed"] > 0

    # Query 1: NHTSA Autopilot recall
    resp1 = retriever.search("Tesla Autosteer recall 23V-838", top_k_parents=2)
    assert len(resp1.results) > 0
    top_hit1 = resp1.results[0]
    assert "NHTSA" in top_hit1.parent_id or "Tesla" in top_hit1.content or "23V-838" in top_hit1.content
    assert top_hit1.score > 0.0

    # Query 2: HEV powertrain system requirements
    resp2 = retriever.search("Curb Weight 1325 kg ICE engine power", top_k_parents=2)
    assert len(resp2.results) > 0
    top_hit2 = resp2.results[0]
    assert "Overall System Requirements" in top_hit2.content or "Engine System Requirements" in top_hit2.content

    # Query 3: Solar vehicle MPPT
    resp3 = retriever.search("photovoltaic Maximum power point tracking", top_k_parents=2)
    assert len(resp3.results) > 0
    top_hit3 = resp3.results[0]
    assert "Solar" in top_hit3.parent_id or "photovoltaic" in top_hit3.content.lower()

    # Query 4: Xiaomi SU7 trim pricing
    resp4 = retriever.search("小米SU7 720km 后驱标准版 21.99万", top_k_parents=2)
    assert len(resp4.results) > 0
    top_hit4 = resp4.results[0]
    assert "Xiaomi" in top_hit4.parent_id or "小米" in top_hit4.content or "21.99" in top_hit4.content

    # Query 5: Real EV Population census query
    resp5 = retriever.search("Electric Vehicle Population VIN Base MSRP", top_k_parents=2)
    assert len(resp5.results) > 0
    top_hit5 = resp5.results[0]
    assert "Population" in top_hit5.parent_id or "VIN" in top_hit5.content or "MSRP" in top_hit5.content or "Worksheet" in top_hit5.content


# ── 11. Incremental Pipeline Integration on Real Documents ────────────────────


def test_incremental_pipeline_real_corpus():
    """Validate IncrementalIngestionPipeline successfully processes real documents."""
    retriever = ParentChildRetriever()
    pipeline = IncrementalIngestionPipeline(parent_child_retriever=retriever)

    # Ingest real files
    doc_path = CORPUS_DIR / "HEV_Powertrain_System_Requirements.docx"
    summary1 = pipeline.ingest_file(doc_path)
    assert summary1.created_count == 1
    assert len(retriever.parent_store) >= 5

    # Idempotent re-ingestion
    summary2 = pipeline.ingest_file(doc_path)
    assert summary2.unchanged_count == 1
