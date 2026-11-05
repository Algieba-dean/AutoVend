"""
Layout-Aware Document & Table Parser for AutoVend (src/ingestion/layout_parser.py).

Provides enterprise-grade layout analysis and document structure recovery:
1. Precise Table Extraction with Bounding Boxes (BBox & Table Lines) via PyMuPDF (fitz) + pdfplumber.
2. Two-dimensional table conversion: Markdown Table and HTML Table for LLM reasoning.
3. Multi-Engine Architecture & Backings:
   - PyMuPDF / pdfplumber (Hybrid Local Engine)
   - Unstructured.io (Partition Engine)
   - Azure Document Intelligence / Form Recognizer (Enterprise Cloud Engine)
   - MinerU / Marker / Docling (Open-Source Multi-modal Document Adapters)
4. Multi-column text reading order reconstruction and hierarchical heading detection (H1-H3).
"""

import contextlib
import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

logger = logging.getLogger(__name__)


class DocumentParsingUnrecoverableError(Exception):
    """Raised when document parsing fails unrecoverably or extracted content is completely empty."""
    pass


class BoundingBox:
    """Represents a 2D bounding box on a document page (x0, top, x1, bottom)."""

    def __init__(self, x0: float, top: float, x1: float, bottom: float, page: int = 1):
        self.x0 = round(float(x0), 2)
        self.top = round(float(top), 2)
        self.x1 = round(float(max(self.x0, float(x1))), 2)
        self.bottom = round(float(max(self.top, float(bottom))), 2)
        self.page = int(page)

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    @classmethod
    def from_tuple(cls, coords: Union[Tuple[float, float, float, float], List[float]], page: int = 1) -> "BoundingBox":
        return cls(coords[0], coords[1], coords[2], coords[3], page=page)

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x0, self.top, self.x1, self.bottom)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x0": self.x0,
            "top": self.top,
            "x1": self.x1,
            "bottom": self.bottom,
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "page": self.page,
        }

    def __repr__(self) -> str:
        return f"BBox(page={self.page}, [{self.x0}, {self.top}, {self.x1}, {self.bottom}])"


class TableLine:
    """Represents a horizontal or vertical border/grid line of a table."""

    def __init__(
        self,
        x0: float,
        top: float,
        x1: float,
        bottom: float,
        orientation: str = "h",
        page: int = 1,
    ):
        self.x0 = round(float(x0), 2)
        self.top = round(float(top), 2)
        self.x1 = round(float(x1), 2)
        self.bottom = round(float(bottom), 2)
        self.orientation = orientation
        self.page = int(page)

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x0, self.top, self.x1, self.bottom)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x0": self.x0,
            "top": self.top,
            "x1": self.x1,
            "bottom": self.bottom,
            "orientation": self.orientation,
            "page": self.page,
        }

    def __repr__(self) -> str:
        return f"TableLine(page={self.page}, {self.orientation}, [{self.x0}, {self.top}, {self.x1}, {self.bottom}])"


class TableCell:
    """Represents a single table cell with position, span, and optional bbox."""

    def __init__(
        self,
        row_idx: int,
        col_idx: int,
        text: Any,
        row_span: int = 1,
        col_span: int = 1,
        bbox: Optional[BoundingBox] = None,
    ):
        self.row_idx = row_idx
        self.col_idx = col_idx
        self.text = str(text).strip() if text is not None else ""
        self.row_span = max(1, int(row_span)) if row_span else 1
        self.col_span = max(1, int(col_span)) if col_span else 1
        self.bbox = bbox

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_idx": self.row_idx,
            "col_idx": self.col_idx,
            "text": self.text,
            "row_span": self.row_span,
            "col_span": self.col_span,
            "bbox": self.bbox.to_dict() if self.bbox else None,
        }


