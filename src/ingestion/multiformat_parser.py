"""
Multi-format document parser for AutoVend (src/ingestion/multiformat_parser.py).

Parses diverse automotive specification documents across:
1. Excel (.xlsx, .xls, .csv, .tsv):
   - Multi-sheet workbook navigation & sheet naming
   - Merged cell resolution (propagating top-left values across spans)
   - Formula evaluation with data-only fallback & currency/date formatting
   - Conversion to TableBlock objects with sheet metadata
2. Word (.docx, .doc):
   - Semantic heading hierarchy (Title, Subtitle, H1-H4)
   - Complex tables with cell spans (row_span, col_span) & multi-paragraph cells
   - Bullet/numbered lists, callouts, footnotes, and captions
3. PowerPoint (.pptx, .ppt):
   - Slide sequence tracking, slide title, and layout semantics
   - Spatial reading order heuristics (top-to-bottom, left-to-right shape sorting)
   - Embedded slide tables converted to TableBlock
   - Speaker / presenter notes extracted into TextSection metadata & callouts
4. Images (.png, .jpg, .jpeg, .webp, .bmp):
   - Image diagnostics (width, height, DPI, aspect ratio, blur/sharpness, contrast)
   - EXIF / IPTC metadata extraction
   - Pluggable OCR adapter pipeline (Tesseract, EasyOCR, and deterministic Offline Mock)
5. Structured & Plain Text (.txt, .md, .html, .rtf, .json, .toml):
   - Markdown headings & tables
   - HTML tags & tables via BeautifulSoup
   - Schema-aware JSON & TOML extraction
"""

import csv
import datetime
import io
import json
import logging
import os
import re
import zipfile
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import ExifTags, Image

from src.ingestion.layout_parser import (
    BoundingBox,
    ParsedDocument,
    TableBlock,
    TableCell,
    TextSection,
)

logger = logging.getLogger(__name__)


# ── Format Enumeration ───────────────────────────────────────────────────


class DocumentFormat(str, Enum):
    """Supported enterprise document formats."""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    TSV = "tsv"
    WORD = "word"
    POWERPOINT = "powerpoint"
    IMAGE = "image"
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    TOML = "toml"
    RTF = "rtf"
    UNKNOWN = "unknown"


# ── OCR Subsystem (Adapter Pattern) ──────────────────────────────────────


class OCRWord:
    """Represents an individual recognized word with bounding box and confidence."""

    def __init__(self, text: str, bbox: BoundingBox, confidence: float = 1.0):
        self.text = text
        self.bbox = bbox
        self.confidence = round(float(confidence), 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "confidence": self.confidence,
        }


class OCRLine:
    """Represents a recognized text line composed of OCRWords."""

    def __init__(
        self,
        text: str,
        bbox: BoundingBox,
        words: Optional[List[OCRWord]] = None,
        confidence: float = 1.0,
    ):
        self.text = text
        self.bbox = bbox
        self.words = words or []
        self.confidence = round(float(confidence), 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "confidence": self.confidence,
            "words": [w.to_dict() for w in self.words],
        }


