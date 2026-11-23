"""
PostgreSQL + pgvector vector store.

Provides a drop-in replacement for ChromaVectorStore backed by PostgreSQL + pgvector
(with HNSW vector index, JSONB GIN metadata index, and psycopg_pool.ConnectionPool),
plus deterministic in-memory fallback when explicitly enabled or in test mode.
"""

import json
import math
import os
import re
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from src.models.vehicle import Vehicle
from src.rag.vector_store import extract_vehicle_trim, generate_vehicle_doc_id
from src.utils.config import config
from src.utils.logger import get_logger, log_performance

_VALID_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_DISTANCE_OPS = {
    "cosine": ("vector_cosine_ops", "<=>"),
    "euclidean": ("vector_l2_ops", "<->"),
    "l2": ("vector_l2_ops", "<->"),
    "ip": ("vector_ip_ops", "<#>"),
}


def _validate_identifier(name: str) -> str:
    """Validate SQL identifier (table or metadata key) to prevent SQL injection."""
    if not _VALID_IDENT_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


def _format_vector_literal(vec: List[float]) -> str:
    """Format a float list as a pgvector literal string '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{float(x):.8g}" for x in vec) + "]"


def _parse_vector_value(val: Any) -> List[float]:
    """Parse a pgvector column value (list, tuple, or '[...]' string) into List[float]."""
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return [float(x) for x in val]
    if isinstance(val, str):
        s = val.strip().strip("[]")
        if not s:
            return []
        return [float(x) for x in s.split(",")]
    try:
        return [float(x) for x in list(val)]
    except Exception:
        return []


def _compute_distance(a: List[float], b: List[float], metric: str = "cosine") -> float:
    """Compute vector distance matching pgvector operator semantics."""
    if not a or not b or len(a) != len(b):
        return 2.0 if metric == "cosine" else float("inf")

    if metric in ("euclidean", "l2"):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    dot = sum(x * y for x, y in zip(a, b))
    if metric == "ip":
        return -dot

    # Cosine distance: 1 - cosine_similarity, clamped to [0, 2]
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    cos_sim = max(-1.0, min(1.0, dot / (norm_a * norm_b)))
    return max(0.0, min(2.0, 1.0 - cos_sim))


def _matches_where(metadata: Dict[str, Any], where: Optional[Dict[str, Any]]) -> bool:
    """Evaluate a Chroma-style `where` filter dict against a metadata dict in Python."""
    if not where:
        return True

    for key, cond in where.items():
        if key == "$and":
            if not all(_matches_where(metadata, sub) for sub in cond):
                return False
            continue
        if key == "$or":
            if not any(_matches_where(metadata, sub) for sub in cond):
                return False
            continue

        val = metadata.get(key)
        if isinstance(cond, dict):
            for op, target in cond.items():
                if op == "$in":
                    if val not in target:
                        return False
                elif op == "$nin":
                    if val in target:
                        return False
                elif op == "$eq":
                    if val != target:
                        return False
                elif op == "$ne":
                    if val == target:
                        return False
                elif op == "$gt":
                    if val is None or not (val > target):
                        return False
                elif op == "$gte":
                    if val is None or not (val >= target):
                        return False
                elif op == "$lt":
                    if val is None or not (val < target):
                        return False
                elif op == "$lte":
                    if val is None or not (val <= target):
                        return False
                else:
                    raise ValueError(f"Unsupported filter operator: {op}")
        else:
            if val != cond:
                return False
    return True


def _build_sql_where(
    where: Optional[Dict[str, Any]],
) -> Tuple[str, List[Any]]:
    """Translate a Chroma-style `where` dict into a parameterized Postgres JSONB WHERE clause."""
    if not where:
        return "", []

    clauses: List[str] = []
    params: List[Any] = []

    for key, cond in where.items():
        if key == "$and":
            sub_clauses = []
            for sub in cond:
                sc, sp = _build_sql_where(sub)
                if sc:
                    sub_clauses.append(f"({sc})")
                    params.extend(sp)
            if sub_clauses:
                clauses.append(" AND ".join(sub_clauses))
            continue

        if key == "$or":
            sub_clauses = []
            for sub in cond:
                sc, sp = _build_sql_where(sub)
                if sc:
                    sub_clauses.append(f"({sc})")
                    params.extend(sp)
            if sub_clauses:
                clauses.append("(" + " OR ".join(sub_clauses) + ")")
            continue

        safe_key = _validate_identifier(key)
        json_text_expr = f"metadata->>'{safe_key}'"

        if isinstance(cond, dict):
            for op, target in cond.items():
                if op == "$in":
                    target_list = [str(x) for x in target]
                    if not target_list:
                        clauses.append("FALSE")
                    else:
                        clauses.append(f"{json_text_expr} = ANY(%s::text[])")
                        params.append(target_list)
                elif op == "$nin":
                    target_list = [str(x) for x in target]
                    if not target_list:
                        clauses.append("TRUE")
                    else:
                        clauses.append(
                            f"({json_text_expr} IS NULL OR NOT ({json_text_expr} = ANY(%s::text[])))"
                        )
                        params.append(target_list)
                elif op == "$eq":
                    if isinstance(target, (str, int, float, bool)):
                        clauses.append("metadata @> %s::jsonb")
                        params.append(json.dumps({safe_key: target}, ensure_ascii=False))
                    elif target is None:
                        clauses.append(f"{json_text_expr} IS NULL")
                    else:
                        clauses.append(f"{json_text_expr} = %s")
                        params.append(str(target))
                elif op == "$ne":
                    clauses.append(f"{json_text_expr} IS DISTINCT FROM %s")
                    params.append(str(target))
                elif op in ("$gt", "$gte", "$lt", "$lte"):
                    sql_op = {"$gt": ">", "$gte": ">=", "$lt": "<", "$lte": "<="}[op]
                    clauses.append(
                        f"({json_text_expr} ~ '^-?[0-9]+(\\.[0-9]+)?$' "
                        f"AND ({json_text_expr})::double precision {sql_op} %s)"
                    )
                    params.append(float(target))
                else:
                    raise ValueError(f"Unsupported filter operator: {op}")
        else:
            if isinstance(cond, (str, int, float, bool)):
                clauses.append("metadata @> %s::jsonb")
                params.append(json.dumps({safe_key: cond}, ensure_ascii=False))
            elif cond is None:
                clauses.append(f"{json_text_expr} IS NULL")
            else:
                clauses.append(f"{json_text_expr} = %s")
                params.append(str(cond))

    return " AND ".join(clauses), params


def _vehicle_to_metadata(vehicle: Vehicle, trim: str) -> Dict[str, Any]:
    """Build normalized metadata dictionary for a Vehicle."""
    metadata: Dict[str, Any] = {
        "car_model": vehicle.car_model,
        "trim": trim,
        "brand": vehicle.precise_labels.brand or "",
        "category": vehicle.precise_labels.vehicle_category_bottom or "",
        "price": vehicle.precise_labels.price or "",
        "powertrain_type": vehicle.precise_labels.powertrain_type or "",
        "size": vehicle.ambiguous_labels.size or "",
        "family_friendliness": vehicle.ambiguous_labels.family_friendliness or "",
        "comfort_level": vehicle.ambiguous_labels.comfort_level or "",
    }
    price_range = vehicle.get_price_range()
    if price_range:
        metadata["price_min"] = price_range[0]
        metadata["price_max"] = price_range[1]
    return metadata


class _CollectionProxy:
    """Lightweight shim exposing `.count()`, `.peek()`, and `.metadata` for IndexBuilder compatibility."""

    def __init__(self, store: "PgVectorStore"):
        self._store = store

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "backend": "pgvector",
            "mode": self._store.backend_mode,
            "distance_metric": self._store.distance_metric,
            "table_name": self._store.table_name,
        }

    def count(self) -> int:
        return self._store.count()

    def peek(self, limit: int = 1) -> Dict[str, Any]:
        return self._store.peek(limit=limit)


class _InMemoryVectorFallback:
    """Deterministic in-memory vector store used when PostgreSQL is unavailable."""

    def __init__(self, distance_metric: str = "cosine"):
        self.distance_metric = distance_metric
        self.rows: Dict[str, Dict[str, Any]] = {}

    def count(self) -> int:
        return len(self.rows)

    def upsert(
        self,
        doc_id: str,
        document: str,
        metadata: Dict[str, Any],
        embedding: List[float],
    ) -> None:
        self.rows[doc_id] = {
            "id": doc_id,
            "document": document,
            "metadata": dict(metadata),
            "embedding": list(embedding),
        }

    def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        include = include or ["metadatas", "documents", "distances", "embeddings"]
        all_ids: List[List[str]] = []
        all_metas: List[List[Dict[str, Any]]] = []
        all_docs: List[List[str]] = []
        all_dists: List[List[float]] = []
        all_embs: List[List[List[float]]] = []

        contains_text = None
        if where_document and "$contains" in where_document:
            contains_text = str(where_document["$contains"])

        candidates = [
            row
            for row in self.rows.values()
            if _matches_where(row["metadata"], where)
            and (contains_text is None or contains_text in row["document"])
        ]

        for q_emb in query_embeddings:
            scored = []
            for row in candidates:
                dist = _compute_distance(q_emb, row["embedding"], self.distance_metric)
                scored.append((dist, row))
            scored.sort(key=lambda item: item[0])
            top = scored[:n_results]

            all_ids.append([r["id"] for _, r in top])
            all_metas.append([r["metadata"] for _, r in top])
            all_docs.append([r["document"] for _, r in top])
            all_dists.append([d for d, _ in top])
            all_embs.append([r["embedding"] for _, r in top])

        res: Dict[str, Any] = {"ids": all_ids}
        if "metadatas" in include:
            res["metadatas"] = all_metas
        if "documents" in include:
            res["documents"] = all_docs
        if "distances" in include:
            res["distances"] = all_dists
        if "embeddings" in include:
            res["embeddings"] = all_embs
        return res

    def get(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        matched = []
        if ids is not None:
            for doc_id in ids:
                if doc_id in self.rows:
                    matched.append(self.rows[doc_id])
        else:
            for row in self.rows.values():
                if _matches_where(row["metadata"], where):
                    matched.append(row)
                    if len(matched) >= limit:
                        break

        res: Dict[str, Any] = {
            "ids": [r["id"] for r in matched],
            "metadatas": [r["metadata"] for r in matched],
            "documents": [r["document"] for r in matched],
        }
        if include and "embeddings" in include:
            res["embeddings"] = [r["embedding"] for r in matched]
        return res

    def delete(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> None:
        if ids:
            for doc_id in ids:
                self.rows.pop(doc_id, None)
        if where:
            to_del = [
                doc_id
                for doc_id, row in self.rows.items()
                if _matches_where(row["metadata"], where)
            ]
            for doc_id in to_del:
                self.rows.pop(doc_id, None)

    def clear(self) -> None:
        self.rows.clear()


def _current_app_env() -> str:
    """Resolve current environment dynamically (respecting monkeypatch in tests)."""
    return (
        os.getenv("APP_ENV")
        or os.getenv("APP_ENVIRONMENT")
        or config.app_environment
        or "development"
    ).strip().lower()


def _resolve_allow_memory_fallback(explicit: Optional[bool]) -> bool:
    """
    Fail-fast in all non-test environments (staging/prod/dev).
    _InMemoryVectorFallback is strictly a unit-test isolation double (APP_ENV=test/testing).
    """
    env = _current_app_env()
    if env not in ("test", "testing"):
        return False
    if explicit is not None:
        return bool(explicit)
    if config.pgvector_allow_memory_fallback is not None:
        return bool(config.pgvector_allow_memory_fallback)
    return True


class PgVectorStore:
    """PostgreSQL + pgvector vector store implementing the AutoVend vector store contract."""

    def __init__(
        self,
        dsn: Optional[str] = None,
        table_name: Optional[str] = None,
        embed_dim: Optional[int] = None,
        distance_metric: str = "cosine",
        embedding_model: Optional[Any] = None,
        hnsw_m: Optional[int] = None,
        hnsw_ef_construction: Optional[int] = None,
        allow_memory_fallback: Optional[bool] = None,
        allow_zero_vector_fallback: bool = False,
        pool_min_size: int = 1,
        pool_max_size: int = 10,
        connection: Optional[Any] = None,
    ):
        self.dsn = dsn or config.pgvector_connection_string
        self.table_name = _validate_identifier(table_name or config.pgvector_table_name)
        self.collection_name = self.table_name
        self.embed_dim = int(embed_dim or config.pgvector_embed_dim)
        self.distance_metric = distance_metric.lower()
        if self.distance_metric not in _DISTANCE_OPS:
            raise ValueError(
                f"Unsupported distance_metric={distance_metric!r}; "
                f"expected one of {tuple(_DISTANCE_OPS)}"
            )
        self.embedding_model = embedding_model
        self.hnsw_m = int(hnsw_m or config.pgvector_hnsw_m)
        self.hnsw_ef_construction = int(
            hnsw_ef_construction or config.pgvector_hnsw_ef_construction
        )
        self.allow_memory_fallback = _resolve_allow_memory_fallback(allow_memory_fallback)
        self.allow_zero_vector_fallback = allow_zero_vector_fallback
        self.pool_min_size = pool_min_size
        self.pool_max_size = pool_max_size

        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._conn = connection
        self._pool: Optional[Any] = None
        self._fallback: Optional[_InMemoryVectorFallback] = None
        self.is_fallback: bool = False
        self.backend_mode: str = "postgres"

        self.stats = {
            "total_documents": 0,
            "total_embeddings": 0,
            "add_time": 0.0,
            "query_time": 0.0,
            "query_count": 0,
        }

        self._initialize_backend()
        self.collection = _CollectionProxy(self)

    @contextmanager
    def _get_conn(self) -> Iterator[Any]:
        """Acquire a connection from the pool (or yield the injected test connection)."""
        if self._conn is not None:
            yield self._conn
            return
        if self._pool is None:
            raise RuntimeError("PostgreSQL connection pool is not initialized")
        with self._pool.connection() as conn:
            yield conn

    def _initialize_backend(self) -> None:
        """Connect to PostgreSQL + pgvector via ConnectionPool and ensure schema."""
        opened_pool = False
        try:
            if self._conn is None:
                from psycopg_pool import ConnectionPool

                self._pool = ConnectionPool(
                    conninfo=self.dsn,
                    min_size=self.pool_min_size,
                    max_size=self.pool_max_size,
                    kwargs={"connect_timeout": 3, "autocommit": True},
                    open=False,
                )
                self._pool.open(wait=True, timeout=5.0)
                opened_pool = True
            self._ensure_schema()
            self.is_fallback = False
            self.backend_mode = "postgres"
            self.logger.info(
                f"已连接 PostgreSQL pgvector 表 '{self.table_name}' "
                f"(dim={self.embed_dim}, metric={self.distance_metric})"
            )
        except Exception as e:
            if opened_pool and self._pool is not None:
                try:
                    self._pool.close()
                except Exception:
                    pass
                self._pool = None
            if not self.allow_memory_fallback:
                raise
            self.logger.warning(
                f"PostgreSQL/pgvector 不可用 ({e})，降级使用内存向量存储"
            )
            self._conn = None
            self._pool = None
            self._fallback = _InMemoryVectorFallback(distance_metric=self.distance_metric)
            self.is_fallback = True
            self.backend_mode = "memory_fallback"

    def _ensure_schema(self) -> None:
        """Create pgvector extension, table, HNSW vector index, GIN metadata index, and tsvector GIN index."""
        ops_name, _ = _DISTANCE_OPS[self.distance_metric]
        idx_vec = _validate_identifier(f"idx_{self.table_name}_embedding_hnsw")
        idx_meta = _validate_identifier(f"idx_{self.table_name}_metadata_gin")
        idx_tsv = _validate_identifier(f"idx_{self.table_name}_tsv_gin")

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        document TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({self.embed_dim}),
                        tsv TSVECTOR,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    f"""
                    ALTER TABLE {self.table_name}
                    ADD COLUMN IF NOT EXISTS tsv TSVECTOR
                    """
                )
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS {idx_vec}
                    ON {self.table_name}
                    USING hnsw (embedding {ops_name})
                    WITH (m = {self.hnsw_m}, ef_construction = {self.hnsw_ef_construction})
                    """
                )
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS {idx_meta}
                    ON {self.table_name}
                    USING gin (metadata)
                    """
                )
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS {idx_tsv}
                    ON {self.table_name}
                    USING gin (tsv)
                    """
                )

    def hybrid_search_rrf(
        self,
        query_embedding: List[float],
        query_text: str,
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Single-SQL Hybrid Retrieval combining metadata JSONB filter + pgvector Dense +
        PostgreSQL tsvector Sparse + Reciprocal Rank Fusion (RRF).
        """
        if self._fallback is not None:
            from src.retrieval.bm25_index import tokenize

            candidate_k = max(int(top_k) * 3, 20)
            dense_res = self._fallback.query(
                query_embeddings=[query_embedding],
                n_results=candidate_k,
                where=where,
                include=["metadatas", "documents", "distances"],
            )
            ids = dense_res["ids"][0] if dense_res["ids"] else []
            docs = dense_res["documents"][0] if dense_res["documents"] else []
            metas = dense_res["metadatas"][0] if dense_res["metadatas"] else []
            dists = dense_res["distances"][0] if dense_res["distances"] else []

            q_tokens = set(tokenize(query_text))
            dense_ranks = {doc_id: idx + 1 for idx, doc_id in enumerate(ids)}
            sparse_scores = []
            for doc_id, doc in zip(ids, docs):
                if q_tokens:
                    doc_tokens = set(tokenize(doc))
                    overlap = len(q_tokens & doc_tokens)
                    if overlap > 0:
                        sparse_scores.append((doc_id, overlap / len(q_tokens)))
            sparse_scores.sort(key=lambda x: x[1], reverse=True)
            sparse_ranks = {doc_id: idx + 1 for idx, (doc_id, _) in enumerate(sparse_scores)}

            fused = []
            for doc_id, doc, meta, dist in zip(ids, docs, metas, dists):
                rrf = 1.0 / (rrf_k + dense_ranks[doc_id])
                if doc_id in sparse_ranks:
                    rrf += 1.0 / (rrf_k + sparse_ranks[doc_id])
                fused.append(
                    {"id": doc_id, "document": doc, "metadata": meta, "rrf_score": rrf, "distance": dist}
                )
            fused.sort(key=lambda x: x["rrf_score"], reverse=True)
            return fused[:top_k]

        _, dist_op = _DISTANCE_OPS[self.distance_metric]
        vec_lit = _format_vector_literal(query_embedding)
        where_sql, where_params = _build_sql_where(where)
        filter_clause = f"WHERE {where_sql}" if where_sql else ""
        and_filter = f"AND {where_sql}" if where_sql else ""

        from src.retrieval.bm25_index import tokenize

        tokens = [t for t in dict.fromkeys(tokenize(query_text)) if re.match(r"^[\w\u4e00-\u9fff]+$", t)]
        tsquery_expr = " | ".join(tokens) if tokens else ""

        if not tsquery_expr:
            sql = f"""
            SELECT id, document, metadata, (1.0 / (%s + ROW_NUMBER() OVER (ORDER BY embedding {dist_op} %s::vector))) AS rrf_score
            FROM {self.table_name}
            {filter_clause}
            ORDER BY embedding {dist_op} %s::vector ASC
            LIMIT %s
            """
            params = [rrf_k, vec_lit, *where_params, vec_lit, int(top_k)]
        else:
            sql = f"""
            WITH dense AS (
                SELECT id, document, metadata,
                       ROW_NUMBER() OVER (ORDER BY embedding {dist_op} %s::vector ASC) AS dense_rank
                FROM {self.table_name}
                {filter_clause}
                ORDER BY embedding {dist_op} %s::vector ASC
                LIMIT %s
            ),
            sparse AS (
                SELECT id, document, metadata,
                       ROW_NUMBER() OVER (ORDER BY ts_rank_cd(tsv, to_tsquery('simple', %s)) DESC) AS sparse_rank
                FROM {self.table_name}
                WHERE tsv @@ to_tsquery('simple', %s)
                {and_filter}
                ORDER BY ts_rank_cd(tsv, to_tsquery('simple', %s)) DESC
                LIMIT %s
            )
            SELECT
                COALESCE(d.id, s.id) AS id,
                COALESCE(d.document, s.document) AS document,
                COALESCE(d.metadata, s.metadata) AS metadata,
                (COALESCE(1.0 / (%s + d.dense_rank), 0.0) + COALESCE(1.0 / (%s + s.sparse_rank), 0.0)) AS rrf_score
            FROM dense d
            FULL OUTER JOIN sparse s ON d.id = s.id
            ORDER BY rrf_score DESC
            LIMIT %s
            """
            candidate_k = max(int(top_k) * 3, 20)
            params = [
                vec_lit,
                *where_params,
                vec_lit,
                candidate_k,
                tsquery_expr,
                tsquery_expr,
                *where_params,
                tsquery_expr,
                candidate_k,
                rrf_k,
                rrf_k,
                int(top_k),
            ]

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [
            {
                "id": str(r[0]),
                "document": str(r[1]),
                "metadata": r[2] if isinstance(r[2], dict) else json.loads(r[2]),
                "rrf_score": float(r[3]),
            }
            for r in rows
        ]

    def count(self) -> int:
        """Return total number of stored vector documents."""
        if self._fallback is not None:
            return self._fallback.count()
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                row = cur.fetchone()
                return int(row[0]) if row else 0

    def peek(self, limit: int = 1) -> Dict[str, Any]:
        """Return up to `limit` records for dimension / sanity inspection."""
        if self._fallback is not None:
            return self._fallback.get(limit=limit, include=["embeddings"])
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, metadata, document, embedding::text "
                    f"FROM {self.table_name} LIMIT %s",
                    (limit,),
                )
                rows = cur.fetchall()
        return {
            "ids": [r[0] for r in rows],
            "metadatas": [r[1] if isinstance(r[1], dict) else json.loads(r[1]) for r in rows],
            "documents": [r[2] for r in rows],
            "embeddings": [_parse_vector_value(r[3]) for r in rows],
        }

    @log_performance
    def add_vehicles(
        self,
        vehicles: List[Vehicle],
        embeddings: List[List[float]],
        batch_size: int = 100,
    ) -> None:
        """Add or upsert vehicles and their embeddings in batches."""
        if len(vehicles) != len(embeddings):
            raise ValueError("车辆数据和嵌入向量数量不匹配")

        start_time = time.time()
        for i in range(0, len(vehicles), batch_size):
            batch_vehicles = vehicles[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]
            self._add_batch(batch_vehicles, batch_embeddings)

        add_time = time.time() - start_time
        self.stats["add_time"] += add_time
        self.stats["total_embeddings"] += len(vehicles)
        self.logger.info(f"已添加 {len(vehicles)} 个车辆数据到 pgvector，耗时 {add_time:.2f}秒")

    def _add_batch(self, vehicles: List[Vehicle], embeddings: List[List[float]]) -> None:
        """Upsert a batch of vehicles using executemany."""
        records = []
        for vehicle, emb in zip(vehicles, embeddings):
            trim = extract_vehicle_trim(vehicle)
            doc_id = generate_vehicle_doc_id(vehicle.car_model or str(uuid.uuid4()), trim=trim)
            document = vehicle.get_search_text()
            metadata = _vehicle_to_metadata(vehicle, trim)
            records.append((doc_id, document, metadata, emb))

        if not records:
            return

        if self._fallback is not None:
            for doc_id, document, metadata, emb in records:
                self._fallback.upsert(doc_id, document, metadata, emb)
            return

        from src.retrieval.bm25_index import tokenize

        sql = f"""
            INSERT INTO {self.table_name} (id, document, metadata, embedding, tsv, updated_at)
            VALUES (%s, %s, %s::jsonb, %s::vector, to_tsvector('simple', %s), NOW())
            ON CONFLICT (id) DO UPDATE SET
                document = EXCLUDED.document,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding,
                tsv = EXCLUDED.tsv,
                updated_at = NOW()
        """
        params_list = [
            (
                doc_id,
                document,
                json.dumps(metadata, ensure_ascii=False),
                _format_vector_literal(emb),
                " ".join(tokenize(document)),
            )
            for doc_id, document, metadata, emb in records
        ]
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, params_list)

    @log_performance
    def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Query nearest neighbors by vector distance with optional metadata/document filters."""
        start_time = time.time()
        if include is None:
            include = ["metadatas", "documents", "distances", "embeddings"]

        try:
            if self._fallback is not None:
                results = self._fallback.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where,
                    where_document=where_document,
                    include=include,
                )
            else:
                results = self._query_postgres(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where,
                    where_document=where_document,
                    include=include,
                )

            query_time = time.time() - start_time
            self.stats["query_time"] += query_time
            self.stats["query_count"] += 1
            return results
        except Exception as e:
            self.logger.error(f"pgvector 查询失败: {e}")
            raise

    def _query_postgres(
        self,
        query_embeddings: List[List[float]],
        n_results: int,
        where: Optional[Dict[str, Any]],
        where_document: Optional[Dict[str, Any]],
        include: List[str],
    ) -> Dict[str, Any]:
        _, op = _DISTANCE_OPS[self.distance_metric]
        where_sql, where_params = _build_sql_where(where)

        clauses: List[str] = []
        extra_params: List[Any] = []
        if where_sql:
            clauses.append(where_sql)
            extra_params.extend(where_params)
        if where_document and "$contains" in where_document:
            clauses.append("document LIKE %s")
            extra_params.append(f"%{where_document['$contains']}%")

        where_clause = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        emb_select = ", embedding::text" if "embeddings" in include else ""

        all_ids: List[List[str]] = []
        all_metas: List[List[Dict[str, Any]]] = []
        all_docs: List[List[str]] = []
        all_dists: List[List[float]] = []
        all_embs: List[List[List[float]]] = []

        sql = f"""
            SELECT id, metadata, document, (embedding {op} %s::vector) AS distance{emb_select}
            FROM {self.table_name}
            {where_clause}
            ORDER BY embedding {op} %s::vector ASC
            LIMIT %s
        """

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                for q_emb in query_embeddings:
                    vec_lit = _format_vector_literal(q_emb)
                    params = [vec_lit, *extra_params, vec_lit, int(n_results)]
                    cur.execute(sql, params)
                    rows = cur.fetchall()

                    all_ids.append([r[0] for r in rows])
                    all_metas.append(
                        [r[1] if isinstance(r[1], dict) else json.loads(r[1]) for r in rows]
                    )
                    all_docs.append([r[2] for r in rows])
                    all_dists.append([float(r[3]) for r in rows])
                    if "embeddings" in include:
                        all_embs.append([_parse_vector_value(r[4]) for r in rows])

        res: Dict[str, Any] = {"ids": all_ids}
        if "metadatas" in include:
            res["metadatas"] = all_metas
        if "documents" in include:
            res["documents"] = all_docs
        if "distances" in include:
            res["distances"] = all_dists
        if "embeddings" in include:
            res["embeddings"] = all_embs
        return res

    def query_by_metadata(self, where: Dict[str, Any], n_results: int = 100) -> Dict[str, Any]:
        """Query documents by metadata filter without vector similarity."""
        if self._fallback is not None:
            return self._fallback.get(where=where, limit=n_results)

        where_sql, params = _build_sql_where(where)
        where_clause = f"WHERE {where_sql}" if where_sql else ""
        sql = f"""
            SELECT id, metadata, document
            FROM {self.table_name}
            {where_clause}
            LIMIT %s
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, [*params, int(n_results)])
                rows = cur.fetchall()
        return {
            "ids": [r[0] for r in rows],
            "metadatas": [r[1] if isinstance(r[1], dict) else json.loads(r[1]) for r in rows],
            "documents": [r[2] for r in rows],
        }

    def get_vehicle_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single vehicle record by document ID."""
        try:
            if self._fallback is not None:
                res = self._fallback.get(ids=[doc_id])
            else:
                with self._get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            f"SELECT id, metadata, document FROM {self.table_name} WHERE id = %s",
                            (doc_id,),
                        )
                        row = cur.fetchone()
                if not row:
                    return None
                meta = row[1] if isinstance(row[1], dict) else json.loads(row[1])
                return {"id": row[0], "metadata": meta, "document": row[2]}

            if res["ids"]:
                return {
                    "id": res["ids"][0],
                    "metadata": res["metadatas"][0],
                    "document": res["documents"][0],
                }
            return None
        except Exception as e:
            self.logger.error(f"根据ID查询失败: {e}")
            return None

    def update_vehicle(self, doc_id: str, vehicle: Vehicle, embedding: List[float]) -> None:
        """Update an existing vehicle document and embedding."""
        document = vehicle.get_search_text()
        trim = extract_vehicle_trim(vehicle)
        metadata = _vehicle_to_metadata(vehicle, trim)
        self.upsert_document(doc_id=doc_id, text=document, metadata=metadata, embedding=embedding)
        self.logger.info(f"已更新车辆数据: {doc_id}")

    def upsert_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """Idempotently insert or update a single document (Ingestion Pipeline contract)."""
        if embedding is None and hasattr(self, "embedding_model") and self.embedding_model:
            try:
                if not getattr(self.embedding_model, "is_degraded", False):
                    embedding = self.embedding_model.get_text_embedding(text)
            except Exception as emb_err:
                self.logger.warning(f"生成嵌入向量失败 ({doc_id}): {emb_err}")

        if embedding is None:
            try:
                from src.rag.embeddings import BGEEmbeddingModel

                bge = BGEEmbeddingModel()
                if not getattr(bge, "is_degraded", False):
                    embedding = bge.get_text_embedding(text)
                    self.embedding_model = bge
            except Exception:
                pass

        if embedding is None:
            if not self.allow_zero_vector_fallback:
                raise ValueError(
                    f"Embedding vector is required for document {doc_id!r} "
                    "and no embedding model is available (zero-vector fallback disabled)."
                )
            embedding = [0.0] * self.embed_dim

        clean_metadata: Dict[str, Any] = {}
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_metadata[k] = v
                elif v is not None:
                    clean_metadata[k] = str(v)
        if not clean_metadata:
            clean_metadata = {"doc_id": doc_id}

        doc_text = text or " "
        if self._fallback is not None:
            self._fallback.upsert(doc_id, doc_text, clean_metadata, embedding)
        else:
            from src.retrieval.bm25_index import tokenize

            tsv_text = " ".join(tokenize(doc_text))
            sql = f"""
                INSERT INTO {self.table_name} (id, document, metadata, embedding, tsv, updated_at)
                VALUES (%s, %s, %s::jsonb, %s::vector, to_tsvector('simple', %s), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    document = EXCLUDED.document,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding,
                    tsv = EXCLUDED.tsv,
                    updated_at = NOW()
            """
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        sql,
                        (
                            doc_id,
                            doc_text,
                            json.dumps(clean_metadata, ensure_ascii=False),
                            _format_vector_literal(embedding),
                            tsv_text,
                        ),
                    )

        self.logger.info(f"已成功 upsert pgvector 文档: {doc_id}")

    def delete_document(self, doc_id: str) -> None:
        """Delete a document by ID or associated car_model metadata."""
        if self._fallback is not None:
            self._fallback.delete(ids=[doc_id], where={"car_model": doc_id})
        else:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {self.table_name} "
                        f"WHERE id = %s OR metadata->>'car_model' = %s",
                        (doc_id, doc_id),
                    )
        self.logger.info(f"已删除 pgvector 文档: {doc_id}")

    def delete_vehicle(self, doc_id: str) -> None:
        """Alias for delete_document."""
        self.delete_document(doc_id)

    def clear_collection(self) -> None:
        """Truncate all rows from the pgvector table."""
        if self._fallback is not None:
            self._fallback.clear()
        else:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"TRUNCATE TABLE {self.table_name}")
        self.stats["total_documents"] = 0
        self.logger.info(f"已清空 pgvector 表: {self.table_name}")

    def get_collection_info(self) -> Dict[str, Any]:
        """Return collection/table metadata and document count."""
        try:
            return {
                "name": self.table_name,
                "count": self.count(),
                "distance_metric": self.distance_metric,
                "embed_dim": self.embed_dim,
                "backend": "pgvector",
                "mode": self.backend_mode,
                "is_fallback": self.is_fallback,
            }
        except Exception as e:
            self.logger.error(f"获取 pgvector 表信息失败: {e}")
            return {}

    def get_statistics(self) -> Dict[str, Any]:
        """Return store performance and collection statistics."""
        info = self.get_collection_info()
        return {
            **self.stats,
            "total_documents": info.get("count", self.stats["total_documents"]),
            "avg_query_time": self.stats["query_time"] / max(self.stats["query_count"], 1),
            "collection_info": info,
        }

    def backup_collection(self, backup_path: Optional[Path] = None) -> Path:
        """Export all rows to a JSONL backup file."""
        if backup_path is None:
            backup_path = (
                Path(config.vehicle_db_path).parent
                / f"backup_{self.table_name}_{int(time.time())}.jsonl"
            )
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        if self._fallback is not None:
            data = self._fallback.get(limit=1_000_000, include=["embeddings"])
        else:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT id, metadata, document, embedding::text FROM {self.table_name}"
                    )
                    rows = cur.fetchall()
            data = {
                "ids": [r[0] for r in rows],
                "metadatas": [r[1] if isinstance(r[1], dict) else json.loads(r[1]) for r in rows],
                "documents": [r[2] for r in rows],
                "embeddings": [_parse_vector_value(r[3]) for r in rows],
            }

        with open(backup_path, "w", encoding="utf-8") as f:
            for idx, doc_id in enumerate(data["ids"]):
                record = {
                    "id": doc_id,
                    "metadata": data["metadatas"][idx],
                    "document": data["documents"][idx],
                    "embedding": data["embeddings"][idx],
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        self.logger.info(f"pgvector 备份完成: {backup_path}")
        return backup_path

    def close(self) -> None:
        """Close the PostgreSQL connection pool (or single connection) if open."""
        if self._pool is not None:
            try:
                self._pool.close()
            except Exception:
                pass
            self._pool = None
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
