"""
PaddleOCR (PP-Structure) Adapter for AutoVend (src/ingestion/paddle_ocr_adapter.py).

Dedicated heavy OCR & structure engine for scanned PDFs, stamped contracts, and images:
- CPU-isolated execution (use_gpu=False) to prevent CUDA memory hijacking and OpenMP deadlocks.
- SLANet table recovery, layout analysis, and text line orientation classification.
- Converts OCR & structure output into AutoVend ontology (ParsedDocument, TableBlock, TextSection).
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np

from src.ingestion.layout_parser import (
    BaseLayoutEngine,
    BoundingBox,
    ParsedDocument,
    PyMuPDFPlumberEngine,
    TableBlock,
    TextSection,
)

logger = logging.getLogger(__name__)


def _html_to_table_rows(html_str: str) -> List[List[str]]:
    """Parse basic HTML table representation into list of string rows."""
    if not html_str:
        return []
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_str, "html.parser")
        table = soup.find("table")
        if not table:
            return []
        rows = []
        for tr in table.find_all("tr"):
            row = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if any(row):
                rows.append(row)
        return rows
    except Exception:
        # Fallback regex parser for <tr><td>
        rows = []
        for tr in re.findall(r"<tr>(.*?)</tr>", html_str, re.IGNORECASE | re.DOTALL):
            cols = [
                re.sub(r"<[^>]+>", "", col).strip()
                for col in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.IGNORECASE | re.DOTALL)
            ]
            if any(cols):
                rows.append(cols)
        return rows


_PPSTRUCTURE_COMPATIBLE: Optional[bool] = None


def _probe_ppstructure_support() -> bool:
    """
    Probe in an isolated subprocess to verify if host CPU architecture
    supports the compiled PaddlePaddle C++ instruction set without raising SIGILL.
    """
    global _PPSTRUCTURE_COMPATIBLE
    if _PPSTRUCTURE_COMPATIBLE is not None:
        return _PPSTRUCTURE_COMPATIBLE

    import subprocess
    import sys

    probe_code = (
        "try:\n"
        "    from paddleocr import PPStructure\n"
        "    eng = PPStructure(show_log=False, use_gpu=False, table=True, layout=True)\n"
        "except Exception:\n"
        "    pass\n"
    )

    try:
        proc = subprocess.run(
            [sys.executable, "-c", probe_code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        _PPSTRUCTURE_COMPATIBLE = (proc.returncode == 0)
    except Exception:
        _PPSTRUCTURE_COMPATIBLE = False

    return _PPSTRUCTURE_COMPATIBLE


class RealPaddleOCRAdapter(BaseLayoutEngine):
    """
    Production adapter for PaddleOCR PP-Structure.
    Runs exclusively on CPU to eliminate PyTorch GPU concurrency deadlocks.
    """

    def __init__(self, use_gpu: bool = False, allow_fallback: bool = True, **kwargs: Any):
        super().__init__()
        self.use_gpu = False  # Hard-enforced CPU execution
        self.allow_fallback = allow_fallback
        self._engine = None
        self._init_error = None
        self._fallback = PyMuPDFPlumberEngine()

    def _get_engine(self):
        if self._engine is None:
            # First verify binary compatibility in isolated subprocess
            if not _probe_ppstructure_support():
                logger.warning(
                    "PaddleOCR PPStructure unavailable on current CPU instruction set; "
                    "operating in graceful CPU fallback mode"
                )
                self._init_error = "PaddleOCR PPStructure incompatible with host CPU instruction set"
                self._engine = False
                return self._engine

            try:
                from paddleocr import PPStructure

                self._engine = PPStructure(
                    show_log=False,
                    use_gpu=False,
                    table=True,
                    layout=True,
                    recovery=True,
                    ocr=True,
                    lang="ch",
                )
                logger.info("Initialized PaddleOCR PP-Structure on CPU")
            except Exception as e:
                logger.warning(f"Could not initialize PaddleOCR PPStructure engine: {e}")
                self._init_error = str(e)
                self._engine = False
        return self._engine

    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        return self.parse_scanned_pdf(Path(file_path))

    def parse_scanned_pdf(
        self, file_path: Path, page_numbers: Optional[Sequence[int]] = None
    ) -> ParsedDocument:
        """
        Extract text sections and structured tables from scanned PDF pages using PP-Structure.
        If page_numbers is provided, only those 1-indexed pages are processed.
        """
        import fitz  # PyMuPDF
        from src.ingestion.layout_parser import DocumentParsingUnrecoverableError

        file_path = Path(file_path)
        engine = self._get_engine()
        all_sections: List[TextSection] = []
        all_tables: List[TableBlock] = []

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            logger.error(f"Cannot open document {file_path}: {e}")
            raise

        total_pages = len(doc)
        target_pages = set(page_numbers) if page_numbers is not None else set(range(1, total_pages + 1))

        if not engine:
            if not self.allow_fallback:
                raise RuntimeError(
                    f"PaddleOCR PPStructure unavailable or incompatible on host CPU: {self._init_error or 'initialization failed'}"
                )
            logger.warning(f"PaddleOCR engine unavailable, falling back on {file_path.name}")
            fallback_doc = self._fallback.parse(file_path)
            fallback_doc.is_degraded = True
            fallback_doc.metadata["engine"] = "paddle_ocr_scanned_pipeline"
            fallback_doc.metadata["cpu_only"] = True
            fallback_doc.metadata["is_degraded"] = True
            fallback_doc.metadata["extraction_quality"] = "degraded"
            fallback_doc.metadata["fallback_level"] = "L2_fallback"
            fallback_doc.metadata["degraded_reason"] = f"PaddleOCR PPStructure unavailable: {self._init_error}"
            for t in fallback_doc.tables:
                t.extraction_engine = "pymupdf_pdfplumber"
            if not fallback_doc.sections and not fallback_doc.tables and not fallback_doc.raw_text.strip():
                raise DocumentParsingUnrecoverableError(
                    f"Scanned document {file_path.name} contains no text and PaddleOCR engine is unavailable."
                )
            return fallback_doc

        import cv2

        for p_idx, page in enumerate(doc):
            p_num = p_idx + 1
            if p_num not in target_pages:
                continue

            try:
                pix = page.get_pixmap(dpi=150)
                # Convert raw memory pixel samples directly to NumPy array without intermediate PNG compression
                img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
                if pix.n == 4:
                    img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                elif pix.n == 3:
                    img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                elif pix.n == 1:
                    img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)

                # Execute PP-Structure inference
                result = engine(img_np)
                page_text_blocks = []

                # In PPStructureV3, result may be a list of dicts or objects
                regions = result if isinstance(result, list) else getattr(result, "regions", [])

                for reg_idx, region in enumerate(regions):
                    r_type = ""
                    res_data = {}
                    bbox_data = None

                    if isinstance(region, dict):
                        r_type = str(region.get("type", "")).lower()
                        res_data = region.get("res", {})
                        bbox_data = region.get("bbox")
                    elif hasattr(region, "type"):
                        r_type = str(getattr(region, "type", "")).lower()
                        res_data = getattr(region, "res", {})
                        bbox_data = getattr(region, "bbox", None)

                    # BoundingBox creation if coordinates available
                    bbox = None
                    if bbox_data and len(bbox_data) == 4:
                        bbox = BoundingBox(
                            x0=bbox_data[0],
                            top=bbox_data[1],
                            x1=bbox_data[2],
                            bottom=bbox_data[3],
                            page=p_num,
                        )

                    if r_type == "table":
                        tbl_html = res_data.get("html", "") if isinstance(res_data, dict) else ""
                        rows = _html_to_table_rows(tbl_html)
                        headers = rows[0] if rows else []

                        tb = TableBlock(
                            page_num=p_num,
                            bbox=bbox,
                            rows=rows,
                            headers=headers,
                            title=f"Scanned_Table_P{p_num}_{reg_idx + 1}",
                            extraction_engine="paddle_pp_structure",
                            metadata={
                                "html_content": tbl_html,
                                "breadcrumb_path": [file_path.stem, f"第 {p_num} 页", f"表格 {reg_idx + 1}"],
                            },
                        )
                        all_tables.append(tb)
                    elif r_type in ["text", "title", "header", "figure", "paragraph"]:
                        if isinstance(res_data, list):
                            t_text = "\n".join(
                                [line.get("text", "") for line in res_data if isinstance(line, dict)]
                            )
                        elif isinstance(res_data, dict):
                            t_text = res_data.get("text", "")
                        else:
                            t_text = str(res_data)

                        if t_text.strip():
                            page_text_blocks.append(t_text.strip())

                content_str = "\n\n".join(page_text_blocks).strip()
                if not content_str:
                    # PyMuPDF real text fallback if image OCR returned empty
                    content_str = page.get_text().strip()

                if content_str:
                    all_sections.append(
                        TextSection(
                            title=f"第 {p_num} 页 扫描正文",
                            content=content_str,
                            level=2,
                            page_num=p_num,
                            bbox=BoundingBox(0.0, 0.0, float(page.rect.width), float(page.rect.height), page=p_num),
                            breadcrumb_path=[file_path.stem, f"第 {p_num} 页"],
                        )
                    )
            except Exception as page_err:
                logger.error(f"PaddleOCR failed for page {p_num} in {file_path.name}: {page_err}")
                p_text = page.get_text().strip()
                if p_text:
                    all_sections.append(
                        TextSection(
                            title=f"第 {p_num} 页 正文",
                            content=p_text,
                            level=2,
                            page_num=p_num,
                            breadcrumb_path=[file_path.stem, f"第 {p_num} 页"],
                        )
                    )

        raw_text_combined = "\n\n".join(s.content for s in all_sections)

        return ParsedDocument(
            title=file_path.stem,
            sections=all_sections,
            tables=all_tables,
            pages=total_pages,
            raw_text=raw_text_combined,
            metadata={
                "engine": "paddle_ocr_scanned_pipeline",
                "cpu_only": True,
                "pages_processed": list(target_pages),
            },
        )

    def extract_tables(self, file_path: Union[str, Path]) -> List[TableBlock]:
        return self.parse_scanned_pdf(Path(file_path)).tables
