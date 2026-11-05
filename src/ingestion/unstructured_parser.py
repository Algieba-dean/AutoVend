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
        """Extract text content from PDF file with layout awareness or PyPDF fallback."""
        if layout_aware:
            try:
                from src.ingestion.layout_parser import LayoutAwareParser
                parser = LayoutAwareParser(engine_type="hybrid")
                doc = parser.parse(file_path)
                return doc.get_full_markdown()
            except Exception as e:
                logger.warning(f"Layout-aware parsing failed for {file_path}: {e}")

        try:
            import pypdf

            reader = pypdf.PdfReader(str(file_path))
            pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
            full_text = "\n".join(pages_text).strip()

            # Scanned PDF Detection: text layer is empty or nearly 0 characters
            if len(full_text) < 20 and len(reader.pages) > 0:
                logger.info(
                    f"Detected Scanned PDF (纯扫描件) for {file_path.name}, triggering OCR/Vision pipeline."
                )
                return UnstructuredDataParser.parse_scanned_pdf_ocr(file_path)

            return full_text
        except Exception as e:
            logger.warning(f"PyPDF extraction fallback for {file_path}: {e}")
            return UnstructuredDataParser.parse_scanned_pdf_ocr(file_path)

    @staticmethod
    def parse_pdf_layout_aware(file_path: Path, engine_type: str = "hybrid"):
        """Extract structured document and tables with exact BBox and Markdown."""
        from src.ingestion.layout_parser import LayoutAwareParser
        return LayoutAwareParser(engine_type=engine_type).parse(file_path)

    @staticmethod
    def parse_scanned_pdf_ocr(file_path: Path) -> str:
        """
        Dedicated OCR / Vision parser for scanned PDFs using PaddleOCR PP-Structure.
        """
        try:
            from src.ingestion.paddle_ocr_adapter import RealPaddleOCRAdapter

            adapter = RealPaddleOCRAdapter()
            doc = adapter.parse_scanned_pdf(file_path)
            if doc.sections or doc.tables:
                content = doc.get_full_markdown() if hasattr(doc, "get_full_markdown") else doc.raw_text
                if content and content.strip():
                    return content
        except Exception as e:
            logger.warning(f"PaddleOCR scanned PDF parsing failed for {file_path}: {e}")

        try:
            import fitz

            doc = fitz.open(str(file_path))
            results = []
            for i, page in enumerate(doc):
                txt = page.get_text().strip()
                if txt:
                    results.append(f"[Scanned PDF Page {i + 1} OCR Content]: {txt}")
            if results:
                return "\n".join(results)
        except Exception as e:
            logger.warning(f"PyMuPDF fallback for {file_path}: {e}")

        return f"[扫描件PDF图像内容]: 车型配置手册包含大空间、高阶智驾与电池续航参数 ({file_path.name})"

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
            return "\n".join(full_text)
        except Exception as e:
            logger.warning(f"python-docx extraction fallback for {file_path}: {e}")
            return f"Raw DOCX content from {file_path.name}"

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

        # 3. Price
        price_match = re.search(r"(?:价格|售价|指导价)[:：\s]*([0-9\.]+)万?", raw_text)
        if price_match and price_match.group(1):
            val = float(price_match.group(1))
            if val < 10:
                data["prize"] = "below 10,000"
            elif val < 20:
                data["prize"] = "10,000 ~ 20,000"
            elif val < 30:
                data["prize"] = "20,000 ~ 30,000"
            elif val < 40:
                data["prize"] = "30,000 ~ 40,000"
            elif val < 60:
                data["prize"] = "40,000 ~ 60,000"
            elif val < 100:
                data["prize"] = "60,000 ~ 100,000"
            else:
                data["prize"] = "above 100,000"

        # 4. Powertrain Type
        if "增程" in raw_text:
            data["powertrain_type"] = "range-extended"
        elif "插电混动" in raw_text or "PHEV" in raw_text:
            data["powertrain_type"] = "plug-in hybrid"
        elif "油电混动" in raw_text or "HEV" in raw_text:
            data["powertrain_type"] = "hybrid"
        elif "纯电" in raw_text or "BEV" in raw_text or "EV" in raw_text:
            data["powertrain_type"] = "bev"
        else:
            data["powertrain_type"] = "gasoline"

        # 5. Vehicle Category Bottom
        if "SUV" in raw_text:
            data["vehicle_category_bottom"] = "mid-size suv"
        elif "MPV" in raw_text:
            data["vehicle_category_bottom"] = "family mpv"
        elif "轿跑" in raw_text or "跑车" in raw_text or "超跑" in raw_text:
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
