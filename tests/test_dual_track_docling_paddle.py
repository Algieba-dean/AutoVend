"""
Decoupled Unit and Integration Tests for Dual-Track Isolation Architecture
(IBM Docling TableFormer + PaddleOCR PP-Structure) in AutoVend.

Strictly segregated into:
1. TestRealEngineMockedArchitecture:
   Verifies real engine conversion and data structures (tables, dataframes, html, prov bboxes,
   sections, breadcrumbs) using high-fidelity mock representations of Docling & Paddle structures.
   Enforces exact engine identity assertions (no vague `in ["A", "B"]`).
2. TestHonestDegradationAndCircuitBreakers:
   Verifies process isolation with OS-level SIGKILL termination on timeout,
   honest degradation tags on runtime exceptions or missing packages (is_degraded = True,
   extraction_quality = "degraded", tableformer = False, fallback_level = "L2_pdfplumber"),
   and multi-tier circuit breaker degradation (L1 -> L2 -> L3).
3. TestPreFlightProbeAndAnchorPropagation:
   Verifies PreFlightProbe character density routing, physical anchor propagation,
   and hybrid page slicing.
"""

import os
import re
import time
from pathlib import Path
from unittest.mock import MagicMock

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
    HierarchicalChunker,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_SAMPLE_PATH = _PROJECT_ROOT / "data" / "sample_specs" / "xiaomi_su7_ultra_specs.pdf"


