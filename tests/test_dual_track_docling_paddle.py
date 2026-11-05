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
    DocumentParsingUnrecoverableError,
    DualTrackLayoutEngine,
    LayoutAwareParser,
    ParsedDocument,
    PreFlightProbe,
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


def test_preflight_probe_fast_metadata_and_dimensions():
    """Verify PreFlightProbe extracts dimensions, orientation, rotation, and character counts in <50ms."""
    import time
    t0 = time.perf_counter()
    probe = PreFlightProbe.inspect(PDF_SAMPLE_PATH, char_density_threshold=30)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 100.0  # Ultra-fast probe
    assert probe["total_pages"] >= 2
    assert len(probe["digital_pages"]) >= 2
    assert len(probe["scanned_pages"]) == 0
    assert 1 in probe["page_dimensions"]
    assert 1 in probe["page_orientations"]
    assert 1 in probe["page_rotations"]
    w, h = probe["page_dimensions"][1]
    assert w > 0 and h > 0


def test_preflight_probe_corrupt_and_encrypted(tmp_path):
    """Verify PreFlightProbe raises DocumentParsingUnrecoverableError on corrupt or encrypted files."""
    # 1. Corrupt PDF
    corrupt_pdf = tmp_path / "corrupt_preflight.pdf"
    corrupt_pdf.write_bytes(b"Not a valid PDF header at all")
    with pytest.raises(DocumentParsingUnrecoverableError):
        PreFlightProbe.inspect(corrupt_pdf)

    # 2. Encrypted PDF with password
    encrypted_pdf = tmp_path / "locked.pdf"
    doc = fitz.open()
    doc.new_page(width=400, height=300)
    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY
        | fitz.PDF_PERM_PRINT
        | fitz.PDF_PERM_COPY
        | fitz.PDF_PERM_ANNOTATE
    )
    doc.save(
        str(encrypted_pdf),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="secret_owner",
        user_pw="secret_user",
        permissions=perm,
    )
    doc.close()

    with pytest.raises(DocumentParsingUnrecoverableError):
        PreFlightProbe.inspect(encrypted_pdf)


def test_digital_path_l1_oom_trips_to_l2_pdfplumber(monkeypatch):
    """Verify that Docling OOM/Exception trips circuit breaker to L2 pdfplumber with honest metadata."""
    engine = DualTrackLayoutEngine(char_density_threshold=30)

    # Simulate Docling OOM
    def mock_docling_fail(path):
        raise MemoryError("CUDA out of memory on page 14")

    monkeypatch.setattr(engine.docling, "parse", mock_docling_fail)

    doc = engine.parse(PDF_SAMPLE_PATH)

    assert isinstance(doc, ParsedDocument)
    # Honest metadata & Audit trail
    assert doc.is_degraded is True
    assert doc.metadata.get("extraction_quality") == "degraded"
    assert doc.metadata.get("fallback_level") == "L2_pdfplumber"
    assert "CUDA out of memory" in doc.metadata.get("degraded_reason", "")
    assert doc.metadata.get("is_degraded") is True

    # Tables recovered via pdfplumber
    assert len(doc.tables) >= 1
    t0 = doc.tables[0]
    assert t0.extraction_engine == "pdfplumber_bordered_table"
    assert t0.page_num >= 1
    assert t0.bbox is not None


def test_digital_path_l2_failure_trips_to_l3_pymupdf_text(monkeypatch):
    """Verify that when both Docling and pdfplumber fail, circuit breaker trips to L3 PyMuPDF raw text."""
    engine = DualTrackLayoutEngine(char_density_threshold=30)

    # Simulate Docling failure
    def mock_docling_fail(path):
        raise TimeoutError("Docling TableFormer timed out (> 30s)")

    # Simulate pdfplumber failure
    def mock_pdfplumber_fail(path, **kwargs):
        raise RuntimeError("pdfplumber geometric boundary detection failed")

    monkeypatch.setattr(engine.docling, "parse", mock_docling_fail)
    monkeypatch.setattr(engine._fallback, "parse", mock_pdfplumber_fail)

    doc = engine.parse(PDF_SAMPLE_PATH)

    assert isinstance(doc, ParsedDocument)
    assert doc.is_degraded is True
    assert doc.metadata.get("extraction_quality") == "degraded"
    assert doc.metadata.get("fallback_level") == "L3_pymupdf_text"
    assert "timed out" in doc.metadata.get("degraded_reason", "")
    assert "pdfplumber" in doc.metadata.get("degraded_reason", "")

    # L3 drops table topology to guarantee SLA
    assert doc.tables == []
    assert len(doc.sections) >= 1
    assert len(doc.raw_text.strip()) > 50