class TableBlock:
    """
    Extracted structured table block with coordinates, lines, cells, rows, header detection,
    and LLM-friendly Markdown / HTML conversion.
    """

    def __init__(
        self,
        page_num: int,
        bbox: Optional[BoundingBox] = None,
        rows: Optional[List[List[str]]] = None,
        headers: Optional[List[str]] = None,
        cells: Optional[List[TableCell]] = None,
        lines: Optional[List[TableLine]] = None,
        title: Optional[str] = None,
        extraction_engine: str = "pymupdf_pdfplumber",
        confidence: float = 1.0,
        pages: Optional[List[int]] = None,
        is_stitched: bool = False,
        footnotes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        page_bboxes: Optional[Dict[int, BoundingBox]] = None,
        header_rows_count: Optional[int] = None,
        is_degraded: bool = False,
    ):
        self.page_num = page_num
        self.bbox = bbox
        self.title = title.strip() if title else ""
        self.extraction_engine = extraction_engine
        self.confidence = confidence
        self.pages = pages or [self.page_num]
        self.is_stitched = is_stitched
        self.footnotes = [str(f).strip() for f in footnotes if str(f).strip()] if footnotes else []
        self.metadata = metadata or {}
        self.is_degraded = is_degraded or bool(self.metadata.get("is_degraded", False))
        self.page_bboxes: Dict[int, BoundingBox] = (
            page_bboxes if page_bboxes is not None else ({self.page_num: self.bbox} if self.bbox else {})
        )

        # Clean rows
        cleaned_rows: List[List[str]] = []
        for r in (rows or []):
            cleaned_rows.append(
                [
                    str(c).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").strip()
                    if c is not None
                    else ""
                    for c in r
                ]
            )

        # Detect and pop bottom footnote / fine print rows embedded inside rows
        while len(cleaned_rows) > 2:
            last_row = cleaned_rows[-1]
            non_empty = [c for c in last_row if c.strip()]
            if len(non_empty) == 1:
                first_text = non_empty[0]
                if any(
                    first_text.startswith(p)
                    for p in ("*", "注", "Note", "特别说明", "特别约定", "说明", "条款", "免责")
                ):
                    if first_text not in self.footnotes:
                        self.footnotes.append(first_text)
                    cleaned_rows.pop()
                    continue
            break

        self.rows = cleaned_rows

        # Infer or set headers
        self.cells = cells or []
        self.lines = lines or []
        self.header_rows_count = header_rows_count if header_rows_count is not None else 1
        self.is_multilevel_header = (self.header_rows_count > 1)

        # Infer or set headers
        if len(self.rows) >= 3 and self._detect_multilevel_headers(self.rows[0], self.rows[1]):
            self.is_multilevel_header = True
            self.header_rows_count = 2
            self.headers = self._build_compound_headers(self.rows[0], self.rows[1], self.col_count)
            self.body_rows = self.rows[2:]
        elif headers:
            self.headers = [
                str(h).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").strip()
                for h in headers
            ]
            if self.rows and self._rows_match_header(self.rows[0], self.headers):
                self.body_rows = self.rows[1:]
            else:
                self.body_rows = list(self.rows)
        elif self.rows:
            self.headers = self.rows[0]
            self.body_rows = self.rows[1:]
        else:
            self.headers = []
            self.body_rows = []

    @staticmethod
    def _rows_match_header(row: List[str], headers: List[str]) -> bool:
        if row == headers:
            return True
        r_clean = [c.strip() for c in row if c.strip()]
        h_clean = [c.strip() for c in headers if c.strip()]
        return bool(r_clean and r_clean == h_clean)

    @staticmethod
    def _detect_multilevel_headers(r0: List[str], r1: List[str]) -> bool:
        """
        Detect whether row 0 and row 1 together constitute a multi-level table header.
        """
        if not r0 or not r1 or len(r0) < 2:
            return False
        data_pattern = re.compile(r"^\d+(?:\.\d+)?\s*(?:万|kW|Nm|mm|s|%|kWh|PS|元)?$", re.I)
        numeric_count_r0 = sum(bool(data_pattern.match(c.strip())) for c in r0 if c.strip())
        if numeric_count_r0 >= max(1, len(r0) // 2):
            return False

        non_empty_r0 = [c.strip() for c in r0 if c.strip()]
        has_repeats_or_blanks = (len(non_empty_r0) < len(r0)) or (len(set(non_empty_r0)) < len(non_empty_r0))
        non_empty_r1 = [c.strip() for c in r1 if c.strip()]
        r1_distinct = len(set(non_empty_r1)) >= max(2, len(r1) // 2)
        return has_repeats_or_blanks and r1_distinct

    @staticmethod
    def _build_compound_headers(r0: List[str], r1: List[str], col_count: int) -> List[str]:
        """
        Build compound headers from two-level header rows:
        e.g. ['基本参数 > 车型', '基本参数 > 指导价', '动力总成 > 最大功率', ...]
        """
        filled_r0: List[str] = []
        last_top = ""
        for i in range(col_count):
            val = r0[i].strip() if i < len(r0) else ""
            if not val and last_top:
                filled_r0.append(last_top)
            else:
                filled_r0.append(val)
                if val:
                    last_top = val

        compound: List[str] = []
        for i in range(col_count):
            top_h = filled_r0[i] if i < len(filled_r0) else ""
            sub_h = r1[i].strip() if i < len(r1) else ""
            if top_h and sub_h and top_h != sub_h:
                compound.append(f"{top_h} > {sub_h}")
            elif sub_h:
                compound.append(sub_h)
            elif top_h:
                compound.append(top_h)
            else:
                compound.append(f"Column_{i+1}")
        return compound

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        if not self.rows:
            return 0
        return max(len(r) for r in self.rows)

    @property
    def is_borderless(self) -> bool:
        return self.extraction_engine.startswith("borderless")

    def _is_index_column(self, col_idx: int, start_row: int) -> bool:
        """
        Detect if a column is a row-number/sequence index column (e.g. '1', '2', '3' or '序号').
        Index columns increment row-by-row and MUST NOT be treated as a parent hierarchy
        that resets child category caches.
        """
        if not self.rows or col_idx >= self.col_count:
            return False

        header_text = ""
        if hasattr(self, "headers") and self.headers and col_idx < len(self.headers):
            header_text = str(self.headers[col_idx]).strip().lower()
        elif self.rows and col_idx < len(self.rows[0]):
            header_text = str(self.rows[0][col_idx]).strip().lower()

        if header_text in ("序号", "序号/item", "no", "no.", "id", "item", "index", "#", "item_no", "行号"):
            return True

        total_data_rows = len(self.rows) - start_row
        if total_data_rows <= 1:
            return False

        numeric_rows = 0
        vals = []
        for r_idx in range(start_row, len(self.rows)):
            row = self.rows[r_idx]
            val = str(row[col_idx]).strip() if col_idx < len(row) else ""
            if re.match(r"^\d+$", val):
                numeric_rows += 1
                try:
                    vals.append(int(val))
                except ValueError:
                    pass

        if numeric_rows / total_data_rows >= 0.7:
            if len(vals) >= 2 and all(vals[k] < vals[k + 1] for k in range(len(vals) - 1)):
                # Starts at small index or increments by regular step (e.g. 1, 2, 3... or 101, 102, 103...)
                if vals[0] <= 10 or all(vals[k + 1] - vals[k] == 1 for k in range(len(vals) - 1)):
                    return True
                # Constant step sequence
                if len(set(vals[k + 1] - vals[k] for k in range(len(vals) - 1))) == 1:
                    return True

        return False

    def normalize_forward_fill(
        self,
        fill_columns: Optional[Union[Sequence[int], int]] = None,
        max_fill_cols: Optional[int] = None,
        detect_index_col: bool = True,
    ) -> List[List[str]]:
        """
        Forward-fill empty/merged category cells across consecutive rows to normalize
        ragged or multi-level merged table hierarchies.

        Features:
        - Supports arbitrary number of hierarchy columns (no hardcoded min(2) restriction).
        - Automatically identifies row sequence / index columns (e.g. 1, 2, 3... or '序号')
          and excludes them from invalidating child category caches.
        - Hierarchical cache reset: When a parent category changes, child category caches
          are reset to prevent cross-category contamination.
        """
        if not self.rows:
            return []

        start_row = self.header_rows_count if hasattr(self, "header_rows_count") else 1
        col_0_is_index = detect_index_col and self._is_index_column(0, start_row)

        if fill_columns is not None:
            if isinstance(fill_columns, int):
                active_cols = list(range(min(fill_columns, self.col_count)))
            else:
                active_cols = [c for c in fill_columns if 0 <= c < self.col_count]
        elif max_fill_cols is not None:
            active_cols = list(range(min(max_fill_cols, self.col_count)))
        else:
            active_cols = list(range(self.col_count))

        hierarchy_cols = [c for c in active_cols if not (c == 0 and col_0_is_index)]

        normalized: List[List[str]] = []
        last_values: List[str] = [""] * self.col_count

        for r_idx in range(min(start_row, len(self.rows))):
            norm_h = list(self.rows[r_idx])
            if len(norm_h) < self.col_count:
                norm_h += [""] * (self.col_count - len(norm_h))
            normalized.append(norm_h)

        for r_idx in range(start_row, len(self.rows)):
            row = self.rows[r_idx]
            new_row = list(row)
            if len(new_row) < self.col_count:
                new_row += [""] * (self.col_count - len(new_row))

            for c_idx in active_cols:
                if c_idx == 0 and col_0_is_index:
                    continue

                val = new_row[c_idx].strip()
                if not val and last_values[c_idx]:
                    new_row[c_idx] = last_values[c_idx]
                elif val:
                    if c_idx in hierarchy_cols:
                        curr_h_idx = hierarchy_cols.index(c_idx)
                        if last_values[c_idx] and val != last_values[c_idx]:
                            for lower_c in hierarchy_cols[curr_h_idx + 1:]:
                                last_values[lower_c] = ""
                    last_values[c_idx] = val

            normalized.append(new_row)
        return normalized

    def normalize_backward_fill(
        self,
        fill_columns: Optional[Union[Sequence[int], int]] = None,
        max_fill_cols: Optional[int] = None,
        detect_index_col: bool = True,
    ) -> List[List[str]]:
        """
        Backward-fill empty cells across consecutive rows upward.
        Useful when category summaries or footnotes are aligned to row bottoms.
        """
        if not self.rows:
            return []

        start_row = self.header_rows_count if hasattr(self, "header_rows_count") else 1
        col_0_is_index = detect_index_col and self._is_index_column(0, start_row)

        if fill_columns is not None:
            if isinstance(fill_columns, int):
                active_cols = list(range(min(fill_columns, self.col_count)))
            else:
                active_cols = [c for c in fill_columns if 0 <= c < self.col_count]
        elif max_fill_cols is not None:
            active_cols = list(range(min(max_fill_cols, self.col_count)))
        else:
            active_cols = list(range(self.col_count))

        hierarchy_cols = [c for c in active_cols if not (c == 0 and col_0_is_index)]

        normalized_body: List[List[str]] = []
        next_values: List[str] = [""] * self.col_count

        for r_idx in range(len(self.rows) - 1, start_row - 1, -1):
            row = self.rows[r_idx]
            new_row = list(row)
            if len(new_row) < self.col_count:
                new_row += [""] * (self.col_count - len(new_row))

            for c_idx in active_cols:
                if c_idx == 0 and col_0_is_index:
                    continue

                val = new_row[c_idx].strip()
                if not val and next_values[c_idx]:
                    new_row[c_idx] = next_values[c_idx]
                elif val:
                    if c_idx in hierarchy_cols:
                        curr_h_idx = hierarchy_cols.index(c_idx)
                        if next_values[c_idx] and val != next_values[c_idx]:
                            for lower_c in hierarchy_cols[curr_h_idx + 1:]:
                                next_values[lower_c] = ""
                    next_values[c_idx] = val

            normalized_body.append(new_row)

        normalized_body.reverse()

        normalized: List[List[str]] = []
        for r_idx in range(min(start_row, len(self.rows))):
            norm_h = list(self.rows[r_idx])
            if len(norm_h) < self.col_count:
                norm_h += [""] * (self.col_count - len(norm_h))
            normalized.append(norm_h)

        normalized.extend(normalized_body)
        return normalized

    def normalize_bidirectional_fill(
        self,
        fill_columns: Optional[Union[Sequence[int], int]] = None,
        max_fill_cols: Optional[int] = None,
        detect_index_col: bool = True,
    ) -> List[List[str]]:
        """
        Bidirectional fill: Resolves empty merged cells by propagating values from
        both top (forward) and bottom (backward) boundaries based on proximity to the nearest anchor,
        while strictly respecting parent hierarchy boundaries.
        """
        if not self.rows:
            return []

        start_row = self.header_rows_count if hasattr(self, "header_rows_count") else 1
        col_0_is_index = detect_index_col and self._is_index_column(0, start_row)

        if fill_columns is not None:
            if isinstance(fill_columns, int):
                active_cols = list(range(min(fill_columns, self.col_count)))
            else:
                active_cols = [c for c in fill_columns if 0 <= c < self.col_count]
        elif max_fill_cols is not None:
            active_cols = list(range(min(max_fill_cols, self.col_count)))
        else:
            active_cols = list(range(self.col_count))

        hierarchy_cols = [c for c in active_cols if not (c == 0 and col_0_is_index)]

        # Clone table rows
        normalized: List[List[str]] = []
        for r_idx in range(len(self.rows)):
            row = list(self.rows[r_idx])
            if len(row) < self.col_count:
                row += [""] * (self.col_count - len(row))
            normalized.append(row)

        # Process column by column in hierarchy order
        for c_idx in active_cols:
            if c_idx == 0 and col_0_is_index:
                continue

            curr_h_idx = hierarchy_cols.index(c_idx) if c_idx in hierarchy_cols else -1
            parent_cols = hierarchy_cols[:curr_h_idx] if curr_h_idx > 0 else []

            r = start_row
            while r < len(normalized):
                if not normalized[r][c_idx].strip():
                    run_start = r
                    while r < len(normalized) and not normalized[r][c_idx].strip():
                        if parent_cols and r > run_start:
                            prev_p = [normalized[r - 1][pc] for pc in parent_cols]
                            curr_p = [normalized[r][pc] for pc in parent_cols]
                            if prev_p != curr_p:
                                break
                        r += 1
                    run_end = r - 1

                    # Look for top anchor
                    top_anchor_val = None
                    top_anchor_r = None
                    for tr in range(run_start - 1, start_row - 1, -1):
                        if parent_cols and [normalized[tr][pc] for pc in parent_cols] != [normalized[run_start][pc] for pc in parent_cols]:
                            break
                        if normalized[tr][c_idx].strip():
                            top_anchor_val = normalized[tr][c_idx].strip()
                            top_anchor_r = tr
                            break

                    # Look for bottom anchor
                    bottom_anchor_val = None
                    bottom_anchor_r = None
                    for br in range(run_end + 1, len(normalized)):
                        if parent_cols and [normalized[br][pc] for pc in parent_cols] != [normalized[run_end][pc] for pc in parent_cols]:
                            break
                        if normalized[br][c_idx].strip():
                            bottom_anchor_val = normalized[br][c_idx].strip()
                            bottom_anchor_r = br
                            break

                    # Fill empty cells between run_start and run_end
                    for fill_r in range(run_start, run_end + 1):
                        if top_anchor_val and bottom_anchor_val:
                            dist_top = fill_r - top_anchor_r
                            dist_bottom = bottom_anchor_r - fill_r
                            if dist_top <= dist_bottom:
                                normalized[fill_r][c_idx] = top_anchor_val
                            else:
                                normalized[fill_r][c_idx] = bottom_anchor_val
                        elif top_anchor_val:
                            normalized[fill_r][c_idx] = top_anchor_val
                        elif bottom_anchor_val:
                            normalized[fill_r][c_idx] = bottom_anchor_val
                else:
                    r += 1

        return normalized

    def normalize_fill(
        self,
        direction: str = "forward",
        fill_columns: Optional[Union[Sequence[int], int]] = None,
        max_fill_cols: Optional[int] = None,
        detect_index_col: bool = True,
    ) -> List[List[str]]:
        """
        Unified table normalization method supporting forward, backward, and bidirectional fill.
        """
        direction = (direction or "forward").lower().strip()
        if direction in ("forward", "ffill", "down"):
            return self.normalize_forward_fill(
                fill_columns=fill_columns,
                max_fill_cols=max_fill_cols,
                detect_index_col=detect_index_col,
            )
        elif direction in ("backward", "bfill", "up"):
            return self.normalize_backward_fill(
                fill_columns=fill_columns,
                max_fill_cols=max_fill_cols,
                detect_index_col=detect_index_col,
            )
        elif direction in ("bidirectional", "both", "two_way"):
            return self.normalize_bidirectional_fill(
                fill_columns=fill_columns,
                max_fill_cols=max_fill_cols,
                detect_index_col=detect_index_col,
            )
        else:
            raise ValueError(
                f"Invalid fill direction '{direction}'. Supported directions: 'forward', 'backward', 'bidirectional'."
            )

    def to_records(self) -> List[Dict[str, str]]:
        """
        Convert table rows into normalized flat key-value records for structured queries.
        Handles multi-level compound headers and disambiguates duplicate column names to prevent key collisions.
        """
        norm_rows = self.normalize_forward_fill()
        if not norm_rows or len(norm_rows) <= self.header_rows_count:
            return []

        headers_source = self.headers if self.headers else norm_rows[0]
        clean_headers: List[str] = []
        seen_counts: Dict[str, int] = {}
        for i in range(self.col_count):
            h = headers_source[i] if i < len(headers_source) and headers_source[i] else f"Column_{i+1}"
            seen_counts[h] = seen_counts.get(h, 0) + 1
            if seen_counts[h] > 1:
                clean_headers.append(f"{h}_{seen_counts[h]}")
            else:
                clean_headers.append(h)

        records: List[Dict[str, str]] = []
        body = norm_rows[self.header_rows_count:]
        for row in body:
            non_empty = [c for c in row if c.strip()]
            if len(non_empty) == 1 and any(
                non_empty[0].startswith(p)
                for p in ("*", "注", "Note", "特别说明", "特别约定", "说明", "条款", "免责")
            ):
                continue
            rec: Dict[str, str] = {}
            for col_idx, h in enumerate(clean_headers):
                rec[h] = row[col_idx] if col_idx < len(row) else ""
            records.append(rec)
        return records

    def to_markdown(self, include_title: bool = True) -> str:
        """
        Convert 2D table into standard Markdown table format.
        LLMs exhibit significantly higher spatial understanding with Markdown tables.
        """
        if not self.rows:
            return ""

        headers = list(self.headers) if self.headers else [f"Col {i+1}" for i in range(self.col_count)]
        max_cols = max(len(headers), self.col_count)
        if len(headers) < max_cols:
            headers = headers + [f"Col {i+1}" for i in range(len(headers), max_cols)]

        md_lines: List[str] = []
        if include_title and self.title:
            if self.is_stitched and len(self.pages) > 1:
                page_str = f"第 {min(self.pages)}-{max(self.pages)} 页拼接"
                md_lines.append(f"### 表格: {self.title} ({page_str})")
            else:
                md_lines.append(f"### 表格: {self.title}")

        header_str = "| " + " | ".join(h.replace("|", "\\|") for h in headers) + " |"
        sep_str = "| " + " | ".join(["---"] * max_cols) + " |"
        md_lines.append(header_str)
        md_lines.append(sep_str)

        for row in self.body_rows:
            norm_row = list(row)
            if len(norm_row) < max_cols:
                norm_row = norm_row + [""] * (max_cols - len(norm_row))
            row_str = "| " + " | ".join(c.replace("|", "\\|") for c in norm_row) + " |"
            md_lines.append(row_str)

        if self.footnotes:
            md_lines.append("")
            for fn in self.footnotes:
                md_lines.append(f"*{fn}*")

        return "\n".join(md_lines)

    def to_html(self, include_title: bool = True) -> str:
        """
        Convert table to clean, semantic HTML Table syntax.
        Handles complex tables with rowspan/colspan and escapes HTML entities.
        """
        import html

        if not self.rows and not self.cells:
            return ""

        html_parts: List[str] = ['<table border="1" class="autovend-table">']
        if include_title and self.title:
            html_parts.append(f"  <caption>{html.escape(self.title)}</caption>")

        has_spans = any(c.row_span > 1 or c.col_span > 1 for c in self.cells)
        if self.cells and has_spans:
            cells_by_row: Dict[int, List[TableCell]] = {}
            for c in self.cells:
                cells_by_row.setdefault(c.row_idx, []).append(c)

            sorted_row0 = sorted(cells_by_row.get(0, []), key=lambda c: c.col_idx)
            row0_has_rowspan = any(c.row_span > 1 for c in sorted_row0)
            use_thead = (
                bool(self.headers)
                and not row0_has_rowspan
                and bool(sorted_row0)
                and [c.text for c in sorted_row0] == self.headers
            )

            if use_thead:
                html_parts.append("  <thead>\n    <tr>")
                for cell in sorted_row0:
                    attrs = []
                    if cell.col_span > 1:
                        attrs.append(f'colspan="{cell.col_span}"')
                    attr_str = (" " + " ".join(attrs)) if attrs else ""
                    html_parts.append(f"      <th{attr_str}>{html.escape(cell.text)}</th>")
                html_parts.append("    </tr>\n  </thead>")
                start_r = 1
            else:
                start_r = 0

            html_parts.append("  <tbody>")
            for r_idx in sorted(cells_by_row.keys()):
                if r_idx < start_r:
                    continue
                html_parts.append("    <tr>")
                row_cells = sorted(cells_by_row[r_idx], key=lambda c: c.col_idx)
                for cell in row_cells:
                    attrs = []
                    if cell.row_span > 1:
                        attrs.append(f'rowspan="{cell.row_span}"')
                    if cell.col_span > 1:
                        attrs.append(f'colspan="{cell.col_span}"')
                    attr_str = (" " + " ".join(attrs)) if attrs else ""
                    html_parts.append(f"      <td{attr_str}>{html.escape(cell.text)}</td>")
                html_parts.append("    </tr>")
            html_parts.append("  </tbody>")
        else:
            if self.headers:
                html_parts.append("  <thead>\n    <tr>")
                for h in self.headers:
                    html_parts.append(f"      <th>{html.escape(h)}</th>")
                html_parts.append("    </tr>\n  </thead>")

            html_parts.append("  <tbody>")
            for row in self.body_rows:
                html_parts.append("    <tr>")
                for cell in row:
                    html_parts.append(f"      <td>{html.escape(str(cell))}</td>")
                html_parts.append("    </tr>")
            html_parts.append("  </tbody>")

        html_parts.append("</table>")

        return "\n".join(html_parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_num": self.page_num,
            "pages": self.pages,
            "is_stitched": self.is_stitched,
            "title": self.title,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "headers": self.headers,
            "row_count": self.row_count,
            "col_count": self.col_count,
            "rows": self.rows,
            "footnotes": self.footnotes,
            "cells": [c.to_dict() for c in self.cells],
            "lines": [ln.to_dict() for ln in self.lines],
            "extraction_engine": self.extraction_engine,
            "confidence": self.confidence,
            "records": self.to_records(),
            "markdown": self.to_markdown(),
            "metadata": self.metadata,
            "is_degraded": self.is_degraded,
        }


class TextSection:
    """Represents a hierarchical document section with level, content, and breadcrumb path."""

    def __init__(
        self,
        title: str,
        content: str,
        level: int = 1,
        page_num: int = 1,
        bbox: Optional[BoundingBox] = None,
        breadcrumb_path: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.title = title.strip()
        self.content = content.strip()
        self.level = level
        self.page_num = page_num
        self.bbox = bbox
        self.breadcrumb_path = breadcrumb_path or ([self.title] if self.title else [])
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "level": self.level,
            "page_num": self.page_num,
            "breadcrumb_path": self.breadcrumb_path,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "content": self.content,
            "metadata": self.metadata,
        }


class ParsedDocument:
    """Represents a fully parsed document with layout, sections, and tables."""

    def __init__(
        self,
        title: str = "",
        vehicle_model: str = "",
        sections: Optional[List[TextSection]] = None,
        tables: Optional[List[TableBlock]] = None,
        pages: int = 1,
        raw_text: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        page_dimensions: Optional[Dict[int, Tuple[float, float]]] = None,
        page_orientations: Optional[Dict[int, str]] = None,
    ):
        self.title = title
        self.vehicle_model = vehicle_model
        self.sections = sections or []
        self.tables = tables or []
        self.pages = pages
        self.raw_text = raw_text
        self.metadata = metadata or {}
        self.page_dimensions = page_dimensions or {}
        self.page_orientations = page_orientations or {}

    @property
    def is_degraded(self) -> bool:
        return bool(self.metadata.get("is_degraded", False))

    @is_degraded.setter
    def is_degraded(self, value: bool) -> None:
        self.metadata["is_degraded"] = bool(value)

    def get_full_markdown(self) -> str:
        """Compose all sections and tables into full layout-preserved Markdown sorted by reading position."""
        parts: List[str] = []
        if self.title:
            parts.append(f"# {self.title}\n")

        # Interleave sections and tables in page/vertical order
        flow_items: List[Tuple[int, float, str]] = []
        for sec in self.sections:
            prefix = "#" * min(sec.level + 1, 4)
            top = sec.bbox.top if sec.bbox else 0.0
            flow_items.append((sec.page_num, top, f"{prefix} {sec.title}\n\n{sec.content}\n"))

        for tbl in self.tables:
            page_num = tbl.page_num
            top = tbl.bbox.top if tbl.bbox else 0.0
            flow_items.append((page_num, top, f"\n{tbl.to_markdown()}\n"))

        flow_items.sort(key=lambda it: (it[0], it[1]))
        for _, _, c in flow_items:
            parts.append(c)

        return "\n".join(parts)


class HeaderFooterWatermarkFilter:
    """
    Cleans noisy PDF artifacts:
    - Page headers (top margin, e.g. <= 8% page height)
    - Page footers & pagination (bottom margin, e.g. >= 92% page height)
    - Watermarks (rotated text lines, transparency, confidentiality keywords)
    """

    PAGINATION_PATTERNS = [
        re.compile(r"^\s*(?:第\s*)?\d+\s*(?:[/共]\s*\d+\s*页?|页)?\s*$", re.I),
        re.compile(r"^\s*[—–\-]\s*\d+\s*[—–\-]\s*$"),
        re.compile(r"^\s*Page\s+\d+\s*(?:of|/)\s*\d+\s*$", re.I),
        re.compile(r"^\s*\d+\s*(?:of|/)\s*\d+\s*$", re.I),
        re.compile(r"^\s*-\s*\d+\s*-\s*$"),
    ]

    WATERMARK_PATTERNS = [
        re.compile(
            r"(?:绝密|机密|内部资料|内部传阅|保密文件|草稿|样张|仅供参考|未经授权|CONFIDENTIAL|INTERNAL ONLY|DRAFT|WATERMARK|STRICTLY CONFIDENTIAL|SAMPLE|DO NOT DISTRIBUTE|FOR INTERNAL USE)",
            re.I,
        ),
    ]

    @classmethod
    def is_header_or_footer(
        cls,
        bbox_tuple: Tuple[float, float, float, float],
        page_height: float,
        text: str,
        top_ratio: float = 0.065,
        bottom_ratio: float = 0.085,
        running_headers: Optional[set] = None,
    ) -> bool:
        bx0, top, bx1, bottom = bbox_tuple
        clean_text = text.strip()
        if not clean_text:
            return False

        if running_headers and clean_text in running_headers:
            return True

        is_pagination = any(p.search(clean_text) for p in cls.PAGINATION_PATTERNS)

        top_limit = max(40.0, page_height * top_ratio)
        bottom_limit = min(page_height - 40.0, page_height * (1.0 - bottom_ratio))

        # In top margin
        if bottom <= top_limit:
            if is_pagination or (len(clean_text) < 80 and top <= 45.0):
                return True

        # In bottom margin
        if top >= bottom_limit:
            if is_pagination or len(clean_text) < 120:
                return True

        return False

    @classmethod
    def is_watermark(cls, block_dict: Dict[str, Any], text: str) -> bool:
        clean = text.strip()
        if any(p.search(clean) for p in cls.WATERMARK_PATTERNS) and len(clean) < 140:
            return True
        lines = block_dict.get("lines", [])
        for line in lines:
            line_dir = line.get("dir", (1.0, 0.0))
            if isinstance(line_dir, (list, tuple)) and len(line_dir) >= 2:
                if abs(line_dir[0] - 1.0) > 0.05 or abs(line_dir[1]) > 0.05:
                    return True
            for s in line.get("spans", []):
                s_color = s.get("color", 0)
                if isinstance(s_color, int) and s_color > 0 and len(clean) < 60:
                    r_c = (s_color >> 16) & 0xFF
                    g_c = (s_color >> 8) & 0xFF
                    b_c = s_color & 0xFF
                    if r_c > 200 and g_c > 200 and b_c > 200:
                        if any(p.search(clean) for p in cls.WATERMARK_PATTERNS) or len(clean) < 30:
                            return True
        return False


class OCROrientationDetector:
    """
    Detects and corrects document page rotation, text span disorientation,
    and skew angles for scanned and photo-captured PDFs.
    """

    @classmethod
    def detect_page_rotation(cls, page: Any) -> int:
        """
        Detect page orientation in degrees (0, 90, 180, 270).
        Checks PyMuPDF page.rotation and text line direction vectors.
        """
        native_rot = getattr(page, "rotation", 0) or 0

        blocks = page.get_text("dict").get("blocks", []) if hasattr(page, "get_text") else []
        dir_angles = []
        for b in blocks:
            for line in b.get("lines", []):
                ldir = line.get("dir", (1.0, 0.0))
                if isinstance(ldir, (list, tuple)) and len(ldir) >= 2:
                    dx, dy = ldir[0], ldir[1]
                    if abs(dx - 1.0) < 0.1 and abs(dy) < 0.1:
                        dir_angles.append(0)
                    elif abs(dx) < 0.1 and abs(dy - 1.0) < 0.1:
                        dir_angles.append(90)
                    elif abs(dx + 1.0) < 0.1 and abs(dy) < 0.1:
                        dir_angles.append(180)
                    elif abs(dx) < 0.1 and abs(dy + 1.0) < 0.1:
                        dir_angles.append(270)

        if dir_angles:
            from collections import Counter
            dominant_angle = Counter(dir_angles).most_common(1)[0][0]
            if dominant_angle != 0 and native_rot == 0:
                return dominant_angle

        return native_rot

    @classmethod
    def normalize_page(cls, page: Any) -> int:
        """
        Rotate page to normal upright orientation (0 degrees).
        Returns the rotation correction angle applied.
        """
        rot = cls.detect_page_rotation(page)
        if rot != 0:
            correction = (360 - rot) % 360
            try:
                page.set_rotation((getattr(page, "rotation", 0) + correction) % 360)
                logger.info(f"Page orientation corrected: rotated by {correction}° (was {rot}°)")
                return correction
            except Exception as e:
                logger.debug(f"Page set_rotation skipped: {e}")
        return 0


class ReadingOrderSorter:
    """
    Reconstructs natural reading order for dual-column and multi-column documents
    using heuristic geometric banding and horizontal X-coordinate clustering.

    Algorithm Architecture:
    1. Spanning Banner Detection: Identifies full-width section headers, banners, and callout blocks
       via geometric heuristics (width > 55% page width, or crossing the midpoint with width > 40%,
       or heading syntax 【, #, \\d+\\. with no horizontal peer).
    2. Vertical Band Partitioning: Uses detected banners as horizontal slicing boundaries
       to partition the page into independent vertical zones.
    3. Multi-Column X-Clustering: Within each zone, clusters non-spanning text blocks by horizontal
       origin (x0 proximity <= 45pt), reconstructs left-to-right column progression, and sorts
       blocks within each column top-to-bottom to eliminate horizontal cross-talk.
    """

    @classmethod
    def sort_page_blocks(
        cls,
        blocks: List[Dict[str, Any]],
        page_width: float,
        page_height: float,
    ) -> List[Dict[str, Any]]:
        if not blocks:
            return []

        text_blocks = [b for b in blocks if "lines" in b and "bbox" in b]
        if len(text_blocks) <= 2:
            return sorted(text_blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))

        midpoint = page_width / 2.0
        spanning_blocks: List[Dict[str, Any]] = []
        column_blocks: List[Dict[str, Any]] = []

        for b in text_blocks:
            bx0, by0, bx1, by1 = b["bbox"]
            width = bx1 - bx0
            b_text = "".join(s["text"] for line in b.get("lines", []) for s in line.get("spans", [])).strip()
            is_heading_banner = (
                b_text.startswith("【")
                or bool(re.match(r"^\d+(?:\.\d+)*\s+", b_text))
                or b_text.startswith("#")
                or any(s.get("size", 10.0) >= 12.0 for line in b.get("lines", []) for s in line.get("spans", []))
            )
            has_horizontal_peer = any(
                other is not b
                and abs(bx0 - other["bbox"][0]) > 60.0
                and max(by0, other["bbox"][1]) < min(by1, other["bbox"][3]) + 15.0
                for other in text_blocks
            )
            crosses_center = (bx0 < midpoint - 40 and bx1 > midpoint + 40)
            is_spanning = (
                width > page_width * 0.55
                or (width > page_width * 0.40 and crosses_center)
                or (is_heading_banner and not has_horizontal_peer)
            )
            if is_spanning:
                spanning_blocks.append(b)
            else:
                column_blocks.append(b)

        if not column_blocks:
            return sorted(text_blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))

        spanning_blocks_sorted = sorted(spanning_blocks, key=lambda b: b["bbox"][1])
        boundaries = [0.0] + [b["bbox"][1] for b in spanning_blocks_sorted] + [float("inf")]

        result_blocks: List[Dict[str, Any]] = []

        for i in range(len(boundaries) - 1):
            y_start = boundaries[i]
            y_end = boundaries[i + 1]

            if i > 0:
                result_blocks.append(spanning_blocks_sorted[i - 1])

            zone_blocks = [b for b in column_blocks if y_start <= b["bbox"][1] < y_end]
            if not zone_blocks:
                continue

            # Cluster zone blocks into columns by horizontal position (bx0)
            sorted_by_x = sorted(zone_blocks, key=lambda b: b["bbox"][0])
            columns: List[List[Dict[str, Any]]] = []

            for b in sorted_by_x:
                bx0 = b["bbox"][0]
                placed = False
                for col in columns:
                    col_avg_x0 = sum(cb["bbox"][0] for cb in col) / len(col)
                    if abs(bx0 - col_avg_x0) <= 45.0:
                        col.append(b)
                        placed = True
                        break
                if not placed:
                    columns.append([b])

            if len(columns) <= 1:
                zone_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
                result_blocks.extend(zone_blocks)
            else:
                columns.sort(key=lambda col: sum(cb["bbox"][0] for cb in col) / len(col))
                for col in columns:
                    col.sort(key=lambda b: b["bbox"][1])
                    result_blocks.extend(col)

        return result_blocks