class TestRealEngineMockedArchitecture:
    """
    Rigorously tests the actual parsing, conversion, and assembly code paths of
    Docling TableFormer and Paddle PP-Structure without falling back to PyMuPDF.
    Uses exact schema mocks representing real C++/DL engine outputs.
    """

    def test_docling_tableformer_conversion_path(self):
        """
        Verify that RealDoclingAdapter faithfully extracts TableFormer tables, DataFrames,
        HTML representations, physical bounding boxes, and Markdown hierarchical sections
        with strictly asserted engine metadata (ZERO fuzzy fallback matching).
        """
        adapter = RealDoclingAdapter(allow_fallback=False)

        mock_converter = MagicMock()
        adapter._converter = mock_converter

        mock_conv_res = MagicMock()
        mock_converter.convert.return_value = mock_conv_res

        mock_doc = MagicMock()
        mock_conv_res.document = mock_doc

        # 1. Mock TableFormer table output
        mock_table = MagicMock()
        mock_df = MagicMock()
        mock_df.columns.tolist.return_value = ["参数名称", "技术规格"]
        mock_df.values.tolist.return_value = [
            ["电机配置", "前双电机 + 后单电机"],
            ["最高车速", "350 km/h"],
        ]
        mock_table.export_to_dataframe.return_value = mock_df
        table_html = (
            "<table><tr><th>参数名称</th><th>技术规格</th></tr>"
            "<tr><td>电机配置</td><td>前双电机 + 后单电机</td></tr>"
            "<tr><td>最高车速</td><td>350 km/h</td></tr></table>"
        )
        mock_table.export_to_html.return_value = table_html

        # Mock physical anchor provenance
        mock_prov = MagicMock()
        mock_prov.page_no = 1
        mock_prov.bbox = MagicMock()
        mock_prov.bbox.l = 45.0
        mock_prov.bbox.t = 120.0
        mock_prov.bbox.r = 380.0
        mock_prov.bbox.b = 260.0
        mock_table.prov = [mock_prov]

        mock_doc.tables = [mock_table]

        # 2. Mock Hierarchical Markdown
        mock_doc.export_to_markdown.return_value = (
            "# 小米SU7 Ultra性能指标\n"
            "## 动力总成\n"
            "系统最大马力达1548PS。\n"
            "## 底盘制动\n"
            "配备碳陶瓷制动盘与固定式卡钳。"
        )
        mock_doc.pages = [MagicMock(), MagicMock()]

        parsed = adapter.parse(PDF_SAMPLE_PATH)

        # Strict non-fuzzy assertions
        assert isinstance(parsed, ParsedDocument)
        assert parsed.metadata["engine"] == "ibm_docling_production"
        assert parsed.metadata["docling_adapter"] is True
        assert parsed.metadata["tableformer"] is True
        assert parsed.is_degraded is False
        assert parsed.metadata.get("extraction_quality") is None or parsed.metadata.get("extraction_quality") != "degraded"
        assert parsed.pages == 2

        # Verify extracted tables
        assert len(parsed.tables) == 1
        t0 = parsed.tables[0]
        assert t0.extraction_engine == "ibm_docling_tableformer"
        assert t0.confidence == 0.98
        assert t0.headers == ["参数名称", "技术规格"]
        assert t0.rows == [
            ["参数名称", "技术规格"],
            ["电机配置", "前双电机 + 后单电机"],
            ["最高车速", "350 km/h"],
        ]
        assert t0.metadata["html_content"] == table_html
        assert t0.page_num == 1
        assert t0.bbox is not None
        assert t0.bbox.x0 == 45.0
        assert t0.bbox.top == 120.0
        assert t0.bbox.x1 == 380.0
        assert t0.bbox.bottom == 260.0

        # Verify hierarchical sections
        assert len(parsed.sections) == 2
        sec_titles = [s.title for s in parsed.sections]
        assert sec_titles == ["动力总成", "底盘制动"]
        assert "1548PS" in parsed.sections[0].content
        assert "碳陶瓷制动盘" in parsed.sections[1].content

    def test_paddle_ppstructure_conversion_path(self, tmp_path):
        """
        Verify that RealPaddleOCRAdapter extracts PP-Structure layout regions,
        table HTML structures, and text blocks on CPU with strictly asserted engine identity.
        """
        adapter = RealPaddleOCRAdapter(allow_fallback=False)

        mock_engine = MagicMock()
        adapter._engine = mock_engine

        # Mock PP-Structure inference result
        tbl_html = (
            "<html><body><table>"
            "<tr><td>检验项目</td><td>检测结果</td><td>参考范围</td></tr>"
            "<tr><td>收缩压</td><td>118</td><td>90-139</td></tr>"
            "</table></body></html>"
        )
        mock_engine.return_value = [
            {
                "type": "title",
                "bbox": [50.0, 30.0, 250.0, 60.0],
                "res": [{"text": "体检结论报告"}],
            },
            {
                "type": "text",
                "bbox": [50.0, 70.0, 320.0, 95.0],
                "res": [{"text": "受检人各项生理指标均符合承保标准。"}],
            },
            {
                "type": "table",
                "bbox": [50.0, 110.0, 380.0, 220.0],
                "res": {"html": tbl_html},
            },
        ]

        scanned_pdf_path = tmp_path / "scanned_spec.pdf"
        doc_pdf = fitz.open()
        p = doc_pdf.new_page(width=400, height=300)
        p.insert_text((50, 50), "短文本")
        doc_pdf.save(str(scanned_pdf_path))
        doc_pdf.close()

        parsed = adapter.parse_scanned_pdf(scanned_pdf_path)

        assert isinstance(parsed, ParsedDocument)
        assert parsed.metadata["engine"] == "paddle_ocr_scanned_pipeline"
        assert parsed.metadata["cpu_only"] is True
        assert parsed.is_degraded is False

        # Verify extracted table
        assert len(parsed.tables) == 1
        t = parsed.tables[0]
        assert t.extraction_engine == "paddle_pp_structure"
        assert t.headers == ["检验项目", "检测结果", "参考范围"]
        assert t.rows == [
            ["检验项目", "检测结果", "参考范围"],
            ["收缩压", "118", "90-139"],
        ]
        assert t.bbox.x0 == 50.0
        assert t.bbox.top == 110.0
        assert t.bbox.x1 == 380.0
        assert t.bbox.bottom == 220.0
        assert t.metadata["html_content"] == tbl_html

        # Verify sections
        assert len(parsed.sections) == 1
        assert "受检人各项生理指标均符合承保标准。" in parsed.raw_text

    def test_dual_track_routes_digital_to_docling_mocked(self):
        """Verify DualTrackLayoutEngine correctly routes digital document to L1 Docling."""
        engine = DualTrackLayoutEngine(char_density_threshold=30)

        # Mock high-quality Docling response
        mock_doc = ParsedDocument(
            title=PDF_SAMPLE_PATH.stem,
            sections=[TextSection(title="动力", content="1548PS", level=1, page_num=1, breadcrumb_path=["动力"])],
            tables=[
                TableBlock(
                    page_num=1,
                    bbox=BoundingBox(0.0, 0.0, 100.0, 100.0, page=1),
                    rows=[["参数", "值"], ["续航", "800km"]],
                    headers=["参数", "值"],
                    extraction_engine="ibm_docling_tableformer",
                )
            ],
            pages=2,
            raw_text="动力 1548PS",
        )
        engine.docling.parse = MagicMock(return_value=mock_doc)

        doc = engine.parse(PDF_SAMPLE_PATH)

        assert doc.metadata["dual_track_route"] == "all_digital_docling"
        assert doc.metadata["fallback_level"] == "L1_docling"
        assert doc.metadata["extraction_quality"] == "high_quality"
        assert doc.is_degraded is False
        assert doc.tables[0].extraction_engine == "ibm_docling_tableformer"

    def test_dual_track_routes_scanned_to_paddle_mocked(self, tmp_path):
        """Verify DualTrackLayoutEngine correctly routes scanned document to L1 PaddleOCR."""
        scanned_pdf = tmp_path / "scanned_doc.pdf"
        doc_pdf = fitz.open()
        p = doc_pdf.new_page(width=400, height=300)
        p.insert_text((50, 50), "短文本")  # < 30 chars
        doc_pdf.save(str(scanned_pdf))
        doc_pdf.close()

        engine = DualTrackLayoutEngine(char_density_threshold=30)

        mock_doc = ParsedDocument(
            title=scanned_pdf.stem,
            sections=[TextSection(title="扫描正文", content="体检内容", level=1, page_num=1, breadcrumb_path=["扫描正文"])],
            tables=[
                TableBlock(
                    page_num=1,
                    bbox=BoundingBox(0.0, 0.0, 100.0, 100.0, page=1),
                    rows=[["检测", "结果"], ["血压", "正常"]],
                    headers=["检测", "结果"],
                    extraction_engine="paddle_pp_structure",
                )
            ],
            pages=1,
            raw_text="体检内容",
        )
        engine.paddle.parse_scanned_pdf = MagicMock(return_value=mock_doc)

        doc = engine.parse(scanned_pdf)

        assert doc.metadata["dual_track_route"] == "all_scanned_paddleocr"
        assert doc.metadata["fallback_level"] == "L1_paddleocr"
        assert doc.metadata["extraction_quality"] == "high_quality"
        assert doc.is_degraded is False
        assert doc.tables[0].extraction_engine == "paddle_pp_structure"

    def test_hybrid_document_pre_extraction_slicing(self, tmp_path):
        """
        Critical Test for Vulnerability 3:
        Verify that for hybrid PDFs, PyMuPDF pre-extraction slices the document,
        feeding Docling ONLY the digital pages and Paddle ONLY the scanned pages.
        Also verify that 1-based page indices are mapped back accurately.
        """
        hybrid_pdf = tmp_path / "hybrid_pre_slice.pdf"
        doc_pdf = fitz.open()

        # Page 1: Digital (> 30 chars)
        p1 = doc_pdf.new_page(width=400, height=300)
        p1.insert_text((50, 50), "这是第一页原生数字内容，包含超过三十个字符以触发Docling通道。" * 2)

        # Page 2: Scanned (< 30 chars)
        p2 = doc_pdf.new_page(width=400, height=300)
        p2.insert_text((50, 50), "短文本")

        # Page 3: Digital (> 30 chars)
        p3 = doc_pdf.new_page(width=400, height=300)
        p3.insert_text((50, 50), "这是第三页原生数字内容，包含超过三十个字符以触发Docling通道。" * 2)

        # Page 4: Scanned (< 30 chars)
        p4 = doc_pdf.new_page(width=400, height=300)
        p4.insert_text((50, 50), "签名")

        doc_pdf.save(str(hybrid_pdf))
        doc_pdf.close()

        engine = DualTrackLayoutEngine(char_density_threshold=30)

        docling_log = tmp_path / "docling_seen.txt"
        paddle_log = tmp_path / "paddle_seen.txt"

        def mock_docling_parse(file_path):
            p = Path(file_path)
            with fitz.open(str(p)) as f:
                slice_len = len(f)
            docling_log.write_text(str(slice_len))
            # Returns doc with sliced 1-based pages [1, 2]
            return ParsedDocument(
                title=p.stem,
                sections=[
                    TextSection(title="数字正文1", content="第一页数字", level=1, page_num=1, breadcrumb_path=["第 1 页"]),
                    TextSection(title="数字正文2", content="第二页数字", level=1, page_num=2, breadcrumb_path=["第 2 页"]),
                ],
                tables=[
                    TableBlock(
                        page_num=2,
                        bbox=BoundingBox(0.0, 0.0, 100.0, 100.0, page=2),
                        rows=[["数字表头", "值"], ["参数", "100"]],
                        headers=["数字表头", "值"],
                        extraction_engine="ibm_docling_tableformer",
                        title="Table_P2_1",
                    )
                ],
                pages=slice_len,
                raw_text="第一页数字\n\n第二页数字",
            )

        def mock_paddle_parse(file_path, page_numbers=None):
            p = Path(file_path)
            with fitz.open(str(p)) as f:
                slice_len = len(f)
            paddle_log.write_text(str(slice_len))
            # Returns doc with sliced 1-based pages [1, 2]
            return ParsedDocument(
                title=p.stem,
                sections=[
                    TextSection(title="扫描正文1", content="第一页扫描", level=1, page_num=1, breadcrumb_path=["第 1 页"]),
                    TextSection(title="扫描正文2", content="第二页扫描", level=1, page_num=2, breadcrumb_path=["第 2 页"]),
                ],
                tables=[
                    TableBlock(
                        page_num=1,
                        bbox=BoundingBox(0.0, 0.0, 100.0, 100.0, page=1),
                        rows=[["扫描表头", "值"], ["印章", "已盖"]],
                        headers=["扫描表头", "值"],
                        extraction_engine="paddle_pp_structure",
                        title="Scanned_Table_P1_1",
                    )
                ],
                pages=slice_len,
                raw_text="第一页扫描\n\n第二页扫描",
            )

        engine.docling.parse = mock_docling_parse
        engine.paddle.parse_scanned_pdf = mock_paddle_parse

        merged = engine.parse(hybrid_pdf)

        # 1. Verify Docling received ONLY a sliced 2-page PDF
        assert docling_log.exists()
        assert int(docling_log.read_text()) == 2, "Docling must ONLY receive the 2 digital pages!"

        # 2. Verify Paddle received ONLY a sliced 2-page PDF
        assert paddle_log.exists()
        assert int(paddle_log.read_text()) == 2, "Paddle must ONLY receive the 2 scanned pages!"

        # 3. Verify output page remapping to original 4-page document indices
        assert merged.pages == 4
        assert merged.metadata["dual_track_route"] == "mixed_pages"
        assert merged.metadata["digital_pages"] == [1, 3]
        assert merged.metadata["scanned_pages"] == [2, 4]

        # Sliced digital page 1 -> orig page 1; sliced digital page 2 -> orig page 3
        # Sliced scanned page 1 -> orig page 2; sliced scanned page 2 -> orig page 4
        all_section_pages = [s.page_num for s in merged.sections]
        assert all_section_pages == [1, 2, 3, 4]

        # Verify table page numbers remapped
        tbl_pages = [t.page_num for t in merged.tables]
        assert tbl_pages == [2, 3]  # scanned table on p2, digital table on p3