class OCRResult:
    """Unified OCR extraction result containing full text, structured lines, and confidence."""

    def __init__(
        self,
        full_text: str,
        lines: Optional[List[OCRLine]] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.full_text = full_text.strip()
        self.lines = lines or []
        self.confidence = round(float(confidence), 4)
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "full_text": self.full_text,
            "lines": [line.to_dict() for line in self.lines],
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class BaseOCREngine(ABC):
    """Abstract interface for pluggable OCR backends."""

    @abstractmethod
    def extract_text_and_boxes(self, image_path: Union[str, Path]) -> OCRResult:
        """Extract text, line bounding boxes, and confidence scores from an image."""
        pass


class TesseractOCREngine(BaseOCREngine):
    """Adapter for Tesseract OCR via pytesseract."""

    def __init__(self, lang: str = "chi_sim+eng"):
        self.lang = lang

    def extract_text_and_boxes(self, image_path: Union[str, Path]) -> OCRResult:
        try:
            import pytesseract
            from pytesseract import Output

            img = Image.open(str(image_path))
            data = pytesseract.image_to_data(img, lang=self.lang, output_type=Output.DICT)
            lines_dict: Dict[Tuple[int, int], List[OCRWord]] = {}
            n_boxes = len(data["text"])

            for i in range(n_boxes):
                text = data["text"][i].strip()
                if not text:
                    continue
                conf = float(data["conf"][i]) / 100.0 if float(data["conf"][i]) > 0 else 0.8
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                bbox = BoundingBox(x0=x, top=y, x1=x + w, bottom=y + h, page=1)
                word = OCRWord(text=text, bbox=bbox, confidence=conf)
                key = (data["block_num"][i], data["line_num"][i])
                lines_dict.setdefault(key, []).append(word)

            ocr_lines: List[OCRLine] = []
            full_text_parts: List[str] = []

            for _, words in sorted(lines_dict.items()):
                if not words:
                    continue
                line_text = " ".join(w.text for w in words)
                full_text_parts.append(line_text)
                min_x = min(w.bbox.x0 for w in words)
                min_y = min(w.bbox.top for w in words)
                max_x = max(w.bbox.x1 for w in words)
                max_y = max(w.bbox.bottom for w in words)
                avg_conf = sum(w.confidence for w in words) / len(words)
                line_bbox = BoundingBox(x0=min_x, top=min_y, x1=max_x, bottom=max_y, page=1)
                ocr_lines.append(OCRLine(text=line_text, bbox=line_bbox, words=words, confidence=avg_conf))

            full_text = "\n".join(full_text_parts)
            avg_all_conf = sum(ln.confidence for ln in ocr_lines) / max(1, len(ocr_lines))
            return OCRResult(full_text=full_text, lines=ocr_lines, confidence=avg_all_conf, metadata={"engine": "tesseract"})
        except Exception as e:
            logger.warning(f"Tesseract OCR failed ({e}); honestly degrading.")
            return OCRResult(full_text="", lines=[], confidence=0.0, metadata={"engine": "tesseract", "is_degraded": True, "error": str(e)})


class EasyOCREngine(BaseOCREngine):
    """Adapter for EasyOCR deep-learning text extraction."""

    def __init__(self, languages: Optional[List[str]] = None):
        self.languages = languages or ["ch_sim", "en"]
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(self.languages, gpu=False)
        return self._reader

    def extract_text_and_boxes(self, image_path: Union[str, Path]) -> OCRResult:
        try:
            reader = self._get_reader()
            results = reader.readtext(str(image_path))
            ocr_lines: List[OCRLine] = []
            full_text_parts: List[str] = []

            for bbox_pts, text, conf in results:
                if not text.strip():
                    continue
                xs = [pt[0] for pt in bbox_pts]
                ys = [pt[1] for pt in bbox_pts]
                bbox = BoundingBox(x0=min(xs), top=min(ys), x1=max(xs), bottom=max(ys), page=1)
                word = OCRWord(text=text, bbox=bbox, confidence=float(conf))
                line = OCRLine(text=text, bbox=bbox, words=[word], confidence=float(conf))
                ocr_lines.append(line)
                full_text_parts.append(text)

            full_text = "\n".join(full_text_parts)
            avg_conf = sum(ln.confidence for ln in ocr_lines) / max(1, len(ocr_lines))
            return OCRResult(full_text=full_text, lines=ocr_lines, confidence=avg_conf, metadata={"engine": "easyocr"})
        except Exception as e:
            logger.warning(f"EasyOCR extraction failed ({e}); honestly degrading.")
            return OCRResult(full_text="", lines=[], confidence=0.0, metadata={"engine": "easyocr", "is_degraded": True, "error": str(e)})


class OfflineMockOCREngine(BaseOCREngine):
    """
    Deterministic offline mock/fallback OCR engine for testing and hermetic CI.
    Completely purges hardcoded domain strings and filename substring matching.
    Accepts explicitly injected mock lines for tests, otherwise honestly degrades or raises.
    """

    def __init__(
        self,
        mock_lines: Optional[List[Tuple[str, float, float, float, float]]] = None,
        raise_on_empty: bool = False,
    ):
        self.mock_lines = mock_lines
        self.raise_on_empty = raise_on_empty

    def extract_text_and_boxes(self, image_path: Union[str, Path]) -> OCRResult:
        p = Path(image_path)
        if self.mock_lines is None:
            if self.raise_on_empty:
                from src.ingestion.layout_parser import DocumentParsingUnrecoverableError
                raise DocumentParsingUnrecoverableError(f"OCR unavailable or failed for {p.name}")
            return OCRResult(
                full_text="",
                lines=[],
                confidence=0.0,
                metadata={"engine": "offline_degraded", "is_degraded": True, "file_name": p.name},
            )

        ocr_lines: List[OCRLine] = []
        full_text_parts: List[str] = []

        for text, x0, top, x1, bottom in self.mock_lines:
            full_text_parts.append(text)
            line_bbox = BoundingBox(x0=x0, top=top, x1=x1, bottom=bottom, page=1)
            tokens = text.split()
            words: List[OCRWord] = []
            if tokens:
                step_w = (x1 - x0) / len(tokens)
                for w_idx, tok in enumerate(tokens):
                    w_x0 = x0 + w_idx * step_w
                    w_x1 = w_x0 + step_w
                    w_bbox = BoundingBox(x0=w_x0, top=top, x1=w_x1, bottom=bottom, page=1)
                    words.append(OCRWord(text=tok, bbox=w_bbox, confidence=1.0))
            else:
                words.append(OCRWord(text=text, bbox=line_bbox, confidence=1.0))

            ocr_lines.append(OCRLine(text=text, bbox=line_bbox, words=words, confidence=1.0))

        return OCRResult(
            full_text="\n".join(full_text_parts),
            lines=ocr_lines,
            confidence=1.0,
            metadata={"engine": "offline_mock", "is_degraded": False, "file_name": p.name},
        )


class VisionAPIOCREngine(BaseOCREngine):
    """
    Adapter for Cloud / LLM Multimodal Vision APIs (OpenAI GPT-4o, Claude 3.5, Azure Vision, etc.).
    Supports direct REST / LLM client execution with honest degradation when credentials are missing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: str = "gpt-4o-mini",
        client: Optional[Any] = None,
    ):
        self.api_key = api_key or os.getenv("AUTOVEND_VISION_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.endpoint = endpoint or os.getenv("AUTOVEND_VISION_ENDPOINT")
        self.model = model
        self.client = client

    def extract_text_and_boxes(self, image_path: Union[str, Path]) -> OCRResult:
        p = Path(image_path)
        # If no client or API key is provided, degrade honestly without faking data
        if not self.client and not self.api_key:
            return OCRResult(
                full_text="",
                lines=[],
                confidence=0.0,
                metadata={"engine": "vision_api", "is_degraded": True, "model": self.model},
            )

        try:
            import base64

            img_bytes = p.read_bytes()
            b64_data = base64.b64encode(img_bytes).decode("utf-8")
            if self.client and hasattr(self.client, "chat"):
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Extract all text with bounding boxes from this vehicle spec sheet."},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_data}"}},
                            ],
                        }
                    ],
                )
                text = resp.choices[0].message.content or ""
                lines = [
                    OCRLine(text=ln.strip(), bbox=BoundingBox(0, idx * 30, 600, idx * 30 + 25, 1))
                    for idx, ln in enumerate(text.split("\n"))
                    if ln.strip()
                ]
                return OCRResult(full_text=text, lines=lines, confidence=0.98, metadata={"engine": "vision_api", "model": self.model})
            else:
                return OCRResult(
                    full_text="",
                    lines=[],
                    confidence=0.0,
                    metadata={"engine": "vision_api", "is_degraded": True, "model": self.model},
                )
        except Exception as e:
            logger.warning(f"Vision API extraction notice ({e}); honestly degrading.")
            return OCRResult(
                full_text="",
                lines=[],
                confidence=0.0,
                metadata={"engine": "vision_api_fallback", "is_degraded": True, "error": str(e)},
            )


def get_ocr_engine(engine_name: Optional[str] = None) -> BaseOCREngine:
    """Factory creating an OCR engine based on name or environment availability."""
    name = (engine_name or os.getenv("AUTOVEND_OCR_ENGINE", "mock")).lower()
    if name == "tesseract":
        return TesseractOCREngine()
    elif name == "easyocr":
        return EasyOCREngine()
    elif name in ["vision", "vision_api", "cloud"]:
        return VisionAPIOCREngine()
    else:
        return OfflineMockOCREngine()


# ── Image Diagnostics & EXIF Extraction ──────────────────────────────────


class ImageDiagnostics:
    """Comprehensive image quality diagnostics and spatial dimensions."""

    def __init__(
        self,
        width: int,
        height: int,
        aspect_ratio: float,
        dpi: Tuple[float, float],
        mode: str,
        channels: int,
        blur_score: float,
        is_blurry: bool,
        contrast_score: float,
    ):
        self.width = width
        self.height = height
        self.aspect_ratio = round(aspect_ratio, 3)
        self.dpi = dpi
        self.mode = mode
        self.channels = channels
        self.blur_score = round(blur_score, 2)
        self.is_blurry = is_blurry
        self.contrast_score = round(contrast_score, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "aspect_ratio": self.aspect_ratio,
            "dpi": list(self.dpi),
            "mode": self.mode,
            "channels": self.channels,
            "blur_score": self.blur_score,
            "is_blurry": self.is_blurry,
            "contrast_score": self.contrast_score,
        }


def extract_image_diagnostics(img: Image.Image) -> ImageDiagnostics:
    """Analyze image geometry, channel depth, blur/sharpness, and contrast."""
    w, h = img.size
    aspect_ratio = float(w) / max(1.0, float(h))
    dpi = img.info.get("dpi", (72.0, 72.0))
    if isinstance(dpi, (int, float)):
        dpi = (float(dpi), float(dpi))
    else:
        dpi = (float(dpi[0]), float(dpi[1]))

    mode = img.mode
    channels = len(img.getbands())

    # Grayscale conversion for blur & contrast calculations
    gray_img = img.convert("L")
    arr = np.array(gray_img, dtype=np.float32)

    # Blur detection via Laplacian variance
    if arr.size > 0 and arr.shape[0] > 2 and arr.shape[1] > 2:
        lap = (
            -4.0 * arr[1:-1, 1:-1]
            + arr[0:-2, 1:-1]
            + arr[2:, 1:-1]
            + arr[1:-1, 0:-2]
            + arr[1:-1, 2:]
        )
        v = float(np.var(lap))
        blur_score = 0.0 if np.isnan(v) or np.isinf(v) else v
    else:
        blur_score = 0.0

    # Sharp image threshold typically >= 80-100; lower implies blur/defocus
    is_blurry = blur_score < 100.0

    # Contrast via standard deviation of pixel intensities
    if arr.size > 0:
        c = float(np.std(arr))
        contrast_score = 0.0 if np.isnan(c) or np.isinf(c) else c
    else:
        contrast_score = 0.0

    return ImageDiagnostics(
        width=w,
        height=h,
        aspect_ratio=aspect_ratio,
        dpi=dpi,
        mode=mode,
        channels=channels,
        blur_score=blur_score,
        is_blurry=is_blurry,
        contrast_score=contrast_score,
    )


def extract_exif_metadata(img: Image.Image) -> Dict[str, Any]:
    """Extract standard EXIF, sub-IFD, and IPTC metadata tags with human-readable keys."""
    exif_data: Dict[str, Any] = {}
    try:
        raw_exif = img.getexif()
        if raw_exif:
            for tag_id, val in raw_exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                # Format bytes or complex types safely
                if isinstance(val, bytes):
                    val_str = val.decode("utf-8", errors="ignore").strip()
                elif isinstance(val, (str, int, float)):
                    val_str = val
                elif hasattr(val, "as_integer_ratio"):
                    val_str = float(val)
                else:
                    val_str = str(val)
                if isinstance(val_str, str):
                    val_str = "".join(ch for ch in val_str if ch in ("\n", "\r", "\t") or ch >= " ").strip()
                    if tag_name == "MakerNote" and len(val_str) > 200:
                        val_str = val_str[:200] + "... [truncated binary makernote]"
                exif_data[tag_name] = val_str

            # Sub-IFDs: Exif and GPSInfo
            try:
                for ifd_id in (ExifTags.IFD.Exif, ExifTags.IFD.GPSInfo):
                    try:
                        sub_ifd = raw_exif.get_ifd(ifd_id)
                        for tag_id, val in sub_ifd.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                            if isinstance(val, bytes):
                                val_str = val.decode("utf-8", errors="ignore").strip()
                            elif isinstance(val, (str, int, float)):
                                val_str = val
                            else:
                                val_str = str(val)
                            if isinstance(val_str, str):
                                val_str = "".join(ch for ch in val_str if ch in ("\n", "\r", "\t") or ch >= " ").strip()
                                if tag_name == "MakerNote" and len(val_str) > 200:
                                    val_str = val_str[:200] + "... [truncated binary makernote]"
                            exif_data[tag_name] = val_str
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"EXIF extraction notice: {e}")

    # IPTC metadata extraction
    try:
        from PIL import IptcImagePlugin

        iptc_raw = IptcImagePlugin.getiptcinfo(img)
        if iptc_raw:
            iptc_dict: Dict[str, Any] = {}
            for k, v in iptc_raw.items():
                k_name = str(k)
                if isinstance(v, bytes):
                    v_str = v.decode("utf-8", errors="ignore").strip()
                elif isinstance(v, list):
                    v_str = ", ".join(
                        x.decode("utf-8", errors="ignore") if isinstance(x, bytes) else str(x)
                        for x in v
                    )
                else:
                    v_str = str(v)
                iptc_dict[k_name] = v_str
            exif_data["iptc"] = iptc_dict
    except Exception as e:
        logger.debug(f"IPTC extraction notice: {e}")

    return exif_data


def extract_ole2_text(file_path: Union[str, Path]) -> str:
    """
    Extract legible UTF-16LE and ASCII text streams from legacy binary Office (OLE2) documents
    (.doc, .xls, .ppt) when modern OpenXML libraries cannot parse them.
    """
    try:
        file_path = Path(file_path)
        raw = file_path.read_bytes()
        decoded_parts: List[str] = []
        # 1. Extract UTF-16LE runs (common in Word/PPT binary streams)
        utf16_runs = re.findall(rb"(?:[\x20-\x7e\x00-\xff]\x00){3,}", raw)
        for run in utf16_runs:
            try:
                txt = run.decode("utf-16le", errors="ignore").strip()
                if len(txt) >= 3 and any("\u4e00" <= ch <= "\u9fff" or ch.isalnum() for ch in txt):
                    if txt not in decoded_parts:
                        decoded_parts.append(txt)
            except Exception:
                pass

        # 2. Extract ASCII/UTF-8 runs
        ascii_runs = re.findall(rb"[\x20-\x7e]{4,}", raw)
        for r in ascii_runs:
            try:
                txt = r.decode("utf-8", errors="ignore").strip()
                if len(txt) >= 4 and not any(txt in p for p in decoded_parts):
                    decoded_parts.append(txt)
            except Exception:
                pass

        return "\n".join(decoded_parts)
    except Exception as e:
        logger.warning(f"OLE2 binary text extraction failed for {file_path}: {e}")
        return ""


# ── Base Format Parser ───────────────────────────────────────────────────


class BaseFormatParser(ABC):
    """Abstract base class for all format-specific document parsers."""

    @abstractmethod
    def can_parse(self, file_path: Path, format_type: DocumentFormat) -> bool:
        """Return True if this parser can handle the given file and detected format."""
        pass

    @abstractmethod
    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedDocument:
        """Parse the input file into a standardized ParsedDocument."""
        pass


# ── Canonical Automotive Model Detection Registry ────────────────────────

AUTOMOTIVE_MODEL_PATTERNS = [
    ("Xiaomi SU7 Ultra", ["SU7 Ultra", "SU7_Ultra", "su7 ultra"]),
    ("Xiaomi SU7", ["Xiaomi SU7", "小米 SU7", "小米SU7", "SU7", "su7"]),
    ("BYD Yangwang U9", ["Yangwang U9", "仰望 U9", "仰望U9"]),
    ("BYD Yangwang U8", ["Yangwang U8", "仰望 U8", "仰望U8"]),
    ("BYD Denza Z9 GT", ["Denza Z9 GT", "腾势 Z9 GT", "腾势Z9 GT", "Z9 GT", "Z9GT"]),
    ("BYD Denza D9", ["Denza D9", "腾势 D9", "腾势D9"]),
    ("Fangchengbao Bao 8", ["Fangchengbao Bao 8", "Fangchengbao Bao8", "方程豹 豹8", "方程豹豹8"]),
    ("Fangchengbao Bao 5", ["Fangchengbao Bao 5", "Fangchengbao Bao5", "方程豹 豹5", "方程豹豹5"]),
    ("BYD Han EV", ["Han EV", "比亚迪 汉", "汉EV", "汉 EV"]),
    ("BYD Tang DM-i", ["Tang DM-i", "唐DM-i", "唐 DM-i"]),
    ("BYD Seal EV", ["Seal EV", "海豹EV", "海豹 EV"]),
    ("Tesla Cybertruck", ["Cybertruck", "cybertruck", "赛博皮卡"]),
    ("Tesla Model S Plaid", ["Model S Plaid", "Model S"]),
    ("Tesla Model 3", ["Model 3", "model 3", "Model3"]),
    ("Tesla Model Y", ["Model Y", "model y", "ModelY"]),
    ("NIO ET9", ["蔚来 ET9", "蔚来ET9", "NIO ET9"]),
    ("NIO ET7", ["蔚来 ET7", "蔚来ET7", "NIO ET7"]),
    ("NIO ES8", ["蔚来 ES8", "蔚来ES8", "NIO ES8"]),
    ("Li Auto MEGA", ["Li Mega", "Li MEGA", "理想 MEGA", "理想MEGA"]),
    ("Li Auto L9", ["Li L9", "理想 L9", "理想L9"]),
    ("Li Auto L8", ["Li L8", "理想 L8", "理想L8"]),
    ("Li Auto L7", ["Li L7", "理想 L7", "理想L7"]),
    ("Li Auto L6", ["Li L6", "理想 L6", "理想L6"]),
    ("Zeekr 001 FR", ["001 FR", "001FR", "极氪 001 FR"]),
    ("Zeekr 009", ["Zeekr 009", "极氪 009", "极氪009"]),
    ("Zeekr 007", ["Zeekr 007", "极氪 007", "极氪007"]),
    ("Zeekr 001", ["Zeekr 001", "极氪 001", "极氪001"]),
    ("AITO M9", ["AITO M9", "问界 M9", "问界M9"]),
    ("AITO M7", ["AITO M7", "问界 M7", "问界M7"]),
    ("Luxeed S7", ["Luxeed S7", "智界 S7", "智界S7"]),
    ("Stelato S9", ["Stelato S9", "享界 S9", "享界S9"]),
    ("Maextro S800", ["Maextro S800", "尊界 S800", "尊界S800"]),
    ("Avatr 12", ["Avatr 12", "阿维塔 12", "阿维塔12"]),
    ("Avatr 11", ["Avatr 11", "阿维塔 11", "阿维塔11"]),
    ("Avatr 07", ["Avatr 07", "阿维塔 07", "阿维塔07"]),
    ("LynkCo 08", ["LynkCo 08", "Lynk & Co 08", "领克 08", "领克08"]),
    ("Geely Galaxy E8", ["Galaxy E8", "银河 E8", "银河E8"]),
    ("Geely Galaxy Starship", ["Galaxy Starship", "银河星舰"]),
    ("Chery Exeed Sterra ES", ["Sterra ES", "星纪元 ES", "星纪元ES"]),
    ("Chery iCAR 03", ["iCAR 03", "iCAR03"]),
    ("GAC Hyper SSR", ["Hyper SSR", "昊铂 SSR", "昊铂SSR"]),
    ("GAC Aion Y Plus", ["Aion Y", "埃安 Y", "埃安Y"]),
    ("Tank 700 Hi4-T", ["Tank 700", "坦克 700", "坦克700"]),
    ("Tank 500 Hi4-T", ["Tank 500", "坦克 500", "坦克500"]),
    ("Haval Raptor Hi4", ["Haval Raptor", "哈弗 猛龙", "哈弗猛龙"]),
    ("Wey Lanshan", ["Wey Lanshan", "魏牌 蓝山", "魏牌蓝山"]),
    ("IM L6", ["IM L6", "智己 L6", "智己L6"]),
    ("IM LS6", ["IM LS6", "智己 LS6", "智己LS6"]),
    ("Porsche Taycan", ["Taycan", "taycan", "保时捷 Taycan", "保时捷Taycan"]),
    ("Porsche Macan", ["Macan", "macan", "保时捷 Macan", "保时捷Macan"]),
    ("BMW i7", ["BMW i7", "宝马 i7", "宝马i7"]),
    ("BMW iX", ["BMW iX", "宝马 iX", "宝马iX"]),
    ("BMW i4", ["BMW i4", "宝马 i4", "宝马i4"]),
    ("BMW i3", ["BMW i3", "宝马 i3", "宝马i3"]),
    ("Mercedes EQS 580", ["EQS 580", "EQS580", "奔驰 EQS", "奔驰EQS"]),
    ("Mercedes Vision EQXX", ["Vision EQXX", "EQXX"]),
    ("Audi RS e-tron GT", ["RS e-tron GT", "e-tron GT"]),
    ("Audi Q6 e-tron", ["Q6 e-tron", "Q6 etron"]),
]


def infer_automotive_vehicle_model(file_path: Union[str, Path], doc_title: str, text_sample: str = "") -> str:
    """Infer vehicle model and brand from file path, title, and initial text."""
    combined_name = f"{Path(file_path).stem} {doc_title}"
    # 1. Match from file path & doc_title first (highest priority)
    for canonical, aliases in AUTOMOTIVE_MODEL_PATTERNS:
        for alias in aliases:
            if alias.lower() in combined_name.lower():
                return canonical

    # 2. Match from top text sample if not found in filename
    if text_sample:
        for canonical, aliases in AUTOMOTIVE_MODEL_PATTERNS:
            for alias in aliases:
                # Use word-boundary matching for short or alphanumeric aliases to prevent substring pollution
                if len(alias) <= 4 or alias.isalnum():
                    pattern = rf"(?<![\w\u4e00-\u9fa5]){re.escape(alias)}(?![\w\u4e00-\u9fa5])"
                    if re.search(pattern, text_sample, re.IGNORECASE):
                        return canonical
                elif alias.lower() in text_sample.lower():
                    return canonical

    return doc_title


# ── Excel Parser (.xlsx, .xls) ───────────────────────────────────────────


class ExcelParser(BaseFormatParser):
    """
    Excel workbook parser using openpyxl with logical grid layout extraction:
    - Multi-sheet workbook navigation
    - Merged cell resolution (propagating top-left values down vertical categories)
    - Formula evaluation with fallback to cached values (data_only=True)
    - Currency and date formatting
    - Conversion to TableBlock and TextSection objects with sheet metadata
    - Graceful degradation: If openpyxl is not installed or file is legacy binary (.xls),
      automatically falls back to OLE2 stream extraction without crashing.
    """

    def can_parse(self, file_path: Path, format_type: DocumentFormat) -> bool:
        return format_type == DocumentFormat.EXCEL or file_path.suffix.lower() in [
            ".xlsx",
            ".xlsm",
            ".xltx",
            ".xls",
        ]

    def _format_cell_value(self, val: Any, number_format: Optional[str] = None) -> str:
        """Format cell value respecting dates, numbers, currency, and formulas."""
        if val is None:
            return ""
        if isinstance(val, (datetime.datetime, datetime.date)):
            if isinstance(val, datetime.datetime) and (val.hour or val.minute or val.second):
                return val.strftime("%Y-%m-%d %H:%M:%S")
            return val.strftime("%Y-%m-%d")
        if isinstance(val, float):
            import math
            if math.isnan(val) or math.isinf(val):
                return "#NUM!"
            if val.is_integer():
                formatted = str(int(val))
            else:
                formatted = f"{val:.4f}".rstrip("0").rstrip(".")
            if number_format and ("¥" in number_format or "￥" in number_format or "$" in number_format):
                prefix = "¥" if ("¥" in number_format or "￥" in number_format) else "$"
                return f"{prefix}{formatted}"
            if number_format and "%" in number_format:
                return f"{val * 100:.2f}%"
            return formatted
        if isinstance(val, int):
            if number_format and ("¥" in number_format or "￥" in number_format or "$" in number_format):
                prefix = "¥" if ("¥" in number_format or "￥" in number_format) else "$"
                return f"{prefix}{val}"
            return str(val)
        val_str = str(val).strip()
        # Standardize Excel calculation error tokens
        if val_str in ("#DIV/0!", "#VALUE!", "#REF!", "#N/A", "#NAME?", "#NUM!", "#NULL!"):
            return val_str
        return val_str

    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedDocument:
        file_path = Path(file_path)
        doc_title = file_path.stem.replace("_", " ")

        MAX_EXCEL_ROWS = kwargs.get("max_rows", 5000)
        MAX_EXCEL_COLS = kwargs.get("max_cols", 200)

        is_large_file = kwargs.get("read_only", False) or (
            file_path.is_file() and file_path.stat().st_size > 2_000_000
        )

        wb_data = None
        wb_formulas = None
        wb_readonly = None

        try:
            import openpyxl
        except ImportError as e:
            logger.warning(
                f"openpyxl (pure Python Excel library) is not installed ({e}). "
                f"Gracefully degrading to OLE2 binary text extraction for {file_path}"
            )
            openpyxl = None

        if openpyxl is not None:
            if is_large_file:
                try:
                    wb_readonly = openpyxl.load_workbook(str(file_path), data_only=True, read_only=True)
                except Exception as e:
                    logger.warning(f"openpyxl read_only load failed for {file_path}: {e}")
                    wb_readonly = None
                wb = wb_readonly
            else:
                # 1. Load data_only workbook for evaluated formula values
                try:
                    wb_data = openpyxl.load_workbook(str(file_path), data_only=True, read_only=False)
                except Exception as e:
                    logger.warning(f"openpyxl data_only load failed for {file_path}: {e}")
                    wb_data = None

                # 2. Load non-data_only workbook for formula fallback if needed
                try:
                    wb_formulas = openpyxl.load_workbook(str(file_path), data_only=False, read_only=False)
                except Exception as e:
                    logger.warning(f"openpyxl formulas load failed for {file_path}: {e}")
                    wb_formulas = None

                wb = wb_data or wb_formulas
        else:
            wb = None

        if not wb:
            ole_text = extract_ole2_text(file_path)
            if ole_text:
                sec = TextSection(
                    title=f"工作表: {doc_title}",
                    content=ole_text,
                    level=1,
                    page_num=1,
                    breadcrumb_path=[doc_title],
                    metadata={"is_legacy_binary": True},
                )
                return ParsedDocument(
                    title=doc_title,
                    vehicle_model=doc_title,
                    sections=[sec],
                    tables=[],
                    pages=1,
                    metadata={"format": "excel", "file_name": file_path.name, "is_legacy_binary": True},
                )
            return ParsedDocument(
                title=file_path.stem,
                raw_text=f"无法解析Excel文件: {file_path.name}",
                metadata={"format": "excel", "file_name": file_path.name},
            )

        try:
            tables: List[TableBlock] = []
            sections: List[TextSection] = []
            sheet_names = wb.sheetnames
            inferred_model = ""

            for sheet_idx, sheet_name in enumerate(sheet_names, start=1):
                sheet = wb[sheet_name]
                sheet_f = (
                    wb_formulas[sheet_name]
                    if wb_formulas and sheet_name in wb_formulas.sheetnames
                    else None
                )

                if is_large_file:
                    grid: List[List[str]] = []
                    for row_vals in sheet.iter_rows(
                        max_row=MAX_EXCEL_ROWS, max_col=MAX_EXCEL_COLS, values_only=True
                    ):
                        grid.append([self._format_cell_value(val) for val in row_vals])
                    max_row = len(grid)
                    max_col = max((len(r) for r in grid), default=0)
                    cells: List[TableCell] = [
                        TableCell(row_idx=r, col_idx=c, text=grid[r][c], row_span=1, col_span=1)
                        for r in range(max_row)
                        for c in range(len(grid[r]))
                    ]
                else:
                    max_row = min(sheet.max_row or 0, MAX_EXCEL_ROWS)
                    max_col = min(sheet.max_column or 0, MAX_EXCEL_COLS)

                    if max_row < 1 or max_col < 1:
                        sec = TextSection(
                            title=f"工作表: {sheet_name}",
                            content=f"*(工作表 {sheet_name} 为空)*",
                            level=2,
                            page_num=sheet_idx,
                            breadcrumb_path=[doc_title, sheet_name],
                            metadata={"sheet_name": sheet_name, "sheet_index": sheet_idx, "is_empty": True},
                        )
                        sections.append(sec)
                        continue

                    # Build raw 2D grid of values (0-indexed)
                    grid: List[List[str]] = [["" for _ in range(max_col)] for _ in range(max_row)]
                    for r in range(1, max_row + 1):
                        for c in range(1, max_col + 1):
                            cell = sheet.cell(row=r, column=c)
                            val = cell.value
                            # If formula returned None in data_only, fallback to formula string
                            if val is None and sheet_f is not None:
                                f_cell = sheet_f.cell(row=r, column=c)
                                if f_cell.value is not None:
                                    val = f_cell.value
                            fmt = getattr(cell, "number_format", None)
                            grid[r - 1][c - 1] = self._format_cell_value(val, fmt)

                    # Resolve merged cells by propagating top-left value across the entire merged range
                    cells: List[TableCell] = []
                    merged_positions: set = set()
                    top_left_positions: set = set()

                    if hasattr(sheet, "merged_cells") and hasattr(sheet.merged_cells, "ranges"):
                        for rng in sheet.merged_cells.ranges:
                            min_r, min_c, max_r_m, max_c_m = rng.min_row, rng.min_col, rng.max_row, rng.max_col
                            if min_r > max_row or min_c > max_col:
                                continue
                            max_r_m = min(max_r_m, max_row)
                            max_c_m = min(max_c_m, max_col)
                            top_left_val = grid[min_r - 1][min_c - 1]

                            # Propagate value down rows for category context, but do NOT duplicate
                            # across columns to avoid repeated header strings in Markdown tables.
                            for r in range(min_r, max_r_m + 1):
                                for c in range(min_c, max_c_m + 1):
                                    if c == min_c:
                                        grid[r - 1][c - 1] = top_left_val
                                    else:
                                        grid[r - 1][c - 1] = ""
                                    if (r, c) != (min_r, min_c):
                                        merged_positions.add((r - 1, c - 1))

                            # Create TableCell for top-left cell
                            cells.append(
                                TableCell(
                                    row_idx=min_r - 1,
                                    col_idx=min_c - 1,
                                    text=top_left_val,
                                    row_span=max_r_m - min_r + 1,
                                    col_span=max_c_m - min_c + 1,
                                )
                            )
                            top_left_positions.add((min_r - 1, min_c - 1))

                    # Add remaining unmerged cells with O(1) set lookup
                    covered_positions = merged_positions | top_left_positions
                    for r in range(max_row):
                        for c in range(max_col):
                            if (r, c) not in covered_positions:
                                cells.append(
                                    TableCell(
                                        row_idx=r,
                                        col_idx=c,
                                        text=grid[r][c],
                                        row_span=1,
                                        col_span=1,
                                    )
                                )

                # Strip empty trailing rows & columns
                while grid and not any(c.strip() for c in grid[-1]):
                    grid.pop()
                if not grid:
                    sec = TextSection(
                        title=f"工作表: {sheet_name}",
                        content=f"*(工作表 {sheet_name} 为空)*",
                        level=2,
                        page_num=sheet_idx,
                        breadcrumb_path=[doc_title, sheet_name],
                        metadata={"sheet_name": sheet_name, "sheet_index": sheet_idx, "is_empty": True},
                    )
                    sections.append(sec)
                    continue

                # Detect vehicle model candidate
                if not inferred_model:
                    inferred_model = infer_automotive_vehicle_model(
                        file_path, doc_title, " ".join(sheet_names) + (" " + " ".join(grid[0]) if grid else "")
                    )

                # Excel workbooks do not possess absolute pixel geometry; use None and record logical grid dimensions
                bbox = None
                tbl = TableBlock(
                    page_num=sheet_idx,
                    bbox=bbox,
                    rows=grid,
                    title=f"{sheet_name} 配置规格表",
                    extraction_engine="openpyxl_excel",
                    cells=cells,
                    metadata={
                        "sheet_name": sheet_name,
                        "sheet_index": sheet_idx,
                        "total_sheets": len(sheet_names),
                        "max_rows": len(grid),
                        "max_cols": max_col,
                        "logical_grid": {"rows": len(grid), "cols": max_col},
                    },
                )
                tables.append(tbl)

                # Create TextSection
                sec_content = f"工作表【{sheet_name}】包含 {len(grid)} 行 {max_col} 列结构化参数数据。"
                sec = TextSection(
                    title=f"工作表: {sheet_name}",
                    content=sec_content,
                    level=2,
                    page_num=sheet_idx,
                    breadcrumb_path=[doc_title, sheet_name],
                    metadata={
                        "sheet_name": sheet_name,
                        "sheet_index": sheet_idx,
                        "row_count": len(grid),
                        "col_count": max_col,
                    },
                )
                sections.append(sec)

            return ParsedDocument(
                title=doc_title,
                vehicle_model=inferred_model or doc_title,
                sections=sections,
                tables=tables,
                pages=len(sheet_names),
                metadata={
                    "format": "excel",
                    "file_name": file_path.name,
                    "sheet_names": sheet_names,
                    "sheet_count": len(sheet_names),
                },
            )
        finally:
            if wb_readonly is not None:
                try:
                    wb_readonly.close()
                except Exception:
                    pass
            if wb_data is not None:
                try:
                    wb_data.close()
                except Exception:
                    pass
            if wb_formulas is not None:
                try:
                    wb_formulas.close()
                except Exception:
                    pass


# ── CSV & TSV Parser ─────────────────────────────────────────────────────


class CsvTsvParser(BaseFormatParser):
    """
    High-performance CSV and TSV parser:
    - Auto-detects encoding (UTF-8, UTF-8-SIG, GB18030, GBK, Latin-1)
    - Delimiter autodetection via csv.Sniffer with dialect fallback
    - Converts tabular rows into TableBlock and TextSection
    """

    def can_parse(self, file_path: Path, format_type: DocumentFormat) -> bool:
        return format_type in [DocumentFormat.CSV, DocumentFormat.TSV] or file_path.suffix.lower() in [
            ".csv",
            ".tsv",
        ]

    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedDocument:
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        raw_bytes = file_path.read_bytes()
        if not raw_bytes.strip():
            return ParsedDocument(
                title=file_path.stem,
                raw_text="",
                metadata={"format": suffix.lstrip("."), "file_name": file_path.name, "is_empty": True},
            )

        # 1. Detect encoding
        encodings = [
            "utf-8-sig",
            "utf-8",
            "gb18030",
            "gbk",
            "gb2312",
            "utf-16",
            "utf-16-le",
            "utf-16-be",
            "latin1",
        ]
        content = ""
        used_encoding = "utf-8"
        for enc in encodings:
            try:
                content = raw_bytes.decode(enc)
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue
        if not content and raw_bytes:
            content = raw_bytes.decode("utf-8", errors="replace")
            used_encoding = "utf-8-replace"

        # 2. Detect delimiter
        delimiter = "\t" if suffix == ".tsv" else ","
        if suffix != ".tsv":
            try:
                sample = content[:4096]
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                delimiter = dialect.delimiter
            except Exception:
                pass
        else:
            # For TSV, prioritize tab; only sniff if no tabs are present
            if "\t" not in content[:4096] and "," in content[:4096]:
                try:
                    dialect = csv.Sniffer().sniff(content[:4096], delimiters=",\t;|")
                    delimiter = dialect.delimiter
                except Exception:
                    pass

        # 3. Read rows (bounded to avoid memory exhaustion)
        MAX_CSV_ROWS = 20000
        rows: List[List[str]] = []
        try:
            reader = csv.reader(io.StringIO(content), delimiter=delimiter)
            for idx, r in enumerate(reader):
                if idx >= MAX_CSV_ROWS:
                    break
                if any(cell.strip() for cell in r):
                    rows.append([c.strip() for c in r])
        except Exception as e:
            logger.warning(f"CSV/TSV reading notice for {file_path}: {e}")
            for line in content.splitlines()[:MAX_CSV_ROWS]:
                parts = [c.strip() for c in line.split(delimiter)]
                if any(parts):
                    rows.append(parts)

        if not rows:
            return ParsedDocument(title=file_path.stem, raw_text="", metadata={"format": suffix.lstrip(".")})

        max_cols = max(len(r) for r in rows)
        bbox = BoundingBox(x0=0, top=0, x1=max_cols * 50.0, bottom=len(rows) * 20.0, page=1)
        doc_title = file_path.stem.replace("_", " ")

        tbl = TableBlock(
            page_num=1,
            bbox=bbox,
            rows=rows,
            title=f"{doc_title} 数据表",
            extraction_engine="csv_tsv_parser",
            metadata={"delimiter": delimiter, "encoding": used_encoding, "row_count": len(rows)},
        )

        sec = TextSection(
            title=doc_title,
            content=f"包含 {len(rows)} 行 {max_cols} 列结构化记录。",
            level=1,
            page_num=1,
            breadcrumb_path=[doc_title],
            metadata={"format": suffix.lstrip("."), "row_count": len(rows)},
        )

        return ParsedDocument(
            title=doc_title,
            vehicle_model=infer_automotive_vehicle_model(file_path, doc_title, content[:300]),
            sections=[sec],
            tables=[tbl],
            pages=1,
            metadata={
                "format": "tsv" if suffix == ".tsv" else "csv",
                "file_name": file_path.name,
                "encoding": used_encoding,
                "delimiter": delimiter,
                "row_count": len(rows),
            },
        )


# ── Word Parser (.docx, .doc) ────────────────────────────────────────────


class WordParser(BaseFormatParser):
    """
    Enterprise Word (.docx) document parser:
    - Semantic heading hierarchy (Document Title, Subtitle, H1-H4)
    - Complex tables with merged cell resolution, multi-paragraph cells, and header rows
    - Bullet/numbered lists, callouts, footnotes/endnotes, captions, and header/footer filtering
    """

    def can_parse(self, file_path: Path, format_type: DocumentFormat) -> bool:
        return format_type == DocumentFormat.WORD or file_path.suffix.lower() in [".docx", ".doc"]

    def _extract_docx_table(self, table: Any, table_idx: int) -> TableBlock:
        """Parse Word table resolving merged cells (tc element sharing) and multi-paragraph cells."""
        grid = [[cell for cell in row.cells] for row in table.rows]
        n_rows = len(grid)
        n_cols = max((len(r) for r in grid), default=0)

        # Track XML tc element spans
        tc_map: Dict[Any, Dict[str, Any]] = {}
        for r_idx, row in enumerate(grid):
            for c_idx, cell in enumerate(row):
                tc = cell._tc
                cell_paras = []
                for p in cell.paragraphs:
                    p_text = p.text.strip()
                    if p_text and (not cell_paras or p_text != cell_paras[-1]):
                        cell_paras.append(p_text)
                cell_text = "\n".join(cell_paras)
                if tc not in tc_map:
                    tc_map[tc] = {
                        "min_r": r_idx,
                        "max_r": r_idx,
                        "min_c": c_idx,
                        "max_c": c_idx,
                        "text": cell_text,
                    }
                else:
                    tc_map[tc]["max_r"] = max(tc_map[tc]["max_r"], r_idx)
                    tc_map[tc]["max_c"] = max(tc_map[tc]["max_c"], c_idx)
                    if cell_text and not tc_map[tc]["text"]:
                        tc_map[tc]["text"] = cell_text

        # Build normalized 2D string matrix
        matrix: List[List[str]] = [["" for _ in range(n_cols)] for _ in range(n_rows)]
        table_cells: List[TableCell] = []

        for tc, info in tc_map.items():
            min_r, max_r = info["min_r"], info["max_r"]
            min_c, max_c = info["min_c"], info["max_c"]
            val = info["text"]

            for r in range(min_r, max_r + 1):
                for c in range(min_c, max_c + 1):
                    if r < n_rows and c < n_cols:
                        matrix[r][c] = val

            r_span = max_r - min_r + 1
            c_span = max_c - min_c + 1
            table_cells.append(
                TableCell(
                    row_idx=min_r,
                    col_idx=min_c,
                    text=val,
                    row_span=r_span,
                    col_span=c_span,
                )
            )

        # Check for Word official header rows (w:tblHeader)
        header_rows_count = 1
        headers: Optional[List[str]] = None
        if table.rows:
            official_header_rows = 0
            for r in table.rows:
                try:
                    if r._tr.xpath("w:trPr/w:tblHeader") or r._tr.xpath(".//*[local-name()='tblHeader']"):
                        official_header_rows += 1
                    else:
                        break
                except Exception:
                    break
            if official_header_rows > 0:
                header_rows_count = official_header_rows
                headers = matrix[0] if matrix else None

        bbox = BoundingBox(x0=0, top=table_idx * 150.0, x1=n_cols * 50.0, bottom=table_idx * 150.0 + n_rows * 20.0, page=1)
        tbl_block = TableBlock(
            page_num=1,
            bbox=bbox,
            rows=matrix,
            headers=headers,
            cells=table_cells,
            title=f"Word 表格 {table_idx}",
            extraction_engine="python_docx",
            metadata={"table_index": table_idx, "header_rows_count": header_rows_count},
        )
        return tbl_block

    @staticmethod
    def _extract_package_notes(file_path: Path) -> Tuple[List[str], List[str]]:
        """Extract footnotes and endnotes directly from Word OpenXML zip package with robust namespace fallback."""
        footnotes: List[str] = []
        endnotes: List[str] = []
        try:
            with zipfile.ZipFile(str(file_path), "r") as zf:
                # 1. Footnotes
                if "word/footnotes.xml" in zf.namelist():
                    raw_xml = zf.read("word/footnotes.xml").decode("utf-8", errors="replace")
                    try:
                        import xml.etree.ElementTree as ET

                        tree = ET.fromstring(raw_xml)
                        for fn in tree.iter():
                            if fn.tag.endswith("footnote"):
                                fn_id = None
                                for k, v in fn.attrib.items():
                                    if k.endswith("id"):
                                        fn_id = v
                                        break
                                if fn_id and int(fn_id) > 0:
                                    texts = [
                                        node.text
                                        for node in fn.iter()
                                        if node.tag.endswith("t") and node.text
                                    ]
                                    if texts:
                                        footnotes.append("".join(texts).strip())
                    except Exception:
                        matches = re.findall(
                            r'<[^>]*?:?footnote[^>]*?id="([1-9]\d*)"[^>]*?>(.*?)</[^>]*?:?footnote>',
                            raw_xml,
                            re.DOTALL,
                        )
                        for _, fn_content in matches:
                            t_matches = re.findall(r'<[^>]*?:?t[^>]*?>(.*?)</[^>]*?:?t>', fn_content, re.DOTALL)
                            if t_matches:
                                footnotes.append("".join(t_matches).strip())

                # 2. Endnotes
                if "word/endnotes.xml" in zf.namelist():
                    raw_xml = zf.read("word/endnotes.xml").decode("utf-8", errors="replace")
                    try:
                        import xml.etree.ElementTree as ET

                        tree = ET.fromstring(raw_xml)
                        for en in tree.iter():
                            if en.tag.endswith("endnote"):
                                en_id = None
                                for k, v in en.attrib.items():
                                    if k.endswith("id"):
                                        en_id = v
                                        break
                                if en_id and int(en_id) > 0:
                                    texts = [
                                        node.text
                                        for node in en.iter()
                                        if node.tag.endswith("t") and node.text
                                    ]
                                    if texts:
                                        endnotes.append("".join(texts).strip())
                    except Exception:
                        matches = re.findall(
                            r'<[^>]*?:?endnote[^>]*?id="([1-9]\d*)"[^>]*?>(.*?)</[^>]*?:?endnote>',
                            raw_xml,
                            re.DOTALL,
                        )
                        for _, en_content in matches:
                            t_matches = re.findall(r'<[^>]*?:?t[^>]*?>(.*?)</[^>]*?:?t>', en_content, re.DOTALL)
                            if t_matches:
                                endnotes.append("".join(t_matches).strip())
        except Exception as e:
            logger.debug(f"Notice: Package notes extraction for {file_path}: {e}")
        return footnotes, endnotes

    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedDocument:
        import docx

        file_path = Path(file_path)
        doc_title = file_path.stem.replace("_", " ")

        try:
            doc = docx.Document(str(file_path))
        except Exception as e:
            logger.warning(f"python-docx failed to open {file_path}: {e}")
            ole_text = extract_ole2_text(file_path)
            if ole_text:
                sec = TextSection(
                    title=doc_title,
                    content=ole_text,
                    level=1,
                    page_num=1,
                    breadcrumb_path=[doc_title],
                    metadata={"is_legacy_binary": True},
                )
                return ParsedDocument(
                    title=doc_title,
                    vehicle_model=doc_title,
                    sections=[sec],
                    tables=[],
                    pages=1,
                    metadata={"format": "word", "file_name": file_path.name, "is_legacy_binary": True},
                )
            return ParsedDocument(
                title=file_path.stem,
                raw_text=f"DOCX解析失败: {e}",
                metadata={"format": "word", "error": str(e)},
            )

        sections: List[TextSection] = []
        tables: List[TableBlock] = []

        # 1. Extract and filter headers & footers
        doc_headers: List[str] = []
        doc_footers: List[str] = []
        for s in doc.sections:
            for hp in s.header.paragraphs:
                ht = hp.text.strip()
                if ht and ht not in doc_headers:
                    doc_headers.append(ht)
            for fp in s.footer.paragraphs:
                ft = fp.text.strip()
                if ft and ft not in doc_footers:
                    doc_footers.append(ft)

        # 2. Extract footnotes & endnotes
        pkg_footnotes, pkg_endnotes = self._extract_package_notes(file_path)
        text_footnotes: List[str] = []
        captions: List[str] = []

        # Current section state machine
        active_title = doc_title
        active_level = 1
        active_paras: List[str] = []
        heading_stack: List[Tuple[int, str]] = [(1, doc_title)]

        def flush_active_section():
            nonlocal active_paras, active_title, active_level
            if active_paras:
                content = "\n\n".join(active_paras).strip()
                breadcrumbs = [t for _, t in heading_stack]
                sec = TextSection(
                    title=active_title,
                    content=content,
                    level=active_level,
                    page_num=1,
                    breadcrumb_path=breadcrumbs,
                    metadata={"section_level": active_level},
                )
                sections.append(sec)
                active_paras = []

        # Parse paragraphs and tables in order
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            # Header / footer / page number filtering
            if text in doc_headers or text in doc_footers:
                continue
            if re.match(r"^\s*(?:第\s*)?\d+\s*(?:[/共]\s*\d+\s*页?|页)?\s*$", text) or re.match(
                r"^\s*Page\s+\d+(?:\s*of\s*\d+)?\s*$", text, re.I
            ):
                continue

            style_name = p.style.name if p.style else ""
            style_lower = style_name.lower()

            # Heading detection
            h_match = re.search(r"heading\s*(\d+)|标题\s*(\d+)", style_lower)
            if "title" in style_lower or "标题" == style_lower:
                flush_active_section()
                doc_title = text
                active_title = text
                active_level = 1
                heading_stack = [(1, text)]
            elif h_match:
                lvl = int(h_match.group(1) or h_match.group(2))
                flush_active_section()
                heading_stack = [(hl, ht) for hl, ht in heading_stack if hl < lvl]
                heading_stack.append((lvl, text))
                active_title = text
                active_level = lvl
            elif "subtitle" in style_lower or "副标题" in style_lower:
                active_paras.append(f"*{text}*")
            elif "list" in style_lower or p.text.startswith(("•", "-", "*", "1.", "2.", "3.", "(1)", "(2)")):
                ilvl = 0
                try:
                    pPr = getattr(p._p, "pPr", None)
                    numPr = getattr(pPr, "numPr", None) if pPr is not None else None
                    ilvl_el = getattr(numPr, "ilvl", None) if numPr is not None else None
                    if ilvl_el is not None and getattr(ilvl_el, "val", None) is not None:
                        ilvl = int(ilvl_el.val)
                except Exception:
                    ilvl = 0
                leading_tabs = len(p.text) - len(p.text.lstrip("\t "))
                indent_level = min(10, max(ilvl, leading_tabs // 2))
                indent_str = "  " * indent_level
                if not text.startswith(("-", "*", "•", "1.", "2.", "3.", "4.", "5.")):
                    text = f"{indent_str}- {text}"
                else:
                    text = f"{indent_str}{text}"
                active_paras.append(text)
            elif "quote" in style_lower or "callout" in style_lower or "警告" in text or "注意" in text:
                active_paras.append(f"> {text}")
            elif "caption" in style_lower or re.match(r"^(?:图|表|Figure|Table)\s*\d+[:：\s]*", text):
                captions.append(text)
                active_paras.append(f"**{text}**")
            elif re.match(r"^[\*•-]?\s*(?:注\d*|说明|Footnote\d*|Note\d*)[:：\s]", text):
                if text not in text_footnotes and text not in pkg_footnotes:
                    text_footnotes.append(text)
                active_paras.append(f"*{text}*")
            else:
                active_paras.append(text)

        flush_active_section()

        # Parse tables
        for tbl_idx, table in enumerate(doc.tables, start=1):
            tbl_block = self._extract_docx_table(table, tbl_idx)
            tables.append(tbl_block)

        # If no sections were created
        if not sections:
            sections.append(
                TextSection(
                    title=doc_title,
                    content=f"包含 {len(tables)} 个 Word 表格及相关说明。",
                    level=1,
                    page_num=1,
                    breadcrumb_path=[doc_title],
                )
            )

        all_footnotes = pkg_footnotes + text_footnotes

        # Detect vehicle model
        text_sample = " ".join(s.title + " " + s.content[:100] for s in sections[:3])
        inferred_model = infer_automotive_vehicle_model(file_path, doc_title, text_sample)

        return ParsedDocument(
            title=doc_title,
            vehicle_model=inferred_model or doc_title,
            sections=sections,
            tables=tables,
            pages=1,
            metadata={
                "format": "word",
                "file_name": file_path.name,
                "table_count": len(tables),
                "headers": doc_headers,
                "footers": doc_footers,
                "footnotes": all_footnotes,
                "endnotes": pkg_endnotes,
                "captions": captions,
            },
        )


# ── PowerPoint Parser (.pptx, .ppt) ──────────────────────────────────────


class PowerPointParser(BaseFormatParser):
    """
    Enterprise PowerPoint presentation parser:
    - Slide-by-slide sequence tracking with slide index, title, and layout semantics
    - Spatial reading order heuristics (sorting shapes by vertical band + horizontal left)
    - Embedded slide tables converted to TableBlock
    - Presenter / speaker notes extraction into TextSection metadata and contextual callouts
    """

    def can_parse(self, file_path: Path, format_type: DocumentFormat) -> bool:
        return format_type == DocumentFormat.POWERPOINT or file_path.suffix.lower() in [
            ".pptx",
            ".ppt",
        ]

    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedDocument:
        import pptx

        file_path = Path(file_path)
        doc_title = file_path.stem.replace("_", " ")

        try:
            prs = pptx.Presentation(str(file_path))
        except Exception as e:
            logger.warning(f"python-pptx failed to open {file_path}: {e}")
            ole_text = extract_ole2_text(file_path)
            if ole_text:
                sec = TextSection(
                    title=doc_title,
                    content=ole_text,
                    level=1,
                    page_num=1,
                    breadcrumb_path=[doc_title],
                    metadata={"is_legacy_binary": True},
                )
                return ParsedDocument(
                    title=doc_title,
                    vehicle_model=doc_title,
                    sections=[sec],
                    tables=[],
                    pages=1,
                    metadata={"format": "powerpoint", "file_name": file_path.name, "is_legacy_binary": True},
                )
            return ParsedDocument(
                title=file_path.stem,
                raw_text=f"PPTX解析失败: {e}",
                metadata={"format": "powerpoint", "error": str(e)},
            )

        sections: List[TextSection] = []
        tables: List[TableBlock] = []
        slide_height = prs.slide_height if hasattr(prs, "slide_height") else 7.5 * 914400

        for slide_idx, slide in enumerate(prs.slides, start=1):
            # 1. Slide title
            slide_title = ""
            if slide.shapes.title and slide.shapes.title.text.strip():
                slide_title = slide.shapes.title.text.strip()

            layout_name = getattr(slide.slide_layout, "name", f"Layout {slide_idx}")

            # 2. Extract speaker notes
            speaker_notes = ""
            if getattr(slide, "has_notes_slide", False) and slide.notes_slide:
                notes_frame = slide.notes_slide.notes_text_frame
                if notes_frame and notes_frame.text.strip():
                    speaker_notes = notes_frame.text.strip()

            # 3. Spatial reading order sorting of shapes:
            # Group into vertical bands (e.g. 8% of slide height) and sort by left
            def collect_shapes(shape_iter):
                shapes_acc = []
                for shape in shape_iter:
                    if shape == slide.shapes.title:
                        continue
                    if hasattr(shape, "shapes"):
                        shapes_acc.extend(collect_shapes(shape.shapes))
                    else:
                        top = getattr(shape, "top", 0) or 0
                        left = getattr(shape, "left", 0) or 0
                        width = getattr(shape, "width", 0) or 0
                        height = getattr(shape, "height", 0) or 0
                        band = round(float(top) / max(1.0, 0.08 * float(slide_height)))
                        shapes_acc.append((band, left, top, width, height, shape))
                return shapes_acc

            content_shapes = collect_shapes(slide.shapes)
            content_shapes.sort(key=lambda item: (item[0], item[1]))

            # 4. Extract text content & embedded tables
            slide_text_blocks: List[str] = []
            if not slide_title and content_shapes:
                # Fallback: top shape text as title
                first_shape = content_shapes[0][5]
                if getattr(first_shape, "has_text_frame", False) and first_shape.text_frame.text.strip():
                    slide_title = first_shape.text_frame.text.split("\n")[0].strip()

            if not slide_title:
                slide_title = f"Slide {slide_idx}"

            for _, left, top, width, height, shape in content_shapes:
                # Handle Table Shape
                if getattr(shape, "has_table", False):
                    table = shape.table
                    matrix = []
                    table_cells: List[TableCell] = []
                    for r_idx, row in enumerate(table.rows):
                        row_vals = []
                        for c_idx, cell in enumerate(row.cells):
                            c_text = cell.text.strip()
                            row_vals.append(c_text)
                            is_spanned = getattr(cell, "is_spanned", False)
                            if not is_spanned:
                                r_span = getattr(cell, "span_height", 1) or 1
                                c_span = getattr(cell, "span_width", 1) or 1
                                table_cells.append(
                                    TableCell(
                                        row_idx=r_idx,
                                        col_idx=c_idx,
                                        text=c_text,
                                        row_span=r_span,
                                        col_span=c_span,
                                    )
                                )
                        matrix.append(row_vals)
                    if matrix:
                        bbox = BoundingBox(
                            x0=float(left) / 9144.0,
                            top=float(top) / 9144.0,
                            x1=(float(left) + float(width)) / 9144.0,
                            bottom=(float(top) + float(height)) / 9144.0,
                            page=slide_idx,
                        )
                        tbl_title = f"幻灯片 {slide_idx} 表格: {slide_title}"
                        tbl = TableBlock(
                            page_num=slide_idx,
                            bbox=bbox,
                            rows=matrix,
                            cells=table_cells,
                            title=tbl_title,
                            extraction_engine="python_pptx",
                            metadata={"slide_index": slide_idx, "slide_title": slide_title},
                        )
                        tables.append(tbl)
                        slide_text_blocks.append(f"[表格: {tbl_title}]")

                # Handle Text Frame Shape
                elif getattr(shape, "has_text_frame", False):
                    tf = shape.text_frame
                    paragraphs = []
                    for p in tf.paragraphs:
                        p_text = p.text.strip()
                        if not p_text:
                            continue
                        level = getattr(p, "level", 0)
                        indent = "  " * level
                        bullet = "- " if level > 0 or len(tf.paragraphs) > 1 else ""
                        paragraphs.append(f"{indent}{bullet}{p_text}")
                    if paragraphs:
                        slide_text_blocks.append("\n".join(paragraphs))

            # Append speaker notes as contextual callout
            if speaker_notes:
                slide_text_blocks.append(f"\n> **演讲者备注**: {speaker_notes}")

            full_slide_content = "\n\n".join(slide_text_blocks).strip()
            sec = TextSection(
                title=f"幻灯片 {slide_idx}: {slide_title}",
                content=full_slide_content or f"*(Slide {slide_idx} 内容)*",
                level=2,
                page_num=slide_idx,
                breadcrumb_path=[doc_title, f"Slide {slide_idx}: {slide_title}"],
                metadata={
                    "slide_index": slide_idx,
                    "slide_title": slide_title,
                    "layout_name": layout_name,
                    "speaker_notes": speaker_notes,
                },
            )
            sections.append(sec)

        # Detect vehicle model
        text_sample = " ".join(s.title + " " + s.content[:100] for s in sections[:3])
        inferred_model = infer_automotive_vehicle_model(file_path, doc_title, text_sample)

        return ParsedDocument(
            title=doc_title,
            vehicle_model=inferred_model or doc_title,
            sections=sections,
            tables=tables,
            pages=len(prs.slides),
            metadata={
                "format": "powerpoint",
                "file_name": file_path.name,
                "slide_count": len(prs.slides),
            },
        )


# ── Image Parser (.png, .jpg, .jpeg, .webp, .bmp) ────────────────────────


class ImageParser(BaseFormatParser):
    """
    Enterprise Image document & spec-sheet parser:
    - Image diagnostics (width, height, DPI, aspect ratio, blur detection, contrast calculation)
    - EXIF / IPTC metadata extraction
    - Pluggable OCR extraction pipeline preserving line bounding boxes and confidence scores
    - Conversion of detected tabular parameters into TableBlock
    """

    def __init__(self, ocr_engine: Optional[BaseOCREngine] = None):
        self.ocr_engine = ocr_engine or get_ocr_engine()

    def can_parse(self, file_path: Path, format_type: DocumentFormat) -> bool:
        return format_type == DocumentFormat.IMAGE or file_path.suffix.lower() in [
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
        ]

    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedDocument:
        file_path = Path(file_path)
        try:
            img = Image.open(str(file_path))
            img.load()
        except Exception as e:
            logger.warning(f"PIL failed to open image {file_path}: {e}")
            return ParsedDocument(
                title=file_path.stem,
                raw_text=f"图像打开失败: {e}",
                metadata={"format": "image", "error": str(e)},
            )

        # 1. Run diagnostics & EXIF
        diagnostics = extract_image_diagnostics(img)
        exif = extract_exif_metadata(img)

        # 2. Execute OCR Extraction
        ocr_res = self.ocr_engine.extract_text_and_boxes(file_path)

        # 3. Create TextSection from OCR lines
        doc_title = file_path.stem.replace("_", " ")
        lines_text = [line.text for line in ocr_res.lines]
        ocr_content = ocr_res.full_text or "\n".join(lines_text)

        w = max(1.0, float(diagnostics.width))
        h = max(1.0, float(diagnostics.height))
        sec = TextSection(
            title=f"图像文字识别 ({doc_title})",
            content=ocr_content,
            level=1,
            page_num=1,
            bbox=BoundingBox(0, 0, w, h, page=1),
            breadcrumb_path=[doc_title],
            metadata={
                "ocr_confidence": ocr_res.confidence,
                "ocr_engine": ocr_res.metadata.get("engine", "unknown"),
                "is_blurry": diagnostics.is_blurry,
            },
        )

        # 4. If OCR lines contain structured automotive parameters (key: value), convert to TableBlock
        tables: List[TableBlock] = []
        table_rows: List[List[str]] = [["配置项目", "参数数值"]]
        for line in ocr_res.lines:
            if ":" in line.text or "：" in line.text:
                parts = re.split(r"[:：]", line.text, maxsplit=1)
                if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                    table_rows.append([parts[0].strip(), parts[1].strip()])

        if len(table_rows) > 2:
            pad_x = min(20.0, w * 0.1)
            pad_y = min(50.0, h * 0.1)
            tbl = TableBlock(
                page_num=1,
                bbox=BoundingBox(x0=pad_x, top=pad_y, x1=max(pad_x + 1.0, w - pad_x), bottom=max(pad_y + 1.0, h - pad_y), page=1),
                rows=table_rows,
                title=f"{doc_title} 图像参数配置表",
                extraction_engine=f"image_ocr_{ocr_res.metadata.get('engine', 'mock')}",
                confidence=ocr_res.confidence,
                metadata={"source_image": file_path.name, "row_count": len(table_rows)},
            )
            tables.append(tbl)

        # Inferred model
        inferred_model = infer_automotive_vehicle_model(file_path, doc_title, ocr_content[:300])

        return ParsedDocument(
            title=doc_title,
            vehicle_model=inferred_model or doc_title,
            sections=[sec],
            tables=tables,
            pages=1,
            raw_text=ocr_content,
            metadata={
                "format": "image",
                "file_name": file_path.name,
                "image_diagnostics": diagnostics.to_dict(),
                "exif": exif,
                "ocr_confidence": ocr_res.confidence,
            },
        )


# ── Structured & Plain Text Parser (.txt, .md, .html, .rtf, .json, .toml)


class StructuredTextParser(BaseFormatParser):
    """
    Schema-aware parser for Markdown, HTML, JSON, TOML, RTF, and plain text documents.
    """

    def can_parse(self, file_path: Path, format_type: DocumentFormat) -> bool:
        return format_type in [
            DocumentFormat.TEXT,
            DocumentFormat.MARKDOWN,
            DocumentFormat.HTML,
            DocumentFormat.JSON,
            DocumentFormat.TOML,
            DocumentFormat.RTF,
        ] or file_path.suffix.lower() in [
            ".txt",
            ".md",
            ".html",
            ".htm",
            ".rtf",
            ".json",
            ".toml",
        ]

    def _parse_markdown(self, content: str, doc_title: str) -> ParsedDocument:
        """Parse markdown heading hierarchy and embedded markdown tables."""
        sections: List[TextSection] = []
        tables: List[TableBlock] = []

        lines = content.split("\n")
        active_title = doc_title
        active_level = 1
        active_paras: List[str] = []
        heading_stack: List[Tuple[int, str]] = [(1, doc_title)]

        def flush_section():
            nonlocal active_paras, active_title, active_level
            if active_paras:
                content_str = "\n".join(active_paras).strip()
                breadcrumbs = [t for _, t in heading_stack]
                sec = TextSection(
                    title=active_title,
                    content=content_str,
                    level=active_level,
                    page_num=1,
                    breadcrumb_path=breadcrumbs,
                )
                sections.append(sec)
                active_paras = []

        # Table detection buffer
        table_buffer: List[str] = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            # Table lines
            if stripped.startswith("|") and stripped.endswith("|"):
                in_table = True
                table_buffer.append(stripped)
                continue
            elif in_table:
                # Flush table buffer
                in_table = False
                parsed_rows = []
                for t_line in table_buffer:
                    if re.match(r"^\|(?:\s*[:-]+[-| :]*)\|?$", t_line):
                        continue
                    cells = [c.strip() for c in t_line.strip("|").split("|")]
                    parsed_rows.append(cells)
                if parsed_rows:
                    tbl = TableBlock(
                        page_num=1,
                        bbox=BoundingBox(0, 0, 500, 200),
                        rows=parsed_rows,
                        title=f"{active_title} 表格",
                        extraction_engine="markdown_parser",
                    )
                    tables.append(tbl)
                table_buffer = []

            # Heading lines
            h_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if h_match:
                flush_section()
                hashes, title = h_match.groups()
                lvl = len(hashes)
                heading_stack = [(hl, ht) for hl, ht in heading_stack if hl < lvl]
                heading_stack.append((lvl, title))
                active_title = title
                active_level = lvl
            else:
                active_paras.append(line)

        # Flush any trailing table at end of markdown document
        if in_table and table_buffer:
            parsed_rows = []
            for t_line in table_buffer:
                if re.match(r"^\|(?:\s*[:-]+[-| :]*)\|?$", t_line):
                    continue
                cells = [c.strip() for c in t_line.strip("|").split("|")]
                parsed_rows.append(cells)
            if parsed_rows:
                tbl = TableBlock(
                    page_num=1,
                    bbox=BoundingBox(0, 0, 500, 200),
                    rows=parsed_rows,
                    title=f"{active_title} 表格",
                    extraction_engine="markdown_parser",
                )
                tables.append(tbl)
            table_buffer = []

        flush_section()

        return ParsedDocument(
            title=doc_title,
            sections=sections,
            tables=tables,
            pages=1,
            raw_text=content,
            metadata={"format": "markdown", "table_count": len(tables), "section_count": len(sections)},
        )

    def _parse_html(self, content: str, doc_title: str) -> ParsedDocument:
        """Parse HTML headings hierarchy (h1-h6) and <table> elements via BeautifulSoup."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "html.parser")
        sections: List[TextSection] = []
        tables: List[TableBlock] = []

        # 1. Extract tables
        for tbl_idx, table in enumerate(soup.find_all("table"), start=1):
            rows: List[List[str]] = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            if rows:
                caption = table.find("caption")
                tbl_title = caption.get_text(strip=True) if caption else f"HTML 表格 {tbl_idx}"
                tbl = TableBlock(
                    page_num=1,
                    bbox=BoundingBox(0, 0, 500, 200),
                    rows=rows,
                    title=tbl_title,
                    extraction_engine="beautifulsoup_html",
                )
                tables.append(tbl)

        # 2. Extract semantic headings (h1-h6) & text paragraphs
        body = soup.find("body") or soup
        active_title = doc_title
        active_level = 1
        active_paras: List[str] = []
        heading_stack: List[Tuple[int, str]] = [(1, doc_title)]

        def flush_active_section():
            nonlocal active_paras, active_title, active_level
            if active_paras:
                sec_text = "\n\n".join(active_paras).strip()
                breadcrumbs = [t for _, t in heading_stack]
                sec = TextSection(
                    title=active_title,
                    content=sec_text,
                    level=active_level,
                    page_num=1,
                    breadcrumb_path=breadcrumbs,
                    metadata={"section_level": active_level},
                )
                sections.append(sec)
                active_paras = []

        for el in body.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote"]):
            tag_name = el.name.lower()
            text = el.get_text(strip=True)
            if not text:
                continue
            if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                flush_active_section()
                lvl = int(tag_name[1])
                heading_stack = [(hl, ht) for hl, ht in heading_stack if hl < lvl]
                heading_stack.append((lvl, text))
                active_title = text
                active_level = lvl
            elif tag_name == "blockquote":
                active_paras.append(f"> {text}")
            elif tag_name == "li":
                active_paras.append(f"- {text}")
            else:
                active_paras.append(text)

        flush_active_section()

        if not sections:
            body_text = body.get_text(separator="\n", strip=True)
            sec = TextSection(
                title=doc_title,
                content=body_text,
                level=1,
                page_num=1,
                breadcrumb_path=[doc_title],
            )
            sections.append(sec)

        return ParsedDocument(
            title=doc_title,
            sections=sections,
            tables=tables,
            pages=1,
            raw_text=body.get_text(separator="\n", strip=True),
            metadata={"format": "html", "table_count": len(tables), "section_count": len(sections)},
        )

    def _parse_json(self, content: str, doc_title: str) -> ParsedDocument:
        """Schema-aware JSON parser extracting structured specifications and records."""
        try:
            data = json.loads(content)
        except Exception as e:
            logger.warning(f"JSON parsing error for {doc_title}: {e}")
            sec = TextSection(
                title=doc_title,
                content=content[:5000],
                level=1,
                page_num=1,
                breadcrumb_path=[doc_title],
                metadata={"error": str(e), "is_corrupt": True},
            )
            return ParsedDocument(
                title=doc_title,
                sections=[sec],
                tables=[],
                pages=1,
                raw_text=content,
                metadata={"format": "json", "error": str(e), "is_corrupt": True},
            )

        sections: List[TextSection] = []
        tables: List[TableBlock] = []

        if isinstance(data, list) and data and isinstance(data[0], dict):
            # Array of objects -> collect union of all keys (with nested dict flattening) across all dicts
            def flatten_record(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
                res = {}
                for k, v in d.items():
                    k_name = f"{prefix}.{k}" if prefix else str(k)
                    if isinstance(v, dict):
                        res.update(flatten_record(v, k_name))
                    elif isinstance(v, list):
                        res[k_name] = ", ".join(str(x) for x in v)
                    else:
                        res[k_name] = v
                return res

            flat_data = [flatten_record(item) if isinstance(item, dict) else item for item in data]
            headers: List[str] = []
            seen: set = set()
            for item in flat_data:
                if isinstance(item, dict):
                    for k in item.keys():
                        if k not in seen:
                            seen.add(k)
                            headers.append(k)

            rows = [headers]
            for item in flat_data:
                if isinstance(item, dict):
                    rows.append([str(item.get(h, "")) if item.get(h) is not None else "" for h in headers])

            tbl = TableBlock(
                page_num=1,
                bbox=BoundingBox(0, 0, len(headers) * 60.0, len(rows) * 20.0),
                rows=rows,
                title=f"{doc_title} 数据记录表",
                extraction_engine="json_parser",
            )
            tables.append(tbl)
            sec_content = f"JSON 数据包含 {len(data)} 条结构化记录。"
        elif isinstance(data, dict):
            # Dict of key-values -> recursively flatten nested dictionary specs
            def flatten_dict(d: Dict[str, Any], prefix: str = "") -> List[Tuple[str, str]]:
                items: List[Tuple[str, str]] = []
                for k, v in d.items():
                    key_name = f"{prefix}.{k}" if prefix else str(k)
                    if isinstance(v, dict):
                        items.extend(flatten_dict(v, key_name))
                    elif isinstance(v, list):
                        items.append((key_name, ", ".join(str(x) for x in v)))
                    else:
                        items.append((key_name, str(v)))
                return items

            flat_items = flatten_dict(data)
            rows = [["参数属性", "配置值"]]
            for k_str, v_str in flat_items:
                rows.append([k_str, v_str])

            tbl = TableBlock(
                page_num=1,
                bbox=BoundingBox(0, 0, 400, len(rows) * 20.0),
                rows=rows,
                title=f"{doc_title} 属性参数表",
                extraction_engine="json_parser",
            )
            tables.append(tbl)
            sec_content = (
                f"JSON 属性配置 (包含 {len(flat_items)} 项参数):\n"
                f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)[:2000]}\n```"
            )
        else:
            sec_content = str(data)

        sec = TextSection(
            title=doc_title,
            content=sec_content,
            level=1,
            page_num=1,
            breadcrumb_path=[doc_title],
        )
        sections.append(sec)

        return ParsedDocument(
            title=doc_title,
            sections=sections,
            tables=tables,
            pages=1,
            raw_text=content,
            metadata={"format": "json"},
        )

    def _parse_toml(self, content: str, doc_title: str) -> ParsedDocument:
        """Parse TOML vehicle specifications with nested section flattening."""
        try:
            import toml

            data = toml.loads(content)
        except Exception as e:
            logger.warning(f"TOML parsing error for {doc_title}: {e}")
            sec = TextSection(
                title=doc_title,
                content=content[:5000],
                level=1,
                page_num=1,
                breadcrumb_path=[doc_title],
                metadata={"error": str(e), "is_corrupt": True},
            )
            return ParsedDocument(
                title=doc_title,
                sections=[sec],
                tables=[],
                pages=1,
                raw_text=content,
                metadata={"format": "toml", "error": str(e), "is_corrupt": True},
            )

        sections: List[TextSection] = []
        tables: List[TableBlock] = []

        def flatten_toml(d: Dict[str, Any], prefix: str = "") -> List[Tuple[str, str]]:
            items: List[Tuple[str, str]] = []
            for k, v in d.items():
                key_name = f"{prefix}.{k}" if prefix else str(k)
                if isinstance(v, dict):
                    items.extend(flatten_toml(v, key_name))
                elif isinstance(v, list):
                    items.append((key_name, ", ".join(str(x) for x in v)))
                else:
                    items.append((key_name, str(v)))
            return items

        flat_rows = flatten_toml(data)
        rows = [["配置字段", "参数值"]]
        for k_str, v_str in flat_rows:
            rows.append([k_str, v_str])

        tbl = TableBlock(
            page_num=1,
            bbox=BoundingBox(0, 0, 400, len(rows) * 20.0),
            rows=rows,
            title=f"{doc_title} TOML 配置表",
            extraction_engine="toml_parser",
        )
        tables.append(tbl)

        sec = TextSection(
            title=doc_title,
            content=f"TOML 车辆参数配置包含 {len(flat_rows)} 项配置。",
            level=1,
            page_num=1,
            breadcrumb_path=[doc_title],
        )
        sections.append(sec)

        return ParsedDocument(
            title=doc_title,
            sections=sections,
            tables=tables,
            pages=1,
            raw_text=content,
            metadata={"format": "toml"},
        )

    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedDocument:
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        doc_title = file_path.stem.replace("_", " ")

        # Read text with multi-encoding fallback
        raw_bytes = file_path.read_bytes()
        if not raw_bytes.strip():
            return ParsedDocument(
                title=doc_title,
                raw_text="",
                metadata={"format": suffix.lstrip("."), "is_empty": True},
            )

        content = ""
        for enc in [
            "utf-8-sig",
            "utf-8",
            "gb18030",
            "gbk",
            "gb2312",
            "utf-16",
            "utf-16-le",
            "utf-16-be",
            "latin1",
        ]:
            try:
                content = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if not content and raw_bytes:
            content = raw_bytes.decode("utf-8", errors="replace")

        if suffix in [".md", ".markdown"]:
            return self._parse_markdown(content, doc_title)
        elif suffix in [".html", ".htm"]:
            return self._parse_html(content, doc_title)
        elif suffix == ".json":
            return self._parse_json(content, doc_title)
        elif suffix == ".toml":
            return self._parse_toml(content, doc_title)
        elif suffix == ".rtf":
            # 1. Decode \uN? unicode escapes (handles signed 16-bit negative values)
            def replace_u(match):
                num = int(match.group(1))
                if num < 0:
                    num += 65536
                try:
                    return chr(num)
                except Exception:
                    return ""

            decoded = re.sub(r"\\u(-?\d+)\??", replace_u, content)

            # 2. Decode \'xx hex characters
            def replace_hex(match):
                try:
                    return bytes.fromhex(match.group(1)).decode("gbk", errors="ignore")
                except Exception:
                    return ""

            decoded = re.sub(r"\\'([0-9a-fA-F]{2})", replace_hex, decoded)

            # 3. Strip RTF control words and braces
            clean_text = re.sub(r"\\[a-z0-9\-]+ ?", " ", decoded)
            clean_text = re.sub(r"[{}]", "", clean_text).strip()
            clean_text = "\n".join(ln.strip() for ln in clean_text.split("\n") if ln.strip())
            sec = TextSection(title=doc_title, content=clean_text, level=1, page_num=1)
            return ParsedDocument(
                title=doc_title,
                sections=[sec],
                pages=1,
                raw_text=clean_text,
                metadata={"format": "rtf"},
            )
        else:
            # Plain text
            sec = TextSection(title=doc_title, content=content, level=1, page_num=1)
            return ParsedDocument(
                title=doc_title,
                sections=[sec],
                pages=1,
                raw_text=content,
                metadata={"format": "text"},
            )


# ── PDF Parser Adapter ───────────────────────────────────────────────────


class PdfParserAdapter(BaseFormatParser):
    """Adapter forwarding PDF files to LayoutAwareParser."""

    def can_parse(self, file_path: Path, format_type: DocumentFormat) -> bool:
        return format_type == DocumentFormat.PDF or file_path.suffix.lower() == ".pdf"

    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedDocument:
        from src.ingestion.layout_parser import LayoutAwareParser

        file_path = Path(file_path)
        engine_type = kwargs.get("engine_type", "hybrid")
        parser = LayoutAwareParser(engine_type=engine_type)
        return parser.parse(file_path)


# ── Unified Multi-Format Parser (Registry & Factory) ─────────────────────


class MultiFormatParser:
    """
    Unified enterprise document parser factory & registry:
    - Autodetects MIME type, file magic bytes, and file extension
    - Routes to specialized parsers for Excel, Word, PPTX, Images, CSV/TSV, Structured Text, and PDF
    - Returns standardized ParsedDocument, TableBlock, and TextSection objects
    """

    def __init__(self, ocr_engine: Optional[BaseOCREngine] = None):
        self.ocr_engine = ocr_engine or get_ocr_engine()
        self._parsers: Dict[DocumentFormat, BaseFormatParser] = {}
        self._register_default_parsers()

    def _register_default_parsers(self) -> None:
        """Register built-in format parsers."""
        self._parsers[DocumentFormat.EXCEL] = ExcelParser()
        self._parsers[DocumentFormat.CSV] = CsvTsvParser()
        self._parsers[DocumentFormat.TSV] = CsvTsvParser()
        self._parsers[DocumentFormat.WORD] = WordParser()
        self._parsers[DocumentFormat.POWERPOINT] = PowerPointParser()
        self._parsers[DocumentFormat.IMAGE] = ImageParser(ocr_engine=self.ocr_engine)
        self._parsers[DocumentFormat.TEXT] = StructuredTextParser()
        self._parsers[DocumentFormat.MARKDOWN] = StructuredTextParser()
        self._parsers[DocumentFormat.HTML] = StructuredTextParser()
        self._parsers[DocumentFormat.JSON] = StructuredTextParser()
        self._parsers[DocumentFormat.TOML] = StructuredTextParser()
        self._parsers[DocumentFormat.RTF] = StructuredTextParser()
        self._parsers[DocumentFormat.PDF] = PdfParserAdapter()

    def register_parser(self, fmt: DocumentFormat, parser: BaseFormatParser) -> None:
        """Register or override a custom parser for a document format."""
        self._parsers[fmt] = parser

    def detect_format(self, file_path: Union[str, Path]) -> DocumentFormat:
        """
        Inspect magic bytes and file extension to accurately detect file format.
        """
        p = Path(file_path)
        if not p.exists():
            return DocumentFormat.UNKNOWN

        # Inspect first 16 bytes for magic signatures
        magic = b""
        try:
            with open(p, "rb") as f:
                magic = f.read(16)
        except Exception:
            pass

        # 1. PDF
        if magic.startswith(b"%PDF"):
            return DocumentFormat.PDF

        # 2. Images
        if magic.startswith(b"\x89PNG\r\n\x1a\n"):
            return DocumentFormat.IMAGE
        if magic.startswith(b"\xff\xd8\xff"):
            return DocumentFormat.IMAGE
        if magic.startswith(b"RIFF") and len(magic) >= 12 and magic[8:12] == b"WEBP":
            return DocumentFormat.IMAGE
        if magic.startswith(b"BM"):
            return DocumentFormat.IMAGE

        # 3. ZIP-based Office Open XML formats (PK\x03\x04)
        if magic.startswith(b"PK\x03\x04"):
            suffix = p.suffix.lower()
            if suffix in [".docx", ".docm"]:
                return DocumentFormat.WORD
            if suffix in [".pptx", ".pptm"]:
                return DocumentFormat.POWERPOINT
            if suffix in [".xlsx", ".xlsm", ".xltx"]:
                return DocumentFormat.EXCEL
            # Inspect internal structure of zip
            try:
                with zipfile.ZipFile(str(p), "r") as zf:
                    namelist = zf.namelist()
                    if any(name.startswith("word/") for name in namelist):
                        return DocumentFormat.WORD
                    if any(name.startswith("ppt/") for name in namelist):
                        return DocumentFormat.POWERPOINT
                    if any(name.startswith("xl/") for name in namelist):
                        return DocumentFormat.EXCEL
            except Exception:
                pass

        # 4. Legacy OLE2 compound files (\xd0\xcf\x11\xe0)
        if magic.startswith(b"\xd0\xcf\x11\xe0"):
            suffix = p.suffix.lower()
            if suffix == ".doc":
                return DocumentFormat.WORD
            if suffix == ".ppt":
                return DocumentFormat.POWERPOINT
            if suffix == ".xls":
                return DocumentFormat.EXCEL

        # 5. Extension-based fallback
        suffix = p.suffix.lower()
        ext_map = {
            ".pdf": DocumentFormat.PDF,
            ".xlsx": DocumentFormat.EXCEL,
            ".xls": DocumentFormat.EXCEL,
            ".xlsm": DocumentFormat.EXCEL,
            ".csv": DocumentFormat.CSV,
            ".tsv": DocumentFormat.TSV,
            ".docx": DocumentFormat.WORD,
            ".doc": DocumentFormat.WORD,
            ".pptx": DocumentFormat.POWERPOINT,
            ".ppt": DocumentFormat.POWERPOINT,
            ".png": DocumentFormat.IMAGE,
            ".jpg": DocumentFormat.IMAGE,
            ".jpeg": DocumentFormat.IMAGE,
            ".webp": DocumentFormat.IMAGE,
            ".bmp": DocumentFormat.IMAGE,
            ".txt": DocumentFormat.TEXT,
            ".md": DocumentFormat.MARKDOWN,
            ".markdown": DocumentFormat.MARKDOWN,
            ".html": DocumentFormat.HTML,
            ".htm": DocumentFormat.HTML,
            ".json": DocumentFormat.JSON,
            ".toml": DocumentFormat.TOML,
            ".rtf": DocumentFormat.RTF,
        }
        return ext_map.get(suffix, DocumentFormat.TEXT)

    def parse(self, file_path: Union[str, Path], **kwargs) -> ParsedDocument:
        """
        Main entry point: autodetects format, selects parser, and executes parsing.
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Document file does not exist: {p}")

        fmt = self.detect_format(p)
        parser = self._parsers.get(fmt)

        if not parser:
            logger.warning(f"No dedicated parser for format '{fmt}'; using StructuredTextParser.")
            parser = self._parsers[DocumentFormat.TEXT]

        doc = parser.parse(p, **kwargs)
        if not doc.metadata.get("format"):
            doc.metadata["format"] = fmt.value

        # Infer vehicle model if not set or default
        if not doc.vehicle_model or doc.vehicle_model == doc.title:
            doc.vehicle_model = infer_automotive_vehicle_model(
                p, doc.title, doc.raw_text[:300] if doc.raw_text else ""
            )

        return doc


# Type alias for external API parity
MultiFormatDocumentParser = MultiFormatParser