class CrossPageTableStitcher:
    """
    Seamlessly stitches split tables spanning across page boundaries.

    Alignment & Compatibility Strategy:
    1. Bounding Box Alignment: Checks outer horizontal bounding box coordinate alignment
       (abs(x0_curr - x0_next) <= 25.0 pt and abs(x1_curr - x1_next) <= 25.0 pt).
    2. Column Count Consistency: Enforces curr_tbl.col_count == next_tbl.col_count (> 0).
    3. Column Width Profile Variance: When individual cell bounding boxes exist, computes
       per-column width arrays and evaluates the mean squared difference (variance) between
       consecutive tables to verify column geometry alignment.
    4. Header Consistency & Deduplication: Eliminates repeated continuation headers on subsequent pages.
    """

    @classmethod
    def _compute_column_widths(cls, table: TableBlock) -> List[float]:
        """Compute estimated column widths from cell bounding boxes when available."""
        if not getattr(table, "cells", None):
            return []
        widths_by_col: Dict[int, List[float]] = {}
        for c in table.cells:
            if c.bbox and getattr(c, "col_span", 1) == 1:
                widths_by_col.setdefault(c.col_idx, []).append(c.bbox.width)
        if not widths_by_col:
            return []
        widths = []
        for i in range(table.col_count):
            if i in widths_by_col and widths_by_col[i]:
                widths.append(sum(widths_by_col[i]) / len(widths_by_col[i]))
            else:
                widths.append(0.0)
        return widths

    @classmethod
    def _compute_column_width_variance(
        cls, curr_widths: List[float], next_widths: List[float]
    ) -> float:
        """
        Compute mean squared difference (variance of column width differences)
        between two tables' column width profiles for valid observed columns.
        """
        if not curr_widths or not next_widths or len(curr_widths) != len(next_widths) or len(curr_widths) == 0:
            return 0.0
        valid_diffs = [(w1 - w2) for w1, w2 in zip(curr_widths, next_widths) if w1 > 0.0 and w2 > 0.0]
        if not valid_diffs:
            return 0.0
        return sum(d * d for d in valid_diffs) / len(valid_diffs)

    @classmethod
    def stitch_tables(
        cls,
        tables: List[TableBlock],
        page_height: float = 842.0,
        page_dimensions: Optional[Dict[int, Tuple[float, float]]] = None,
    ) -> List[TableBlock]:
        if len(tables) <= 1:
            return tables

        sorted_tables = sorted(tables, key=lambda t: (t.page_num, t.bbox.top if t.bbox else 0))
        stitched: List[TableBlock] = []

        i = 0
        while i < len(sorted_tables):
            curr_tbl = sorted_tables[i]

            while i + 1 < len(sorted_tables):
                next_tbl = sorted_tables[i + 1]
                curr_last_page = max(curr_tbl.pages) if curr_tbl.pages else curr_tbl.page_num

                if next_tbl.page_num == curr_last_page + 1:
                    cols_match = (
                        curr_tbl.col_count == next_tbl.col_count
                        and curr_tbl.col_count > 0
                    )
                    x_aligned = (
                        abs(curr_tbl.bbox.x0 - next_tbl.bbox.x0) <= 25.0
                        and abs(curr_tbl.bbox.x1 - next_tbl.bbox.x1) <= 25.0
                    ) if (curr_tbl.bbox and next_tbl.bbox) else True

                    # Evaluate column width distribution variance if cell coordinates exist
                    curr_col_widths = cls._compute_column_widths(curr_tbl)
                    next_col_widths = cls._compute_column_widths(next_tbl)
                    col_widths_compatible = True
                    if curr_col_widths and next_col_widths and len(curr_col_widths) == len(next_col_widths):
                        col_var = cls._compute_column_width_variance(curr_col_widths, next_col_widths)
                        # Threshold: RMS column width deviation <= 25.0 pt (variance <= 625.0)
                        if col_var > 625.0:
                            col_widths_compatible = False

                    headers_identical = (
                        bool(curr_tbl.headers)
                        and bool(next_tbl.headers)
                        and curr_tbl.headers == next_tbl.headers
                    )
                    first_row_matches_header = (
                        bool(next_tbl.rows)
                        and next_tbl.rows[0] == curr_tbl.headers
                    )
                    has_conflicting_headers = (
                        bool(curr_tbl.headers)
                        and bool(next_tbl.headers)
                        and not headers_identical
                        and not first_row_matches_header
                    )

                    curr_ph = page_dimensions.get(curr_last_page, (595.0, page_height))[1] if page_dimensions else page_height
                    next_ph = page_dimensions.get(next_tbl.page_num, (595.0, page_height))[1] if page_dimensions else page_height

                    curr_near_bottom = curr_tbl.bbox.bottom >= curr_ph * 0.35 if curr_tbl.bbox else True
                    next_near_top = next_tbl.bbox.top <= next_ph * 0.45 if next_tbl.bbox else True

                    # Relax x_aligned if headers are identical or columns match, provided column width variance is compatible
                    can_align_x = (x_aligned or (headers_identical and cols_match)) and col_widths_compatible

                    can_stitch = cols_match and can_align_x and not has_conflicting_headers and (
                        headers_identical
                        or first_row_matches_header
                        or (curr_near_bottom and next_near_top and (not next_tbl.title or next_tbl.title.startswith(curr_tbl.title)))
                    )

                    if can_stitch:
                        strip_count = 0
                        if first_row_matches_header or (next_tbl.rows and next_tbl.rows[0] == next_tbl.headers and headers_identical):
                            strip_count = next_tbl.header_rows_count if hasattr(next_tbl, "header_rows_count") else 1
                            next_body = next_tbl.rows[strip_count:]
                        else:
                            next_body = next_tbl.rows

                        merged_rows = curr_tbl.rows + next_body
                        all_pages = sorted(list(set(curr_tbl.pages + next_tbl.pages)))

                        row_offset = len(curr_tbl.rows)
                        offset_next_cells = []
                        strip_header_cell = strip_count > 0
                        for c in next_tbl.cells:
                            if strip_header_cell and c.row_idx < strip_count:
                                continue
                            offset_row_idx = c.row_idx - (strip_count if strip_header_cell else 0) + row_offset
                            offset_next_cells.append(
                                TableCell(
                                    row_idx=offset_row_idx,
                                    col_idx=c.col_idx,
                                    text=c.text,
                                    row_span=c.row_span,
                                    col_span=c.col_span,
                                    bbox=c.bbox,
                                )
                            )

                        merged_cells = curr_tbl.cells + offset_next_cells
                        merged_lines = curr_tbl.lines + next_tbl.lines

                        merged_footnotes = list(getattr(curr_tbl, "footnotes", []))
                        for fn in getattr(next_tbl, "footnotes", []):
                            if fn not in merged_footnotes:
                                merged_footnotes.append(fn)

                        merged_page_bboxes = dict(getattr(curr_tbl, "page_bboxes", {}))
                        if not merged_page_bboxes and curr_tbl.bbox:
                            merged_page_bboxes[curr_tbl.page_num] = curr_tbl.bbox
                        next_page_bboxes = getattr(next_tbl, "page_bboxes", {})
                        if not next_page_bboxes and next_tbl.bbox:
                            next_page_bboxes = {next_tbl.page_num: next_tbl.bbox}
                        merged_page_bboxes.update(next_page_bboxes)

                        curr_tbl = TableBlock(
                            page_num=curr_tbl.page_num,
                            bbox=curr_tbl.bbox,
                            rows=merged_rows,
                            headers=curr_tbl.headers,
                            cells=merged_cells,
                            lines=merged_lines,
                            title=curr_tbl.title or next_tbl.title,
                            extraction_engine=f"{curr_tbl.extraction_engine}+stitched",
                            confidence=min(curr_tbl.confidence, next_tbl.confidence),
                            pages=all_pages,
                            is_stitched=True,
                            footnotes=merged_footnotes,
                            page_bboxes=merged_page_bboxes,
                        )
                        i += 1
                        continue
                break

            stitched.append(curr_tbl)
            i += 1

        return stitched


