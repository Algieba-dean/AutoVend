"""
PostgreSQL (+ Redis hot-cache) storage for profiles, sessions, and test drive reservations.

Replaces the legacy single-node `FileStorage` (JSON files on local disk).
In non-test environments, PostgreSQL is mandatory (fail-fast).
In test mode (`APP_ENV=test` / `testing`), an isolated in-memory store is used
when PostgreSQL is unavailable.

`FileStorage` is deprecated and disabled outside test mode.
"""

import hashlib
import json
import logging
import os
import threading
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from backend.app.config import PROFILES_DIR, SESSIONS_DIR, TEST_DRIVES_DIR
from backend.app.models.schemas import UserProfile
from src.utils.config import config

logger = logging.getLogger(__name__)


def _is_test_env() -> bool:
    env = (
        os.getenv("APP_ENV")
        or os.getenv("APP_ENVIRONMENT")
        or config.app_environment
        or "development"
    ).strip().lower()
    return env in ("test", "testing")


class PostgresStorage:
    """PostgreSQL-backed storage for profiles, test drives, and sessions."""

    _lock = threading.RLock()
    _pool: Optional[Any] = None
    _schema_ready: bool = False
    _use_memory_test_store: bool = False

    # Test-mode only in-memory isolation stores
    _mem_profiles: Dict[str, UserProfile] = {}
    _mem_test_drives: Dict[str, Dict[str, Any]] = {}
    _mem_sessions: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def reset_for_tests(cls) -> None:
        """Reset connection pool and test-mode memory stores."""
        with cls._lock:
            if cls._pool is not None:
                try:
                    cls._pool.close()
                except Exception:
                    pass
                cls._pool = None
            cls._schema_ready = False
            cls._use_memory_test_store = False
            cls._mem_profiles.clear()
            cls._mem_test_drives.clear()
            cls._mem_sessions.clear()

    @classmethod
    def _ensure_backend(cls) -> bool:
        """
        Initialize PostgreSQL pool and schema.
        Returns True if PostgreSQL is active, False if in-memory test mode is active.
        Raises RuntimeError in non-test environments when PostgreSQL is unavailable.
        """
        with cls._lock:
            if cls._schema_ready and cls._pool is not None:
                return True
            if cls._use_memory_test_store and _is_test_env():
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
                            CREATE TABLE IF NOT EXISTS app_profiles (
                                phone_number TEXT PRIMARY KEY,
                                payload JSONB NOT NULL,
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            CREATE TABLE IF NOT EXISTS app_test_drives (
                                phone_number TEXT PRIMARY KEY,
                                payload JSONB NOT NULL,
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            CREATE TABLE IF NOT EXISTS app_sessions (
                                session_id TEXT PRIMARY KEY,
                                payload JSONB NOT NULL,
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            """
                        )
                cls._pool = pool
                cls._schema_ready = True
                cls._use_memory_test_store = False
                return True
            except Exception as exc:
                if not _is_test_env():
                    raise RuntimeError(
                        f"PostgreSQL is required for application storage in non-test environments: {exc}"
                    ) from exc
                logger.warning(
                    f"PostgreSQL unavailable in test mode ({exc}); using in-memory test storage."
                )
                cls._use_memory_test_store = True
                return False

    @classmethod
    @contextmanager
    def _conn(cls) -> Iterator[Any]:
        cls._ensure_backend()
        if cls._pool is None:
            raise RuntimeError("PostgreSQL pool is not initialized")
        with cls._pool.connection() as conn:
            yield conn

    # --- Profiles ---

    @classmethod
    def save_profile(cls, phone_number: str, profile: UserProfile) -> None:
        if not cls._ensure_backend():
            cls._mem_profiles[phone_number] = profile.model_copy(deep=True)
            return
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_profiles (phone_number, payload, updated_at)
                    VALUES (%s, %s::jsonb, NOW())
                    ON CONFLICT (phone_number) DO UPDATE
                    SET payload = EXCLUDED.payload, updated_at = NOW()
                    """,
                    (phone_number, profile.model_dump_json()),
                )

    @classmethod
    def load_profile(cls, phone_number: str) -> Optional[UserProfile]:
        if not cls._ensure_backend():
            prof = cls._mem_profiles.get(phone_number)
            return prof.model_copy(deep=True) if prof else None
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload FROM app_profiles WHERE phone_number = %s",
                    (phone_number,),
                )
                row = cur.fetchone()
        if not row:
            return None
        data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return UserProfile(**data)

    @classmethod
    def list_profiles(cls) -> List[str]:
        if not cls._ensure_backend():
            return sorted(cls._mem_profiles.keys())
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT phone_number FROM app_profiles ORDER BY phone_number")
                return [r[0] for r in cur.fetchall()]

    @classmethod
    def delete_profile(cls, phone_number: str) -> bool:
        if not cls._ensure_backend():
            return cls._mem_profiles.pop(phone_number, None) is not None
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM app_profiles WHERE phone_number = %s",
                    (phone_number,),
                )
                return cur.rowcount > 0

    # --- Test Drives ---

    @classmethod
    def save_test_drive(cls, phone_number: str, data: Dict[str, Any]) -> None:
        if not cls._ensure_backend():
            cls._mem_test_drives[phone_number] = dict(data)
            return
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_test_drives (phone_number, payload, updated_at)
                    VALUES (%s, %s::jsonb, NOW())
                    ON CONFLICT (phone_number) DO UPDATE
                    SET payload = EXCLUDED.payload, updated_at = NOW()
                    """,
                    (phone_number, json.dumps(data, ensure_ascii=False)),
                )

    @classmethod
    def load_test_drive(cls, phone_number: str) -> Optional[Dict[str, Any]]:
        if not cls._ensure_backend():
            d = cls._mem_test_drives.get(phone_number)
            return dict(d) if d is not None else None
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload FROM app_test_drives WHERE phone_number = %s",
                    (phone_number,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return row[0] if isinstance(row[0], dict) else json.loads(row[0])

    @classmethod
    def list_test_drives(cls) -> List[str]:
        if not cls._ensure_backend():
            return sorted(cls._mem_test_drives.keys())
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT phone_number FROM app_test_drives ORDER BY phone_number")
                return [r[0] for r in cur.fetchall()]

    @classmethod
    def delete_test_drive(cls, phone_number: str) -> bool:
        if not cls._ensure_backend():
            return cls._mem_test_drives.pop(phone_number, None) is not None
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM app_test_drives WHERE phone_number = %s",
                    (phone_number,),
                )
                return cur.rowcount > 0

    # --- Sessions ---

    @classmethod
    def save_session(cls, session_id: str, data: Dict[str, Any]) -> None:
        if not cls._ensure_backend():
            cls._mem_sessions[session_id] = dict(data)
            return
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_sessions (session_id, payload, updated_at)
                    VALUES (%s, %s::jsonb, NOW())
                    ON CONFLICT (session_id) DO UPDATE
                    SET payload = EXCLUDED.payload, updated_at = NOW()
                    """,
                    (session_id, json.dumps(data, ensure_ascii=False)),
                )

    @classmethod
    def load_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        if not cls._ensure_backend():
            s = cls._mem_sessions.get(session_id)
            return dict(s) if s is not None else None
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload FROM app_sessions WHERE session_id = %s",
                    (session_id,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return row[0] if isinstance(row[0], dict) else json.loads(row[0])

    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        if not cls._ensure_backend():
            return cls._mem_sessions.pop(session_id, None) is not None
        with cls._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM app_sessions WHERE session_id = %s",
                    (session_id,),
                )
                return cur.rowcount > 0


