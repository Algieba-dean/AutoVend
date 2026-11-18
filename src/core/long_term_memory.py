"""
Async Long-Term User Memory Store (src/core/long_term_memory.py).

Extracts high-value persistent user profile attributes at session end
(parking/charging conditions, family structure, residence, brand/powertrain
preferences), persists them to PostgreSQL (`autovend_long_term_memory`) with
safe in-memory fallback when PostgreSQL is unavailable, and recalls them
across sessions on demand.
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.utils.config import config

logger = logging.getLogger(__name__)


class UserLongTermMemory(BaseModel):
    """Persistent cross-session customer profile."""

    user_key: str
    name: str = ""
    parking_conditions: str = ""
    family_size: str = ""
    residence: str = ""
    price_sensitivity: str = ""
    expertise: str = ""
    preferred_brands: List[str] = Field(default_factory=list)
    powertrain_preference: str = ""
    summary: str = ""
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LongTermMemoryStore:
    """
    PostgreSQL-backed long-term memory store with safe in-memory fallback.
    """

    _instance: Optional["LongTermMemoryStore"] = None

    def __init__(self, dsn: Optional[str] = None):
        self._dsn = dsn or config.pgvector_connection_string
        self._memory_fallback: Dict[str, UserLongTermMemory] = {}
        self._pg_available: Optional[bool] = None
        self._table_ready: bool = False

    @classmethod
    def get_instance(cls) -> "LongTermMemoryStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _can_use_postgres(self) -> bool:
        if os.getenv("PYTEST_CURRENT_TEST") and self._dsn == config.pgvector_connection_string:
            return False
        if self._pg_available is False:
            return False
        return bool(self._dsn)

    def _ensure_table(self, conn) -> None:
        if self._table_ready:
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS autovend_long_term_memory (
                    user_key TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        conn.commit()
        self._table_ready = True

    def save(self, memory: UserLongTermMemory) -> None:
        """Persist `UserLongTermMemory` to PostgreSQL or in-memory fallback."""
        memory.updated_at = datetime.now(timezone.utc).isoformat()
        self._memory_fallback[memory.user_key] = memory

        if not self._can_use_postgres():
            return
        try:
            import psycopg

            with psycopg.connect(self._dsn, connect_timeout=2) as conn:
                self._ensure_table(conn)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO autovend_long_term_memory (user_key, payload, updated_at)
                        VALUES (%s, %s::jsonb, NOW())
                        ON CONFLICT (user_key)
                        DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
                        """,
                        (memory.user_key, memory.model_dump_json()),
                    )
                conn.commit()
                self._pg_available = True
        except Exception as exc:
            self._pg_available = False
            logger.debug(f"PostgreSQL long-term memory save fell back to memory: {exc}")

    def recall(self, user_key: str) -> Optional[UserLongTermMemory]:
        """Recall `UserLongTermMemory` by `user_key` (phone_number / user_id / session_id)."""
        if not user_key:
            return None
        if user_key in self._memory_fallback:
            return self._memory_fallback[user_key]

        if not self._can_use_postgres():
            return None
        try:
            import psycopg

            with psycopg.connect(self._dsn, connect_timeout=2) as conn:
                self._ensure_table(conn)
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT payload FROM autovend_long_term_memory WHERE user_key = %s",
                        (user_key,),
                    )
                    row = cur.fetchone()
                self._pg_available = True
                if row and row[0]:
                    data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                    mem = UserLongTermMemory.model_validate(data)
                    self._memory_fallback[user_key] = mem
                    return mem
        except Exception as exc:
            self._pg_available = False
            logger.debug(f"PostgreSQL long-term memory recall fell back to memory: {exc}")
        return None

    def extract_profile_facts(
        self,
        user_key: str,
        session_state: Any,
        conversation_text: str = "",
    ) -> Optional[UserLongTermMemory]:
        """Extract high-value persistent profile facts from session_state & transcript."""
        profile = getattr(session_state, "profile", None)
        needs = getattr(session_state, "needs", None)
        explicit = getattr(needs, "explicit", None) if needs else None

        parking = getattr(profile, "parking_conditions", "") or ""
        family = getattr(profile, "family_size", "") or ""
        residence = getattr(profile, "residence", "") or ""
        name = getattr(profile, "name", "") or ""
        price_sens = getattr(profile, "price_sensitivity", "") or ""
        expertise = getattr(profile, "expertise", "") or ""

        # Heuristic supplement from conversation_text if slots weren't filled
        if not parking and conversation_text:
            m = re.search(r"(有固定车位|无固定车位|有家充桩|没有充电桩|无法装桩|地下车库|小区车位)", conversation_text)
            if m:
                parking = m.group(1)
        if not family and conversation_text:
            m = re.search(r"(三口之家|四口之家|五口之家|二胎|有老人|带娃|单身|夫妻)", conversation_text)
            if m:
                family = m.group(1)

        brands: List[str] = []
        if explicit and getattr(explicit, "brand", ""):
            brands = [b.strip() for b in re.split(r"[,，/、\s]+", explicit.brand) if b.strip()]
        powertrain = getattr(explicit, "powertrain_type", "") if explicit else ""

        if not any([parking, family, residence, name, brands, powertrain, price_sens, expertise]):
            return None

        existing = self.recall(user_key)
        merged_brands = list(dict.fromkeys([*(existing.preferred_brands if existing else []), *brands]))

        parts = []
        if family:
            parts.append(f"家庭结构: {family}")
        if parking:
            parts.append(f"车位/充电: {parking}")
        if residence:
            parts.append(f"常驻地: {residence}")
        if powertrain:
            parts.append(f"动力偏好: {powertrain}")
        if merged_brands:
            parts.append(f"关注品牌: {'/'.join(merged_brands)}")

        return UserLongTermMemory(
            user_key=user_key,
            name=name or (existing.name if existing else ""),
            parking_conditions=parking or (existing.parking_conditions if existing else ""),
            family_size=family or (existing.family_size if existing else ""),
            residence=residence or (existing.residence if existing else ""),
            price_sensitivity=price_sens or (existing.price_sensitivity if existing else ""),
            expertise=expertise or (existing.expertise if existing else ""),
            preferred_brands=merged_brands,
            powertrain_preference=powertrain or (existing.powertrain_preference if existing else ""),
            summary="；".join(parts),
        )

    async def aextract_and_save(
        self,
        user_key: str,
        session_state: Any,
        conversation_text: str = "",
    ) -> Optional[UserLongTermMemory]:
        """Asynchronously extract and persist long-term user memory."""
        mem = self.extract_profile_facts(user_key, session_state, conversation_text)
        if mem is None:
            return None
        await asyncio.to_thread(self.save, mem)
        return mem

    @staticmethod
    def format_for_prompt(memory: Optional[UserLongTermMemory]) -> str:
        if memory is None or not memory.summary:
            return ""
        return f"[跨会话长期用户记忆] {memory.summary}"

    def clear(self) -> None:
        self._memory_fallback.clear()
