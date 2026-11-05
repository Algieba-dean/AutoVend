"""
Lexical BM25 index over the vehicle catalogue.

Complements dense retrieval: embeddings generalise ("电动车" ≈ "Battery Electric
Vehicle") but blur exact tokens, so a query naming a specific model, trim or
brand can rank below a semantically-similar-but-wrong car. BM25 is the opposite
— literal and unforgiving. Fusing the two covers both failure modes; see
`src/retrieval/fusion.py`.

**Corpus source is SQLite, not the TOML files or ChromaDB.** The label columns
already hold every value the documents are built from, and reading them keeps
this index buildable without torch or a vector store — which is what lets the
CI evaluation gate run in seconds instead of downloading a 2GB model.
"""

import json
import re
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Columns excluded from the lexical document — near-constant values (every car
#: has ABS) add no discriminative signal and dilute BM25's term weighting.
_LOW_SIGNAL_COLUMNS = frozenset({"abs", "esp", "city_commuting", "cargo_capability"})

_LATIN_TOKEN = re.compile(r"[a-z0-9]+")
_CJK = re.compile(r"[一-鿿]")


def tokenize(text: str) -> List[str]:
    """
    Mixed Chinese/English tokenizer.

    Latin runs split on non-alphanumerics; CJK runs go through jieba. Falling
    back to per-character bigrams when jieba is unavailable keeps the index
    buildable in a minimal environment rather than failing the whole gate.
    """
    lowered = text.lower()
    tokens = _LATIN_TOKEN.findall(lowered)

    cjk_text = "".join(_CJK.findall(lowered))
    if cjk_text:
        try:
            import jieba

            tokens.extend(t for t in jieba.cut(cjk_text) if t.strip())
        except ImportError:  # pragma: no cover - environment-dependent
            tokens.extend(cjk_text[i : i + 2] for i in range(len(cjk_text) - 1))
            tokens.extend(cjk_text)
    return tokens


class BM25Index:
    """Persistent BM25 index keyed by car_model."""

    def __init__(self, car_models: Sequence[str], corpus_tokens: Sequence[Sequence[str]]):
        from rank_bm25 import BM25Okapi

        self.car_models = list(car_models)
        self.corpus_tokens = [list(t) for t in corpus_tokens]
        self._bm25 = BM25Okapi(self.corpus_tokens)

    def __len__(self) -> int:
        return len(self.car_models)

    def search(self, query_text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Return (car_model, score) pairs ranked best first, applying query-time field boost for model hits."""
        query_tokens = tokenize(query_text)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        q_lower = query_text.lower()
        scored_pairs = []
        for model, score in zip(self.car_models, scores):
            if score <= 0:
                continue
            boosted = float(score)
            if model:
                m_lower = model.lower()
                # Clean query-time field boost for exact or sub-name vehicle model hit
                if m_lower in q_lower or ("-" in m_lower and m_lower.split("-", 1)[1] in q_lower):
                    boosted *= 1.25
            scored_pairs.append((model, boosted))

        ranked = sorted(scored_pairs, key=lambda p: p[1], reverse=True)
        return ranked[:top_k]

    # ── persistence (OWASP CWE-502 Safe JSON) ─────────────────────────

    def save(self, path: Optional[str] = None) -> Path:
        target = Path(path or config.bm25_index_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "format": "safe_json",
            "car_models": self.car_models,
            "corpus_tokens": self.corpus_tokens,
        }
        with target.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        logger.info(f"BM25 索引已安全保存 (Safe JSON): {target} ({len(self)} 条)")
        return target

    @classmethod
    def load(cls, path: Optional[str] = None) -> "BM25Index":
        target = Path(path or config.bm25_index_path)
        with target.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, dict) or "car_models" not in payload or "corpus_tokens" not in payload:
            raise ValueError(f"Invalid BM25 index payload structure in {target}")
        index = cls(payload["car_models"], payload["corpus_tokens"])
        logger.info(f"BM25 索引已安全加载: {target} ({len(index)} 条)")
        return index

    @classmethod
    def build(cls, db=None) -> "BM25Index":
        """Build from the SQLite catalogue, importing from TOML if it is empty."""
        from src.filter.vehicle_db import VehicleDB

        db = db or VehicleDB()
        if db.count() == 0:
            logger.info("SQLite 数据库为空，先从 TOML 导入")
            db.import_from_toml_dir()

        rows = db.conn.execute("SELECT * FROM vehicles").fetchall()
        columns = [d[0] for d in db.conn.execute("SELECT * FROM vehicles LIMIT 1").description]

        car_models: List[str] = []
        corpus: List[List[str]] = []
        for row in rows:
            record = dict(zip(columns, row))
            car_model = record.get("car_model") or ""
            if not car_model:
                continue
            car_models.append(car_model)
            corpus.append(tokenize(_document_text(record)))

        logger.info(f"BM25 索引构建完成: {len(car_models)} 条")
        return cls(car_models, corpus)

    @classmethod
    def load_or_build(cls, path: Optional[str] = None) -> "BM25Index":
        """Load the persisted index, building and saving it on first use."""
        target = Path(path or config.bm25_index_path)
        if target.exists():
            try:
                return cls.load(target)
            except Exception as exc:
                logger.warning(f"BM25 索引损坏，重建: {exc}")
        index = cls.build()
        index.save(target)
        return index


def _document_text(record: dict) -> str:
    """
    Flatten one catalogue row into a lexical document.
    """
    car_model = record.get("car_model") or ""
    parts = [car_model] if car_model else []
    for column, value in record.items():
        if column == "car_model" or column in _LOW_SIGNAL_COLUMNS:
            continue
        if value and str(value).strip() and str(value).lower() not in ("none", "no"):
            parts.append(str(value))
    return " ".join(parts)


class SQLiteFTS5Index:
    """
    Production-grade Sparse Lexical Retrieval using SQLite FTS5 with native bm25() scoring.
    Zero resident memory overhead, ACID compliant, no pickle vulnerability (CWE-502).
    """

    def __init__(self, db: Optional[Any] = None):
        from src.filter.vehicle_db import VehicleDB

        self.db = db or VehicleDB()

    def __len__(self) -> int:
        return self.db.count()

    def search(self, query_text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Return (car_model, score) pairs ranked best first using SQLite FTS5 BM25."""
        results = self.db.search_fts5(query_text, top_k=top_k)
        return [(m, score) for m, _, score in results]

