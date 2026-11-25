"""
Unified Persistent Storage for Dealership Info, Promotions, and Test-Drive Bookings
(`src/core/dealer_store.py`).

Uses PostgreSQL (`dealer_stores`, `dealer_promotions`, `test_drive_bookings`) when PG
is active, with a deterministic SQLite fallback (`sqlite3`) for offline / test-mode runs.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.config import PROJECT_ROOT, config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _is_test_env() -> bool:
    env = (
        os.getenv("APP_ENV")
        or os.getenv("APP_ENVIRONMENT")
        or config.app_environment
        or "development"
    ).strip().lower()
    return env in ("test", "testing")


SEED_DEALER_STORES: Dict[str, Dict[str, Any]] = {
    "朝阳": {
        "store_key": "朝阳",
        "store_name": "AutoVend 朝阳旗舰4S店",
        "address": "北京市朝阳区东四环北路88号汽车大道1号馆",
        "parking": "院内专属地面及地下免费停车场，支持2小时免费充电",
        "business_hours": "每日 09:00 - 20:30（周末及节假日正常营业）",
        "showroom_models": ["小米SU7 Max", "特斯拉Model Y", "理想L6", "比亚迪海豹", "问界M7"],
        "available_test_drive_slots": ["10:00", "11:30", "14:00", "15:30", "17:00", "18:30"],
    },
    "海淀": {
        "store_key": "海淀",
        "store_name": "AutoVend 海淀中关村体验中心",
        "address": "北京市海淀区北四环西路66号",
        "parking": "大厦B2层专属客户停车位，凭试驾短信免费停3小时",
        "business_hours": "每日 09:30 - 21:00",
        "showroom_models": ["小米SU7", "特斯拉Model 3", "极氪001", "理想L6"],
        "available_test_drive_slots": ["10:30", "13:30", "15:00", "16:30", "19:00"],
    },
}

SEED_DEALER_PROMOTIONS: List[Dict[str, Any]] = [
    {
        "promo_id": "promo_trade_in_2026",
        "store_key": "*",
        "car_model": "*",
        "promo_type": "置换补贴",
        "benefit": "旧车置换至高补贴1.5万元",
        "valid_until": "本月底前有效",
    },
    {
        "promo_id": "promo_finance_2026",
        "store_key": "*",
        "car_model": "*",
        "promo_type": "金融礼遇",
        "benefit": "指定车型享2年0息或3.5%低息方案",
        "valid_until": "本月底前有效",
    },
    {
        "promo_id": "promo_charging_2026",
        "store_key": "*",
        "car_model": "*",
        "promo_type": "充电/保养礼包",
        "benefit": "本月下订赠家用充电桩或3次基础保养",
        "valid_until": "本月底前有效",
    },
]


class _DealerPersistenceBackend:
    """Shared PG + SQLite persistence backend for dealer catalog & test-drive bookings."""

    _lock = threading.RLock()
    _pg_pool: Optional[Any] = None
    _pg_ready: bool = False
    _pg_unavailable: bool = False
    _sqlite_conn: Optional[sqlite3.Connection] = None
    _sqlite_path: Optional[Path] = None
    _store_keywords_cache: Optional[List[str]] = None

    @classmethod
    def reset_for_tests(cls) -> None:
        with cls._lock:
            if cls._pg_pool is not None:
                try:
                    cls._pg_pool.close()
                except Exception:
                    pass
                cls._pg_pool = None
            cls._pg_ready = False
            cls._pg_unavailable = False
            if cls._sqlite_conn is not None:
                try:
                    cls._sqlite_conn.close()
                except Exception:
                    pass
                cls._sqlite_conn = None
            cls._sqlite_path = None
            cls._store_keywords_cache = None

    @classmethod
    def _ensure_pg(cls) -> bool:
        with cls._lock:
            if cls._pg_ready and cls._pg_pool is not None:
                return True
            if cls._pg_unavailable:
                return False
            if _is_test_env():
                # In test mode without explicit PG, use deterministic SQLite immediately
                cls._pg_unavailable = True
                return False
            pool: Optional[Any] = None
            try:
                import psycopg
                from psycopg_pool import ConnectionPool

                with psycopg.connect(config.pgvector_connection_string, connect_timeout=1):
                    pass

                pool = ConnectionPool(
                    conninfo=config.pgvector_connection_string,
                    min_size=1,
                    max_size=4,
                    kwargs={"connect_timeout": 1, "autocommit": True},
                    open=False,
                )
                pool.open(wait=True, timeout=1.2)
                with pool.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS dealer_stores (
                                store_key TEXT PRIMARY KEY,
                                store_name TEXT NOT NULL,
                                address TEXT NOT NULL,
                                parking TEXT NOT NULL,
                                business_hours TEXT NOT NULL,
                                showroom_models JSONB NOT NULL,
                                available_test_drive_slots JSONB NOT NULL,
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            CREATE TABLE IF NOT EXISTS dealer_promotions (
                                promo_id TEXT PRIMARY KEY,
                                store_key TEXT NOT NULL DEFAULT '*',
                                car_model TEXT NOT NULL DEFAULT '*',
                                promo_type TEXT NOT NULL,
                                benefit TEXT NOT NULL,
                                valid_until TEXT NOT NULL,
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            CREATE TABLE IF NOT EXISTS test_drive_bookings (
                                reservation_id TEXT PRIMARY KEY,
                                status TEXT NOT NULL,
                                car_model TEXT NOT NULL,
                                reservation_date TEXT NOT NULL,
                                reservation_time TEXT NOT NULL,
                                reservation_location TEXT NOT NULL,
                                test_driver TEXT NOT NULL,
                                phone_number TEXT NOT NULL,
                                idempotency_key TEXT,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            """
                        )
                cls._pg_pool = pool
                cls._pg_ready = True
                cls._bootstrap_pg_if_empty()
                return True
            except Exception as exc:
                if pool is not None:
                    try:
                        pool.close()
                    except Exception:
                        pass
                logger.debug(f"[DealerStore] PG unavailable ({exc}); using SQLite fallback.")
                cls._pg_unavailable = True
                return False

    @classmethod
    def _bootstrap_pg_if_empty(cls) -> None:
        if cls._pg_pool is None:
            return
        with cls._pg_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM dealer_stores")
                if cur.fetchone()[0] == 0:
                    for key, s in SEED_DEALER_STORES.items():
                        cur.execute(
                            """
                            INSERT INTO dealer_stores (
                                store_key, store_name, address, parking, business_hours,
                                showroom_models, available_test_drive_slots
                            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                            ON CONFLICT (store_key) DO NOTHING
                            """,
                            (
                                key,
                                s["store_name"],
                                s["address"],
                                s["parking"],
                                s["business_hours"],
                                json.dumps(s["showroom_models"], ensure_ascii=False),
                                json.dumps(s["available_test_drive_slots"], ensure_ascii=False),
                            ),
                        )
                cur.execute("SELECT COUNT(*) FROM dealer_promotions")
                if cur.fetchone()[0] == 0:
                    for p in SEED_DEALER_PROMOTIONS:
                        cur.execute(
                            """
                            INSERT INTO dealer_promotions (
                                promo_id, store_key, car_model, promo_type, benefit, valid_until
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (promo_id) DO NOTHING
                            """,
                            (
                                p["promo_id"],
                                p["store_key"],
                                p["car_model"],
                                p["promo_type"],
                                p["benefit"],
                                p["valid_until"],
                            ),
                        )

    @classmethod
    def _get_sqlite(cls) -> sqlite3.Connection:
        with cls._lock:
            if cls._sqlite_conn is not None:
                return cls._sqlite_conn
            if _is_test_env():
                conn = sqlite3.connect(":memory:", check_same_thread=False)
            else:
                db_dir = PROJECT_ROOT / "storage"
                db_dir.mkdir(parents=True, exist_ok=True)
                db_path = db_dir / "dealer_bookings.db"
                cls._sqlite_path = db_path
                conn = sqlite3.connect(str(db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS dealer_stores (
                    store_key TEXT PRIMARY KEY,
                    store_name TEXT NOT NULL,
                    address TEXT NOT NULL,
                    parking TEXT NOT NULL,
                    business_hours TEXT NOT NULL,
                    showroom_models TEXT NOT NULL,
                    available_test_drive_slots TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS dealer_promotions (
                    promo_id TEXT PRIMARY KEY,
                    store_key TEXT NOT NULL DEFAULT '*',
                    car_model TEXT NOT NULL DEFAULT '*',
                    promo_type TEXT NOT NULL,
                    benefit TEXT NOT NULL,
                    valid_until TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS test_drive_bookings (
                    reservation_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    car_model TEXT NOT NULL,
                    reservation_date TEXT NOT NULL,
                    reservation_time TEXT NOT NULL,
                    reservation_location TEXT NOT NULL,
                    test_driver TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    idempotency_key TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            now_iso = datetime.now(timezone.utc).isoformat()
            cur = conn.cursor()
            if cur.execute("SELECT COUNT(*) FROM dealer_stores").fetchone()[0] == 0:
                for key, s in SEED_DEALER_STORES.items():
                    cur.execute(
                        """
                        INSERT INTO dealer_stores (
                            store_key, store_name, address, parking, business_hours,
                            showroom_models, available_test_drive_slots, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            key,
                            s["store_name"],
                            s["address"],
                            s["parking"],
                            s["business_hours"],
                            json.dumps(s["showroom_models"], ensure_ascii=False),
                            json.dumps(s["available_test_drive_slots"], ensure_ascii=False),
                            now_iso,
                        ),
                    )
            if cur.execute("SELECT COUNT(*) FROM dealer_promotions").fetchone()[0] == 0:
                for p in SEED_DEALER_PROMOTIONS:
                    cur.execute(
                        """
                        INSERT INTO dealer_promotions (
                            promo_id, store_key, car_model, promo_type, benefit, valid_until, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            p["promo_id"],
                            p["store_key"],
                            p["car_model"],
                            p["promo_type"],
                            p["benefit"],
                            p["valid_until"],
                            now_iso,
                        ),
                    )
            conn.commit()
            cls._sqlite_conn = conn
            return conn


class DealerStore:
    """Unified repository for dealership store info and active promotions."""

    @classmethod
    def list_stores(cls) -> List[Dict[str, Any]]:
        if _DealerPersistenceBackend._ensure_pg():
            with _DealerPersistenceBackend._pg_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT store_key, store_name, address, parking, business_hours,
                               showroom_models, available_test_drive_slots
                        FROM dealer_stores
                        ORDER BY store_key
                        """
                    )
                    rows = cur.fetchall()
            return [
                {
                    "store_key": r[0],
                    "store_name": r[1],
                    "address": r[2],
                    "parking": r[3],
                    "business_hours": r[4],
                    "showroom_models": list(r[5] or []),
                    "available_test_drive_slots": list(r[6] or []),
                }
                for r in rows
            ]

        with _DealerPersistenceBackend._lock:
            conn = _DealerPersistenceBackend._get_sqlite()
            rows = conn.execute(
                """
                SELECT store_key, store_name, address, parking, business_hours,
                       showroom_models, available_test_drive_slots
                FROM dealer_stores
                ORDER BY store_key
                """
            ).fetchall()
            return [
                {
                    "store_key": r["store_key"],
                    "store_name": r["store_name"],
                    "address": r["address"],
                    "parking": r["parking"],
                    "business_hours": r["business_hours"],
                    "showroom_models": json.loads(r["showroom_models"]),
                    "available_test_drive_slots": json.loads(r["available_test_drive_slots"]),
                }
                for r in rows
            ]

    @classmethod
    def get_store_keywords(cls) -> List[str]:
        """Return cached list of store keys & names for <1ms entity extraction."""
        if _DealerPersistenceBackend._store_keywords_cache is not None:
            return list(_DealerPersistenceBackend._store_keywords_cache)
        stores = cls.list_stores()
        keywords: List[str] = []
        for s in stores:
            key = str(s.get("store_key") or "").strip()
            name = str(s.get("store_name") or "").strip()
            if key and key not in keywords:
                keywords.append(key)
            if name and name not in keywords:
                keywords.append(name)
        _DealerPersistenceBackend._store_keywords_cache = keywords
        return list(keywords)

    @classmethod
    def upsert_store(
        cls,
        store_key: str,
        store_name: str,
        address: str,
        parking: str,
        business_hours: str,
        showroom_models: List[str],
        available_test_drive_slots: List[str],
    ) -> None:
        _DealerPersistenceBackend._store_keywords_cache = None
        if _DealerPersistenceBackend._ensure_pg():
            with _DealerPersistenceBackend._pg_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO dealer_stores (
                            store_key, store_name, address, parking, business_hours,
                            showroom_models, available_test_drive_slots, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, NOW())
                        ON CONFLICT (store_key) DO UPDATE SET
                            store_name = EXCLUDED.store_name,
                            address = EXCLUDED.address,
                            parking = EXCLUDED.parking,
                            business_hours = EXCLUDED.business_hours,
                            showroom_models = EXCLUDED.showroom_models,
                            available_test_drive_slots = EXCLUDED.available_test_drive_slots,
                            updated_at = NOW()
                        """,
                        (
                            store_key,
                            store_name,
                            address,
                            parking,
                            business_hours,
                            json.dumps(showroom_models, ensure_ascii=False),
                            json.dumps(available_test_drive_slots, ensure_ascii=False),
                        ),
                    )
            return

        now_iso = datetime.now(timezone.utc).isoformat()
        with _DealerPersistenceBackend._lock:
            conn = _DealerPersistenceBackend._get_sqlite()
            conn.execute(
                """
                INSERT INTO dealer_stores (
                    store_key, store_name, address, parking, business_hours,
                    showroom_models, available_test_drive_slots, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(store_key) DO UPDATE SET
                    store_name = excluded.store_name,
                    address = excluded.address,
                    parking = excluded.parking,
                    business_hours = excluded.business_hours,
                    showroom_models = excluded.showroom_models,
                    available_test_drive_slots = excluded.available_test_drive_slots,
                    updated_at = excluded.updated_at
                """,
                (
                    store_key,
                    store_name,
                    address,
                    parking,
                    business_hours,
                    json.dumps(showroom_models, ensure_ascii=False),
                    json.dumps(available_test_drive_slots, ensure_ascii=False),
                    now_iso,
                ),
            )
            conn.commit()

    @classmethod
    def get_dealer_info(
        cls,
        store_name: Optional[str] = None,
        car_model: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        stores = cls.list_stores()
        selected = stores[0] if stores else dict(SEED_DEALER_STORES["朝阳"])
        if store_name:
            for info in stores:
                if info["store_key"] in store_name or store_name in info["store_name"]:
                    selected = info
                    break
        has_showroom_car = True
        if car_model:
            has_showroom_car = any(
                car_model.lower() in m.lower() or m.lower() in car_model.lower()
                for m in selected.get("showroom_models", [])
            )
        return {
            "store_key": selected.get("store_key", ""),
            "store_name": selected.get("store_name", ""),
            "address": selected.get("address", ""),
            "parking": selected.get("parking", ""),
            "business_hours": selected.get("business_hours", ""),
            "showroom_models": list(selected.get("showroom_models", [])),
            "available_test_drive_slots": list(selected.get("available_test_drive_slots", [])),
            "query_date": date or "今日",
            "requested_car_model": car_model,
            "showroom_car_available": has_showroom_car,
        }

    @classmethod
    def get_promotions(
        cls,
        car_model: Optional[str] = None,
        store_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        if _DealerPersistenceBackend._ensure_pg():
            with _DealerPersistenceBackend._pg_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT store_key, car_model, promo_type, benefit, valid_until FROM dealer_promotions"
                    )
                    rows = cur.fetchall()
            raw_promos = [
                {
                    "store_key": r[0],
                    "car_model": r[1],
                    "type": r[2],
                    "benefit": r[3],
                    "valid_until": r[4],
                }
                for r in rows
            ]
        else:
            with _DealerPersistenceBackend._lock:
                conn = _DealerPersistenceBackend._get_sqlite()
                rows = conn.execute(
                    "SELECT store_key, car_model, promo_type, benefit, valid_until FROM dealer_promotions"
                ).fetchall()
                raw_promos = [
                    {
                        "store_key": r["store_key"],
                        "car_model": r["car_model"],
                        "type": r["promo_type"],
                        "benefit": r["benefit"],
                        "valid_until": r["valid_until"],
                    }
                    for r in rows
                ]

        matched: List[Dict[str, str]] = []
        valid_until = "本月底前有效"
        for p in raw_promos:
            s_ok = p["store_key"] == "*" or (store_name and p["store_key"] in store_name)
            m_ok = p["car_model"] == "*" or (
                car_model and (car_model.lower() in p["car_model"].lower() or p["car_model"].lower() in car_model.lower())
            )
            if s_ok and m_ok:
                matched.append({"type": p["type"], "benefit": p["benefit"]})
                valid_until = p["valid_until"]

        return {
            "car_model": car_model or "全系热门车型",
            "store_name": store_name or "AutoVend 旗舰体验中心",
            "promotions": matched,
            "valid_until": valid_until,
        }


class TestDriveStore:
    """Unified persistent repository for test-drive bookings across submit & manage tools."""

    @classmethod
    def upsert_booking(
        cls,
        reservation_id: str,
        status: str,
        car_model: str,
        reservation_date: str,
        reservation_time: str,
        reservation_location: str,
        test_driver: str,
        phone_number: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if _DealerPersistenceBackend._ensure_pg():
            with _DealerPersistenceBackend._pg_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO test_drive_bookings (
                            reservation_id, status, car_model, reservation_date,
                            reservation_time, reservation_location, test_driver,
                            phone_number, idempotency_key, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (reservation_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            car_model = EXCLUDED.car_model,
                            reservation_date = EXCLUDED.reservation_date,
                            reservation_time = EXCLUDED.reservation_time,
                            reservation_location = EXCLUDED.reservation_location,
                            test_driver = EXCLUDED.test_driver,
                            phone_number = EXCLUDED.phone_number,
                            idempotency_key = COALESCE(EXCLUDED.idempotency_key, test_drive_bookings.idempotency_key),
                            updated_at = NOW()
                        """,
                        (
                            reservation_id,
                            status,
                            car_model,
                            reservation_date,
                            reservation_time,
                            reservation_location,
                            test_driver,
                            phone_number,
                            idempotency_key,
                        ),
                    )
        else:
            now_iso = datetime.now(timezone.utc).isoformat()
            with _DealerPersistenceBackend._lock:
                conn = _DealerPersistenceBackend._get_sqlite()
                conn.execute(
                    """
                    INSERT INTO test_drive_bookings (
                        reservation_id, status, car_model, reservation_date,
                        reservation_time, reservation_location, test_driver,
                        phone_number, idempotency_key, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(reservation_id) DO UPDATE SET
                        status = excluded.status,
                        car_model = excluded.car_model,
                        reservation_date = excluded.reservation_date,
                        reservation_time = excluded.reservation_time,
                        reservation_location = excluded.reservation_location,
                        test_driver = excluded.test_driver,
                        phone_number = excluded.phone_number,
                        idempotency_key = COALESCE(excluded.idempotency_key, test_drive_bookings.idempotency_key),
                        updated_at = excluded.updated_at
                    """,
                    (
                        reservation_id,
                        status,
                        car_model,
                        reservation_date,
                        reservation_time,
                        reservation_location,
                        test_driver,
                        phone_number,
                        idempotency_key,
                        now_iso,
                        now_iso,
                    ),
                )
                conn.commit()
        return {
            "reservation_id": reservation_id,
            "status": status,
            "car_model": car_model,
            "reservation_date": reservation_date,
            "reservation_time": reservation_time,
            "reservation_location": reservation_location,
            "test_driver": test_driver,
            "phone_number": phone_number,
            "idempotency_key": idempotency_key,
        }

    @classmethod
    def query_bookings(
        cls,
        reservation_id: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if reservation_id:
            clauses.append("reservation_id = %s" if _DealerPersistenceBackend._ensure_pg() else "reservation_id = ?")
            params.append(reservation_id)
        if phone_number:
            clauses.append("phone_number = %s" if _DealerPersistenceBackend._ensure_pg() else "phone_number = ?")
            params.append(phone_number)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        if _DealerPersistenceBackend._ensure_pg():
            with _DealerPersistenceBackend._pg_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT reservation_id, status, car_model, reservation_date,
                               reservation_time, reservation_location, test_driver,
                               phone_number, idempotency_key
                        FROM test_drive_bookings
                        {where_sql}
                        ORDER BY updated_at DESC
                        """,
                        tuple(params),
                    )
                    rows = cur.fetchall()
            return [
                {
                    "reservation_id": r[0],
                    "status": r[1],
                    "car_model": r[2],
                    "reservation_date": r[3],
                    "reservation_time": r[4],
                    "reservation_location": r[5],
                    "test_driver": r[6],
                    "phone_number": r[7],
                    "idempotency_key": r[8],
                }
                for r in rows
            ]

        with _DealerPersistenceBackend._lock:
            conn = _DealerPersistenceBackend._get_sqlite()
            rows = conn.execute(
                f"""
                SELECT reservation_id, status, car_model, reservation_date,
                       reservation_time, reservation_location, test_driver,
                       phone_number, idempotency_key
                FROM test_drive_bookings
                {where_sql}
                ORDER BY updated_at DESC
                """,
                tuple(params),
            ).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def cancel_booking(
        cls,
        reservation_id: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        matches = cls.query_bookings(reservation_id=reservation_id, phone_number=phone_number)
        target = None
        for m in matches:
            if m.get("status") != "CANCELLED":
                target = m
                break
        if target is None and matches:
            target = matches[0]
        if target is None:
            return None

        rid = target["reservation_id"]
        if _DealerPersistenceBackend._ensure_pg():
            with _DealerPersistenceBackend._pg_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE test_drive_bookings SET status = 'CANCELLED', updated_at = NOW() WHERE reservation_id = %s",
                        (rid,),
                    )
        else:
            now_iso = datetime.now(timezone.utc).isoformat()
            with _DealerPersistenceBackend._lock:
                conn = _DealerPersistenceBackend._get_sqlite()
                conn.execute(
                    "UPDATE test_drive_bookings SET status = 'CANCELLED', updated_at = ? WHERE reservation_id = ?",
                    (now_iso, rid),
                )
                conn.commit()
        target["status"] = "CANCELLED"
        return target

    @classmethod
    def reset_for_tests(cls) -> None:
        _DealerPersistenceBackend.reset_for_tests()
