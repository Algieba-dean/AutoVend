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
from src.utils.logger import get_logger


# TOML 字段名 → SQLite 规范字段名的映射（处理拼写不一致）
TOML_FIELD_NORMALIZE: Dict[str, str] = {
    "passenger_sapce_volume": "passenger_space_volume",
    "voice_interfaction": "voice_interaction",
    "passibility": "passability",
    "clod_resistance": "cold_resistance",
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
        self.logger = get_logger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "vehicles.db")
        self.db_path = db_path

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
            self._conn = sqlite3.connect(self.db_path)
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
            f"CREATE TABLE IF NOT EXISTS vehicles ("
            f'"car_model" TEXT PRIMARY KEY, {col_defs})'
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
                    f'CREATE INDEX IF NOT EXISTS "{idx_name}" '
                    f'ON vehicles ("{field}")'
                )

        self.conn.commit()

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
            data_dir = str(
                Path(__file__).parent.parent.parent / "DataInUse" / "VehicleData"
            )

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
            f"INSERT OR REPLACE INTO vehicles ({col_names}) "
            f"VALUES ({placeholders})",
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
            f'SELECT DISTINCT "{column}" FROM vehicles '
            f'WHERE "{column}" != "" ORDER BY "{column}"'
        )
        return [r[0] for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

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