class TestHonestDegradationAndCircuitBreakers:
    """
    Rigorously tests audit integrity, honest degradation tags, and process isolation SIGKILL
    when exceptions, OOM, or timeouts occur.
    """

    def test_docling_adapter_runtime_exception_honest_audit(self):
        """
        Critical Test for Vulnerability 1:
        Verify that when Docling raises a runtime exception (e.g. CUDA OOM or internal crash),
        the adapter strictly marks:
          - is_degraded = True
          - extraction_quality = "degraded"
          - tableformer = False  (NOT True!)
          - fallback_level = "L2_pdfplumber"
          - t.extraction_engine = "pymupdf_pdfplumber" (NOT ibm_docling_tableformer!)
        """
        adapter = RealDoclingAdapter(allow_fallback=True)

        mock_converter = MagicMock()
        mock_converter.convert.side_effect = RuntimeError("CUDA out of memory on TableFormer backbone")
        adapter._converter = mock_converter

        doc = adapter.parse(PDF_SAMPLE_PATH)

        assert isinstance(doc, ParsedDocument)
        # 1. Honest audit flags
        assert doc.is_degraded is True
        assert doc.metadata["is_degraded"] is True
        assert doc.metadata["extraction_quality"] == "degraded"
        assert doc.metadata["fallback_level"] == "L2_pdfplumber"
        assert doc.metadata["tableformer"] is False
        assert "CUDA out of memory" in doc.metadata.get("degraded_reason", "")

        # 2. Honest table engine labeling (no fake TableFormer claim)
        assert len(doc.tables) >= 1
        for t in doc.tables:
            assert t.extraction_engine == "pymupdf_pdfplumber"
            assert t.extraction_engine != "ibm_docling_tableformer"

    def test_docling_adapter_unavailable_honest_audit(self):
        """Verify that when Docling is completely uninstalled/unavailable, degradation is honest."""
        adapter = RealDoclingAdapter(allow_fallback=True)
        adapter._converter = False
        adapter._init_error = "Package ibm_docling not found in environment"

        doc = adapter.parse(PDF_SAMPLE_PATH)

        assert doc.is_degraded is True
        assert doc.metadata["tableformer"] is False
        assert doc.metadata["extraction_quality"] == "degraded"
        assert doc.metadata["fallback_level"] == "L2_pdfplumber"
        for t in doc.tables:
            assert t.extraction_engine == "pymupdf_pdfplumber"

    def test_docling_adapter_strict_no_fallback_raises(self):
        """Verify that when allow_fallback=False, conversion exceptions raise directly without falling back."""
        adapter = RealDoclingAdapter(allow_fallback=False)
        mock_converter = MagicMock()
        mock_converter.convert.side_effect = RuntimeError("Fatal Docling conversion error")
        adapter._converter = mock_converter

        with pytest.raises(RuntimeError) as exc_info:
            adapter.parse(PDF_SAMPLE_PATH)
        assert "Fatal Docling conversion error" in str(exc_info.value)

    def test_process_timeout_sigkill_termination(self):
        """
        Critical Test for Vulnerability 2:
        Verify that _run_with_timeout executes in a real process, terminates on timeout,
        delivers OS-level SIGKILL to the child process, and leaves zero orphan/zombie threads.
        """
        def infinite_blocking_worker():
            while True:
                time.sleep(0.05)

        t0 = time.time()
        with pytest.raises(TimeoutError) as exc_info:
            DualTrackLayoutEngine._run_with_timeout(
                infinite_blocking_worker,
                timeout_seconds=0.4,
            )
        elapsed = time.time() - t0

        err_msg = str(exc_info.value)
        assert "timed out after 0.4s" in err_msg
        assert "SIGKILL delivered to PID" in err_msg
        assert elapsed < 2.0  # Prompt termination

        # Verify child PID is dead and reaped
        match = re.search(r"PID (\d+)", err_msg)
        assert match is not None
        child_pid = int(match.group(1))

        # Check process existence via signal 0
        try:
            os.kill(child_pid, 0)
            pytest.fail(f"Child process {child_pid} was not terminated! Zombie process hazard.")
        except ProcessLookupError:
            # Expected: Process does not exist
            pass

    def test_process_timeout_large_payload_no_deadlock(self):
        """
        Verify that _run_with_timeout drains pipe continuously and does not deadlock
        when worker returns large payloads (> 64KB OS pipe buffer limit).
        """
        def large_payload_worker():
            return "D" * 2_000_000  # 2MB payload exceeds OS pipe buffer

        t0 = time.time()
        res = DualTrackLayoutEngine._run_with_timeout(
            large_payload_worker,
            timeout_seconds=3.0,
        )
        elapsed = time.time() - t0

        assert len(res) == 2_000_000
        assert elapsed < 1.0  # Must return immediately without pipe buffer deadlock

    def test_digital_path_l1_oom_trips_to_l2_pdfplumber(self, monkeypatch):
        """Verify that Docling OOM trips circuit breaker to L2 pdfplumber with honest metadata."""
        engine = DualTrackLayoutEngine(char_density_threshold=30)

        def mock_docling_fail(path):
            raise MemoryError("CUDA out of memory on page 14")

        monkeypatch.setattr(engine.docling, "parse", mock_docling_fail)

        doc = engine.parse(PDF_SAMPLE_PATH)

        assert isinstance(doc, ParsedDocument)
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

    def test_digital_path_l2_failure_trips_to_l3_pymupdf_text(self, monkeypatch):
        """Verify that when both Docling and pdfplumber fail, circuit breaker trips to L3 PyMuPDF raw text."""
        engine = DualTrackLayoutEngine(char_density_threshold=30)

        def mock_docling_fail(path):
            raise TimeoutError("Docling TableFormer timed out (> 30s)")

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

    def test_scanned_path_l1_failure_trips_to_l2_pymupdf_ocr(self, tmp_path, monkeypatch):
        """Verify that PaddleOCR crash on scanned document trips circuit breaker specifically to L2 PyMuPDF OCR."""
        scanned_path = tmp_path / "scanned_doc.pdf"
        doc_pdf = fitz.open()
        page = doc_pdf.new_page(width=400, height=300)
        page.insert_text((50, 50), "短文本")  # 3 chars < 30
        page.draw_rect(fitz.Rect(10, 10, 390, 290), color=(0, 0, 0))
        doc_pdf.save(str(scanned_path))
        doc_pdf.close()

        engine = DualTrackLayoutEngine(char_density_threshold=30)

        monkeypatch.setattr(
            engine.paddle,
            "parse_scanned_pdf",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("PaddleOCR PPStructure crashed: SIGSEGV")),
        )

        mock_l2_doc = ParsedDocument(
            title=scanned_path.stem,
            sections=[
                TextSection(
                    title=f"{scanned_path.stem} 第 1 页 OCR正文",
                    content="OCR识别出的文字内容",
                    level=1,
                    page_num=1,
                    breadcrumb_path=[scanned_path.stem, "第 1 页"],
                )
            ],
            tables=[],
            pages=1,
            raw_text="OCR识别出的文字内容",
            metadata={
                "engine": "pymupdf_ocr_fallback",
                "extraction_quality": "degraded",
                "fallback_level": "L2_pymupdf_ocr",
                "degraded_reason": "PaddleOCR PPStructure crashed: SIGSEGV",
                "is_degraded": True,
            },
        )
        monkeypatch.setattr(engine, "_extract_l2_pymupdf_ocr", lambda *a, **k: mock_l2_doc)

        doc = engine.parse(scanned_path)

        assert isinstance(doc, ParsedDocument)
        assert doc.is_degraded is True
        assert doc.metadata["extraction_quality"] == "degraded"
        assert doc.metadata["fallback_level"] == "L2_pymupdf_ocr"
        assert doc.metadata["engine"] == "pymupdf_ocr_fallback"
        assert "PaddleOCR PPStructure crashed" in doc.metadata["degraded_reason"]
        assert len(doc.sections) == 1

    def test_scanned_path_l2_failure_trips_to_l3_pymupdf_text(self, tmp_path, monkeypatch):
        """Verify that when both PaddleOCR and PyMuPDF OCR fail, circuit breaker trips specifically to L3 raw text."""
        scanned_path = tmp_path / "scanned_doc.pdf"
        doc_pdf = fitz.open()
        page = doc_pdf.new_page(width=400, height=300)
        page.insert_text((50, 50), "短文本")  # 3 chars < 30
        page.draw_rect(fitz.Rect(10, 10, 390, 290), color=(0, 0, 0))
        doc_pdf.save(str(scanned_path))
        doc_pdf.close()

        engine = DualTrackLayoutEngine(char_density_threshold=30)

        monkeypatch.setattr(
            engine.paddle,
            "parse_scanned_pdf",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("PaddleOCR PPStructure crashed")),
        )
        monkeypatch.setattr(
            engine,
            "_extract_l2_pymupdf_ocr",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Tesseract OCR engine missing")),
        )

        doc = engine.parse(scanned_path)

        assert isinstance(doc, ParsedDocument)
        assert doc.is_degraded is True
        assert doc.metadata["extraction_quality"] == "degraded"
        assert doc.metadata["fallback_level"] == "L3_pymupdf_text"
        assert doc.metadata["engine"] == "pymupdf_raw_text_fallback"
        assert "PaddleOCR PPStructure crashed" in doc.metadata["degraded_reason"]
        assert "Tesseract OCR engine missing" in doc.metadata["degraded_reason"]
        assert len(doc.sections) >= 1

    def test_zero_mock_data_unrecoverable_error(self, tmp_path):
        """Verify that if even PyMuPDF extracts nothing, DocumentParsingUnrecoverableError is raised."""
        blank_pdf = tmp_path / "completely_blank.pdf"
        doc_pdf = fitz.open()
        doc_pdf.new_page(width=400, height=300)  # Empty white page
        doc_pdf.save(str(blank_pdf))
        doc_pdf.close()

        engine = DualTrackLayoutEngine(char_density_threshold=30)

        with pytest.raises(DocumentParsingUnrecoverableError):
            engine.parse(blank_pdf)


