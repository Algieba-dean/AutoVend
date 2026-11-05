"""
Distributed Session State & Lock Management (src/core/storage/distributed_session.py).

Provides:
1. DistributedSessionStore: Redis-backed (or in-memory fallback) session storage with 7-day TTL.
2. Distributed Lease Lock: Redis SETNX lease lock with Lua-script atomic release.
3. Optimistic Concurrency Control (OCC): version-incrementing on each save to prevent stale-write race conditions.
"""

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional, Tuple

from src.agent.schemas import SessionState, UserProfile

logger = logging.getLogger(__name__)

# Try importing redis.asyncio or aioredis
_AIOREDIS = None
try:
    import redis.asyncio as _aioredis
    _AIOREDIS = _aioredis
except ImportError:
    try:
        import aioredis as _aioredis_legacy
        _AIOREDIS = _aioredis_legacy
    except ImportError:
        _AIOREDIS = None


class SessionLockTimeoutError(Exception):
    """Raised when a distributed session lock cannot be acquired within the timeout."""

    def __init__(
        self,
        session_id: str,
        message: str = "User turn is already being processed. Please wait.",
    ):
        super().__init__(message)
        self.session_id = session_id
        self.status_code = 429
        self.detail = message


class DistributedSessionStore:
    """
    Distributed session state store backed by Redis Hash / Key-Value with auto-expiring TTL
    and distributed lease locking. Gracefully falls back to high-performance in-memory async locking
    when Redis is not running or redis package is not installed.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: int = 86400 * 7,  # 7-day auto-expiry
    ):
        self.ttl = ttl_seconds
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.redis = None
        self._redis_available = False

        # In-memory storage & locking fallback for standalone / test environments
        self._local_sessions: Dict[str, Tuple[SessionState, float]] = {}  # session_id -> (state, expire_at)
        self._local_locks: Dict[str, asyncio.Lock] = {}
        self._lock_tokens: Dict[str, str] = {}

        if self.redis_url and _AIOREDIS is not None:
            try:
                self.redis = _AIOREDIS.from_url(self.redis_url, decode_responses=True)
                self._redis_available = True
                logger.info(f"DistributedSessionStore configured with Redis at {self.redis_url}")
            except Exception as e:
                logger.warning(
                    f"Failed to connect to Redis at {self.redis_url}: {e}. Falling back to in-memory store."
                )
                self.redis = None
                self._redis_available = False

    async def get(self, session_id: str) -> Optional[SessionState]:
        """Fetch session snapshot from Redis or in-memory store."""
        if self._redis_available and self.redis is not None:
            try:
                data = await self.redis.get(f"session:{session_id}")
                if not data:
                    return None
                return SessionState.model_validate_json(data)
            except Exception as e:
                logger.warning(
                    f"Redis get failed for session {session_id}: {e}. Checking local cache."
                )

        # Local fallback
        entry = self._local_sessions.get(session_id)
        if not entry:
            return None
        state, expire_at = entry
        if time.time() > expire_at:
            self._local_sessions.pop(session_id, None)
            return None
        return state

    async def get_or_create(
        self,
        session_id: str,
        profile: Optional[UserProfile] = None,
    ) -> SessionState:
        """Atomic fetch or initialize session."""
        state = await self.get(session_id)
        if state is None:
            state = SessionState(
                session_id=session_id,
                profile=profile or UserProfile(),
                version=1,
            )
            await self.save(session_id, state)
        return state

    async def save(self, session_id: str, state: SessionState) -> None:
        """Persist state with optimistic concurrency control (OCC version bump) and auto-expiring TTL."""
        state.version += 1
        serialized = state.model_dump_json()

        if self._redis_available and self.redis is not None:
            try:
                await self.redis.set(f"session:{session_id}", serialized, ex=self.ttl)
                return
            except Exception as e:
                logger.warning(f"Redis save failed for session {session_id}: {e}. Storing locally.")

        # Local fallback
        self._local_sessions[session_id] = (state.model_copy(deep=True), time.time() + self.ttl)

    async def delete(self, session_id: str) -> bool:
        """Delete session from Redis and local cache."""
        deleted = False
        if self._redis_available and self.redis is not None:
            try:
                res = await self.redis.delete(f"session:{session_id}")
                deleted = bool(res)
            except Exception as e:
                logger.warning(f"Redis delete failed for session {session_id}: {e}")

        if session_id in self._local_sessions:
            del self._local_sessions[session_id]
            deleted = True
        return deleted

    async def _acquire_redis_lock(
        self, lock_key: str, token: str, timeout: float, wait_timeout: float = 5.0
    ) -> bool:
        """Try to acquire Redis lock with timeout."""
        deadline = asyncio.get_running_loop().time() + wait_timeout
        while asyncio.get_running_loop().time() < deadline:
            try:
                ok = await self.redis.set(lock_key, token, nx=True, px=int(timeout * 1000))
                if ok:
                    return True
            except Exception as e:
                logger.warning(f"Redis setnx error: {e}")
                return False
            await asyncio.sleep(0.05)
        return False

    @asynccontextmanager
    async def lock_session(
        self,
        session_id: str,
        timeout: float = 10.0,
        wait_timeout: float = 5.0,
    ):
        """
        Distributed re-entrant lease lock using Redis SETNX + Unique Token.
        Automatically safely released via Lua script.
        Falls back to local asyncio Lock when Redis is unavailable.
        Raises SessionLockTimeoutError when lock cannot be acquired within wait_timeout.
        """
        lock_key = f"lock:session:{session_id}"
        token = str(uuid.uuid4())

        if self._redis_available and self.redis is not None:
            acquired = await self._acquire_redis_lock(
                lock_key, token, timeout=timeout, wait_timeout=wait_timeout
            )
            if not acquired:
                logger.warning(
                    f"Session {session_id} Redis lock acquisition timed out. Rejecting concurrent turn."
                )
                raise SessionLockTimeoutError(session_id=session_id)
            try:
                yield
            finally:
                # Lua script ensures only the owner token can release the lock
                release_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                try:
                    await self.redis.eval(release_script, 1, lock_key, token)
                except Exception as e:
                    logger.error(f"Failed to release Redis lock for {session_id}: {e}")
        else:
            # Local async lock fallback
            if session_id not in self._local_locks:
                self._local_locks[session_id] = asyncio.Lock()
            lock = self._local_locks[session_id]

            acquired = False
            try:
                await asyncio.wait_for(lock.acquire(), timeout=wait_timeout)
                acquired = True
            except asyncio.TimeoutError:
                logger.warning(
                    f"Session {session_id} local lock acquisition timed out. Rejecting concurrent turn."
                )
                raise SessionLockTimeoutError(session_id=session_id)

            self._lock_tokens[session_id] = token
            try:
                yield
            finally:
                if acquired and lock.locked() and self._lock_tokens.get(session_id) == token:
                    self._lock_tokens.pop(session_id, None)
                    lock.release()


# Global singleton instance
_GLOBAL_DISTRIBUTED_STORE: Optional[DistributedSessionStore] = None


def get_distributed_session_store() -> DistributedSessionStore:
    """Get or initialize global distributed session store."""
    global _GLOBAL_DISTRIBUTED_STORE
    if _GLOBAL_DISTRIBUTED_STORE is None:
        _GLOBAL_DISTRIBUTED_STORE = DistributedSessionStore()
    return _GLOBAL_DISTRIBUTED_STORE


def set_distributed_session_store(store: DistributedSessionStore) -> None:
    """Inject a custom distributed session store (for tests or custom Redis configs)."""
    global _GLOBAL_DISTRIBUTED_STORE
    _GLOBAL_DISTRIBUTED_STORE = store
