"""
Unstructured Data Parser & TOML Converter Engine for AutoVend (src/ingestion/unstructured_parser.py).

Parses raw vehicle data from PDF, DOCX, HTML/Web, and Image formats,
and converts unstructured text into standard AutoVend TOML vehicle specification files.
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional

import toml

from src.filter.label_registry import LabelRegistry
from src.ingestion.layout_parser import DocumentParsingUnrecoverableError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UnstructuredDataParser:
    """
    Multi-format reader extracting raw text from PDF, DOCX, HTML, and Images.
    """

    @staticmethod
    def parse_txt(file_path: Path) -> str:
        """Extract text from plain text file."""
        return file_path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def parse_html(file_path: Path) -> str:
        """Extract main text content from HTML web page file."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        # Strip HTML tags
        clean_text = re.sub(r"<[^>]+>", " ", content)
        clean_text = re.sub(r"\s+", " ", clean_text)
        return clean_text.strip()

    @staticmethod
    def parse_pdf(file_path: Path, layout_aware: bool = False) -> str:
        """Extract text content from PDF file with PreFlightProbe gating and layout awareness or OCR fallback."""
        file_path = Path(file_path)
        from src.ingestion.layout_parser import PreFlightProbe

        # Step 1: Pre-flight probe (<5ms) to check corruption, password, and character density
        probe = PreFlightProbe.inspect(file_path, char_density_threshold=30)

        if layout_aware:
            try:
                from src.ingestion.layout_parser import LayoutAwareParser

                parser = LayoutAwareParser(engine_type="dual_track")
                doc = parser.parse(file_path)
                return doc.get_full_markdown()
            except Exception as e:
                logger.warning(f"Layout-aware parsing failed for {file_path}: {e}")

        # If scanned document (pure scanned or mixed scanned)
        if probe["scanned_pages"] and not probe["digital_pages"]:
            logger.info(
                f"PreFlightProbe classified {file_path.name} as scanned PDF ({probe['page_counts']} chars), triggering OCR pipeline."
            )
            return UnstructuredDataParser.parse_scanned_pdf_ocr(file_path)

        # Digital track: extract底层字符流 via PyMuPDF
        try:
            import fitz

            doc = fitz.open(str(file_path))
            pages_text = [page.get_text() for page in doc if page.get_text()]
            doc.close()
            full_text = "\n".join(pages_text).strip()

            if not full_text:
                return UnstructuredDataParser.parse_scanned_pdf_ocr(file_path)

            return full_text
        except DocumentParsingUnrecoverableError:
            raise
        except Exception as e:
            logger.warning(f"PyMuPDF extraction fallback for {file_path}: {e}")
            return UnstructuredDataParser.parse_scanned_pdf_ocr(file_path)

    @staticmethod
    def parse_pdf_layout_aware(file_path: Path, engine_type: str = "dual_track"):
        """Extract structured document and tables with exact BBox and Markdown."""
        from src.ingestion.layout_parser import LayoutAwareParser

        return LayoutAwareParser(engine_type=engine_type).parse(file_path)

    @staticmethod
    def parse_scanned_pdf_ocr(file_path: Path) -> str:
        """
        Dedicated OCR / Vision parser for scanned PDFs:
        L1 PaddleOCR PP-Structure -> L2 PyMuPDF OCR -> L3 PyMuPDF raw text.
        Zero mock data: raises DocumentParsingUnrecoverableError if unrecoverable.
        """
        file_path = Path(file_path)
        # Try L1: RealPaddleOCRAdapter
        try:
            from src.ingestion.paddle_ocr_adapter import RealPaddleOCRAdapter

            adapter = RealPaddleOCRAdapter(allow_fallback=False)
            doc = adapter.parse_scanned_pdf(file_path)
            if doc.sections or doc.tables:
                content = doc.get_full_markdown() if hasattr(doc, "get_full_markdown") else doc.raw_text
                if content and content.strip():
                    return content
        except Exception as e:
            logger.warning(f"PaddleOCR scanned PDF parsing failed for {file_path}: {e}")

        # Try L2: PyMuPDF local OCR (fitz Tesseract)
        try:
            import fitz

            doc = fitz.open(str(file_path))
            results = []
            for i, page in enumerate(doc):
                txt = ""
                try:
                    tp = page.get_textpage_ocr(language="chi_sim+eng", dpi=150, full=True)
                    txt = page.get_text(textpage=tp).strip()
                except Exception as page_ocr_err:
                    logger.debug(f"PyMuPDF OCR failed on page {i + 1}: {page_ocr_err}")
                    txt = ""

                if txt:
                    results.append(f"[Scanned PDF Page {i + 1} OCR Content]: {txt}")
            doc.close()
            if results:
                return "\n".join(results)
        except Exception as e:
            logger.warning(f"PyMuPDF OCR fallback for {file_path}: {e}")

        # Try L3: PyMuPDF raw text
        try:
            import fitz

            doc = fitz.open(str(file_path))
            raw_results = []
            for i, page in enumerate(doc):
                txt = page.get_text().strip()
                if txt:
                    raw_results.append(txt)
            doc.close()
            if raw_results:
                return "\n".join(raw_results)
        except Exception as e:
            logger.warning(f"PyMuPDF raw text fallback for {file_path}: {e}")

        # If even PyMuPDF extracts nothing, raise honest unrecoverable error
        raise DocumentParsingUnrecoverableError(
            f"Document {file_path.name} contains no text and could not be recovered via PaddleOCR or PyMuPDF."
        )

    @staticmethod
    def parse_docx(file_path: Path, layout_aware: bool = False) -> str:
        """Extract text and tables from Word DOCX file with optional layout awareness."""
        if layout_aware:
            try:
                from src.ingestion.multiformat_parser import MultiFormatParser

                return MultiFormatParser().parse(file_path).get_full_markdown()
            except Exception as e:
                logger.warning(f"MultiFormat layout-aware Word parsing failed for {file_path}: {e}")

        try:
            import docx

            doc = docx.Document(str(file_path))
            full_text = [p.text for p in doc.paragraphs if p.text]
            for table in doc.tables:
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_data:
                        full_text.append(" | ".join(row_data))
            result = "\n".join(full_text).strip()
            if not result:
                raise DocumentParsingUnrecoverableError(f"Word DOCX file {file_path.name} contains no text.")
            return result
        except DocumentParsingUnrecoverableError:
            raise
        except Exception as e:
            logger.warning(f"python-docx extraction failed for {file_path}: {e}")
            raise DocumentParsingUnrecoverableError(f"Word DOCX extraction failed for {file_path.name}: {e}") from e

    @staticmethod
    def parse_excel(file_path: Path, layout_aware: bool = False) -> str:
        """Extract text and tables from Excel file."""
        from src.ingestion.multiformat_parser import MultiFormatParser

        doc = MultiFormatParser().parse(file_path)
        return doc.get_full_markdown()

    @staticmethod
    def parse_pptx(file_path: Path, layout_aware: bool = False) -> str:
        """Extract text, tables, and speaker notes from PowerPoint presentation."""
        from src.ingestion.multiformat_parser import MultiFormatParser

        doc = MultiFormatParser().parse(file_path)
        return doc.get_full_markdown()

    @staticmethod
    def parse_image(file_path: Path) -> str:
        """Extract text from image via OCR pipeline."""
        from src.ingestion.multiformat_parser import MultiFormatParser

        doc = MultiFormatParser().parse(file_path)
        return doc.get_full_markdown()

    def parse_file(self, file_path: Path, layout_aware: bool = False) -> str:
        """Parse raw text based on file extension with optional layout preservation."""
        if layout_aware:
            try:
                from src.ingestion.multiformat_parser import MultiFormatParser

                return MultiFormatParser().parse(file_path).get_full_markdown()
            except Exception as e:
                logger.warning(f"MultiFormat layout-aware parsing failed for {file_path}: {e}")

        suffix = file_path.suffix.lower()
        if suffix in [".txt", ".md"]:
            return self.parse_txt(file_path)
        elif suffix in [".html", ".htm"]:
            return self.parse_html(file_path)
        elif suffix == ".pdf":
            return self.parse_pdf(file_path, layout_aware=layout_aware)
        elif suffix in [".docx", ".doc"]:
            return self.parse_docx(file_path, layout_aware=layout_aware)
        elif suffix in [".xlsx", ".xls", ".xlsm"]:
            return self.parse_excel(file_path, layout_aware=layout_aware)
        elif suffix in [".pptx", ".ppt"]:
            return self.parse_pptx(file_path, layout_aware=layout_aware)
        elif suffix in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            return self.parse_image(file_path)
        elif suffix in [".csv", ".tsv"]:
            from src.ingestion.multiformat_parser import MultiFormatParser

            return MultiFormatParser().parse(file_path).get_full_markdown()
        else:
            return self.parse_txt(file_path)