class FileStorage:
    """
    DEPRECATED: Legacy file-based JSON storage.

    Disabled in all non-test environments. Retained strictly for legacy unit tests
    running under APP_ENV=test/testing. Production code must use PostgresStorage
    and DistributedSessionStore.
    """

    @staticmethod
    def _guard_test_only() -> None:
        if not _is_test_env():
            raise RuntimeError(
                "FileStorage is deprecated and disabled outside test mode. "
                "Use PostgresStorage / DistributedSessionStore instead."
            )

    @staticmethod
    def save_profile(phone_number: str, profile: UserProfile) -> None:
        FileStorage._guard_test_only()
        path = PROFILES_DIR / f"{phone_number}.json"
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def load_profile(phone_number: str) -> Optional[UserProfile]:
        FileStorage._guard_test_only()
        path = PROFILES_DIR / f"{phone_number}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return UserProfile(**data)
        except Exception as e:
            logger.warning(f"Failed to load profile {phone_number}: {e}")
            return None

    @staticmethod
    def list_profiles() -> List[str]:
        FileStorage._guard_test_only()
        return [p.stem for p in PROFILES_DIR.glob("*.json")]

    @staticmethod
    def delete_profile(phone_number: str) -> bool:
        FileStorage._guard_test_only()
        path = PROFILES_DIR / f"{phone_number}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    @staticmethod
    def save_test_drive(phone_number: str, data: Dict) -> None:
        FileStorage._guard_test_only()
        path = TEST_DRIVES_DIR / f"{phone_number}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def load_test_drive(phone_number: str) -> Optional[Dict]:
        FileStorage._guard_test_only()
        path = TEST_DRIVES_DIR / f"{phone_number}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to load test drive {phone_number}: {e}")
            return None

    @staticmethod
    def list_test_drives() -> List[str]:
        FileStorage._guard_test_only()
        return [p.stem for p in TEST_DRIVES_DIR.glob("*.json")]

    @staticmethod
    def delete_test_drive(phone_number: str) -> bool:
        FileStorage._guard_test_only()
        path = TEST_DRIVES_DIR / f"{phone_number}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    @staticmethod
    def _session_path(session_id: str):
        digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        return SESSIONS_DIR / f"{digest}.json"

    @staticmethod
    def save_session(session_id: str, data: Dict) -> None:
        FileStorage._guard_test_only()
        path = FileStorage._session_path(session_id)
        temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def load_session(session_id: str) -> Optional[Dict]:
        FileStorage._guard_test_only()
        path = FileStorage._session_path(session_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to load session {session_id}: {e}")
            return None

    @staticmethod
    def delete_session(session_id: str) -> bool:
        FileStorage._guard_test_only()
        path = FileStorage._session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False
