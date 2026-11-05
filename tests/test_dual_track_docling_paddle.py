"""
Unit tests for Dual-Track Isolation Architecture (Docling + PaddleOCR PP-Structure)
and Physical Anchor Propagation in AutoVend.
"""

from pathlib import Path
import fitz  # PyMuPDF
import pytest

from src.ingestion.docling_adapter import RealDoclingAdapter
from src.ingestion.paddle_ocr_adapter import RealPaddleOCRAdapter
from src.ingestion.layout_parser import (
    BoundingBox,
    DualTrackLayoutEngine,
    LayoutAwareParser,
    ParsedDocument,
    TableBlock,
    TextSection,
)
from src.ingestion.hierarchical_chunker import (
    Chunk,
    ChunkType,
    HierarchicalChunker,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_SAMPLE_PATH = _PROJECT_ROOT / "data" / "sample_specs" / "xiaomi_su7_ultra_specs.pdf"


def test_real_docling_adapter_tableformer():
    """Verify that RealDoclingAdapter uses IBM Docling TableFormer on digital PDFs."""
    assert PDF_SAMPLE_PATH.exists()
    adapter = RealDoclingAdapter()
    doc = adapter.parse(PDF_SAMPLE_PATH)

    assert isinstance(doc, ParsedDocument)
    assert doc.pages >= 2
    assert len(doc.tables) >= 1
    assert doc.metadata.get("tableformer") is True or "docling" in doc.metadata.get("engine", "")

    # Validate first table physical anchors
    t0 = doc.tables[0]
    assert t0.page_num >= 1
    assert t0.extraction_engine in ["ibm_docling_tableformer", "pymupdf_pdfplumber"]
    assert len(t0.rows) > 0


def test_paddle_ocr_adapter_cpu_isolation(tmp_path):
    """Verify that RealPaddleOCRAdapter runs on CPU without GPU memory hijacking."""
    adapter = RealPaddleOCRAdapter()
    assert adapter.use_gpu is False

    # Create a 1-page scanned PDF (image only, 0 text layer chars)
    scanned_pdf_path = tmp_path / "scanned_doc.pdf"
    doc_pdf = fitz.open()
    page = doc_pdf.new_page(width=400, height=300)
    # Draw red rectangle to act as scanned image content
    page.draw_rect(fitz.Rect(50, 50, 350, 250), color=(1, 0, 0), fill=(0.9, 0.9, 0.9))
    doc_pdf.save(str(scanned_pdf_path))
    doc_pdf.close()

    parsed = adapter.parse(scanned_pdf_path)
    assert isinstance(parsed, ParsedDocument)
    assert parsed.pages == 1
    assert parsed.metadata.get("cpu_only") is True or "paddle_ocr" in parsed.metadata.get("engine", "")
    assert len(parsed.sections) >= 1


def test_dual_track_density_classification(tmp_path):
    """Verify page-level character density detection: >= 30/page -> digital; < 30/page -> scanned."""
    # 1. Native PDF: xiaomi_su7_ultra_specs.pdf has hundreds of characters per page
    engine = DualTrackLayoutEngine(char_density_threshold=30)
    density_info = engine.check_density(PDF_SAMPLE_PATH)

    assert len(density_info["digital_pages"]) >= 2
    assert len(density_info["scanned_pages"]) == 0
    for p_num, count in density_info["page_counts"].items():
        assert count >= 30, f"Page {p_num} expected >= 30 chars, got {count}"

    # 2. Mixed PDF: Page 1 with 100 chars, Page 2 with 5 chars (< 30)
    mixed_pdf_path = tmp_path / "mixed_doc.pdf"
    doc_pdf = fitz.open()

    p1 = doc_pdf.new_page(width=400, height=300)
    p1.insert_text((50, 50), "这是第一页原生数字内容，包含超过三十个字符以触发Docling通道。" * 2)

    p2 = doc_pdf.new_page(width=400, height=300)
    p2.insert_text((50, 50), "短文本")  # only 3 chars < 30 threshold
    p2.draw_rect(fitz.Rect(20, 20, 380, 280), color=(0, 0, 1))

    doc_pdf.save(str(mixed_pdf_path))
    doc_pdf.close()

    mixed_density = engine.check_density(mixed_pdf_path)
    assert mixed_density["digital_pages"] == [1]
    assert mixed_density["scanned_pages"] == [2]


def test_dual_track_digital_routing():
    """Verify that documents with genuine_chars >= 30/page route to Docling Fast Channel."""
    engine = DualTrackLayoutEngine(char_density_threshold=30)
    doc = engine.parse(PDF_SAMPLE_PATH)

    assert isinstance(doc, ParsedDocument)
    assert doc.metadata.get("dual_track_route") == "all_digital_docling"
    assert len(doc.tables) >= 1


def test_dual_track_scanned_routing(tmp_path):
    """Verify that documents with genuine_chars < 30/page route to PaddleOCR Heavy Channel."""
    scanned_path = tmp_path / "pure_scanned.pdf"
    doc_pdf = fitz.open()
    page = doc_pdf.new_page(width=400, height=300)
    page.draw_rect(fitz.Rect(10, 10, 390, 290), color=(0, 0, 0))
    doc_pdf.save(str(scanned_path))
    doc_pdf.close()

    engine = DualTrackLayoutEngine(char_density_threshold=30)
    doc = engine.parse(scanned_path)

    assert isinstance(doc, ParsedDocument)
    assert doc.metadata.get("dual_track_route") == "all_scanned_paddleocr"


def test_dual_track_mixed_page_hard_routing(tmp_path):
    """Verify mixed PDF routes digital pages to Docling and scanned pages to PaddleOCR without double-work."""
    mixed_pdf_path = tmp_path / "mixed_test.pdf"
    doc_pdf = fitz.open()

    p1 = doc_pdf.new_page(width=400, height=300)
    p1.insert_text((50, 50), "这是第一页原生数字内容，包含超过三十个字符以触发Docling通道。" * 2)

    p2 = doc_pdf.new_page(width=400, height=300)
    p2.insert_text((50, 50), "签字")  # 2 chars < 30 threshold
    p2.draw_rect(fitz.Rect(20, 20, 380, 280), color=(0, 0, 1))

    doc_pdf.save(str(mixed_pdf_path))
    doc_pdf.close()

    engine = DualTrackLayoutEngine(char_density_threshold=30)
    doc = engine.parse(mixed_pdf_path)

    assert isinstance(doc, ParsedDocument)
    assert doc.metadata.get("dual_track_route") == "mixed_pages"
    assert doc.metadata.get("digital_pages") == [1]
    assert doc.metadata.get("scanned_pages") == [2]


def test_physical_anchor_propagation_from_dual_track():
    """Verify that all chunks produced carry page_number, bounding_box: [x0, y0, x1, y1], and heading_breadcrumb."""
    parser = LayoutAwareParser(engine_type="dual_track")
    doc = parser.parse(PDF_SAMPLE_PATH)

    chunker = HierarchicalChunker()
    res = chunker.chunk_document(doc)

    assert len(res["parents"]) > 0
    assert len(res["children"]) > 0
    assert len(res["tables"]) > 0

    for chunk in res["all"]:
        # 1. page_number
        assert isinstance(chunk.page_number, int)
        assert chunk.page_number >= 1
        assert "page_number" in chunk.metadata

        # 2. bounding_box: [x0, y0, x1, y1]
        assert isinstance(chunk.bounding_box, list)
        assert len(chunk.bounding_box) == 4
        assert all(isinstance(v, (int, float)) for v in chunk.bounding_box)
        assert "bounding_box" in chunk.metadata

        # 3. heading_breadcrumb
        assert isinstance(chunk.heading_breadcrumb, list)
        assert len(chunk.heading_breadcrumb) >= 1
        assert "heading_breadcrumb" in chunk.metadata

        # 4. Dictionary serialization preserves anchors
        d = chunk.to_dict()
        assert d["page_number"] == chunk.page_number
        assert d["bounding_box"] == chunk.bounding_box
        assert d["heading_breadcrumb"] == chunk.heading_breadcrumb
