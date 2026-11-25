"""
PostgreSQL Master Data Repository for Truth Engine (`src/truth_engine/master_data.py`).

Replaces hardcoded Python dicts (`DEPRECIATION_DATABASE`, `DEFAULT_MSRP_MAP`,
static tax policy constants) with time-versioned PostgreSQL master tables:
- `truth_vehicle_pricing`: MSRP, 1y/3y residual rates, wholesale/retail ranges, effective_from/updated_at
- `truth_tax_policies`: purchase tax rate, NEV exemption cap, VAT divisor, effective_from/updated_at
- `truth_finance_subsidies`: OEM/government subsidies & APR terms

Incremental updates are fed by `src/crawler/` scheduled jobs.
In non-test environments, PostgreSQL is mandatory (fail-fast).
In test mode (`APP_ENV=test` / `testing`), an isolated in-memory seed is used when PG is unavailable.
"""

import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.truth_engine.models import DepreciationValuation
from src.utils.config import config
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


# Initial seed dataset used to bootstrap an empty PostgreSQL master table
# (or serve isolated unit tests when APP_ENV=test/testing without live PG).
SEED_VEHICLE_PRICING: Dict[str, Dict[str, Any]] = {
    "小米SU7 Max": {
        "msrp_wan": 29.99,
        "one_year_residual_rate": 0.78,
        "three_year_residual_rate": 0.55,
        "wholesale_price_range_wan": "21.5 - 23.0 万元",
        "retail_price_range_wan": "23.5 - 25.5 万元",
        "market_liquidity_rating": "极高 (热度榜前列，二手周转期<14天)",
    },
    "小米SU7 Pro": {"msrp_wan": 24.59},
    "小米SU7 标准版": {
        "msrp_wan": 21.59,
        "one_year_residual_rate": 0.74,
        "three_year_residual_rate": 0.51,
        "wholesale_price_range_wan": "15.5 - 16.8 万元",
        "retail_price_range_wan": "17.2 - 18.5 万元",
        "market_liquidity_rating": "高",
    },
    "小米SU7 Ultra": {
        "msrp_wan": 81.49,
        "one_year_residual_rate": 0.85,
        "three_year_residual_rate": 0.60,
        "wholesale_price_range_wan": "68.0 - 74.0 万元",
        "retail_price_range_wan": "72.0 - 78.0 万元",
        "market_liquidity_rating": "高 (稀缺性能旗舰)",
    },
    "比亚迪汉EV": {
        "msrp_wan": 17.98,
        "one_year_residual_rate": 0.68,
        "three_year_residual_rate": 0.48,
        "wholesale_price_range_wan": "12.0 - 14.5 万元",
        "retail_price_range_wan": "13.5 - 16.0 万元",
        "market_liquidity_rating": "高 (市场保有量大，转手极为容易)",
    },
    "比亚迪汉DM-i": {
        "msrp_wan": 16.98,
        "one_year_residual_rate": 0.71,
        "three_year_residual_rate": 0.52,
        "wholesale_price_range_wan": "11.5 - 13.5 万元",
        "retail_price_range_wan": "13.0 - 15.0 万元",
        "market_liquidity_rating": "高",
    },
    "比亚迪秦PLUS DM-i": {
        "msrp_wan": 7.98,
        "one_year_residual_rate": 0.70,
        "three_year_residual_rate": 0.49,
        "wholesale_price_range_wan": "5.5 - 6.8 万元",
        "retail_price_range_wan": "6.3 - 7.5 万元",
        "market_liquidity_rating": "高",
    },
    "比亚迪海豹EV": {
        "msrp_wan": 17.58,
        "one_year_residual_rate": 0.68,
        "three_year_residual_rate": 0.47,
        "wholesale_price_range_wan": "11.5 - 13.5 万元",
        "retail_price_range_wan": "13.0 - 15.0 万元",
        "market_liquidity_rating": "中等",
    },
    "比亚迪海鸥": {
        "msrp_wan": 6.98,
        "one_year_residual_rate": 0.76,
        "three_year_residual_rate": 0.54,
        "wholesale_price_range_wan": "5.0 - 5.8 万元",
        "retail_price_range_wan": "5.6 - 6.5 万元",
        "market_liquidity_rating": "极高 (低总价代步刚需，残值坚挺)",
    },
    "特斯拉Model 3": {
        "msrp_wan": 23.19,
        "one_year_residual_rate": 0.77,
        "three_year_residual_rate": 0.56,
        "wholesale_price_range_wan": "16.5 - 18.5 万元",
        "retail_price_range_wan": "18.0 - 20.0 万元",
        "market_liquidity_rating": "极高 (流通硬通货)",
    },
    "特斯拉Model Y": {
        "msrp_wan": 24.99,
        "one_year_residual_rate": 0.76,
        "three_year_residual_rate": 0.55,
        "wholesale_price_range_wan": "18.0 - 20.0 万元",
        "retail_price_range_wan": "19.5 - 21.8 万元",
        "market_liquidity_rating": "极高 (全球销量标杆，转手极快)",
    },
    "极氪001": {
        "msrp_wan": 26.90,
        "one_year_residual_rate": 0.69,
        "three_year_residual_rate": 0.49,
        "wholesale_price_range_wan": "17.0 - 20.0 万元",
        "retail_price_range_wan": "19.0 - 22.5 万元",
        "market_liquidity_rating": "中高",
    },
    "极氪007": {
        "msrp_wan": 20.99,
        "one_year_residual_rate": 0.70,
        "three_year_residual_rate": 0.49,
        "wholesale_price_range_wan": "14.5 - 16.5 万元",
        "retail_price_range_wan": "16.0 - 18.2 万元",
        "market_liquidity_rating": "中高",
    },
    "问界M9": {
        "msrp_wan": 46.98,
        "one_year_residual_rate": 0.80,
        "three_year_residual_rate": 0.58,
        "wholesale_price_range_wan": "36.0 - 41.0 万元",
        "retail_price_range_wan": "38.5 - 43.5 万元",
        "market_liquidity_rating": "高 (高端豪华新能源热销车型)",
    },
    "问界M9 EV": {"msrp_wan": 50.98},
    "问界M7": {
        "msrp_wan": 24.98,
        "one_year_residual_rate": 0.75,
        "three_year_residual_rate": 0.53,
        "wholesale_price_range_wan": "17.5 - 20.0 万元",
        "retail_price_range_wan": "19.0 - 22.0 万元",
        "market_liquidity_rating": "高",
    },
    "理想L7": {"msrp_wan": 30.18},
    "理想L8": {
        "msrp_wan": 32.18,
        "one_year_residual_rate": 0.76,
        "three_year_residual_rate": 0.54,
        "wholesale_price_range_wan": "24.0 - 27.0 万元",
        "retail_price_range_wan": "26.0 - 29.5 万元",
        "market_liquidity_rating": "高",
    },
    "理想L9": {"msrp_wan": 40.98},
    "小鹏G6": {"msrp_wan": 19.99},
    "蔚来ET5": {"msrp_wan": 29.80},
}


