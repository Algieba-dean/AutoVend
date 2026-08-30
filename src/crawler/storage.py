"""
Storage Engine for crawled vehicle data.
Manages raw multi-tiered JSON files and SQLite catalog indexing.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.crawler.schemas import RawSerialSpecSheet, RawVehicleTrim
from src.utils.logger import get_logger

logger = get_logger(__name__)


BRAND_SLUG_MAP = {
    "比亚迪": "byd",
    "特斯拉": "tesla",
    "理想": "li_auto",
    "蔚来": "nio",
    "小鹏": "xpeng",
    "极氪": "zeekr",
    "小米": "xiaomi",
    "问界": "aito",
    "零跑": "leapmotor",
    "腾势": "tengshi",
    "仰望": "yangwang",
    "方程豹": "fangchengbao",
    "吉利": "geely",
    "极狐": "arcfox",
    "智己": "im_motors",
    "阿维塔": "avatar",
    "大众": "volkswagen",
    "奥迪": "audi",
    "宝马": "bmw",
    "奔驰": "mercedes_benz",
    "丰田": "toyota",
    "本田": "honda",
}


class RawDataStorage:
    """Handles raw JSON file archiving and SQLite indexing for crawled vehicle datasets."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path("/home/algieba/projects/hackthon/AutoVend/data/crawled/yiche")
        self.raw_dir = self.base_dir / "raw"
        self.db_path = self.base_dir / "yiche_catalog.db"
        self._init_storage()

    def _init_storage(self) -> None:
        """Create necessary directories and SQLite tables."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_trims (
                    car_id TEXT PRIMARY KEY,
                    brand TEXT NOT NULL,
                    serial TEXT NOT NULL,
                    serial_slug TEXT NOT NULL,
                    trim_name TEXT NOT NULL,
                    year TEXT,
                    price_guide TEXT,
                    price_reference TEXT,
                    category_bottom TEXT,
                    powertrain_type TEXT,
                    crawled_at REAL,
                    raw_specs_json TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_brand_serial ON vehicle_trims (brand, serial)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_powertrain ON vehicle_trims (powertrain_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON vehicle_trims (category_bottom)")
            conn.commit()

    def save_serial_specs(self, sheet: RawSerialSpecSheet) -> Path:
        """
        Save complete series specification sheet to raw JSON and index into SQLite.
        """
        # 1. Save Series-level JSON under clean English brand slug
        brand_slug = BRAND_SLUG_MAP.get(sheet.brand, sheet.brand.lower().replace(" ", "_"))
        brand_raw_dir = self.raw_dir / brand_slug
        brand_raw_dir.mkdir(parents=True, exist_ok=True)

        serial_file = brand_raw_dir / f"{sheet.serial_slug}_full_specs.json"
        serial_file.write_text(
            json.dumps(sheet.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 2. Index Trims into SQLite
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for trim in sheet.trims:
                cid = trim.car_id or f"{sheet.serial_slug}_{abs(hash(trim.trim_name))}"
                cursor.execute("""
                    INSERT OR REPLACE INTO vehicle_trims (
                        car_id, brand, serial, serial_slug, trim_name,
                        year, price_guide, price_reference,
                        category_bottom, powertrain_type, crawled_at, raw_specs_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cid,
                    trim.brand,
                    trim.serial,
                    trim.serial_slug,
                    trim.trim_name,
                    trim.year or "",
                    trim.price_guide or "",
                    trim.price_reference or "",
                    trim.category_bottom or "",
                    trim.powertrain_type or "",
                    trim.crawled_at,
                    json.dumps(trim.specs, ensure_ascii=False),
                ))
            conn.commit()

        logger.info(f"Saved {len(sheet.trims)} trims for series [{sheet.serial}] to {serial_file}")
        return serial_file

    def get_brand_slug(self, brand_name: str) -> str:
        """Get canonical English slug for a brand."""
        return BRAND_SLUG_MAP.get(brand_name, brand_name.lower().replace(" ", "_"))

    def get_all_trims(self, brand: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all indexed trims from SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if brand:
                cursor.execute("SELECT * FROM vehicle_trims WHERE brand = ?", (brand,))
            else:
                cursor.execute("SELECT * FROM vehicle_trims")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_brand_stats(self) -> Dict[str, Dict[str, int]]:
        """Get series count and trim count per brand."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT brand, COUNT(DISTINCT serial) as s_cnt, COUNT(*) as t_cnt
                FROM vehicle_trims
                GROUP BY brand
                ORDER BY t_cnt DESC
            """)
            rows = cursor.fetchall()
            return {r[0]: {"series_count": r[1], "trims_count": r[2]} for r in rows}

    def rebuild_index_from_raw(self) -> int:
        """
        Self-healing: Rebuild entire SQLite index from raw JSON data lake.
        Guarantees 100% sync between raw JSON files and SQLite catalog.
        """
        rebuilt_count = 0
        json_files = list(self.raw_dir.glob("*/*.json"))
        logger.info(f"Found {len(json_files)} raw spec sheet JSON files. Rebuilding SQLite index...")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for jf in json_files:
                try:
                    data = json.loads(jf.read_text(encoding="utf-8"))
                    brand = data.get("brand", jf.parent.name)
                    serial = data.get("serial", jf.stem.replace("_full_specs", ""))
                    serial_slug = data.get("serial_slug", jf.stem.replace("_full_specs", ""))

                    for trim in data.get("trims", []):
                        cid = trim.get("car_id") or f"{serial_slug}_{abs(hash(trim.get('trim_name', '')))}"
                        cursor.execute("""
                            INSERT OR REPLACE INTO vehicle_trims (
                                car_id, brand, serial, serial_slug, trim_name,
                                year, price_guide, price_reference,
                                category_bottom, powertrain_type, crawled_at, raw_specs_json
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            cid,
                            trim.get("brand", brand),
                            trim.get("serial", serial),
                            trim.get("serial_slug", serial_slug),
                            trim.get("trim_name", ""),
                            trim.get("year", ""),
                            trim.get("price_guide", ""),
                            trim.get("price_reference", ""),
                            trim.get("category_bottom", ""),
                            trim.get("powertrain_type", ""),
                            trim.get("crawled_at", 0.0),
                            json.dumps(trim.get("specs", {}), ensure_ascii=False),
                        ))
                        rebuilt_count += 1
                except Exception as e:
                    logger.error(f"Error reading {jf}: {e}")
            conn.commit()

        logger.info(f"Successfully rebuilt SQLite index: {rebuilt_count} trims indexed across {len(json_files)} series.")
        return rebuilt_count
