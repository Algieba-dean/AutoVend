"""
Hierarchical & Semantic Document Chunker for AutoVend (src/ingestion/hierarchical_chunker.py).

Implements:
1. Table Independent Chunking:
   - Tables are kept atomic (never cut across arbitrary token limits).
   - Context Enrichment: Prepend structured metadata (document title, vehicle model, section heading, table title).
2. Parent-Child Document Splitting:
   - Parent Chunks (approx. 800 - 1000 tokens): Rich, cohesive context for LLM generation without truncation.
   - Child Chunks (approx. 150 - 250 tokens): Fine-grained slices for exact dense/sparse vector retrieval.
   - Bidirectional linkage (parent_id on children, child_ids on parent).
"""

import logging
import re
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.ingestion.layout_parser import ParsedDocument, TableBlock, TextSection

logger = logging.getLogger(__name__)


class ChunkType(str, Enum):
    PARENT = "parent"
    CHILD = "child"
    TABLE = "table"


class Chunk:
    """Represents a text or table chunk with rich hierarchical metadata."""

    def __init__(
        self,
        chunk_id: str,
        content: str,
        chunk_type: ChunkType,
        parent_id: Optional[str] = None,
        child_ids: Optional[List[str]] = None,
        token_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.chunk_id = chunk_id
        self.content = content
        self.chunk_type = chunk_type
        self.parent_id = parent_id
        self.child_ids = child_ids or []
        self.token_count = token_count or self.estimate_tokens(content)
        self.metadata = metadata or {}

    @property
    def page_number(self) -> int:
        return int(self.metadata.get("page_number", self.metadata.get("page_num", 1)))

    @property
    def bounding_box(self) -> List[float]:
        bbox = self.metadata.get("bounding_box")
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            return [float(x) for x in bbox]
        raw_b = self.metadata.get("bbox")
        if isinstance(raw_b, dict) and "x0" in raw_b and "top" in raw_b:
            return [float(raw_b["x0"]), float(raw_b["top"]), float(raw_b["x1"]), float(raw_b["bottom"])]
        return [0.0, 0.0, 0.0, 0.0]

    @property
    def heading_breadcrumb(self) -> List[str]:
        return list(self.metadata.get("heading_breadcrumb", self.metadata.get("breadcrumb_path", [])))

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count across mixed Chinese & English:
        Chinese characters: ~1-1.5 chars per token
        English words: ~0.75 words per token
        """
        if not text:
            return 0
        chinese_chars = len(re.findall(r"[\u4e00-\u9fa5]", text))
        non_chinese = re.sub(r"[\u4e00-\u9fa5]", " ", text)
        english_words = len(non_chinese.split())
        return max(1, int(chinese_chars * 0.8 + english_words * 1.3))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "chunk_type": self.chunk_type.value,
            "token_count": self.token_count,
            "content": self.content,
            "page_number": self.page_number,
            "bounding_box": self.bounding_box,
            "heading_breadcrumb": self.heading_breadcrumb,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"<Chunk {self.chunk_id} ({self.chunk_type.value}, ~{self.token_count} tokens)>"


class HierarchicalChunker:
    """
    Splits layout-aware parsed documents into hierarchical Parent-Child chunks
    and context-enriched atomic table chunks.
    """

    def __init__(
        self,
        parent_max_tokens: int = 1000,
        parent_min_tokens: int = 300,
        child_max_tokens: int = 200,
        child_overlap_tokens: int = 40,
    ):
        self.parent_max_tokens = parent_max_tokens
        self.parent_min_tokens = parent_min_tokens
        self.child_max_tokens = child_max_tokens
        self.child_overlap_tokens = child_overlap_tokens

    def chunk_document(self, doc: ParsedDocument) -> Dict[str, List[Chunk]]:
        """
        Process a ParsedDocument into parents, children, and enriched table chunks.

        Returns:
            Dict with keys:
            - 'parents': List of Parent chunks (large context, ~1000 tokens)
            - 'children': List of Child chunks (retrieval units, ~200 tokens)
            - 'tables': List of atomic table chunks
            - 'all': Unified list of all indexed chunks
        """
        parent_chunks: List[Chunk] = []
        child_chunks: List[Chunk] = []
        table_chunks: List[Chunk] = []

        # 1. Process Tables Independently with Context Enrichment
        for idx, tbl in enumerate(doc.tables):
            t_chunk = self._create_enriched_table_chunk(doc, tbl, idx)
            table_chunks.append(t_chunk)

            # Table is also a primary Parent Chunk
            parent_chunks.append(t_chunk)

            # Generate fine-grained Child Chunks for the table (e.g. per key row or summary)
            t_children = self._create_table_child_chunks(t_chunk, tbl, doc)
            child_chunks.extend(t_children)
            t_chunk.child_ids = [c.chunk_id for c in t_children]

        # 2. Process Hierarchical Text Sections
        for sec in doc.sections:
            sec_parents, sec_children = self._chunk_section(doc, sec)
            parent_chunks.extend(sec_parents)
            child_chunks.extend(sec_children)

        # Fallback if no sections were parsed
        if not doc.sections and doc.raw_text.strip():
            raw_sec = TextSection(title="Full Document", content=doc.raw_text)
            sec_parents, sec_children = self._chunk_section(doc, raw_sec)
            parent_chunks.extend(sec_parents)
            child_chunks.extend(sec_children)

        all_chunks = parent_chunks + child_chunks

        return {
            "parents": parent_chunks,
            "children": child_chunks,
            "tables": table_chunks,
            "all": all_chunks,
        }

    def _create_enriched_table_chunk(
        self, doc: ParsedDocument, tbl: TableBlock, table_idx: int
    ) -> Chunk:
        """
        Atomic table chunk with rich injected header context:
        [文档主题: {model} | 所属章节: {section} | 表格类型: 结构化参数表 | 坐标: {bbox}]
        followed by complete Markdown table representation.
        """
        doc_topic = doc.vehicle_model or doc.title or "车辆规格参数"
        section_title = tbl.title or "规格配置"
        table_id = f"tbl_{uuid.uuid4().hex[:10]}"

        # Context Header Injection (Context Enrichment)
        bbox_repr = f"[{tbl.bbox.x0}, {tbl.bbox.top}, {tbl.bbox.x1}, {tbl.bbox.bottom}]" if tbl.bbox else "未提供"
        pages_repr = (
            f"第 {min(tbl.pages)} 至 {max(tbl.pages)} 页 (跨页缝合)"
            if getattr(tbl, "is_stitched", False) and len(getattr(tbl, "pages", [])) > 1
            else f"第 {tbl.page_num} 页"
        )
        tbl_meta = getattr(tbl, "metadata", {}) or {}
        extra_lines = []
        if tbl_meta.get("sheet_name"):
            extra_lines.append(f"• 工作表名称: {tbl_meta['sheet_name']}\n")
        if tbl_meta.get("slide_index"):
            extra_lines.append(f"• 幻灯片序号: Slide {tbl_meta['slide_index']}\n")
        if doc.metadata.get("format"):
            extra_lines.append(f"• 原始文档格式: {doc.metadata['format']}\n")
        format_extra_str = "".join(extra_lines)

        header_context = (
            f"【结构化元数据】\n"
            f"• 车型/文档主题: {doc_topic}\n"
            f"• 所属章节/功能模块: {section_title}\n"
            f"• 数据形态: 结构化二维参数表 (Markdown)\n"
            f"• 所在页码: {pages_repr}\n"
            + format_extra_str
            + f"• 跨页状态: {'已完成跨页自动拼接' if getattr(tbl, 'is_stitched', False) else '单页完整'}\n"
            f"• 边框坐标 BBox: {bbox_repr}\n"
            f"─────────────────────────────\n"
        )

        table_md = tbl.to_markdown(include_title=True)
        full_content = header_context + table_md

        bbox_coords = [tbl.bbox.x0, tbl.bbox.top, tbl.bbox.x1, tbl.bbox.bottom] if tbl.bbox else [0.0, 0.0, 0.0, 0.0]
        crumbs = tbl.metadata.get("breadcrumb_path") or [doc_topic, section_title]

        metadata = {
            "vehicle_model": doc_topic,
            "section_title": section_title,
            "is_table": True,
            "is_stitched": getattr(tbl, "is_stitched", False),
            "pages": getattr(tbl, "pages", [tbl.page_num]),
            "table_index": table_idx,
            "page_num": tbl.page_num,
            "page_number": tbl.page_num,
            "bbox": tbl.bbox.to_dict() if tbl.bbox else None,
            "bounding_box": bbox_coords,
            "heading_breadcrumb": crumbs,
            "breadcrumb_path": crumbs,
            "row_count": tbl.row_count,
            "col_count": tbl.col_count,
            "headers": tbl.headers,
            "records": tbl.to_records()[:10] if hasattr(tbl, "to_records") else [],
            "extraction_engine": tbl.extraction_engine,
            **tbl_meta,
        }

        return Chunk(
            chunk_id=table_id,
            content=full_content,
            chunk_type=ChunkType.TABLE,
            parent_id=None,  # Table itself acts as parent
            metadata=metadata,
        )

    def _create_table_child_chunks(
        self, parent_table_chunk: Chunk, tbl: TableBlock, doc: ParsedDocument
    ) -> List[Chunk]:
        """
        Create 200-token child chunks from a table for high-precision retrieval:
        groups 2-3 rows together with the column headers.
        """
        children: List[Chunk] = []
        if not tbl.body_rows:
            # Single child covering the table
            child = Chunk(
                chunk_id=f"c_{uuid.uuid4().hex[:10]}",
                content=parent_table_chunk.content[:400],
                chunk_type=ChunkType.CHILD,
                parent_id=parent_table_chunk.chunk_id,
                metadata={**parent_table_chunk.metadata, "is_table_child": True},
            )
            return [child]

        headers_str = " | ".join(tbl.headers) if tbl.headers else ""
        vehicle_model = doc.vehicle_model or doc.title
        breadcrumbs = tbl.metadata.get("breadcrumb_path", [])
        if breadcrumbs and len(breadcrumbs) > 1:
            breadcrumb_label = " > ".join(breadcrumbs)
        else:
            breadcrumb_label = tbl.title or "参数配置"

        # Group rows into small chunks (~150-200 tokens)
        row_step = max(1, 3)
        for r_start in range(0, len(tbl.body_rows), row_step):
            slice_rows = tbl.body_rows[r_start : r_start + row_step]
            rows_formatted = []
            for r in slice_rows:
                rows_formatted.append(" | ".join(r))

            child_content = (
                f"[{vehicle_model} - {breadcrumb_label} - 第{r_start+1}至{r_start+len(slice_rows)}项]\n"
                f"表头: {headers_str}\n"
                + "\n".join(rows_formatted)
            )

            child_id = f"c_{uuid.uuid4().hex[:10]}"
            child = Chunk(
                chunk_id=child_id,
                content=child_content,
                chunk_type=ChunkType.CHILD,
                parent_id=parent_table_chunk.chunk_id,
                metadata={
                    **parent_table_chunk.metadata,
                    "is_table_child": True,
                    "row_range": [r_start, r_start + len(slice_rows)],
                },
            )
            children.append(child)

        # Generate child chunk for table footnotes / fine print if present
        if getattr(tbl, "footnotes", None):
            fn_text = "\n".join(tbl.footnotes)
            fn_child_content = (
                f"[{vehicle_model} - {breadcrumb_label} - 特别说明与附注条款]\n"
                f"{fn_text}"
            )
            fn_child_id = f"c_{uuid.uuid4().hex[:10]}"
            fn_child = Chunk(
                chunk_id=fn_child_id,
                content=fn_child_content,
                chunk_type=ChunkType.CHILD,
                parent_id=parent_table_chunk.chunk_id,
                metadata={
                    **parent_table_chunk.metadata,
                    "is_table_child": True,
                    "is_footnote": True,
                },
            )
            children.append(fn_child)

        return children

    def _chunk_section(
        self, doc: ParsedDocument, sec: TextSection
    ) -> Tuple[List[Chunk], List[Chunk]]:
        """
        Split a TextSection into Parent chunks (~1000 tokens) and Child chunks (~200 tokens).
        """
        parents: List[Chunk] = []
        children: List[Chunk] = []

        paragraphs = [p.strip() for p in sec.content.split("\n\n") if p.strip()]
        if not paragraphs:
            return parents, children

        vehicle_model = doc.vehicle_model or doc.title or "汽车资料"

        # 1. Assemble Parent Chunks
        current_parent_paras: List[str] = []
        current_tokens = 0

        parent_groups: List[str] = []
        for p in paragraphs:
            p_tokens = Chunk.estimate_tokens(p)
            if current_tokens + p_tokens > self.parent_max_tokens and current_parent_paras:
                parent_groups.append("\n\n".join(current_parent_paras))
                current_parent_paras = [p]
                current_tokens = p_tokens
            else:
                current_parent_paras.append(p)
                current_tokens += p_tokens

        if current_parent_paras:
            parent_groups.append("\n\n".join(current_parent_paras))

        breadcrumbs = getattr(sec, "breadcrumb_path", None)
        has_deep_hierarchy = bool(breadcrumbs and len(breadcrumbs) > 1)
        breadcrumb_part = f" | 路径: {' > '.join(breadcrumbs)}" if has_deep_hierarchy else ""
        breadcrumb_str = " > ".join(breadcrumbs) if has_deep_hierarchy else sec.title

        sec_meta = dict(getattr(sec, "metadata", {}) or {})
        doc_format = getattr(doc, "metadata", {}).get("format")
        if doc_format and "format" not in sec_meta:
            sec_meta["format"] = doc_format
        sec_bbox_coords = [sec.bbox.x0, sec.bbox.top, sec.bbox.x1, sec.bbox.bottom] if getattr(sec, "bbox", None) else [0.0, 0.0, 0.0, 0.0]
        crumbs = breadcrumbs or [sec.title]

        for p_idx, p_text in enumerate(parent_groups):
            p_id = f"p_{uuid.uuid4().hex[:10]}"
            enriched_parent_content = (
                f"【章节: {sec.title}{breadcrumb_part} | 车型: {vehicle_model} | 级别: H{sec.level}】\n\n{p_text}"
            )

            parent_chunk = Chunk(
                chunk_id=p_id,
                content=enriched_parent_content,
                chunk_type=ChunkType.PARENT,
                metadata={
                    "vehicle_model": vehicle_model,
                    "section_title": sec.title,
                    "breadcrumb_path": crumbs,
                    "heading_breadcrumb": crumbs,
                    "section_level": sec.level,
                    "page_num": sec.page_num,
                    "page_number": sec.page_num,
                    "bbox": sec.bbox.to_dict() if getattr(sec, "bbox", None) else None,
                    "bounding_box": sec_bbox_coords,
                    "is_table": False,
                    **sec_meta,
                },
            )
            parents.append(parent_chunk)

            # 2. Slice Parent into Child Chunks (~200 tokens each with overlap)
            sec_child_chunks = self._slice_into_children(parent_chunk, p_text, vehicle_model, breadcrumb_str)
            children.extend(sec_child_chunks)
            parent_chunk.child_ids = [c.chunk_id for c in sec_child_chunks]

        return parents, children

    def _slice_into_children(
        self, parent_chunk: Chunk, raw_text: str, vehicle_model: str, section_title: str
    ) -> List[Chunk]:
        """
        Slice text into ~200 tokens child chunks with sliding window overlap.
        """
        children: List[Chunk] = []

        # Sentence split (supports Chinese punctuation and English sentences ending with period/exclamation/question mark followed by whitespace)
        sentences = re.split(r"([。！？\n]+|[.!?]\s+)", raw_text)
        reconstructed_sents = []
        for i in range(0, len(sentences) - 1, 2):
            reconstructed_sents.append(sentences[i] + sentences[i + 1])
        if len(sentences) % 2 == 1 and sentences[-1]:
            reconstructed_sents.append(sentences[-1])

        if not reconstructed_sents:
            reconstructed_sents = [raw_text]

        # Further subdivide any sentence that by itself exceeds child_max_tokens
        final_sents: List[str] = []
        for s in reconstructed_sents:
            if Chunk.estimate_tokens(s) > self.child_max_tokens:
                sub_parts = re.split(r"([，；,;]\s*)", s)
                reconstructed_subs = []
                for j in range(0, len(sub_parts) - 1, 2):
                    reconstructed_subs.append(sub_parts[j] + sub_parts[j + 1])
                if len(sub_parts) % 2 == 1 and sub_parts[-1]:
                    reconstructed_subs.append(sub_parts[-1])

                for sub in reconstructed_subs:
                    if Chunk.estimate_tokens(sub) > self.child_max_tokens:
                        step = max(40, int(self.child_max_tokens * 1.5))
                        for k in range(0, len(sub), step):
                            final_sents.append(sub[k : k + step])
                    else:
                        final_sents.append(sub)
            else:
                final_sents.append(s)

        curr_child_sents: List[str] = []
        curr_tokens = 0

        for sent in final_sents:
            s_tokens = Chunk.estimate_tokens(sent)
            if curr_tokens + s_tokens > self.child_max_tokens and curr_child_sents:
                child_body = "".join(curr_child_sents).strip()
                child_text = f"[{vehicle_model} > {section_title}]\n{child_body}"
                c_id = f"c_{uuid.uuid4().hex[:10]}"
                children.append(
                    Chunk(
                        chunk_id=c_id,
                        content=child_text,
                        chunk_type=ChunkType.CHILD,
                        parent_id=parent_chunk.chunk_id,
                        metadata={
                            **parent_chunk.metadata,
                            "parent_chunk_id": parent_chunk.chunk_id,
                        },
                    )
                )

                # Overlap: keep trailing sentences approximating child_overlap_tokens
                overlap_sents: List[str] = []
                overlap_tokens = 0
                for prev_s in reversed(curr_child_sents):
                    prev_tok = Chunk.estimate_tokens(prev_s)
                    if overlap_tokens + prev_tok <= self.child_overlap_tokens:
                        overlap_sents.insert(0, prev_s)
                        overlap_tokens += prev_tok
                    else:
                        break

                curr_child_sents = overlap_sents + [sent]
                curr_tokens = overlap_tokens + s_tokens
            else:
                curr_child_sents.append(sent)
                curr_tokens += s_tokens

        if curr_child_sents:
            child_body = "".join(curr_child_sents).strip()
            child_text = f"[{vehicle_model} > {section_title}]\n{child_body}"
            c_id = f"c_{uuid.uuid4().hex[:10]}"
            children.append(
                Chunk(
                    chunk_id=c_id,
                    content=child_text,
                    chunk_type=ChunkType.CHILD,
                    parent_id=parent_chunk.chunk_id,
                    metadata={
                        **parent_chunk.metadata,
                        "parent_chunk_id": parent_chunk.chunk_id,
                    },
                )
            )

        return children
