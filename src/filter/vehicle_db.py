"""
SQLite 车辆数据库

将 TOML 车辆标签数据导入 SQLite，支持高效的结构化过滤查询。
所有值统一小写存储，字段名使用 LabelsTree.json 的规范名称。
"""

import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.filter.label_registry import LabelRegistry
from src.utils.config import config
from src.utils.logger import get_logger

# TOML 字段名 → SQLite 规范字段名的映射（处理拼写不一致）
TOML_FIELD_NORMALIZE: Dict[str, str] = {
    "passenger_sapce_volume": "passenger_space_volume",
    "voice_interfaction": "voice_interaction",
    "passibility": "passability",
    "clod_resistance": "cold_resistance",
    "price": "prize",
}


class VehicleDB:
    """
    SQLite 车辆数据库

    从 TOML 文件批量导入车辆标签数据，提供结构化查询接口。
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        registry: Optional[LabelRegistry] = None,
    ):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        self.db_path = db_path or config.vehicle_db_path

        # 确保目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.registry = registry or LabelRegistry()
        self.columns = self.registry.get_all_db_columns()

        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_table()

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # 表结构
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        """创建车辆表（如果不存在）"""
        col_defs = ", ".join(f'"{col}" TEXT' for col in self.columns)
        create_sql = (
            f'CREATE TABLE IF NOT EXISTS vehicles ("car_model" TEXT PRIMARY KEY, {col_defs})'
        )
        self.conn.execute(create_sql)

        # 创建高频查询字段索引
        index_fields = [
            "brand",
            "vehicle_category_bottom",
            "prize",
            "powertrain_type",
            "drive_type",
            "seat_layout",
        ]
        for field in index_fields:
            if field in self.columns:
                idx_name = f"idx_vehicles_{field}"
                self.conn.execute(
                    f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON vehicles ("{field}")'
                )

        try:
            # Checksum 持久化表（支持 Pod 重启恢复状态，避免全量重算）
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS checksum_store (
                    key TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )"""
            )

            # Transactional Outbox / DLQ 事件表（支持多引擎写入一致性与事务补偿）
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS outbox_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )"""
            )

            self.conn.commit()
        except sqlite3.OperationalError as e:
            if "readonly" in str(e).lower() or "read-only" in str(e).lower():
                self.logger.debug(f"Database opened in read-only environment: {e}")
            else:
                raise

    # ------------------------------------------------------------------
    # 数据导入
    # ------------------------------------------------------------------

    def import_from_toml_dir(
        self,
        data_dir: Optional[str] = None,
        clear_first: bool = True,
    ) -> Dict[str, int]:
        """
        从 TOML 文件目录批量导入车辆数据

        Args:
            data_dir: 车辆数据目录，默认 DataInUse/VehicleData
            clear_first: 导入前是否清空现有数据

        Returns:
            导入统计 {"total", "imported", "failed"}
        """
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent.parent / "DataInUse" / "VehicleData")

        start = time.time()
        stats = {"total": 0, "imported": 0, "failed": 0}

        if clear_first:
            self.conn.execute("DELETE FROM vehicles")

        toml_files = self._find_toml_files(data_dir)
        stats["total"] = len(toml_files)

        for file_path in toml_files:
            try:
                row = self._parse_toml(file_path)
                if row:
                    self._upsert_row(row)
                    stats["imported"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                self.logger.debug(f"导入失败 {file_path}: {e}")
                stats["failed"] += 1

        self.conn.commit()
        elapsed = time.time() - start
        self.logger.info(
            f"SQLite导入完成: {stats['imported']}/{stats['total']} 辆, "
            f"失败 {stats['failed']}, 耗时 {elapsed:.2f}s"
        )
        return stats

    def _find_toml_files(self, data_dir: str) -> List[str]:
        """递归查找所有车辆 TOML 文件"""
        result: List[str] = []
        for root, _, files in os.walk(data_dir):
            for fname in files:
                if fname.endswith(".toml") and fname != "CarLabels.toml":
                    result.append(os.path.join(root, fname))
        return result

    def _parse_toml(self, file_path: str) -> Optional[Dict[str, str]]:
        """解析单个 TOML 文件为扁平的 {column: value} 字典"""
        with open(file_path, "rb") as f:
            import tomllib

            data = tomllib.load(f)

        car_model = data.get("car_model", "")
        if not car_model:
            return None

        precise = data.get("PriciseLabels", {})
        ambiguous = data.get("AmbiguousLabels", {})

        row: Dict[str, str] = {"car_model": car_model}

        # 合并 precise + ambiguous，排除 _comments 字段
        raw_labels = {}
        for k, v in precise.items():
            if not k.endswith("_comments"):
                raw_labels[k] = v
        for k, v in ambiguous.items():
            if not k.endswith("_comments"):
                raw_labels[k] = v

        # 规范化字段名并写入 row
        for raw_key, value in raw_labels.items():
            # 统一字段名：小写 + 拼写修正
            norm_key = raw_key.lower()
            norm_key = TOML_FIELD_NORMALIZE.get(norm_key, norm_key)

            if norm_key in self.columns:
                raw_val = str(value).lower().strip()
                row[norm_key] = self._normalize_value(raw_val, norm_key)

        return row

    def _normalize_value(self, value: str, column: str) -> str:
        """将 TOML 原始值规范化为 registry 中的候选值格式"""
        label = self.registry.get_label(column)
        if label is None:
            return value

        # 精确匹配
        if value in label.value_index:
            return value

        # 模糊匹配：去空格 + 统一分隔符
        norm = self._fuzzy_key(value)
        for candidate in label.candidates:
            if self._fuzzy_key(candidate) == norm:
                return candidate

        return value

    @staticmethod
    def _fuzzy_key(s: str) -> str:
        """去空格、统一分隔符，用于模糊比较"""
        s = s.lower().strip()
        s = re.sub(r"\s*[~\-–]\s*", "~", s)
        s = re.sub(r"\s+", "", s)
        return s

    def _upsert_row(self, row: Dict[str, str]) -> None:
        """插入或替换一行数据"""
        all_cols = ["car_model"] + self.columns
        placeholders = ", ".join("?" for _ in all_cols)
        col_names = ", ".join(f'"{c}"' for c in all_cols)
        values = [row.get(c, "") for c in all_cols]

        self.conn.execute(
            f"INSERT OR REPLACE INTO vehicles ({col_names}) VALUES ({placeholders})",
            values,
        )

    # ------------------------------------------------------------------
    # 查询接口
    # ------------------------------------------------------------------

    def query(
        self,
        where_clauses: List[str],
        params: List[Any],
        limit: int = 200,
    ) -> List[Dict[str, str]]:
        """
        执行结构化查询

        Args:
            where_clauses: SQL WHERE 子句片段列表（用 AND 连接）
            params: 对应的参数列表
            limit: 最大返回数

        Returns:
            匹配的车辆行列表
        """
        sql = "SELECT * FROM vehicles"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += f" LIMIT {limit}"

        cursor = self.conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

    def get_all_car_models(self) -> List[str]:
        """获取所有 car_model"""
        cursor = self.conn.execute("SELECT car_model FROM vehicles ORDER BY car_model")
        return [r[0] for r in cursor.fetchall()]

    def count(self) -> int:
        """获取车辆总数"""
        cursor = self.conn.execute("SELECT COUNT(*) FROM vehicles")
        return cursor.fetchone()[0]

    def get_distinct_values(self, column: str) -> List[str]:
        """获取某列的所有不同值"""
        if column not in self.columns and column != "car_model":
            return []
        cursor = self.conn.execute(
            f'SELECT DISTINCT "{column}" FROM vehicles WHERE "{column}" != "" ORDER BY "{column}"'
        )
        return [r[0] for r in cursor.fetchall()]

    def get_by_model(self, car_model: str) -> Optional[Dict[str, Any]]:
        """获取指定 car_model 的记录字典"""
        cursor = self.conn.execute("SELECT * FROM vehicles WHERE car_model = ?", (car_model,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_vehicle(self, car_model: str) -> Optional[Any]:
        """获取指定 car_model 并重构为 Vehicle 对象"""
        row = self.get_by_model(car_model)
        if not row:
            return None
        from src.models.vehicle import AmbiguousLabels, KeyDetails, PreciseLabels, Vehicle

        precise = PreciseLabels(
            brand=row.get("brand"),
            prize=row.get("prize"),
            vehicle_category_bottom=row.get("vehicle_category_bottom"),
            powertrain_type=row.get("powertrain_type"),
            wheelbase=row.get("wheelbase"),
            chassis_height=row.get("chassis_height"),
            passenger_sapce_volume=row.get("passenger_space_volume") or row.get("passenger_sapce_volume"),
            trunk_volume=row.get("trunk_volume"),
        )
        ambiguous = AmbiguousLabels(
            size=row.get("size"),
            family_friendliness=row.get("family_friendliness"),
            comfort_level=row.get("comfort_level"),
            passibility=row.get("passability") or row.get("passibility"),
            power=row.get("power"),
            handling=row.get("handling"),
        )
        key_details = KeyDetails(key_details=row.get("key_details") or "")
        return Vehicle(
            car_model=row.get("car_model", car_model),
            PriciseLabels=precise,
            AmbiguousLabels=ambiguous,
            KeyDetails=key_details,
            raw_data=row,
        )

    def upsert_vehicle(self, v_data: Dict[str, Any]) -> None:
        """执行单条车辆记录的插入或更新 (INSERT OR REPLACE)"""
        car_model = v_data.get("car_model") or v_data.get("model")
        if not car_model:
            return

        row_data = {"car_model": str(car_model)}
        for col in self.columns:
            val = v_data.get(col)
            row_data[col] = str(val).lower() if val is not None else ""

        cols = list(row_data.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_names = ", ".join(f'"{c}"' for c in cols)
        sql = f"INSERT OR REPLACE INTO vehicles ({col_names}) VALUES ({placeholders})"
        self.conn.execute(sql, [row_data[c] for c in cols])
        self.conn.commit()

    def delete_vehicle(self, car_model: str) -> None:
        """删除指定 car_model 的记录"""
        self.conn.execute("DELETE FROM vehicles WHERE car_model = ?", (car_model,))
        self.conn.commit()

    def get_all_models(self) -> List[str]:
        """获取所有 car_model 列表"""
        return self.get_all_car_models()

    def summary(self) -> Dict[str, Any]:
        """数据库摘要"""
        total = self.count()
        brands = len(self.get_distinct_values("brand"))
        categories = len(self.get_distinct_values("vehicle_category_bottom"))
        return {
            "total_vehicles": total,
            "distinct_brands": brands,
            "distinct_categories": categories,
            "db_path": self.db_path,
        }

    # ------------------------------------------------------------------
    # Checksum 持久化接口
    # ------------------------------------------------------------------

    def get_checksum(self, key: str) -> Optional[str]:
        """获取指定 key 的持久化 Checksum"""
        try:
            cursor = self.conn.execute("SELECT checksum FROM checksum_store WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error:
            return None

    def set_checksum(self, key: str, checksum: str) -> None:
        """保存或更新 key 的 Checksum"""
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO checksum_store (key, checksum, updated_at) VALUES (?, ?, ?)",
                (key, checksum, time.time()),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.debug(f"Unable to write persistent checksum: {e}")

    def delete_checksum(self, key: str) -> None:
        """删除 key 的 Checksum"""
        try:
            self.conn.execute("DELETE FROM checksum_store WHERE key = ?", (key,))
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.debug(f"Unable to delete persistent checksum: {e}")

    def get_all_checksums(self) -> Dict[str, str]:
        """加载所有已持久化的 Checksum 字典"""
        try:
            cursor = self.conn.execute("SELECT key, checksum FROM checksum_store")
            return {row[0]: row[1] for row in cursor.fetchall()}
        except sqlite3.Error:
            return {}

    # ------------------------------------------------------------------
    # Transactional Outbox / DLQ 事件持久化
    # ------------------------------------------------------------------

    def record_outbox_event(
        self,
        event_id: str,
        event_type: str,
        payload_json: str,
        status: str = "PENDING",
        error_message: Optional[str] = None,
    ) -> None:
        """写入或更新 Outbox / DLQ 事件记录"""
        try:
            now = time.time()
            self.conn.execute(
                """INSERT OR REPLACE INTO outbox_events 
                   (id, event_type, payload, status, error_message, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event_id, event_type, payload_json, status, error_message or "", now, now),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.debug(f"Unable to record outbox event: {e}")

    def get_outbox_events(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取 Outbox / DLQ 事件列表"""
        try:
            if status:
                cursor = self.conn.execute(
                    """SELECT id, event_type, payload, status, error_message, created_at, updated_at
                       FROM outbox_events WHERE status = ? ORDER BY created_at ASC""",
                    (status,),
                )
            else:
                cursor = self.conn.execute(
                    """SELECT id, event_type, payload, status, error_message, created_at, updated_at
                       FROM outbox_events ORDER BY created_at ASC"""
                )
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "event_type": r[1],
                    "payload": r[2],
                    "status": r[3],
                    "error_message": r[4],
                    "created_at": r[5],
                    "updated_at": r[6],
                }
                for r in rows
            ]
        except sqlite3.Error:
            return []