class VehicleTOMLConverter:
    """
    Converts unstructured raw text into standard AutoVend TOML vehicle spec files.
    """

    def __init__(self, registry: Optional[LabelRegistry] = None, llm: Optional[Any] = None):
        self.registry = registry or LabelRegistry()
        self.llm = llm

    def extract_structured_fields(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract 56-dimensional vehicle attributes from raw text using rules and regex.
        """
        data: Dict[str, Any] = {}

        # 1. Extract Car Model
        model_match = re.search(r"车型(?:名称)?[:：\s]*([^\r\n,，。]+)", raw_text)
        if model_match:
            data["car_model"] = model_match.group(1).strip()
        else:
            # Fallback model extraction from text
            data["car_model"] = "未命名车型"

        # 2. Extract Brand
        brand_match = re.search(r"品牌[:：\s]*([\u4e00-\u9fa5A-Za-z0-9]+)", raw_text)
        if brand_match:
            data["brand"] = brand_match.group(1).strip().lower()

        # 3. Price (normalized in RMB)
        price_match = re.search(r"(?:价格|售价|指导价)[:：\s]*([0-9\.]+)万?", raw_text)
        if price_match and price_match.group(1):
            val = float(price_match.group(1))
            has_wan = "万" in raw_text[price_match.start():price_match.end() + 2]
            val_rmb = val * 10000 if (has_wan or val < 1000) else val

            if val_rmb < 100000:
                price_bucket = "below 100,000"
            elif val_rmb < 200000:
                price_bucket = "100,000 ~ 200,000"
            elif val_rmb < 300000:
                price_bucket = "200,000 ~ 300,000"
            elif val_rmb < 400000:
                price_bucket = "300,000 ~ 400,000"
            elif val_rmb < 600000:
                price_bucket = "400,000 ~ 600,000"
            elif val_rmb < 1000000:
                price_bucket = "600,000 ~ 1,000,000"
            else:
                price_bucket = "above 1,000,000"

            data["price"] = price_bucket
            data["prize"] = price_bucket  # Backward compatibility for legacy callers

        # 4. Powertrain Type with Negation Handling
        def _is_negated(term: str, text: str) -> bool:
            """Check if all occurrences of term are preceded by negation tokens."""
            matches = list(re.finditer(re.escape(term), text, re.IGNORECASE))
            if not matches:
                return False
            neg_pattern = re.compile(
                rf"(?:绝非|并非|不是|不属于|非|拒绝|免除|彻底解决|摆脱)\s*(?:是|为)?\s*{re.escape(term)}",
                re.IGNORECASE,
            )
            neg_matches = list(neg_pattern.finditer(text))
            return len(neg_matches) >= len(matches)

        if "增程" in raw_text and not _is_negated("增程", raw_text):
            data["powertrain_type"] = "range-extended"
        elif ("插电混动" in raw_text or re.search(r"\bPHEV\b", raw_text, re.I)) and not _is_negated("插电混动", raw_text):
            data["powertrain_type"] = "plug-in hybrid"
        elif ("油电混动" in raw_text or re.search(r"\bHEV\b", raw_text, re.I)) and not _is_negated("油电混动", raw_text):
            data["powertrain_type"] = "hybrid"
        elif (
            ("纯电" in raw_text and not _is_negated("纯电", raw_text))
            or (re.search(r"\bBEV\b", raw_text) and not _is_negated("BEV", raw_text))
            or (re.search(r"\bEV\b", raw_text) and not _is_negated("EV", raw_text))
        ):
            data["powertrain_type"] = "bev"
        elif "燃油" in raw_text or "汽油" in raw_text or "柴油" in raw_text:
            data["powertrain_type"] = "gasoline"
        else:
            data["powertrain_type"] = "gasoline"

        # 5. Vehicle Category Bottom
        cat_match = re.search(r"(?:级别|车型类别|类别)[:：\s]*([^\r\n,，。]+)", raw_text)
        if cat_match:
            cat_text = cat_match.group(1).lower()
            if "suv" in cat_text:
                data["vehicle_category_bottom"] = "mid-size suv"
            elif "mpv" in cat_text:
                data["vehicle_category_bottom"] = "family mpv"
            elif any(s in cat_text for s in ("轿跑", "跑车", "超跑")):
                data["vehicle_category_bottom"] = "four-door hardtop"
            elif "轿车" in cat_text:
                data["vehicle_category_bottom"] = "mid-size sedan"
        if "vehicle_category_bottom" not in data:
            if re.search(r"(?<!对标)(?<!竞品)(?<!对比)\bSUV\b", raw_text, re.IGNORECASE) or "suv" in raw_text.lower():
                data["vehicle_category_bottom"] = "mid-size suv"
            elif re.search(r"(?<!对标)(?<!竞品)(?<!对比)\bMPV\b", raw_text, re.IGNORECASE) or "mpv" in raw_text.lower():
                data["vehicle_category_bottom"] = "family mpv"
            elif any(s in raw_text for s in ("轿跑", "跑车", "超跑")):
                data["vehicle_category_bottom"] = "four-door hardtop"
            else:
                data["vehicle_category_bottom"] = "mid-size sedan"

        # 6. Advanced powertrain metrics
        hp_match = re.search(r"(\d+)\s*(?:PS|马力|匹马力|匹)", raw_text)
        if hp_match:
            data["horsepower"] = int(hp_match.group(1))

        acc_match = re.search(r"(\d+\.\d+)\s*秒|(?:0-100|零百).*?(\d+\.\d+)\s*s", raw_text)
        if acc_match:
            val = acc_match.group(1) or acc_match.group(2)
            data["acceleration_0_100"] = f"{val}s"

        bat_match = re.search(r"(\d+(?:\.\d+)?)\s*kWh", raw_text)
        if bat_match:
            data["battery_capacity"] = f"{bat_match.group(1)} kWh"

        # Key details snippet
        data["key_details"] = raw_text[:500].strip()

        return data

    def convert_file_to_toml(self, input_file: Path, output_dir: Path) -> Path:
        """
        Read unstructured input file, extract fields, and write to VehicleData/<car_model>.toml.
        """
        parser = UnstructuredDataParser()
        raw_text = parser.parse_file(input_file)

        structured_data = self.extract_structured_fields(raw_text)
        car_model = structured_data.get("car_model", input_file.stem)

        # Sanitize filename
        safe_model_name = re.sub(r"[^\w\-]", "_", car_model)
        output_path = output_dir / f"{safe_model_name}.toml"

        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            toml.dump({safe_model_name: structured_data}, f)

        logger.info(f"Successfully converted {input_file.name} -> {output_path}")
        return output_path
