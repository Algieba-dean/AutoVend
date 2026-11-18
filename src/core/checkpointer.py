"""
Unified LangGraph Checkpointer factory (`src/core/checkpointer.py`).

Uses `langgraph.checkpoint.postgres.PostgresSaver` backed by `psycopg_pool.ConnectionPool`
sharing PostgreSQL configuration with `PgVectorStore`, with safe fallback to `MemorySaver`
when PostgreSQL is unreachable in development/testing.
"""

import logging
import os
from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from src.utils.config import config

logger = logging.getLogger(__name__)


def _should_allow_memory_fallback(explicit: Optional[bool]) -> bool:
    if explicit is not None:
        return bool(explicit)
    if config.pgvector_allow_memory_fallback is not None:
        return bool(config.pgvector_allow_memory_fallback)
    if config.is_production:
        return False
    return True


def create_checkpointer(
    dsn: Optional[str] = None,
    allow_memory_fallback: Optional[bool] = None,
    pool_min_size: int = 1,
    pool_max_size: int = 10,
) -> BaseCheckpointSaver:
    """
    Create a LangGraph `BaseCheckpointSaver`.

    Tries `PostgresSaver` with `psycopg_pool.ConnectionPool` when a PostgreSQL DSN
    is configured (and not in an isolated unit-test unless `dsn` is explicitly passed);
    falls back to `MemorySaver` if allowed and PostgreSQL is unavailable.
    """
    resolved_dsn = dsn or config.pgvector_connection_string
    fallback_allowed = _should_allow_memory_fallback(allow_memory_fallback)

    # In pytest without an explicit DSN, avoid 3-5s TCP timeout per test
    if dsn is None and os.getenv("PYTEST_CURRENT_TEST") and fallback_allowed:
        return MemorySaver()

    pool = None
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool

        pool = ConnectionPool(
            conninfo=resolved_dsn,
            min_size=pool_min_size,
            max_size=pool_max_size,
            kwargs={"autocommit": True, "prepare_threshold": 0, "connect_timeout": 3},
            open=False,
        )
        pool.open(wait=True, timeout=3.0)
        saver = PostgresSaver(pool)
        saver.setup()
        # Keep pool reference on saver so callers can close it on shutdown if needed
        saver._autovend_pool = pool  # type: ignore[attr-defined]
        logger.info("LangGraph checkpointer initialized with PostgresSaver (ConnectionPool).")
        return saver
    except Exception as exc:
        if pool is not None:
            try:
                pool.close()
            except Exception:
                pass
        if not fallback_allowed:
            raise
        logger.warning(f"PostgresSaver unavailable ({exc}), falling back to MemorySaver.")
        return MemorySaver()
