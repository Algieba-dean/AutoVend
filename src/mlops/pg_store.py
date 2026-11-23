"""
PostgreSQL Persistence Backend for MLOps & LLMOps (`src/mlops/pg_store.py`).

Replaces single-node local disk JSON files across:
- registry.py (experiments, prompts, models, datasets, artifact bundles)
- drift.py (drift reports)
- dlq_replay.py (multi-worker DLQ with FOR UPDATE SKIP LOCKED)
- observability.py (alert events)

In non-test environments, PostgreSQL is mandatory (fail-fast).
In test mode (`APP_ENV=test` / `testing`), gracefully allows isolated test doubles.
"""

import json
import os
import threading
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def is_test_env() -> bool:
    env = (
        os.getenv("APP_ENV")
        or os.getenv("APP_ENVIRONMENT")
        or config.app_environment
        or "development"
    ).strip().lower()
    return env in ("test", "testing")


class MLOpsPostgresStore:
    """Thread-safe PostgreSQL connection pool and schema manager for MLOps."""

    _lock = threading.RLock()
    _pool: Optional[Any] = None
    _schema_ready: bool = False
    _unavailable_in_test: bool = False

    @classmethod
    def reset_for_tests(cls) -> None:
        with cls._lock:
            if cls._pool is not None:
                try:
                    cls._pool.close()
                except Exception:
                    pass
                cls._pool = None
            cls._schema_ready = False
            cls._unavailable_in_test = False

    @classmethod
    def ensure_ready(cls) -> bool:
        """
        Ensure PostgreSQL pool and MLOps schema are ready.
        Returns True if PostgreSQL is connected, False in test mode when PG is unavailable.
        Raises RuntimeError in non-test environments if PG is unavailable.
        """
        with cls._lock:
            if cls._schema_ready and cls._pool is not None:
                return True
            if cls._unavailable_in_test and is_test_env():
                return False

            try:
                from psycopg_pool import ConnectionPool

                pool = ConnectionPool(
                    conninfo=config.pgvector_connection_string,
                    min_size=1,
                    max_size=5,
                    kwargs={"connect_timeout": 3, "autocommit": True},
                    open=False,
                )
                pool.open(wait=True, timeout=5.0)
                with pool.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS mlops_kv (
                                namespace TEXT NOT NULL,
                                item_key TEXT NOT NULL,
                                payload JSONB NOT NULL,
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                PRIMARY KEY (namespace, item_key)
                            );
                            CREATE TABLE IF NOT EXISTS mlops_dlq_tasks (
                                task_id TEXT PRIMARY KEY,
                                task_type TEXT NOT NULL,
                                status TEXT NOT NULL,
                                next_retry_at DOUBLE PRECISION NOT NULL,
                                attempts INT NOT NULL DEFAULT 1,
                                max_attempts INT NOT NULL DEFAULT 3,
                                payload JSONB NOT NULL,
                                created_at DOUBLE PRECISION NOT NULL,
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            CREATE INDEX IF NOT EXISTS idx_mlops_dlq_pending
                                ON mlops_dlq_tasks (status, next_retry_at)
                                WHERE status = 'pending';
                            CREATE TABLE IF NOT EXISTS mlops_drift_reports (
                                id SERIAL PRIMARY KEY,
                                report_type TEXT NOT NULL,
                                payload JSONB NOT NULL,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            CREATE TABLE IF NOT EXISTS mlops_alert_events (
                                id SERIAL PRIMARY KEY,
                                rule_name TEXT NOT NULL,
                                severity TEXT NOT NULL,
                                payload JSONB NOT NULL,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            """
                        )
                cls._pool = pool
                cls._schema_ready = True
                cls._unavailable_in_test = False
                return True
            except Exception as exc:
                if not is_test_env():
                    raise RuntimeError(
                        f"PostgreSQL is required for MLOps in non-test environments: {exc}"
                    ) from exc
                logger.debug(f"MLOps PostgreSQL unavailable in test mode ({exc}); using test isolation.")
                cls._unavailable_in_test = True
                return False

    @classmethod
    @contextmanager
    def connection(cls) -> Iterator[Any]:
        if not cls.ensure_ready() or cls._pool is None:
            raise RuntimeError("MLOps PostgreSQL pool is not available")
        with cls._pool.connection() as conn:
            yield conn

    # ── Generic KV helpers (registry namespaces) ───────────────────────

    @classmethod
    def kv_upsert(cls, namespace: str, item_key: str, payload: Dict[str, Any]) -> None:
        with cls.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mlops_kv (namespace, item_key, payload, updated_at)
                    VALUES (%s, %s, %s::jsonb, NOW())
                    ON CONFLICT (namespace, item_key) DO UPDATE
                    SET payload = EXCLUDED.payload, updated_at = NOW()
                    """,
                    (namespace, item_key, json.dumps(payload, ensure_ascii=False)),
                )

    @classmethod
    def kv_load_all(cls, namespace: str) -> Dict[str, Dict[str, Any]]:
        with cls.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT item_key, payload FROM mlops_kv WHERE namespace = %s",
                    (namespace,),
                )
                rows = cur.fetchall()
        out: Dict[str, Dict[str, Any]] = {}
        for key, payload in rows:
            out[key] = payload if isinstance(payload, dict) else json.loads(payload)
        return out

    # ── DLQ FOR UPDATE SKIP LOCKED helpers ─────────────────────────────

    @classmethod
    def dlq_upsert(cls, record_dict: Dict[str, Any]) -> None:
        with cls.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mlops_dlq_tasks
                        (task_id, task_type, status, next_retry_at, attempts, max_attempts, payload, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, NOW())
                    ON CONFLICT (task_id) DO UPDATE
                    SET status = EXCLUDED.status,
                        next_retry_at = EXCLUDED.next_retry_at,
                        attempts = EXCLUDED.attempts,
                        max_attempts = EXCLUDED.max_attempts,
                        payload = EXCLUDED.payload,
                        updated_at = NOW()
                    """,
                    (
                        record_dict["task_id"],
                        record_dict["task_type"],
                        record_dict["status"],
                        float(record_dict["next_retry_at"]),
                        int(record_dict["attempts"]),
                        int(record_dict["max_attempts"]),
                        json.dumps(record_dict, ensure_ascii=False),
                        float(record_dict["created_at"]),
                    ),
                )

    @classmethod
    def dlq_get(cls, task_id: str) -> Optional[Dict[str, Any]]:
        with cls.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload FROM mlops_dlq_tasks WHERE task_id = %s",
                    (task_id,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return row[0] if isinstance(row[0], dict) else json.loads(row[0])

    @classmethod
    def dlq_claim_pending(
        cls,
        now_ts: float,
        task_type: Optional[str] = None,
        force: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Atomically claim pending DLQ tasks across multiple workers using FOR UPDATE SKIP LOCKED."""
        with cls.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    where_parts = ["status = 'pending'"]
                    params: List[Any] = []
                    if not force:
                        where_parts.append("next_retry_at <= %s")
                        params.append(float(now_ts))
                    if task_type:
                        where_parts.append("task_type = %s")
                        params.append(task_type)
                    params.append(int(limit))
                    where_sql = " AND ".join(where_parts)
                    cur.execute(
                        f"""
                        WITH claimed AS (
                            SELECT task_id
                            FROM mlops_dlq_tasks
                            WHERE {where_sql}
                            ORDER BY next_retry_at ASC
                            LIMIT %s
                            FOR UPDATE SKIP LOCKED
                        )
                        UPDATE mlops_dlq_tasks t
                        SET status = 'replaying', updated_at = NOW()
                        FROM claimed
                        WHERE t.task_id = claimed.task_id
                        RETURNING t.payload
                        """,
                        params,
                    )
                    rows = cur.fetchall()
        return [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in rows]

    @classmethod
    def dlq_list(cls, status: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        with cls.connection() as conn:
            with conn.cursor() as cur:
                if status:
                    cur.execute(
                        "SELECT payload FROM mlops_dlq_tasks WHERE status = %s ORDER BY created_at DESC LIMIT %s",
                        (status, int(limit)),
                    )
                else:
                    cur.execute(
                        "SELECT payload FROM mlops_dlq_tasks ORDER BY created_at DESC LIMIT %s",
                        (int(limit),),
                    )
                rows = cur.fetchall()
        return [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in rows]

    @classmethod
    def append_alert_event(cls, event_dict: Dict[str, Any]) -> None:
        with cls.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mlops_alert_events (rule_name, severity, payload)
                    VALUES (%s, %s, %s::jsonb)
                    """,
                    (
                        event_dict["rule_name"],
                        event_dict["severity"],
                        json.dumps(event_dict, ensure_ascii=False),
                    ),
                )

    @classmethod
    def append_drift_report(cls, report_type: str, report_dict: Dict[str, Any]) -> None:
        with cls.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mlops_drift_reports (report_type, payload)
                    VALUES (%s, %s::jsonb)
                    """,
                    (report_type, json.dumps(report_dict, ensure_ascii=False)),
                )