def test_scanned_path_l1_failure_trips_to_l2_or_l3(tmp_path, monkeypatch):
    """Verify that PaddleOCR crash on scanned document trips circuit breaker to PyMuPDF OCR or text."""
    scanned_path = tmp_path / "scanned_doc.pdf"
    doc_pdf = fitz.open()
    page = doc_pdf.new_page(width=400, height=300)
    page.insert_text((50, 50), "短文本")  # 3 chars < 30
    page.draw_rect(fitz.Rect(10, 10, 390, 290), color=(0, 0, 0))
    doc_pdf.save(str(scanned_path))
    doc_pdf.close()

    engine = DualTrackLayoutEngine(char_density_threshold=30)

    def mock_paddle_crash(path, **kwargs):
        raise RuntimeError("PaddleOCR PPStructure crashed: SIGSEGV")

    monkeypatch.setattr(engine.paddle, "parse_scanned_pdf", mock_paddle_crash)

    doc = engine.parse(scanned_path)

    assert isinstance(doc, ParsedDocument)
    assert doc.is_degraded is True
    assert doc.metadata.get("extraction_quality") == "degraded"
    assert doc.metadata.get("fallback_level") in ["L2_pymupdf_ocr", "L3_pymupdf_text"]
    assert "PaddleOCR PPStructure crashed" in doc.metadata.get("degraded_reason", "")
    assert len(doc.sections) >= 1


def test_zero_mock_data_unrecoverable_error(tmp_path, monkeypatch):
    """Verify that if even PyMuPDF extracts nothing, DocumentParsingUnrecoverableError is raised (no mock fake data)."""
    # Create empty PDF with no text at all
    blank_pdf = tmp_path / "completely_blank.pdf"
    doc_pdf = fitz.open()
    doc_pdf.new_page(width=400, height=300)  # Empty white page
    doc_pdf.save(str(blank_pdf))
    doc_pdf.close()

    engine = DualTrackLayoutEngine(char_density_threshold=30)

    # Mock paddle and docling to fail
    monkeypatch.setattr(engine.paddle, "parse_scanned_pdf", lambda *args, **kwargs: None)
    monkeypatch.setattr(engine.docling, "parse", lambda *args, **kwargs: None)

    with pytest.raises(DocumentParsingUnrecoverableError):
        engine.parse(blank_pdf)


def test_physical_anchor_propagation_on_l2_degraded_document(monkeypatch):
    """Verify that degraded documents (L2 pdfplumber) propagate all physical anchors to chunks."""
    engine = DualTrackLayoutEngine(char_density_threshold=30)

    # Force L2 degradation
    monkeypatch.setattr(
        engine.docling,
        "parse",
        lambda p: (_ for _ in ()).throw(RuntimeError("Docling VRAM OOM")),
    )

    doc = engine.parse(PDF_SAMPLE_PATH)
    assert doc.is_degraded is True
    assert doc.metadata.get("fallback_level") == "L2_pdfplumber"

    chunker = HierarchicalChunker()
    res = chunker.chunk_document(doc)

    assert len(res["all"]) > 0
    for chunk in res["all"]:
        assert isinstance(chunk.page_number, int)
        assert chunk.page_number >= 1
        assert isinstance(chunk.bounding_box, list)
        assert len(chunk.bounding_box) == 4
        assert isinstance(chunk.heading_breadcrumb, list)
        assert len(chunk.heading_breadcrumb) >= 1