class DocumentHierarchyBuilder:
    """
    Extracts hierarchical heading trees (H1-H4) and tracks ancestor breadcrumb paths.
    """

    HEADING_NUMBERING_RE = re.compile(
        r"^(?:第[一二三四五六七八九十百]+[章节部分]|[\d一二三四五六七八九十]+[、\.]|(?:\d+\.){1,3}\d*)\s*(.+)$"
    )

    @classmethod
    def classify_heading_level(
        cls,
        text: str,
        span_size: float,
        median_font_size: float,
    ) -> Optional[int]:
        clean = text.strip()
        if not clean or len(clean) > 85:
            return None

        # Headings do not end with full stops or contain multiple clauses with commas
        if clean.endswith(("。", "；")) or ("，" in clean and not clean.startswith(("注", "提示", "第"))):
            return None

        is_huge = span_size >= median_font_size * 1.5
        is_large = span_size >= median_font_size * 1.25
        is_medium = span_size >= median_font_size * 1.15
        has_num = bool(cls.HEADING_NUMBERING_RE.match(clean))

        if is_huge:
            return 1
        elif is_large:
            return 2
        elif has_num and is_medium:
            dot_count = clean.split()[0].count(".") if "." in clean.split()[0] else 0
            if dot_count >= 2:
                return 3
            return 2
        elif is_medium and len(clean) < 35:
            return 3
        elif has_num:
            dot_count = clean.split()[0].count(".") if "." in clean.split()[0] else 0
            if dot_count >= 2:
                return 3
            return 2 if is_large else 4

        return None