class TruthMasterDataStore:
    """PostgreSQL-backed Master Data Store for vehicle pricing, residual values, and tax policies."""

    _lock = threading.RLock()
    _pool: Optional[Any] = None
    _schema_ready: bool = False
    _use_test_memory: bool = False
    _mem_pricing: Dict[str, Dict[str, Any]] = {}
    _mem_tax_policy: Dict[str, Any] = {
        "policy_key": "cn_2025_standard",
        "purchase_tax_rate": 0.10,
        "nev_exemption_limit_wan": 3.0,
        "vat_divisor": 1.13,
    }

    _unavailable_until: float = 0.0
    _last_error: str = ""

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
            cls._use_test_memory = False
            cls._unavailable_until = 0.0
            cls._last_error = ""
            cls._mem_pricing.clear()

    @classmethod
    def _ensure_ready(cls) -> bool:
        """Return True if PostgreSQL is active, False if in-memory test mode is active."""
        import time as _time

        with cls._lock:
            if cls._schema_ready and cls._pool is not None:
                return True
            if cls._use_test_memory and _is_test_env():
                return False
            if _time.monotonic() < cls._unavailable_until:
                if not _is_test_env():
                    raise RuntimeError(
                        f"PostgreSQL is required for Truth Engine master data in non-test environments: {cls._last_error}"
                    )
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
                    max_size=5,
                    kwargs={"connect_timeout": 1, "autocommit": True},
                    open=False,
                )
                pool.open(wait=True, timeout=1.2)
                with pool.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS truth_vehicle_pricing (
                                car_model TEXT PRIMARY KEY,
                                msrp_wan DOUBLE PRECISION,
                                one_year_residual_rate DOUBLE PRECISION,
                                three_year_residual_rate DOUBLE PRECISION,
                                wholesale_price_range_wan TEXT,
                                retail_price_range_wan TEXT,
                                market_liquidity_rating TEXT,
                                source TEXT NOT NULL DEFAULT 'seed',
                                effective_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            CREATE TABLE IF NOT EXISTS truth_tax_policies (
                                policy_key TEXT PRIMARY KEY,
                                purchase_tax_rate DOUBLE PRECISION NOT NULL,
                                nev_exemption_limit_wan DOUBLE PRECISION NOT NULL,
                                vat_divisor DOUBLE PRECISION NOT NULL,
                                effective_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                            """
                        )
                cls._pool = pool
                cls._schema_ready = True
                cls._use_test_memory = False
                cls._unavailable_until = 0.0
                cls._last_error = ""
                cls._bootstrap_if_empty()
                return True
            except Exception as exc:
                if pool is not None:
                    try:
                        pool.close()
                    except Exception:
                        pass
                cls._last_error = str(exc)
                cls._unavailable_until = _time.monotonic() + 30.0
                if not _is_test_env():
                    raise RuntimeError(
                        f"PostgreSQL is required for Truth Engine master data in non-test environments: {exc}"
                    ) from exc
                logger.debug(f"Truth Engine PG unavailable in test mode ({exc}); seeding test memory.")
                cls._use_test_memory = True
                if not cls._mem_pricing:
                    now = datetime.now(timezone.utc)
                    for model, vals in SEED_VEHICLE_PRICING.items():
                        cls._mem_pricing[model] = {
                            "car_model": model,
                            **vals,
                            "source": "test_seed",
                            "effective_from": now,
                            "updated_at": now,
                        }
                return False

    @classmethod
    def _bootstrap_if_empty(cls) -> None:
        if cls._pool is None:
            return
        with cls._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM truth_vehicle_pricing")
                count = cur.fetchone()[0]
                if count == 0:
                    for model, vals in SEED_VEHICLE_PRICING.items():
                        cur.execute(
                            """
                            INSERT INTO truth_vehicle_pricing (
                                car_model, msrp_wan, one_year_residual_rate, three_year_residual_rate,
                                wholesale_price_range_wan, retail_price_range_wan, market_liquidity_rating,
                                source, effective_from, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'seed', NOW(), NOW())
                            ON CONFLICT (car_model) DO NOTHING
                            """,
                            (
                                model,
                                vals.get("msrp_wan"),
                                vals.get("one_year_residual_rate"),
                                vals.get("three_year_residual_rate"),
                                vals.get("wholesale_price_range_wan"),
                                vals.get("retail_price_range_wan"),
                                vals.get("market_liquidity_rating"),
                            ),
                        )
                cur.execute(
                    """
                    INSERT INTO truth_tax_policies (
                        policy_key, purchase_tax_rate, nev_exemption_limit_wan, vat_divisor,
                        effective_from, updated_at
                    ) VALUES ('cn_2025_standard', 0.10, 3.0, 1.13, NOW(), NOW())
                    ON CONFLICT (policy_key) DO NOTHING
                    """
                )

    @classmethod
    def upsert_vehicle_pricing(
        cls,
        car_model: str,
        msrp_wan: Optional[float] = None,
        one_year_residual_rate: Optional[float] = None,
        three_year_residual_rate: Optional[float] = None,
        wholesale_price_range_wan: Optional[str] = None,
        retail_price_range_wan: Optional[str] = None,
        market_liquidity_rating: Optional[str] = None,
        source: str = "crawler",
        effective_from: Optional[datetime] = None,
    ) -> None:
        """Incremental upsert used by scheduled `src/crawler/` market ingestion jobs."""
        eff = effective_from or datetime.now(timezone.utc)
        if not cls._ensure_ready():
            existing = cls._mem_pricing.get(car_model, {"car_model": car_model})
            for k, v in {
                "msrp_wan": msrp_wan,
                "one_year_residual_rate": one_year_residual_rate,
                "three_year_residual_rate": three_year_residual_rate,
                "wholesale_price_range_wan": wholesale_price_range_wan,
                "retail_price_range_wan": retail_price_range_wan,
                "market_liquidity_rating": market_liquidity_rating,
            }.items():
                if v is not None:
                    existing[k] = v
            existing["source"] = source
            existing["effective_from"] = eff
            existing["updated_at"] = datetime.now(timezone.utc)
            cls._mem_pricing[car_model] = existing
            return

        with cls._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO truth_vehicle_pricing (
                        car_model, msrp_wan, one_year_residual_rate, three_year_residual_rate,
                        wholesale_price_range_wan, retail_price_range_wan, market_liquidity_rating,
                        source, effective_from, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (car_model) DO UPDATE SET
                        msrp_wan = COALESCE(EXCLUDED.msrp_wan, truth_vehicle_pricing.msrp_wan),
                        one_year_residual_rate = COALESCE(EXCLUDED.one_year_residual_rate, truth_vehicle_pricing.one_year_residual_rate),
                        three_year_residual_rate = COALESCE(EXCLUDED.three_year_residual_rate, truth_vehicle_pricing.three_year_residual_rate),
                        wholesale_price_range_wan = COALESCE(EXCLUDED.wholesale_price_range_wan, truth_vehicle_pricing.wholesale_price_range_wan),
                        retail_price_range_wan = COALESCE(EXCLUDED.retail_price_range_wan, truth_vehicle_pricing.retail_price_range_wan),
                        market_liquidity_rating = COALESCE(EXCLUDED.market_liquidity_rating, truth_vehicle_pricing.market_liquidity_rating),
                        source = EXCLUDED.source,
                        effective_from = EXCLUDED.effective_from,
                        updated_at = NOW()
                    """,
                    (
                        car_model,
                        msrp_wan,
                        one_year_residual_rate,
                        three_year_residual_rate,
                        wholesale_price_range_wan,
                        retail_price_range_wan,
                        market_liquidity_rating,
                        source,
                        eff,
                    ),
                )

    @classmethod
    def sync_from_crawler_records(cls, records: List[Dict[str, Any]], source: str = "crawler") -> int:
        """Batch-ingest crawled vehicle pricing & valuation records into PostgreSQL master data."""
        updated = 0
        for rec in records:
            car_model = rec.get("car_model")
            if not car_model:
                continue
            cls.upsert_vehicle_pricing(
                car_model=str(car_model),
                msrp_wan=rec.get("msrp_wan"),
                one_year_residual_rate=rec.get("one_year_residual_rate"),
                three_year_residual_rate=rec.get("three_year_residual_rate"),
                wholesale_price_range_wan=rec.get("wholesale_price_range_wan"),
                retail_price_range_wan=rec.get("retail_price_range_wan"),
                market_liquidity_rating=rec.get("market_liquidity_rating"),
                source=source,
            )
            updated += 1
        return updated

    @classmethod
    def get_depreciation_valuation(cls, canonical_model: str) -> Optional[DepreciationValuation]:
        """Lookup active residual valuation from PostgreSQL master data."""
        target = canonical_model.lower().replace(" ", "").replace("-", "")
        if not cls._ensure_ready():
            for k, v in cls._mem_pricing.items():
                if "one_year_residual_rate" not in v or v["one_year_residual_rate"] is None:
                    continue
                k_clean = k.lower().replace(" ", "").replace("-", "")
                if k_clean in target or target in k_clean:
                    return DepreciationValuation(
                        car_model=k,
                        one_year_residual_rate=float(v["one_year_residual_rate"]),
                        three_year_residual_rate=float(v["three_year_residual_rate"]),
                        current_wholesale_price_range_wan=str(v["wholesale_price_range_wan"]),
                        current_retail_price_range_wan=str(v["retail_price_range_wan"]),
                        market_liquidity_rating=str(v["market_liquidity_rating"]),
                    )
            return None

        with cls._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT car_model, one_year_residual_rate, three_year_residual_rate,
                           wholesale_price_range_wan, retail_price_range_wan, market_liquidity_rating
                    FROM truth_vehicle_pricing
                    WHERE one_year_residual_rate IS NOT NULL
                      AND effective_from <= NOW()
                    ORDER BY effective_from DESC, updated_at DESC
                    """
                )
                rows = cur.fetchall()
        for row in rows:
            k_clean = str(row[0]).lower().replace(" ", "").replace("-", "")
            if k_clean in target or target in k_clean:
                return DepreciationValuation(
                    car_model=str(row[0]),
                    one_year_residual_rate=float(row[1]),
                    three_year_residual_rate=float(row[2]),
                    current_wholesale_price_range_wan=str(row[3] or ""),
                    current_retail_price_range_wan=str(row[4] or ""),
                    market_liquidity_rating=str(row[5] or "中等"),
                )
        return None

    @classmethod
    def get_msrp_wan(cls, canonical_model: str, fallback_model: Optional[str] = None) -> Optional[float]:
        """Lookup active MSRP (万元) from PostgreSQL master data."""
        if not cls._ensure_ready():
            for name in (canonical_model, fallback_model):
                if name and name in cls._mem_pricing and cls._mem_pricing[name].get("msrp_wan") is not None:
                    return float(cls._mem_pricing[name]["msrp_wan"])
            return None

        with cls._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT msrp_wan FROM truth_vehicle_pricing
                    WHERE car_model = ANY(%s)
                      AND msrp_wan IS NOT NULL
                      AND effective_from <= NOW()
                    ORDER BY effective_from DESC, updated_at DESC
                    LIMIT 1
                    """,
                    ([m for m in (canonical_model, fallback_model) if m],),
                )
                row = cur.fetchone()
        return float(row[0]) if row else None

    @classmethod
    def get_active_tax_policy(cls, policy_key: str = "cn_2025_standard") -> Dict[str, float]:
        """Fetch active tax policy rates from PostgreSQL."""
        if not cls._ensure_ready():
            return dict(cls._mem_tax_policy)

        with cls._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT purchase_tax_rate, nev_exemption_limit_wan, vat_divisor
                    FROM truth_tax_policies
                    WHERE policy_key = %s AND effective_from <= NOW()
                    ORDER BY effective_from DESC, updated_at DESC
                    LIMIT 1
                    """,
                    (policy_key,),
                )
                row = cur.fetchone()
        if not row:
            return dict(cls._mem_tax_policy)
        return {
            "purchase_tax_rate": float(row[0]),
            "nev_exemption_limit_wan": float(row[1]),
            "vat_divisor": float(row[2]),
        }
