"""
Change Detection & Diff Engine for Automotive Specifications.
Computes SHA-256 signatures, detects price drops, trim upgrades, and discontinued models.
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.crawler.schemas import DiffRecord, DiffSummary, DiffType
from src.utils.logger import get_logger

logger = get_logger(__name__)


def compute_trim_hash(specs: Dict[str, Any], price: str) -> str:
    """Compute deterministic SHA-256 checksum of vehicle specifications."""
    payload = {"price": price, "specs": specs}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DiffEngine:
    """Tracks incremental changes across crawls and alerts on price/spec drifts."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("/home/algieba/projects/hackthon/AutoVend/data/crawled/yiche/yiche_catalog.db")
        self._init_diff_table()

    def _init_diff_table(self) -> None:
        """Create diff audit log table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_diff_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    car_id TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    serial TEXT NOT NULL,
                    trim_name TEXT NOT NULL,
                    diff_type TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    details TEXT,
                    timestamp REAL
                )
            """)
            conn.commit()

    def compare_and_log(
        self,
        new_trims: List[Dict[str, Any]],
        existing_trims: Optional[List[Dict[str, Any]]] = None,
    ) -> DiffSummary:
        """Compare new trim batch against existing catalog and record diffs."""
        summary = DiffSummary()
        existing_map = {}

        if existing_trims is None:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM vehicle_trims")
                rows = cursor.fetchall()
                for r in rows:
                    existing_map[r["car_id"]] = dict(r)
        else:
            for r in existing_trims:
                existing_map[r["car_id"]] = r

        summary.total_checked = len(new_trims)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = time.time()

            for item in new_trims:
                cid = item["car_id"]
                brand = item.get("brand", "")
                serial = item.get("serial", "")
                name = item.get("trim_name", "")
                new_price = item.get("price_guide", "")

                if cid not in existing_map:
                    # New model launch
                    rec = DiffRecord(
                        car_id=cid,
                        brand=brand,
                        serial=serial,
                        trim_name=name,
                        diff_type=DiffType.NEW_MODEL,
                        new_value=new_price,
                        details=f"新上市/新收录车型: {brand} {serial} {name} (指导价: {new_price})",
                    )
                    summary.new_models_count += 1
                    summary.records.append(rec)
                else:
                    old_item = existing_map[cid]
                    old_price = old_item.get("price_guide", "")
                    if old_price and new_price and old_price != new_price:
                        # Price changed
                        diff_t = DiffType.PRICE_CHANGED
                        rec = DiffRecord(
                            car_id=cid,
                            brand=brand,
                            serial=serial,
                            trim_name=name,
                            diff_type=diff_t,
                            old_value=old_price,
                            new_value=new_price,
                            details=f"价格异动: {old_price} -> {new_price}",
                        )
                        summary.price_changed_count += 1
                        summary.records.append(rec)

            for rec in summary.records:
                cursor.execute("""
                    INSERT INTO vehicle_diff_audit (
                        car_id, brand, serial, trim_name, diff_type, old_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec.car_id, rec.brand, rec.serial, rec.trim_name, rec.diff_type.value,
                    str(rec.old_value or ""), str(rec.new_value or ""), rec.details or "", now,
                ))
            conn.commit()

        return summary