class TestPreFlightProbeAndAnchorPropagation:
    """
    Verifies PreFlightProbe character density classification and physical anchor
    propagation (page_number, bounding_box, breadcrumb) across chunking layers.
    """

    def test_dual_track_density_classification(self, tmp_path):
        """Verify page-level character density detection: >= 30/page -> digital; < 30/page -> scanned."""
        engine = DualTrackLayoutEngine(char_density_threshold=30)
        density_info = engine.check_density(PDF_SAMPLE_PATH)

        assert len(density_info["digital_pages"]) >= 2
        assert len(density_info["scanned_pages"]) == 0
        for p_num, count in density_info["page_counts"].items():
            assert count >= 30, f"Page {p_num} expected >= 30 chars, got {count}"

        # Mixed PDF: Page 1 with 100 chars, Page 2 with 5 chars (< 30)
        mixed_pdf_path = tmp_path / "mixed_doc.pdf"
        doc_pdf = fitz.open()

        p1 = doc_pdf.new_page(width=400, height=300)
        p1.insert_text((50, 50), "这是第一页原生数字内容，包含超过三十个字符以触发Docling通道。" * 2, fontname="china-s")

        p2 = doc_pdf.new_page(width=400, height=300)
        p2.insert_text((50, 50), "短文本", fontname="china-s")
        p2.draw_rect(fitz.Rect(20, 20, 380, 280), color=(0, 0, 1))

        doc_pdf.save(str(mixed_pdf_path))
        doc_pdf.close()

        mixed_density = engine.check_density(mixed_pdf_path)
        assert mixed_density["digital_pages"] == [1]
        assert mixed_density["scanned_pages"] == [2]

    def test_preflight_probe_fast_metadata_and_dimensions(self):
        """Verify PreFlightProbe extracts dimensions, orientation, rotation, and character counts in <100ms."""
        t0 = time.perf_counter()
        probe = PreFlightProbe.inspect(PDF_SAMPLE_PATH, char_density_threshold=30)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert elapsed_ms < 100.0
        assert probe["total_pages"] >= 2
        assert len(probe["digital_pages"]) >= 2
        assert len(probe["scanned_pages"]) == 0
        assert 1 in probe["page_dimensions"]
        assert 1 in probe["page_orientations"]
        assert 1 in probe["page_rotations"]
        w, h = probe["page_dimensions"][1]
        assert w > 0 and h > 0

    def test_preflight_probe_corrupt_and_encrypted(self, tmp_path):
        """Verify PreFlightProbe raises DocumentParsingUnrecoverableError on corrupt or encrypted files."""
        corrupt_pdf = tmp_path / "corrupt_preflight.pdf"
        corrupt_pdf.write_bytes(b"Not a valid PDF header at all")
        with pytest.raises(DocumentParsingUnrecoverableError):
            PreFlightProbe.inspect(corrupt_pdf)

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

    def test_physical_anchor_propagation_from_dual_track(self):
        """Verify that all chunks produced carry page_number, bounding_box, and heading_breadcrumb."""
        parser = LayoutAwareParser(engine_type="dual_track")
        doc = parser.parse(PDF_SAMPLE_PATH)

        chunker = HierarchicalChunker()
        res = chunker.chunk_document(doc)

        assert len(res["parents"]) > 0
        assert len(res["children"]) > 0
        assert len(res["tables"]) > 0

        for chunk in res["all"]:
            assert isinstance(chunk.page_number, int)
            assert chunk.page_number >= 1
            assert "page_number" in chunk.metadata

            assert isinstance(chunk.bounding_box, list)
            assert len(chunk.bounding_box) == 4
            assert all(isinstance(v, (int, float)) for v in chunk.bounding_box)
            assert "bounding_box" in chunk.metadata

            assert isinstance(chunk.heading_breadcrumb, list)
            assert len(chunk.heading_breadcrumb) >= 1
            assert "heading_breadcrumb" in chunk.metadata

            d = chunk.to_dict()
            assert d["page_number"] == chunk.page_number
            assert d["bounding_box"] == chunk.bounding_box
            assert d["heading_breadcrumb"] == chunk.heading_breadcrumb

    def test_physical_anchor_propagation_on_l2_degraded_document(self, monkeypatch):
        """Verify that degraded documents (L2 pdfplumber) propagate all physical anchors to chunks."""
        engine = DualTrackLayoutEngine(char_density_threshold=30)

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

    def test_physical_anchor_propagation_on_l3_degraded_document(self, monkeypatch):
        """Verify that L3 PyMuPDF degraded documents propagate page_number, bounding_box, and breadcrumb to all chunks."""
        engine = DualTrackLayoutEngine(char_density_threshold=30)

        monkeypatch.setattr(engine.docling, "parse", lambda p: (_ for _ in ()).throw(RuntimeError("Docling failed")))
        monkeypatch.setattr(engine._fallback, "parse", lambda p, **kw: (_ for _ in ()).throw(RuntimeError("pdfplumber failed")))

        doc = engine.parse(PDF_SAMPLE_PATH)
        assert doc.is_degraded is True
        assert doc.metadata.get("fallback_level") == "L3_pymupdf_text"

        chunker = HierarchicalChunker()
        res = chunker.chunk_document(doc)

        assert len(res["all"]) > 0
        for chunk in res["all"]:
            assert isinstance(chunk.page_number, int)
            assert chunk.page_number >= 1
            assert isinstance(chunk.bounding_box, list)
            assert len(chunk.bounding_box) == 4
            assert any(v > 0 for v in chunk.bounding_box)
            assert isinstance(chunk.heading_breadcrumb, list)
            assert len(chunk.heading_breadcrumb) >= 1

    def test_alternating_multipage_hybrid_document(self, tmp_path):
        """Verify 6-page hybrid document with alternating digital and scanned pages routes and merges correctly."""
        hybrid_pdf = tmp_path / "alternating_hybrid.pdf"
        doc_pdf = fitz.open()

        for p in range(1, 7):
            page = doc_pdf.new_page(width=400, height=300)
            if p % 2 == 1:
                page.insert_text(
                    (50, 50),
                    f"这是第 {p} 页数字原生内容，包含足够多的参数字符以确保字符数大于三十个字符门限值。",
                    fontname="china-s",
                )
            else:
                page.insert_text((50, 50), f"附录{p}", fontname="china-s")
                page.draw_rect(fitz.Rect(20, 20, 380, 280), color=(0, 0, 1))

        doc_pdf.save(str(hybrid_pdf))
        doc_pdf.close()

        engine = DualTrackLayoutEngine(char_density_threshold=30)
        density_info = engine.check_density(hybrid_pdf)
        assert density_info["digital_pages"] == [1, 3, 5]
        assert density_info["scanned_pages"] == [2, 4, 6]

        doc = engine.parse(hybrid_pdf)
        assert isinstance(doc, ParsedDocument)
        assert doc.pages == 6
        assert doc.metadata.get("dual_track_route") == "mixed_pages"
        assert doc.metadata.get("digital_pages") == [1, 3, 5]
        assert doc.metadata.get("scanned_pages") == [2, 4, 6]
        assert doc.is_degraded is True
        assert doc.metadata.get("extraction_quality") == "degraded"

        pages_found = [s.page_num for s in doc.sections]
        assert 1 in pages_found
        assert 2 in pages_found
        assert pages_found == sorted(pages_found)

    def test_slice_pdf_to_temp_invalid_pages(self, tmp_path):
        """Verify _slice_pdf_to_temp raises ValueError cleanly and does not leak directories on invalid pages."""
        pdf_path = tmp_path / "simple.pdf"
        doc_pdf = fitz.open()
        doc_pdf.new_page(width=400, height=300)
        doc_pdf.save(str(pdf_path))
        doc_pdf.close()

        with pytest.raises(ValueError) as exc_info:
            with DualTrackLayoutEngine._slice_pdf_to_temp(pdf_path, [999, 1000]):
                pass
        assert "No valid pages found" in str(exc_info.value)