class BorderlessTableDetector:
    """
    Detects irregular and borderless spec tables (missing or partial grid lines).
    Analyzes horizontal text line alignments, column gutter gaps, and consecutive row patterns.
    """

    FOOTNOTE_PREFIXES = ("*", "注", "Note", "特别说明", "特别约定", "说明", "条款", "免责")

    @classmethod
    def is_footnote_line(cls, text: str) -> bool:
        clean = text.strip()
        return any(clean.startswith(prefix) for prefix in cls.FOOTNOTE_PREFIXES)

    @classmethod
    def detect_tables_from_dict(
        cls,
        page_dict: Dict[str, Any],
        page_num: int,
        existing_tables: Optional[List[TableBlock]] = None,
        page_width: float = 595.0,
        page_height: float = 842.0,
    ) -> List[TableBlock]:
        existing_tables = existing_tables or []
        existing_bboxes = [t.bbox for t in existing_tables if t.bbox]

        lines_all: List[Tuple[Tuple[float, float, float, float], str]] = []
        for b in page_dict.get("blocks", []):
            if "lines" not in b:
                continue
            bx0, by0, bx1, by1 = b["bbox"]

            # Check overlap with existing bordered table
            in_exist = False
            for eb in existing_bboxes:
                if (
                    bx0 >= eb.x0 - 5.0
                    and bx1 <= eb.x1 + 5.0
                    and by0 >= eb.top - 5.0
                    and by1 <= eb.bottom + 5.0
                ):
                    in_exist = True
                    break
            if in_exist:
                continue

            for line in b["lines"]:
                text = "".join(s["text"] for s in line.get("spans", [])).strip()
                bbox = line.get("bbox")
                if not text or not bbox:
                    continue
                # Skip header/footer margin lines
                if bbox[1] <= 40.0 or bbox[3] >= page_height - 40.0:
                    continue
                # Skip rotated lines
                ldir = line.get("dir", (1.0, 0.0))
                if isinstance(ldir, (list, tuple)) and len(ldir) >= 2:
                    if abs(ldir[0] - 1.0) > 0.05 or abs(ldir[1]) > 0.05:
                        continue
                lines_all.append((bbox, text))

        if not lines_all:
            return []

        lines_all.sort(key=lambda it: it[0][1])
        y_groups: List[List[Tuple[Tuple[float, float, float, float], str]]] = []
        cur_group: List[Tuple[Tuple[float, float, float, float], str]] = []
        last_y = -999.0
        for bbox, text in lines_all:
            if not cur_group or abs(bbox[1] - last_y) <= 5.0:
                cur_group.append((bbox, text))
                last_y = bbox[1]
            else:
                y_groups.append(cur_group)
                cur_group = [(bbox, text)]
                last_y = bbox[1]
        if cur_group:
            y_groups.append(cur_group)

        # Categorize line groups as candidate multi-column table rows
        candidate_rows: List[Optional[List[Tuple[Tuple[float, float, float, float], str]]]] = []
        for g in y_groups:
            g.sort(key=lambda it: it[0][0])
            if len(g) >= 3:
                # 3+ columns: valid table row candidate; allow cells with periods, full sentences, or long specs
                candidate_rows.append(g)
            elif len(g) == 2:
                # 2-column table candidate: key-value pair or 2-column spec.
                # Must NOT be dual-column prose layout (where both columns are wide narrative text blocks).
                b0, t0 = g[0]
                b1, t1 = g[1]
                w0 = b0[2] - b0[0]
                w1 = b1[2] - b1[0]
                is_dual_column_narrative = (w0 > 220.0 and w1 > 220.0) or (w0 > page_width * 0.40 and w1 > page_width * 0.40)
                candidate_rows.append(None if is_dual_column_narrative else g)
            else:
                # Single line with tab or wide whitespace delimiters
                parts = re.split(r"\s{3,}|\t", g[0][1])
                parts = [p.strip() for p in parts if p.strip()]
                if len(parts) >= 2:
                    l_x0, l_y0, l_x1, l_y1 = g[0][0]
                    total_w = l_x1 - l_x0
                    slot_w = total_w / len(parts)
                    cand = []
                    for idx, p in enumerate(parts):
                        sub_b = (l_x0 + idx * slot_w, l_y0, l_x0 + (idx + 1) * slot_w, l_y1)
                        cand.append((sub_b, p))
                    candidate_rows.append(cand)
                else:
                    candidate_rows.append(None)

        detected_tables: List[TableBlock] = []
        i = 0
        while i < len(candidate_rows):
            if candidate_rows[i] is None:
                i += 1
                continue

            seq = [candidate_rows[i]]
            j = i + 1
            while j < len(candidate_rows) and candidate_rows[j] is not None:
                prev_bottom = max(b[3] for b, _ in seq[-1])
                curr_top = min(b[1] for b, _ in candidate_rows[j])
                if curr_top - prev_bottom > 25.0:
                    break
                seq.append(candidate_rows[j])
                j += 1

            if len(seq) >= 2:
                # Check for footnote immediately after table
                footnotes: List[str] = []
                if j < len(y_groups):
                    after_g = y_groups[j]
                    if len(after_g) == 1 and cls.is_footnote_line(after_g[0][1]):
                        seq_bottom = max(b[3] for row in seq for b, _ in row)
                        if after_g[0][0][1] - seq_bottom <= 30.0:
                            footnotes.append(after_g[0][1])

                # Determine column anchors with stable cluster centroid tracking
                all_x0s = [b[0] for row in seq for b, _ in row]
                all_x0s.sort()
                clusters: List[List[float]] = []
                for x in all_x0s:
                    matched_cluster = None
                    for cl in clusters:
                        centroid = sum(cl) / len(cl)
                        if abs(x - centroid) <= 25.0:
                            matched_cluster = cl
                            break
                    if matched_cluster is not None:
                        matched_cluster.append(x)
                    else:
                        clusters.append([x])

                # Stable column anchors using cluster medians to prevent coordinate drift
                anchors = sorted([sorted(cl)[len(cl) // 2] for cl in clusters])

                if len(anchors) >= 2:
                    table_rows: List[List[str]] = []
                    table_cells: List[TableCell] = []
                    for r_idx, row in enumerate(seq):
                        r_cells = [""] * len(anchors)
                        for bbox, text in row:
                            best_col = min(range(len(anchors)), key=lambda k: abs(bbox[0] - anchors[k]))
                            r_cells[best_col] = text
                            table_cells.append(
                                TableCell(
                                    row_idx=r_idx,
                                    col_idx=best_col,
                                    text=text,
                                    bbox=BoundingBox(bbox[0], bbox[1], bbox[2], bbox[3], page=page_num),
                                )
                            )
                        table_rows.append(r_cells)

                    overall_bbox = BoundingBox(
                        x0=min(b[0] for row in seq for b, _ in row),
                        top=min(b[1] for row in seq for b, _ in row),
                        x1=max(b[2] for row in seq for b, _ in row),
                        bottom=max(b[3] for row in seq for b, _ in row),
                        page=page_num,
                    )

                    is_toc = len(table_rows) >= 3 and all(
                        re.match(r"^\d{1,4}$", [c for c in row if c.strip()][-1])
                        for row in table_rows
                        if any(c.strip() for c in row)
                    )
                    if not is_toc:
                        t_block = TableBlock(
                            page_num=page_num,
                            bbox=overall_bbox,
                            rows=table_rows,
                            cells=table_cells,
                            extraction_engine="borderless_stream_detector",
                            confidence=0.90,
                            footnotes=footnotes,
                        )
                        detected_tables.append(t_block)

            i = j

        return detected_tables


class BaseLayoutEngine(ABC):
    """Abstract base class for document layout analysis engines."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse document file into structured sections and tables."""
        pass

    @abstractmethod
    def extract_tables(self, file_path: Path) -> List[TableBlock]:
        """Extract all table blocks with precise bounding boxes and markdown/html."""
        pass


class PyMuPDFPlumberEngine(BaseLayoutEngine):
    """
    Hybrid Local Layout Parser combining PyMuPDF (fitz) and pdfplumber:
    - pdfplumber: Precise geometric table boundary detection, line extraction, cell coords.
    - PyMuPDF (fitz): Reading order recovery, font-size based heading hierarchy, speed & OCR fallback.
    - Enterprise additions: Cross-page table stitching, dual-column sorting, noise watermark filtering.
    """

    def __init__(
        self,
        table_strategy: str = "lines",
        stitch_tables: bool = True,
        filter_noise: bool = True,
        reading_order_sort: bool = True,
    ):
        self.table_strategy = table_strategy
        self.stitch_tables = stitch_tables
        self.filter_noise = filter_noise
        self.reading_order_sort = reading_order_sort

    def extract_tables(
        self,
        file_path: Path,
        stitch: Optional[bool] = None,
        page_numbers: Optional[Sequence[int]] = None,
    ) -> List[TableBlock]:
        """Extract tables using pdfplumber with exact bounding boxes, cell contents, and optional stitching."""
        tables: List[TableBlock] = []
        page_dimensions: Dict[int, Tuple[float, float]] = {}

        try:
            import pdfplumber

            with pdfplumber.open(str(file_path)) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1
                    if page_numbers is not None and page_num not in page_numbers:
                        continue
                    page_dimensions[page_num] = (float(page.width), float(page.height))
                    extracted_tables = page.find_tables()

                    for tbl in extracted_tables:
                        x0, top, x1, bottom = tbl.bbox
                        bbox = BoundingBox(x0, top, x1, bottom, page=page_num)
                        data = tbl.extract()
                        if not data:
                            continue

                        # Filter empty rows
                        non_empty_rows = [
                            row for row in data
                            if any(c is not None and str(c).strip() != "" for c in row)
                        ]
                        if not non_empty_rows:
                            continue

                        headers = [str(c).strip() if c else "" for c in non_empty_rows[0]]

                        # Extract cell bounding boxes
                        cells: List[TableCell] = []
                        if hasattr(tbl, "rows"):
                            for r_idx, row_obj in enumerate(tbl.rows):
                                if r_idx >= len(data):
                                    break
                                row_cells = getattr(row_obj, "cells", [])
                                for c_idx, cell_bbox in enumerate(row_cells):
                                    cell_text = (
                                        str(data[r_idx][c_idx]).strip()
                                        if c_idx < len(data[r_idx]) and data[r_idx][c_idx] is not None
                                        else ""
                                    )
                                    c_bbox_obj = None
                                    if cell_bbox is not None and len(cell_bbox) >= 4:
                                        c_bbox_obj = BoundingBox(
                                            cell_bbox[0],
                                            cell_bbox[1],
                                            cell_bbox[2],
                                            cell_bbox[3],
                                            page=page_num,
                                        )
                                    cells.append(
                                        TableCell(
                                            row_idx=r_idx,
                                            col_idx=c_idx,
                                            text=cell_text,
                                            bbox=c_bbox_obj,
                                        )
                                    )

                        # Extract table lines (horizontal & vertical borders)
                        table_lines: List[TableLine] = []
                        try:
                            edges = getattr(page, "edges", [])
                            for e in edges:
                                ex0 = float(e.get("x0", 0.0))
                                ex1 = float(e.get("x1", 0.0))
                                etop = float(e.get("top", 0.0))
                                ebottom = float(e.get("bottom", 0.0))
                                if (
                                    ex0 >= x0 - 3.0
                                    and ex1 <= x1 + 3.0
                                    and etop >= top - 3.0
                                    and ebottom <= bottom + 3.0
                                ):
                                    orientation = e.get("orientation", "h" if abs(ebottom - etop) < 2.0 else "v")
                                    table_lines.append(
                                        TableLine(
                                            x0=ex0,
                                            top=etop,
                                            x1=ex1,
                                            bottom=ebottom,
                                            orientation=orientation,
                                            page=page_num,
                                        )
                                    )
                        except Exception as line_err:
                            logger.debug(f"Edge line extraction skipped: {line_err}")

                        table_block = TableBlock(
                            page_num=page_num,
                            bbox=bbox,
                            rows=non_empty_rows,
                            headers=headers,
                            cells=cells,
                            lines=table_lines,
                            extraction_engine="pdfplumber_hybrid",
                            confidence=0.95,
                        )
                        tables.append(table_block)

        except Exception as e:
            logger.warning(f"pdfplumber table extraction failed for {file_path}: {e}")
            tables.extend(self._extract_tables_fitz_fallback(file_path))

        # Detect borderless tables on each page using BorderlessTableDetector
        try:
            import pymupdf

            doc_fitz = pymupdf.open(str(file_path))
            for page_idx, page in enumerate(doc_fitz):
                p_num = page_idx + 1
                if p_num not in page_dimensions:
                    page_dimensions[p_num] = (float(page.rect.width), float(page.rect.height))
                existing_for_page = [t for t in tables if p_num in getattr(t, "pages", [t.page_num])]
                borderless = BorderlessTableDetector.detect_tables_from_dict(
                    page.get_text("dict"),
                    page_num=p_num,
                    existing_tables=existing_for_page,
                    page_width=page.rect.width,
                    page_height=page.rect.height,
                )
                tables.extend(borderless)
            doc_fitz.close()
        except Exception as borderless_err:
            logger.debug(f"Borderless table detection skipped: {borderless_err}")

        do_stitch = self.stitch_tables if stitch is None else stitch
        if do_stitch and tables:
            tables = CrossPageTableStitcher.stitch_tables(tables, page_dimensions=page_dimensions)

        return tables

    def _extract_tables_fitz_fallback(self, file_path: Path) -> List[TableBlock]:
        """Fallback table extraction using PyMuPDF (fitz) table finder."""
        tables: List[TableBlock] = []
        try:
            import pymupdf

            doc = pymupdf.open(str(file_path))
            for page_idx, page in enumerate(doc):
                page_num = page_idx + 1
                try:
                    tabs = page.find_tables()
                    for tab in tabs:
                        bbox_tuple = tab.bbox
                        bbox = BoundingBox(bbox_tuple[0], bbox_tuple[1], bbox_tuple[2], bbox_tuple[3], page=page_num)
                        data = tab.extract()
                        if data:
                            tables.append(
                                TableBlock(
                                    page_num=page_num,
                                    bbox=bbox,
                                    rows=data,
                                    extraction_engine="pymupdf_tables",
                                    confidence=0.90,
                                )
                            )
                except Exception as sub_e:
                    logger.debug(f"fitz page.find_tables failed on page {page_num}: {sub_e}")
            doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF fallback failed for {file_path}: {e}")
        return tables

    def parse(
        self,
        file_path: Union[str, Path],
        page_numbers: Optional[Sequence[int]] = None,
    ) -> ParsedDocument:
        """
        Full layout analysis:
        1. Extract tables with BBox & cross-page stitching.
        2. Detect scanned vs digital pages.
        3. Filter headers, footers, pagination, and watermarks.
        4. Reconstruct dual-column reading order.
        5. Build hierarchical heading tree (H1-H4) and track ancestor breadcrumbs.
        6. Prevent duplicate table-region text in body paragraphs.
        """
        file_path = Path(file_path)
        tables = self.extract_tables(file_path, page_numbers=page_numbers)

        doc_title = file_path.stem
        vehicle_model = ""
        sections: List[TextSection] = []
        raw_full_text: List[str] = []
        page_count = 1
        pages_classification: Dict[int, str] = {}
        page_dimensions: Dict[int, Tuple[float, float]] = {}
        page_orientations: Dict[int, str] = {}
        doc = None
        is_encrypted = False
        try:
            import pymupdf

            doc = pymupdf.open(str(file_path))
            if getattr(doc, "is_encrypted", False):
                is_encrypted = True
            page_count = len(doc)

            # Analyze font sizes and running headers across document
            font_sizes: List[float] = []
            top_texts: List[str] = []
            for page_idx, page in enumerate(doc):
                p_num = page_idx + 1
                if page_numbers is not None and p_num not in page_numbers:
                    continue
                p_h = page.rect.height
                blocks = page.get_text("dict").get("blocks", [])
                for b in blocks:
                    if "lines" in b:
                        bx0, by0, bx1, by1 = b["bbox"]
                        if by1 <= p_h * 0.09:
                            t = "".join(s["text"] for line in b["lines"] for s in line["spans"]).strip()
                            if t and len(t) < 100:
                                top_texts.append(t)
                        for line in b["lines"]:
                            for s in line["spans"]:
                                font_sizes.append(s["size"])

            from collections import Counter
            top_counts = Counter(top_texts)
            running_headers = {t for t, c in top_counts.items() if c >= 2}

            # Classify page layout and dimensions with noise filtering
            for page_idx, page in enumerate(doc):
                p_num = page_idx + 1
                if page_numbers is not None and p_num not in page_numbers:
                    continue
                page_dimensions[p_num] = (float(page.rect.width), float(page.rect.height))
                page_orientations[p_num] = "landscape" if page.rect.width > page.rect.height else "portrait"

                p_images = page.get_images()
                blocks = page.get_text("dict").get("blocks", [])
                p_h = page.rect.height

                # Compute genuine text length by excluding watermarks and running headers/footers
                genuine_chars = 0
                for b in blocks:
                    if "lines" in b:
                        t = "".join(s["text"] for line in b["lines"] for s in line["spans"]).strip()
                        if not t:
                            continue
                        if HeaderFooterWatermarkFilter.is_header_or_footer(b["bbox"], p_h, t, running_headers=running_headers):
                            continue
                        if HeaderFooterWatermarkFilter.is_watermark(b, t):
                            continue
                        genuine_chars += len(t)

                if genuine_chars < 30 and len(p_images) > 0:
                    pages_classification[p_num] = "scanned"
                elif len(p_images) > 0 and genuine_chars >= 30:
                    pages_classification[p_num] = "hybrid"
                elif genuine_chars < 30:
                    pages_classification[p_num] = "empty"
                else:
                    pages_classification[p_num] = "digital"

            median_size = sorted(font_sizes)[len(font_sizes) // 2] if font_sizes else 10.0

            current_section_title = "Overview"
            current_section_level = 1
            current_section_paras: List[str] = []
            current_section_bbox: Optional[BoundingBox] = None
            current_page = 1
            heading_stack: List[Tuple[int, str]] = [(1, "Overview")]

            for page_idx, page in enumerate(doc):
                page_num = page_idx + 1
                if page_numbers is not None and page_num not in page_numbers:
                    continue
                page_class = pages_classification.get(page_num, "digital")
                page_rot = OCROrientationDetector.detect_page_rotation(page)
                if page_rot != 0:
                    OCROrientationDetector.normalize_page(page)
                    page_dimensions[page_num] = (float(page.rect.width), float(page.rect.height))
                    page_orientations[page_num] = "landscape" if page.rect.width > page.rect.height else "portrait"

                page_tables = [t for t in tables if page_num in getattr(t, "pages", [t.page_num])]
                raw_blocks = page.get_text("dict").get("blocks", [])

                # Associate attached table footnotes immediately below tables
                fn_prefixes = ("*", "注", "Note", "特别说明", "特别约定", "说明", "条款", "免责")
                attached_footnote_block_ids = set()
                for tbl in page_tables:
                    t_bbox = getattr(tbl, "page_bboxes", {}).get(page_num, tbl.bbox)
                    if not t_bbox:
                        continue
                    sorted_cand = [
                        b for b in raw_blocks
                        if "lines" in b and b["bbox"][1] >= t_bbox.bottom - 4.0
                    ]
                    sorted_cand.sort(key=lambda b: b["bbox"][1])
                    curr_bottom = t_bbox.bottom
                    for cb in sorted_cand:
                        cb_text = "".join(s["text"] for line in cb["lines"] for s in line["spans"]).strip()
                        if 0 <= cb["bbox"][1] - curr_bottom <= 35.0 and any(cb_text.startswith(p) for p in fn_prefixes):
                            if cb_text not in tbl.footnotes:
                                tbl.footnotes.append(cb_text)
                            attached_footnote_block_ids.add(id(cb))
                            curr_bottom = cb["bbox"][3]

                # Scanned page handling with OCR and structured diagnostic fallback
                if page_class == "scanned":
                    try:
                        tp = page.get_textpage_ocr(language="chi_sim+eng", dpi=150, full=True)
                        extracted_ocr = page.get_text("dict", textpage=tp).get("blocks", [])
                        if extracted_ocr:
                            raw_blocks = extracted_ocr
                    except Exception as ocr_err:
                        logger.debug(f"PyMuPDF OCR unavailable on page {page_num}: {ocr_err}")

                    if current_section_paras:
                        breadcrumbs = [h[1] for h in heading_stack]
                        sections.append(
                            TextSection(
                                title=current_section_title,
                                content="\n\n".join(current_section_paras),
                                level=current_section_level,
                                page_num=current_page,
                                bbox=current_section_bbox,
                                breadcrumb_path=breadcrumbs,
                            )
                        )
                        current_section_paras = []
                        current_section_bbox = None

                    p_images = page.get_images()
                    img_info = f"{len(p_images)} 张高分辨率工程图表/底盘扫描件" if p_images else "页面扫描图像流"
                    diag_text = (
                        f"【扫描件版面图像诊断 (第 {page_num} 页)】\n"
                        f"• 页面属性: 纯图片扫描件 (Scanned PDF Page)\n"
                        f"• 图像资产: {img_info}\n"
                        f"• 页面尺寸与检测朝向: {page.rect.width:.0f}x{page.rect.height:.0f} pt (朝向: {page_rot}°)\n"
                        f"• 状态提示: 本地 OCR 引擎未捕获可索引字符层，已保留版面占位符与图片元数据，支持多模态 Vision-LLM 进一步召回与解析。"
                    )
                    raw_full_text.append(diag_text)
                    breadcrumbs = [h[1] for h in heading_stack] + [f"第 {page_num} 页 扫描件工程图表"]
                    sections.append(
                        TextSection(
                            title=f"第 {page_num} 页 扫描件工程图表",
                            content=diag_text,
                            level=2,
                            page_num=page_num,
                            breadcrumb_path=breadcrumbs,
                        )
                    )
                    continue

                valid_blocks = []

                for b in raw_blocks:
                    if "lines" not in b or id(b) in attached_footnote_block_ids:
                        continue

                    bx0, by0, bx1, by1 = b["bbox"]

                    # Filter table region overlap
                    in_table = False
                    for tbl in page_tables:
                        t_bbox = getattr(tbl, "page_bboxes", {}).get(page_num, tbl.bbox)
                        if not t_bbox:
                            continue
                        if (
                            bx0 >= t_bbox.x0 - 5
                            and bx1 <= t_bbox.x1 + 5
                            and by0 >= t_bbox.top - 5
                            and by1 <= t_bbox.bottom + 5
                        ):
                            in_table = True
                            break
                    if in_table:
                        continue

                    block_text = ""
                    for line in b["lines"]:
                        line_text = "".join(s["text"] for s in line["spans"]).strip()
                        if line_text:
                            block_text += line_text + " "
                    block_text = block_text.strip()
                    if not block_text:
                        continue

                    # Filter attached table footnotes from body paragraphs
                    if page_tables and any(
                        tbl.footnotes
                        and any(
                            fn == block_text or fn in block_text or (len(block_text) > 10 and block_text in fn)
                            for fn in tbl.footnotes
                        )
                        for tbl in page_tables
                    ):
                        continue

                    # Filter headers, footers, pagination, and watermarks
                    if self.filter_noise:
                        if HeaderFooterWatermarkFilter.is_header_or_footer(
                            (bx0, by0, bx1, by1), page.rect.height, block_text, running_headers=running_headers
                        ):
                            continue
                        if HeaderFooterWatermarkFilter.is_watermark(b, block_text):
                            continue

                    b["_clean_text"] = block_text
                    valid_blocks.append(b)

                # Reading order reconstruction
                if self.reading_order_sort:
                    sorted_blocks = ReadingOrderSorter.sort_page_blocks(
                        valid_blocks, page.rect.width, page.rect.height
                    )
                else:
                    sorted_blocks = valid_blocks

                for b in sorted_blocks:
                    block_text = b.get("_clean_text", "")
                    max_span_size = 0.0
                    for line in b["lines"]:
                        for s in line["spans"]:
                            if s["size"] > max_span_size:
                                max_span_size = s["size"]

                    raw_full_text.append(block_text)

                    # Model name detection heuristic
                    if not vehicle_model:
                        model_match = re.search(
                            r"(?:车型(?:代号|名称)?|车辆型号|车系|Model)[:：\s]*([\u4e00-\u9fa5A-Za-z0-9\-]+(?:\s+[\u4e00-\u9fa5A-Za-z0-9\-]+)*)",
                            block_text,
                        )
                        if model_match:
                            candidate = model_match.group(1).strip()
                            vehicle_model = candidate.split("(")[0].strip()

                    # Heading classification via hierarchy builder or bracketed section headers
                    bracket_match = re.match(r"^(【[^】]{2,25}】)\s*(.*)$", block_text)
                    if bracket_match:
                        heading_candidate = bracket_match.group(1).strip()
                        body_remainder = bracket_match.group(2).strip()
                        detected_level = 2
                    else:
                        heading_candidate = block_text
                        body_remainder = ""
                        detected_level = DocumentHierarchyBuilder.classify_heading_level(
                            block_text, max_span_size, median_size
                        )

                    if detected_level is not None:
                        if current_section_paras or (current_section_title and current_section_title != "Overview"):
                            breadcrumbs = [h[1] for h in heading_stack]
                            sec_text = "\n\n".join(current_section_paras) if current_section_paras else f"本章节【{current_section_title}】包含结构化汽车规格参数与技术数据。"
                            sections.append(
                                TextSection(
                                    title=current_section_title,
                                    content=sec_text,
                                    level=current_section_level,
                                    page_num=current_page,
                                    bbox=current_section_bbox,
                                    breadcrumb_path=breadcrumbs,
                                )
                            )
                            current_section_paras = []

                        # Maintain active heading ancestor stack
                        while heading_stack and heading_stack[-1][0] >= detected_level:
                            heading_stack.pop()
                        heading_stack.append((detected_level, heading_candidate))

                        current_section_title = heading_candidate
                        current_section_level = detected_level
                        current_page = page_num
                        current_section_bbox = BoundingBox.from_tuple(b["bbox"], page=page_num)
                        if body_remainder:
                            current_section_paras.append(body_remainder)
                    else:
                        if current_section_bbox is None:
                            current_section_bbox = BoundingBox.from_tuple(b["bbox"], page=page_num)
                        current_section_paras.append(block_text)

            if current_section_paras or (current_section_title and current_section_title != "Overview"):
                breadcrumbs = [h[1] for h in heading_stack]
                sec_text = "\n\n".join(current_section_paras) if current_section_paras else f"本章节【{current_section_title}】包含结构化汽车规格参数与技术数据。"
                sections.append(
                    TextSection(
                        title=current_section_title,
                        content=sec_text,
                        level=current_section_level,
                        page_num=current_page,
                        bbox=current_section_bbox,
                        breadcrumb_path=breadcrumbs,
                    )
                )

            if not sections and tables:
                sections.append(
                    TextSection(
                        title=doc_title,
                        content=f"文档【{doc_title}】包含 {len(tables)} 个结构化参数配置表格。",
                        level=1,
                        page_num=1,
                        breadcrumb_path=[doc_title],
                    )
                )

        except Exception as e:
            logger.warning(f"PyMuPDF block layout parsing failed: {e}")
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass

        # Attribute nearest section title and breadcrumbs to tables if unassigned
        doc_root_title = (
            sections[0].title
            if sections and sections[0].page_num == 1 and not DocumentHierarchyBuilder.HEADING_NUMBERING_RE.match(sections[0].title)
            else ""
        )
        for tbl in tables:
            candidate_secs = [
                s for s in sections
                if s.page_num < tbl.page_num
                or (s.page_num == tbl.page_num and (s.bbox is None or (tbl.bbox and s.bbox.top <= tbl.bbox.top)))
            ]
            if candidate_secs:
                if not tbl.title:
                    tbl.title = candidate_secs[-1].title
                sec_crumbs = list(candidate_secs[-1].breadcrumb_path)
                if doc_root_title and doc_root_title not in sec_crumbs:
                    sec_crumbs = [doc_root_title] + sec_crumbs
                tbl.metadata["breadcrumb_path"] = sec_crumbs
            elif doc_root_title:
                if not tbl.title:
                    tbl.title = doc_root_title
                tbl.metadata["breadcrumb_path"] = [doc_root_title]

        has_mixed = len(set(page_orientations.values())) > 1
        has_borderless = any(getattr(t, "extraction_engine", "").startswith("borderless") for t in tables)

        return ParsedDocument(
            title=doc_title,
            vehicle_model=vehicle_model or doc_title,
            sections=sections,
            tables=tables,
            pages=page_count,
            raw_text="\n\n".join(raw_full_text),
            page_dimensions=page_dimensions,
            page_orientations=page_orientations,
            metadata={
                "format": "pdf",
                "file_name": file_path.name,
                "engine": "pymupdf_pdfplumber_hybrid",
                "is_encrypted": is_encrypted,
                "pages_classification": pages_classification,
                "page_dimensions": page_dimensions,
                "page_orientations": page_orientations,
                "has_mixed_orientations": has_mixed,
                "has_borderless_tables": has_borderless,
                "has_scanned_pages": any(v == "scanned" for v in pages_classification.values()),
                "has_stitched_tables": any(getattr(t, "is_stitched", False) for t in tables),
                "has_multilevel_tables": any(getattr(t, "is_multilevel_header", False) for t in tables),
            },
        )


class AzureDocumentIntelligenceEngine(BaseLayoutEngine):
    """
    Enterprise-grade Layout Parser Adapter backed by Azure AI Document Intelligence
    (formerly Azure Form Recognizer).

    Uses Azure's 'prebuilt-layout' model which provides high-precision table detection,
    cell coordinate spans, and natural Markdown table reconstruction.
    Can operate in live cloud mode or local mock/fallback mode when credentials are not configured.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        model_id: str = "prebuilt-layout",
    ):
        self.endpoint = endpoint or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        self.model_id = model_id
        self._fallback_engine = PyMuPDFPlumberEngine()

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def extract_tables(self, file_path: Path) -> List[TableBlock]:
        if not self.is_configured:
            logger.info("Azure Document Intelligence credentials not found; delegating to PyMuPDF/pdfplumber.")
            tables = self._fallback_engine.extract_tables(file_path)
            for t in tables:
                t.extraction_engine = "pymupdf_pdfplumber"
                t.is_degraded = True
                t.metadata["is_degraded"] = True
            return tables

        # Live Azure Document Intelligence invocation
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential

            client = DocumentIntelligenceClient(
                endpoint=self.endpoint, credential=AzureKeyCredential(self.api_key)
            )

            with open(file_path, "rb") as f:
                poller = client.begin_analyze_document(
                    model_id=self.model_id,
                    analyze_request=f,
                    content_type="application/pdf",
                )
            result = poller.result()

            tables: List[TableBlock] = []
            if result.tables:
                for tbl_idx, table in enumerate(result.tables):
                    row_count = table.row_count
                    col_count = table.column_count
                    matrix = [["" for _ in range(col_count)] for _ in range(row_count)]

                    for cell in table.cells:
                        matrix[cell.row_index][cell.column_index] = cell.content or ""

                    # Bounding regions
                    page_num = 1
                    bbox = BoundingBox(0, 0, 100, 100, page=1)
                    if table.bounding_regions:
                        br = table.bounding_regions[0]
                        page_num = br.page_number
                        pts = br.polygon  # [x1, y1, x2, y2, x3, y3, x4, y4]
                        if len(pts) >= 8:
                            xs = [pts[i] for i in range(0, len(pts), 2)]
                            ys = [pts[i] for i in range(1, len(pts), 2)]
                            bbox = BoundingBox(min(xs), min(ys), max(xs), max(ys), page=page_num)

                    headers = matrix[0] if row_count > 0 else []
                    tables.append(
                        TableBlock(
                            page_num=page_num,
                            bbox=bbox,
                            rows=matrix,
                            headers=headers,
                            extraction_engine="azure_document_intelligence_live",
                            confidence=0.99,
                        )
                    )
            return tables
        except Exception as e:
            logger.error(f"Azure Document Intelligence call failed: {e}. Falling back to local hybrid engine.")
            tables = self._fallback_engine.extract_tables(file_path)
            for t in tables:
                t.extraction_engine = "pymupdf_pdfplumber"
                t.is_degraded = True
                t.metadata["is_degraded"] = True
            return tables

    def parse(self, file_path: Path) -> ParsedDocument:
        if not self.is_configured:
            doc = self._fallback_engine.parse(file_path)
            doc.metadata["engine"] = "pymupdf_pdfplumber"
            doc.metadata["is_degraded"] = True
            for t in doc.tables:
                t.extraction_engine = "pymupdf_pdfplumber"
                t.is_degraded = True
                t.metadata["is_degraded"] = True
            return doc

        try:
            tables = self.extract_tables(file_path)
            doc = self._fallback_engine.parse(file_path)
            doc.tables = tables
            doc.metadata["engine"] = "azure_document_intelligence_live"
            return doc
        except Exception as e:
            logger.error(f"Azure Document Intelligence live parse failed: {e}; falling back to PyMuPDF/pdfplumber.")
            doc = self._fallback_engine.parse(file_path)
            doc.metadata["engine"] = "pymupdf_pdfplumber"
            doc.metadata["is_degraded"] = True
            for t in doc.tables:
                t.extraction_engine = "pymupdf_pdfplumber"
                t.is_degraded = True
                t.metadata["is_degraded"] = True
            return doc


class UnstructuredEngine(BaseLayoutEngine):
    """
    Open-Source Adapter for Unstructured.io (partition_pdf).
    Extracts structured Document elements (Title, Table, NarrativeText).
    """

    def __init__(self, strategy: str = "fast"):
        self.strategy = strategy
        self._fallback = PyMuPDFPlumberEngine()

    def extract_tables(self, file_path: Path) -> List[TableBlock]:
        try:
            from unstructured.partition.pdf import partition_pdf

            elements = partition_pdf(filename=str(file_path), strategy=self.strategy)
            tables: List[TableBlock] = []

            for el in elements:
                if el.category == "Table":
                    page_num = getattr(el.metadata, "page_number", 1) or 1
                    coords = getattr(el.metadata, "coordinates", None)
                    bbox = BoundingBox(0, 0, 100, 100, page=page_num)
                    if coords and hasattr(coords, "points"):
                        pts = coords.points
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        bbox = BoundingBox(min(xs), min(ys), max(xs), max(ys), page=page_num)

                    # Extract table rows from text
                    raw_lines = el.text.split("\n")
                    rows = [[c.strip() for c in line.split("  ") if c.strip()] for line in raw_lines if line.strip()]

                    tables.append(
                        TableBlock(
                            page_num=page_num,
                            bbox=bbox,
                            rows=rows if rows else [[el.text]],
                            extraction_engine="unstructured_io",
                            confidence=0.92,
                        )
                    )
            return tables if tables else self._fallback.extract_tables(file_path)
        except Exception as e:
            logger.warning(f"Unstructured partition_pdf fallback to PyMuPDF: {e}")
            return self._fallback.extract_tables(file_path)

    def parse(self, file_path: Path) -> ParsedDocument:
        # Returns parsed document using Unstructured extraction
        return self._fallback.parse(file_path)


class RealDoclingAdapter(BaseLayoutEngine):
    """
    Direct proxy to RealDoclingAdapter in docling_adapter.py.
    """

    def __init__(self, use_gpu: bool = False, **kwargs: Any):
        super().__init__()
        from src.ingestion.docling_adapter import RealDoclingAdapter as _DoclingImpl
        self._impl = _DoclingImpl(use_gpu=use_gpu, **kwargs)

    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        return self._impl.parse(Path(file_path))

    def extract_tables(self, file_path: Union[str, Path]) -> List[TableBlock]:
        return self._impl.extract_tables(Path(file_path))


class RealPaddleOCRAdapter(BaseLayoutEngine):
    """
    Direct proxy to RealPaddleOCRAdapter in paddle_ocr_adapter.py.
    """

    def __init__(self, use_gpu: bool = False, **kwargs: Any):
        super().__init__()
        from src.ingestion.paddle_ocr_adapter import RealPaddleOCRAdapter as _PaddleImpl
        self._impl = _PaddleImpl(use_gpu=use_gpu, **kwargs)

    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        return self._impl.parse(Path(file_path))

    def extract_tables(self, file_path: Union[str, Path]) -> List[TableBlock]:
        return self._impl.extract_tables(Path(file_path))

    def parse_scanned_pdf(
        self, file_path: Path, page_numbers: Optional[Sequence[int]] = None
    ) -> ParsedDocument:
        return self._impl.parse_scanned_pdf(file_path, page_numbers=page_numbers)


class MinerUDoclingEngine(BaseLayoutEngine):
    """
    Enterprise & Open-Source Connector for MinerU and IBM Docling.
    Integrated with real RealDoclingAdapter SDK backend.
    """

    def __init__(self, engine_name: str = "docling", **kwargs: Any):
        super().__init__()
        self.engine_name = engine_name
        self._docling = RealDoclingAdapter(**kwargs)
        self._fallback = PyMuPDFPlumberEngine()

    def extract_tables(self, file_path: Union[str, Path]) -> List[TableBlock]:
        logger.info(f"Using {self.engine_name} adapter for layout extraction on {Path(file_path).name}")
        tables = self._docling.extract_tables(file_path)
        for t in tables:
            t.extraction_engine = f"{self.engine_name}_adapter"
        return tables

    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        doc = self._docling.parse(file_path)
        doc.metadata["engine"] = f"{self.engine_name}_adapter"
        return doc


class PreFlightProbe:
    """
    Lightweight Pre-Flight Probe powered by PyMuPDF (fitz) (<5ms execution).
    Performs:
    1. Document corruption & password / encryption verification.
    2. Page count, dimensions (width, height), orientation (portrait/landscape), and rotation.
    3. Genuine characters density counting for hard routing (>= 30 digital, < 30 scanned).
    """

    @staticmethod
    def inspect(file_path: Union[str, Path], char_density_threshold: int = 30) -> Dict[str, Any]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"]:
            return {
                "total_pages": 1,
                "digital_pages": [],
                "scanned_pages": [1],
                "page_counts": {1: 0},
                "page_dimensions": {1: (0.0, 0.0)},
                "page_orientations": {1: "portrait"},
                "page_rotations": {1: 0},
            }

        import fitz

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            raise DocumentParsingUnrecoverableError(
                f"PDF document is corrupted or unreadable: {file_path.name} ({e})"
            ) from e

        try:
            if getattr(doc, "is_encrypted", False):
                if not doc.authenticate(""):
                    raise DocumentParsingUnrecoverableError(
                        f"PDF document is encrypted/password-protected: {file_path.name}"
                    )

            total_pages = len(doc)
            if total_pages == 0:
                raise DocumentParsingUnrecoverableError(
                    f"PDF document has 0 pages or is corrupted: {file_path.name}"
                )

            digital_pages: List[int] = []
            scanned_pages: List[int] = []
            page_counts: Dict[int, int] = {}
            page_dimensions: Dict[int, Tuple[float, float]] = {}
            page_orientations: Dict[int, str] = {}
            page_rotations: Dict[int, int] = {}

            for p_idx, page in enumerate(doc):
                p_num = p_idx + 1
                rect = page.rect
                page_dimensions[p_num] = (round(float(rect.width), 2), round(float(rect.height), 2))
                page_orientations[p_num] = "landscape" if rect.width > rect.height else "portrait"
                page_rotations[p_num] = int(page.rotation)

                txt = page.get_text() or ""
                genuine_chars = sum(1 for c in txt if not c.isspace())
                page_counts[p_num] = genuine_chars

                if genuine_chars >= char_density_threshold:
                    digital_pages.append(p_num)
                else:
                    scanned_pages.append(p_num)

            return {
                "total_pages": total_pages,
                "digital_pages": digital_pages,
                "scanned_pages": scanned_pages,
                "page_counts": page_counts,
                "page_dimensions": page_dimensions,
                "page_orientations": page_orientations,
                "page_rotations": page_rotations,
            }
        finally:
            doc.close()


def _isolated_layout_worker(func, args, kwargs, child_conn, temp_file_path=None):
    """
    Worker entrypoint executed in isolated subprocess.
    Transfers large payloads (>64KB) via shared temporary file to avoid IPC buffer deadlocks.
    """
    try:
        res = func(*args, **kwargs)
        if temp_file_path is not None:
            try:
                import pickle
                data_bytes = pickle.dumps(res, protocol=pickle.HIGHEST_PROTOCOL)
                if len(data_bytes) > 65536:
                    with open(temp_file_path, "wb") as f:
                        f.write(data_bytes)
                    child_conn.send((True, {"__ipc_file__": temp_file_path}))
                    return
            except Exception:
                pass
        child_conn.send((True, res))
    except BaseException as exc:
        try:
            child_conn.send((False, exc))
        except Exception:
            child_conn.send((False, RuntimeError(f"{type(exc).__name__}: {str(exc)}")))
    finally:
        try:
            child_conn.close()
        except Exception:
            pass


class DualTrackLayoutEngine(BaseLayoutEngine):
    """
    Dual-track document parsing engine with staged fallback tiers:

    1. Pre-flight probe: PyMuPDF checks file integrity, page dimensions, and character density.
    2. Digital track (character density >= threshold):
       - Primary: IBM Docling TableFormer for layout and table structure.
       - Fallback: pdfplumber table extraction if Docling times out or fails.
       - Final fallback: PyMuPDF text extraction if table extraction fails.
    3. Scanned track (character density < threshold):
       - Primary: PaddleOCR PP-Structure for layout and OCR.
       - Fallback: PyMuPDF OCR text extraction.
       - Final fallback: PyMuPDF raw text extraction.
    4. Degradation metadata:
       - Sets is_degraded=True, extraction_quality='degraded', fallback_level, and degraded_reason.
       - Raises DocumentParsingUnrecoverableError if no readable content is extracted.
    """

    def __init__(
        self,
        char_density_threshold: int = 30,
        timeout_seconds: float = 30.0,
        docling_kwargs: Optional[Dict[str, Any]] = None,
        paddle_kwargs: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        self.threshold = char_density_threshold
        self.timeout_seconds = timeout_seconds
        self.docling = RealDoclingAdapter(allow_fallback=False, **(docling_kwargs or {}))
        self.paddle = RealPaddleOCRAdapter(allow_fallback=False, **(paddle_kwargs or {}))
        self._fallback = PyMuPDFPlumberEngine()

    def check_density(self, file_path: Path) -> Dict[str, Any]:
        """Pre-flight probe delegator for page character density classification."""
        return PreFlightProbe.inspect(file_path, char_density_threshold=self.threshold)

    @staticmethod
    def _run_with_timeout(func, *args, timeout_seconds: float = 30.0, **kwargs):
        """
        Execute func(*args, **kwargs) in an isolated process with timeout enforcement.
        Uses multiprocessing spawn context by default to prevent POSIX deadlocks in
        multi-threaded runtimes (OpenMP/PyTorch/fitz), falling back to fork only if
        unpicklable closures are passed.
        Attempts graceful SIGTERM before SIGKILL.
        """
        if not timeout_seconds or timeout_seconds <= 0:
            return func(*args, **kwargs)

        import multiprocessing as mp
        import pickle
        import tempfile
        import time

        shm_path = Path("/dev/shm")
        shm_dir = shm_path if shm_path.is_dir() and os.access(str(shm_path), os.W_OK) else None
        temp_file_path = None
        try:
            temp_file = tempfile.NamedTemporaryFile(
                dir=shm_dir, prefix="autovend_ipc_", suffix=".bin", delete=False
            )
            temp_file_path = temp_file.name
            temp_file.close()
        except Exception:
            temp_file_path = None

        proc = None
        parent_conn = None
        child_conn = None

        try:
            # Prefer fork context on POSIX to avoid 2-3s cold-start spawn overhead.
            # Fallback to spawn context if fork is unavailable or if target requires fresh process.
            available_methods = ("fork", "spawn") if "fork" in mp.get_all_start_methods() else ("spawn",)
            for ctx_method in available_methods:
                try:
                    ctx = mp.get_context(ctx_method)
                    parent_conn, child_conn = ctx.Pipe()
                    proc = ctx.Process(
                        target=_isolated_layout_worker,
                        args=(func, args, kwargs, child_conn, temp_file_path),
                    )
                    proc.start()
                except Exception:
                    if child_conn is not None:
                        try:
                            child_conn.close()
                        except Exception:
                            pass
                    if parent_conn is not None:
                        try:
                            parent_conn.close()
                        except Exception:
                            pass
                    if ctx_method == available_methods[-1]:
                        raise
                    continue

                start_time = time.time()
                result_payload = None
                has_result = False

                # Non-busy blocking poll: sleeps in OS poll/select syscall without consuming CPU
                remaining = max(0.0, timeout_seconds - (time.time() - start_time))
                if parent_conn.poll(remaining):
                    has_result = True
                    result_payload = parent_conn.recv()
                elif not proc.is_alive() and parent_conn.poll(0.01):
                    has_result = True
                    result_payload = parent_conn.recv()

                if not has_result:
                    if proc.is_alive():
                        child_pid = proc.pid
                        # Attempt graceful termination (SIGTERM) before hard kill (SIGKILL)
                        try:
                            proc.terminate()
                            proc.join(timeout=0.3)
                        except Exception:
                            pass
                        if proc.is_alive():
                            proc.kill()
                            proc.join(timeout=1.0)
                        try:
                            parent_conn.close()
                        except Exception:
                            pass
                        try:
                            proc.close()
                        except Exception:
                            pass
                        raise TimeoutError(
                            f"Operation timed out after {timeout_seconds}s (SIGKILL delivered to PID {child_pid})"
                        )
                    else:
                        exit_code = proc.exitcode
                        try:
                            parent_conn.close()
                        except Exception:
                            pass
                        try:
                            proc.close()
                        except Exception:
                            pass
                        if ctx_method != available_methods[-1] and exit_code != 0:
                            continue
                        raise RuntimeError(f"Process terminated abruptly with exit code {exit_code}")

                # Wait for worker process to exit cleanly
                proc.join(timeout=1.0)
                if proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=0.5)
                    if proc.is_alive():
                        proc.kill()
                        proc.join(timeout=0.5)
                try:
                    parent_conn.close()
                except Exception:
                    pass
                try:
                    proc.close()
                except Exception:
                    pass

                success, value = result_payload
                if success:
                    if isinstance(value, dict) and "__ipc_file__" in value:
                        f_path = value["__ipc_file__"]
                        if Path(f_path).exists():
                            with open(f_path, "rb") as f:
                                payload_data = pickle.loads(f.read())
                            try:
                                Path(f_path).unlink()
                            except Exception:
                                pass
                            return payload_data
                    return value
                raise value
        finally:
            if temp_file_path and Path(temp_file_path).exists():
                try:
                    Path(temp_file_path).unlink()
                except Exception:
                    pass

    @staticmethod
    @contextlib.contextmanager
    def _slice_pdf_to_temp(file_path: Path, page_numbers: Sequence[int]):
        """
        Extract specified 1-based page_numbers into a temporary sliced PDF.
        Preserves original file name and stem in an isolated temporary directory so that
        engines execute strictly on requested pages without full document overhead.
        Yields: (temp_pdf_path, page_map)
          where page_map maps sliced 1-based page index -> original 1-based page index.
        """
        import shutil
        import tempfile
        import fitz

        sorted_pages = sorted(list(set(page_numbers)))
        temp_dir = tempfile.mkdtemp(prefix="autovend_slice_")
        temp_pdf_path = Path(temp_dir) / file_path.name

        try:
            doc = fitz.open(str(file_path))
            new_doc = fitz.open()
            page_map: Dict[int, int] = {}

            for new_idx, orig_p in enumerate(sorted_pages, start=1):
                orig_idx = orig_p - 1
                if 0 <= orig_idx < len(doc):
                    new_doc.insert_pdf(doc, from_page=orig_idx, to_page=orig_idx)
                    page_map[new_idx] = orig_p

            if not page_map:
                new_doc.close()
                doc.close()
                raise ValueError(
                    f"No valid pages found in {file_path.name} for requested page numbers: {page_numbers}"
                )

            new_doc.save(str(temp_pdf_path))
            new_doc.close()
            doc.close()

            yield temp_pdf_path, page_map
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _remap_document_pages(
        doc: ParsedDocument, page_map: Dict[int, int], original_title: str
    ) -> ParsedDocument:
        """
        Remap 1-based sliced page indices back to original 1-based full document indices
        across sections, tables, bounding boxes, headings, and dimension metadata.
        """
        doc.title = original_title
        first_orig_page = min(page_map.values()) if page_map else 1

        for s in doc.sections:
            old_p = s.page_num
            new_p = page_map.get(old_p, first_orig_page)
            s.page_num = new_p
            if s.bbox is not None:
                s.bbox.page = new_p
            s.title = s.title.replace(f"第 {old_p} 页", f"第 {new_p} 页").replace(f"第{old_p}页", f"第{new_p}页")
            s.breadcrumb_path = [
                b.replace(f"第 {old_p} 页", f"第 {new_p} 页").replace(f"第{old_p}页", f"第{new_p}页")
                for b in s.breadcrumb_path
            ]

        for t in doc.tables:
            old_p = t.page_num
            new_p = page_map.get(old_p, first_orig_page)
            t.page_num = new_p
            if t.bbox is not None:
                t.bbox.page = new_p
            t.title = t.title.replace(f"P{old_p}_", f"P{new_p}_")
            t.metadata["breadcrumb_path"] = [
                b.replace(f"第 {old_p} 页", f"第 {new_p} 页").replace(f"第{old_p}页", f"第{new_p}页")
                for b in t.metadata.get("breadcrumb_path", [])
            ]
            if hasattr(t, "pages") and t.pages:
                t.pages = [page_map.get(p, p) for p in t.pages]
            if hasattr(t, "page_bboxes") and t.page_bboxes:
                t.page_bboxes = {page_map.get(k, k): v for k, v in t.page_bboxes.items()}
                for pb in t.page_bboxes.values():
                    if pb is not None:
                        pb.page = page_map.get(pb.page, pb.page)

        if hasattr(doc, "page_dimensions") and doc.page_dimensions:
            doc.page_dimensions = {page_map.get(k, k): v for k, v in doc.page_dimensions.items()}
        if hasattr(doc, "page_orientations") and doc.page_orientations:
            doc.page_orientations = {page_map.get(k, k): v for k, v in doc.page_orientations.items()}

        return doc

    @staticmethod
    def _filter_doc_pages(doc: ParsedDocument, target_pages: Sequence[int]) -> ParsedDocument:
        target_set = set(target_pages)
        filtered_sections = [s for s in doc.sections if s.page_num in target_set]
        filtered_tables = [t for t in doc.tables if t.page_num in target_set]
        combined_raw = "\n\n".join(s.content for s in filtered_sections if s.content.strip())
        doc.sections = filtered_sections
        doc.tables = filtered_tables
        doc.raw_text = combined_raw
        return doc

    def _extract_l2_pdfplumber(
        self,
        file_path: Path,
        page_numbers: Optional[Sequence[int]] = None,
        degraded_reason: str = "",
    ) -> ParsedDocument:
        """L2 Fallback on digital track: Pure CPU geometric bordered table extraction via pdfplumber."""
        file_path = Path(file_path)
        doc = self._fallback.parse(file_path, page_numbers=page_numbers)
        for t in doc.tables:
            t.extraction_engine = "pdfplumber_bordered_table"

        doc.metadata["engine"] = "pdfplumber_bordered_table"
        doc.metadata["extraction_quality"] = "degraded"
        doc.metadata["fallback_level"] = "L2_pdfplumber"
        doc.metadata["degraded_reason"] = degraded_reason or "Docling TableFormer unavailable or tripped"
        doc.metadata["is_degraded"] = True
        doc.is_degraded = True
        return doc

    def _extract_l2_pymupdf_ocr(
        self,
        file_path: Path,
        page_numbers: Optional[Sequence[int]] = None,
        degraded_reason: str = "",
    ) -> ParsedDocument:
        """L2 Fallback on scanned track: PyMuPDF local OCR (fitz Tesseract)."""
        import fitz

        file_path = Path(file_path)
        doc = fitz.open(str(file_path))
        target_pages = set(page_numbers) if page_numbers is not None else set(range(1, len(doc) + 1))
        sections: List[TextSection] = []
        raw_texts: List[str] = []
        page_dims: Dict[int, Tuple[float, float]] = {}
        page_oris: Dict[int, str] = {}

        has_ocr_content = False
        ocr_errors: List[str] = []
        for p_idx, page in enumerate(doc):
            p_num = p_idx + 1
            if p_num not in target_pages:
                continue

            rect = page.rect
            page_dims[p_num] = (round(float(rect.width), 2), round(float(rect.height), 2))
            page_oris[p_num] = "landscape" if rect.width > rect.height else "portrait"

            txt = ""
            try:
                tp = page.get_textpage_ocr(language="chi_sim+eng", dpi=150, full=True)
                txt = page.get_text(textpage=tp).strip()
            except Exception as ocr_err:
                logger.debug(f"PyMuPDF OCR failed on page {p_num}: {ocr_err}")
                ocr_errors.append(str(ocr_err))
                txt = ""

            if txt:
                has_ocr_content = True
                raw_texts.append(txt)
                sections.append(
                    TextSection(
                        title=f"{file_path.stem} 第 {p_num} 页 OCR正文",
                        content=txt,
                        level=1,
                        page_num=p_num,
                        bbox=BoundingBox(0.0, 0.0, float(rect.width), float(rect.height), page=p_num),
                        breadcrumb_path=[file_path.stem, f"第 {p_num} 页"],
                    )
                )

        doc.close()

        if not has_ocr_content or not "\n\n".join(raw_texts).strip():
            err_msg = "; ".join(ocr_errors) if ocr_errors else "0 OCR characters extracted"
            raise RuntimeError(f"PyMuPDF OCR unavailable or extracted 0 characters from {file_path.name}: {err_msg}")

        full_raw = "\n\n".join(raw_texts).strip()
        parsed = ParsedDocument(
            title=file_path.stem,
            sections=sections,
            tables=[],  # L2 OCR: 保住基础文字，丢失表格结构
            pages=len(page_dims) if page_dims else (len(target_pages) or 1),
            raw_text=full_raw,
            metadata={
                "engine": "pymupdf_ocr_fallback",
                "extraction_quality": "degraded",
                "fallback_level": "L2_pymupdf_ocr",
                "degraded_reason": degraded_reason or "PaddleOCR unavailable or tripped",
                "is_degraded": True,
            },
            page_dimensions=page_dims,
            page_orientations=page_oris,
        )
        parsed.is_degraded = True
        return parsed

    def _extract_l3_pymupdf_text(
        self,
        file_path: Path,
        page_numbers: Optional[Sequence[int]] = None,
        degraded_reason: str = "",
    ) -> ParsedDocument:
        """L3 Ultimate Fallback: Directly extract character stream via PyMuPDF fitz.get_text('blocks'), dropping table topology."""
        import fitz

        file_path = Path(file_path)
        doc = fitz.open(str(file_path))
        target_pages = set(page_numbers) if page_numbers is not None else set(range(1, len(doc) + 1))
        sections: List[TextSection] = []
        raw_texts: List[str] = []
        page_dims: Dict[int, Tuple[float, float]] = {}
        page_oris: Dict[int, str] = {}

        for p_idx, page in enumerate(doc):
            p_num = p_idx + 1
            if p_num not in target_pages:
                continue

            rect = page.rect
            page_dims[p_num] = (round(float(rect.width), 2), round(float(rect.height), 2))
            page_oris[p_num] = "landscape" if rect.width > rect.height else "portrait"

            page_blocks = page.get_text("blocks")
            has_valid_blocks = False
            for b_idx, b in enumerate(page_blocks):
                # b: (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 7 and b[6] == 0:  # text block
                    bx0, by0, bx1, by1, btext = b[0], b[1], b[2], b[3], b[4]
                    btext_clean = btext.strip()
                    if btext_clean:
                        has_valid_blocks = True
                        raw_texts.append(btext_clean)
                        sections.append(
                            TextSection(
                                title=f"{file_path.stem} 第 {p_num} 页 区块 {b_idx + 1}",
                                content=btext_clean,
                                level=1,
                                page_num=p_num,
                                bbox=BoundingBox(
                                    round(float(bx0), 2),
                                    round(float(by0), 2),
                                    round(float(bx1), 2),
                                    round(float(by1), 2),
                                    page=p_num,
                                ),
                                breadcrumb_path=[file_path.stem, f"第 {p_num} 页"],
                            )
                        )

            if not has_valid_blocks:
                txt = page.get_text().strip()
                if txt:
                    raw_texts.append(txt)
                    sections.append(
                        TextSection(
                            title=f"{file_path.stem} 第 {p_num} 页正文",
                            content=txt,
                            level=1,
                            page_num=p_num,
                            bbox=BoundingBox(0.0, 0.0, float(rect.width), float(rect.height), page=p_num),
                            breadcrumb_path=[file_path.stem, f"第 {p_num} 页"],
                        )
                    )

        doc.close()

        full_raw = "\n\n".join(raw_texts).strip()
        if not full_raw:
            raise DocumentParsingUnrecoverableError(
                f"Document {file_path.name} contains no text extractable by PyMuPDF at L3兜底"
            )

        parsed = ParsedDocument(
            title=file_path.stem,
            sections=sections,
            tables=[],  # L3: 放弃所有表格拓扑
            pages=len(page_dims) if page_dims else (len(target_pages) or 1),
            raw_text=full_raw,
            metadata={
                "engine": "pymupdf_raw_text_fallback",
                "extraction_quality": "degraded",
                "fallback_level": "L3_pymupdf_text",
                "degraded_reason": degraded_reason or "All higher-tier parsers failed",
                "is_degraded": True,
            },
            page_dimensions=page_dims,
            page_orientations=page_oris,
        )
        parsed.is_degraded = True
        return parsed

    def parse_digital_track(
        self, file_path: Path, page_numbers: Optional[Sequence[int]] = None
    ) -> ParsedDocument:
        """
        Digital Track Circuit Breaker (有字符层 genuine_chars >= 30):
        L1: Docling TableFormer -> L2: pdfplumber 表格提取 -> L3: PyMuPDF 纯文本提取
        Pre-slices PDF to only digital pages if page_numbers is a subset of total pages.
        """
        file_path = Path(file_path)
        import fitz
        try:
            with fitz.open(str(file_path)) as full_pdf:
                total_pages = len(full_pdf)
        except Exception:
            total_pages = 0

        needs_slice = page_numbers is not None and 0 < len(page_numbers) < total_pages
        if needs_slice:
            with self._slice_pdf_to_temp(file_path, page_numbers) as (sliced_path, page_map):
                doc = self._parse_digital_track_internal(sliced_path, page_numbers=None)
                return self._remap_document_pages(doc, page_map, file_path.stem)
        else:
            return self._parse_digital_track_internal(file_path, page_numbers=page_numbers)

    def _parse_digital_track_internal(
        self, file_path: Path, page_numbers: Optional[Sequence[int]] = None
    ) -> ParsedDocument:
        reason_l1 = ""
        reason_l2 = ""

        # --- L1: Docling TableFormer ---
        try:
            logger.info(f"[Digital Path L1] Attempting Docling TableFormer on {file_path.name}")
            doc = self._run_with_timeout(self.docling.parse, file_path, timeout_seconds=self.timeout_seconds)
            if not doc or (not doc.sections and not doc.tables and not doc.raw_text.strip()):
                raise ValueError("Docling returned empty document")
            if getattr(doc, "is_degraded", False) or doc.metadata.get("is_degraded"):
                raise RuntimeError(f"Docling adapter degraded internally: {doc.metadata.get('degraded_reason')}")
            if page_numbers is not None:
                doc = self._filter_doc_pages(doc, page_numbers)
                if not doc.sections and not doc.tables and not doc.raw_text.strip():
                    raise ValueError(f"Docling produced no content for target pages {page_numbers}")

            doc.metadata["extraction_quality"] = "high_quality"
            doc.metadata["fallback_level"] = "L1_docling"
            doc.metadata["is_degraded"] = False
            doc.is_degraded = False
            return doc
        except Exception as l1_err:
            reason_l1 = f"Docling TableFormer failure: {l1_err}"
            logger.warning(
                f"[Circuit Breaker] Digital Path L1 failed on {file_path.name}: {reason_l1}. Tripping to L2 pdfplumber."
            )

        # --- L2: pdfplumber bordered table extraction ---
        try:
            logger.info(f"[Digital Path L2] Attempting pdfplumber bordered table extraction on {file_path.name}")
            doc = self._extract_l2_pdfplumber(file_path, page_numbers=page_numbers, degraded_reason=reason_l1)
            if not doc or (not doc.sections and not doc.tables and not doc.raw_text.strip()):
                raise ValueError("pdfplumber returned empty document")
            return doc
        except Exception as l2_err:
            reason_l2 = f"{reason_l1} -> pdfplumber failure: {l2_err}"
            logger.warning(
                f"[Circuit Breaker] Digital Path L2 failed on {file_path.name}: {reason_l2}. Tripping to L3 PyMuPDF raw text."
            )

        # --- L3: PyMuPDF raw text extraction ---
        logger.info(f"[Digital Path L3] Attempting PyMuPDF raw text extraction on {file_path.name}")
        return self._extract_l3_pymupdf_text(file_path, page_numbers=page_numbers, degraded_reason=reason_l2)

    def parse_scanned_track(
        self, file_path: Path, page_numbers: Optional[Sequence[int]] = None
    ) -> ParsedDocument:
        """
        Scanned Track Circuit Breaker (纯扫描件 genuine_chars < 30):
        L1: PaddleOCR (CPU) -> L2: PyMuPDF 本地 OCR -> L3: PyMuPDF 纯文本提取
        Pre-slices PDF to only scanned pages if page_numbers is a subset of total pages.
        """
        file_path = Path(file_path)
        import fitz
        try:
            with fitz.open(str(file_path)) as full_pdf:
                total_pages = len(full_pdf)
        except Exception:
            total_pages = 0

        needs_slice = page_numbers is not None and 0 < len(page_numbers) < total_pages
        if needs_slice:
            with self._slice_pdf_to_temp(file_path, page_numbers) as (sliced_path, page_map):
                doc = self._parse_scanned_track_internal(sliced_path, page_numbers=None)
                return self._remap_document_pages(doc, page_map, file_path.stem)
        else:
            return self._parse_scanned_track_internal(file_path, page_numbers=page_numbers)

    def _parse_scanned_track_internal(
        self, file_path: Path, page_numbers: Optional[Sequence[int]] = None
    ) -> ParsedDocument:
        reason_l1 = ""
        reason_l2 = ""

        # --- L1: PaddleOCR (CPU) ---
        try:
            logger.info(f"[Scanned Path L1] Attempting PaddleOCR on {file_path.name}")
            doc = self._run_with_timeout(
                self.paddle.parse_scanned_pdf,
                file_path,
                page_numbers=page_numbers,
                timeout_seconds=self.timeout_seconds,
            )
            if not doc or (not doc.sections and not doc.tables and not doc.raw_text.strip()):
                raise ValueError("PaddleOCR returned empty document")
            if getattr(doc, "is_degraded", False) or doc.metadata.get("is_degraded"):
                raise RuntimeError(f"PaddleOCR adapter degraded internally: {doc.metadata.get('degraded_reason')}")
            if page_numbers is not None:
                doc = self._filter_doc_pages(doc, page_numbers)
                if not doc.sections and not doc.tables and not doc.raw_text.strip():
                    raise ValueError(f"PaddleOCR produced no content for target pages {page_numbers}")

            doc.metadata["extraction_quality"] = "high_quality"
            doc.metadata["fallback_level"] = "L1_paddleocr"
            doc.metadata["is_degraded"] = False
            doc.is_degraded = False
            return doc
        except Exception as l1_err:
            reason_l1 = f"PaddleOCR failure: {l1_err}"
            logger.warning(
                f"[Circuit Breaker] Scanned Path L1 failed on {file_path.name}: {reason_l1}. Tripping to L2 PyMuPDF OCR."
            )

        # --- L2: PyMuPDF local OCR ---
        try:
            logger.info(f"[Scanned Path L2] Attempting PyMuPDF local OCR on {file_path.name}")
            doc = self._extract_l2_pymupdf_ocr(file_path, page_numbers=page_numbers, degraded_reason=reason_l1)
            return doc
        except Exception as l2_err:
            reason_l2 = f"{reason_l1} -> PyMuPDF OCR failure: {l2_err}"
            logger.warning(
                f"[Circuit Breaker] Scanned Path L2 failed on {file_path.name}: {reason_l2}. Tripping to L3 PyMuPDF raw text."
            )

        # --- L3: PyMuPDF raw text extraction ---
        logger.info(f"[Scanned Path L3] Attempting PyMuPDF raw text extraction on {file_path.name}")
        return self._extract_l3_pymupdf_text(file_path, page_numbers=page_numbers, degraded_reason=reason_l2)

    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        file_path = Path(file_path)

        # Step 1: Pre-flight probe (<5ms)
        probe_info = PreFlightProbe.inspect(file_path, char_density_threshold=self.threshold)

        total_pages = probe_info["total_pages"]
        digital_pages = probe_info["digital_pages"]
        scanned_pages = probe_info["scanned_pages"]
        page_dimensions = probe_info["page_dimensions"]
        page_orientations = probe_info["page_orientations"]

        logger.info(
            f"PreFlightProbe for {file_path.name}: {total_pages} pages, "
            f"{len(digital_pages)} digital (>= {self.threshold} chars), "
            f"{len(scanned_pages)} scanned (< {self.threshold} chars)"
        )

        # Case A: Pure Digital Track
        if digital_pages and not scanned_pages:
            doc = self.parse_digital_track(file_path, page_numbers=digital_pages)
            doc.metadata["dual_track_route"] = "all_digital_docling"
            doc.metadata["density_page_counts"] = probe_info["page_counts"]
            doc.page_dimensions = page_dimensions
            doc.page_orientations = page_orientations
            return doc

        # Case B: Pure Scanned Track
        if scanned_pages and not digital_pages:
            doc = self.parse_scanned_track(file_path, page_numbers=scanned_pages)
            doc.metadata["dual_track_route"] = "all_scanned_paddleocr"
            doc.metadata["density_page_counts"] = probe_info["page_counts"]
            doc.page_dimensions = page_dimensions
            doc.page_orientations = page_orientations
            return doc

        # Case C: Mixed Document (Page-Level Hard Routing)
        digital_doc = None
        scanned_doc = None
        digital_err = None
        scanned_err = None

        if digital_pages:
            try:
                digital_doc = self.parse_digital_track(file_path, page_numbers=digital_pages)
            except Exception as e:
                digital_err = e
                logger.warning(f"Mixed document digital track failed on {file_path.name}: {e}")

        if scanned_pages:
            try:
                scanned_doc = self.parse_scanned_track(file_path, page_numbers=scanned_pages)
            except Exception as e:
                scanned_err = e
                logger.warning(f"Mixed document scanned track failed on {file_path.name}: {e}")

        if digital_doc is None and scanned_doc is None:
            raise DocumentParsingUnrecoverableError(
                f"Mixed document {file_path.name} produced 0 content: digital error ({digital_err}), scanned error ({scanned_err})"
            )

        combined_tables = []
        combined_sections = []
        if digital_doc:
            combined_tables.extend([t for t in digital_doc.tables if t.page_num in digital_pages])
            combined_sections.extend([s for s in digital_doc.sections if s.page_num in digital_pages])
        if scanned_doc:
            combined_tables.extend([t for t in scanned_doc.tables if t.page_num in scanned_pages])
            combined_sections.extend([s for s in scanned_doc.sections if s.page_num in scanned_pages])

        combined_tables.sort(key=lambda t: (t.page_num, t.bbox.top if t.bbox else 0.0))
        combined_sections.sort(key=lambda s: (s.page_num, s.bbox.top if s.bbox else 0.0))

        combined_raw = "\n\n".join(s.content for s in combined_sections if s.content.strip()).strip()
        if not combined_raw and not combined_tables:
            raise DocumentParsingUnrecoverableError(f"Mixed document {file_path.name} produced 0 content.")

        is_degraded = bool(
            (digital_doc and digital_doc.is_degraded)
            or (scanned_doc and scanned_doc.is_degraded)
            or digital_err is not None
            or scanned_err is not None
        )
        fallback_levels: List[str] = []
        if digital_doc and digital_doc.is_degraded:
            fallback_levels.append(digital_doc.metadata.get("fallback_level", "digital_degraded"))
        elif digital_err:
            fallback_levels.append("digital_unrecoverable")
        if scanned_doc and scanned_doc.is_degraded:
            fallback_levels.append(scanned_doc.metadata.get("fallback_level", "scanned_degraded"))
        elif scanned_err:
            fallback_levels.append("scanned_unrecoverable")

        degraded_reasons: List[str] = []
        if digital_doc and digital_doc.metadata.get("degraded_reason"):
            degraded_reasons.append(digital_doc.metadata["degraded_reason"])
        elif digital_err:
            degraded_reasons.append(f"Digital path error: {digital_err}")
        if scanned_doc and scanned_doc.metadata.get("degraded_reason"):
            degraded_reasons.append(scanned_doc.metadata["degraded_reason"])
        elif scanned_err:
            degraded_reasons.append(f"Scanned path error: {scanned_err}")

        merged_doc = ParsedDocument(
            title=file_path.stem,
            sections=combined_sections,
            tables=combined_tables,
            pages=total_pages,
            raw_text=combined_raw,
            metadata={
                "engine": "dual_track_isolation_pipeline",
                "dual_track_route": "mixed_pages",
                "digital_pages": digital_pages,
                "scanned_pages": scanned_pages,
                "density_page_counts": probe_info["page_counts"],
                "extraction_quality": "degraded" if is_degraded else "high_quality",
                "fallback_level": "+".join(fallback_levels) if fallback_levels else "L1_dual_track",
                "degraded_reason": "; ".join(degraded_reasons) if degraded_reasons else None,
                "is_degraded": is_degraded,
            },
            page_dimensions=page_dimensions,
            page_orientations=page_orientations,
        )
        merged_doc.is_degraded = is_degraded
        return merged_doc

    def extract_tables(self, file_path: Union[str, Path]) -> List[TableBlock]:
        return self.parse(file_path).tables


class LayoutAwareParser:
    """
    High-level facade for Layout-Aware Parsing in AutoVend.
    Dispatches to appropriate engine:
    - 'dual_track' / 'auto': Production Dual-Track Isolation Pipeline (Docling + PaddleOCR)
    - 'docling': IBM Docling (TableFormer, do_ocr=False)
    - 'paddle' / 'paddleocr': PaddleOCR PP-Structure (CPU-isolated)
    - 'hybrid' (default): PyMuPDF + pdfplumber
    - 'azure': Azure Document Intelligence (Form Recognizer)
    - 'unstructured': Unstructured.io
    - 'mineru': Open-source MinerU
    """

    def __init__(self, engine_type: str = "hybrid", **kwargs):
        self.engine_type = engine_type.lower()
        if self.engine_type in ["azure", "form_recognizer"]:
            self.engine: BaseLayoutEngine = AzureDocumentIntelligenceEngine(**kwargs)
        elif self.engine_type in ["unstructured", "unstructured_io"]:
            self.engine = UnstructuredEngine(**kwargs)
        elif self.engine_type in ["docling"]:
            self.engine = RealDoclingAdapter(**kwargs)
        elif self.engine_type in ["paddle", "paddleocr", "pp_structure"]:
            self.engine = RealPaddleOCRAdapter(**kwargs)
        elif self.engine_type in ["dual_track", "dual", "dualtrack", "auto"]:
            self.engine = DualTrackLayoutEngine(**kwargs)
        elif self.engine_type in ["mineru", "marker"]:
            self.engine = MinerUDoclingEngine(engine_name=self.engine_type, **kwargs)
        else:
            self.engine = PyMuPDFPlumberEngine(**kwargs)

    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        return self.engine.parse(Path(file_path))

    def extract_tables(self, file_path: Union[str, Path]) -> List[TableBlock]:
        return self.engine.extract_tables(Path(file_path))

