"""
ChromaDB向量存储

基于ChromaDB的向量数据库实现，提供高效的向量存储和检索功能。
"""

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from src.models.vehicle import Vehicle
from src.utils.config import config
from src.utils.logger import get_logger, log_performance


class ChromaVectorStore:
    """ChromaDB向量存储"""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        distance_metric: str = "cosine",
    ):
        """
        初始化向量存储

        Args:
            persist_directory: 持久化目录
            collection_name: 集合名称
            distance_metric: 距离度量方式 (cosine, euclidean, manhattan)
        """
        self.persist_directory = Path(persist_directory or config.chroma_persist_dir)
        self.collection_name = collection_name or config.chroma_collection_name
        self.distance_metric = distance_metric

        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        # 确保目录存在
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # 集合对象
        self.collection = None

        # 统计信息
        self.stats = {
            "total_documents": 0,
            "total_embeddings": 0,
            "add_time": 0.0,
            "query_time": 0.0,
            "query_count": 0,
        }

        self._initialize_collection()

    def _initialize_collection(self) -> None:
        """初始化或获取集合"""
        try:
            # 尝试获取现有集合
            self.collection = self.client.get_collection(name=self.collection_name)
            self.logger.info(f"已加载现有集合: {self.collection_name}")

            # 更新统计信息
            self.stats["total_documents"] = self.collection.count()

        except Exception:
            # 创建新集合
            self.collection = self.client.create_collection(
                name=self.collection_name, metadata={"distance_metric": self.distance_metric}
            )
            self.logger.info(f"已创建新集合: {self.collection_name}")

    @log_performance
    def add_vehicles(
        self, vehicles: List[Vehicle], embeddings: List[List[float]], batch_size: int = 100
    ) -> None:
        """
        添加车辆数据到向量存储

        Args:
            vehicles: 车辆数据列表
            embeddings: 对应的嵌入向量列表
            batch_size: 批处理大小
        """
        if len(vehicles) != len(embeddings):
            raise ValueError("车辆数据和嵌入向量数量不匹配")

        start_time = time.time()

        # 分批处理
        for i in range(0, len(vehicles), batch_size):
            batch_vehicles = vehicles[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            self._add_batch(batch_vehicles, batch_embeddings)

        add_time = time.time() - start_time
        self.stats["add_time"] += add_time
        self.stats["total_documents"] = self.collection.count()

        self.logger.info(f"已添加 {len(vehicles)} 个车辆数据，耗时 {add_time:.2f}秒")

    def _add_batch(self, vehicles: List[Vehicle], embeddings: List[List[float]]) -> None:
        """添加一批数据"""
        ids = []
        documents = []
        metadatas = []

        for vehicle in vehicles:
            # 生成唯一ID
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)

            # 文档内容（用于检索）
            documents.append(vehicle.get_search_text())

            # 元数据
            metadata = {
                "car_model": vehicle.car_model,
                "brand": vehicle.precise_labels.brand or "",
                "category": vehicle.precise_labels.vehicle_category_bottom or "",
                "price": vehicle.precise_labels.prize or "",
                "powertrain_type": vehicle.precise_labels.powertrain_type or "",
                "size": vehicle.ambiguous_labels.size or "",
                "family_friendliness": vehicle.ambiguous_labels.family_friendliness or "",
                "comfort_level": vehicle.ambiguous_labels.comfort_level or "",
            }

            # 添加价格区间信息
            price_range = vehicle.get_price_range()
            if price_range:
                metadata["price_min"] = price_range[0]
                metadata["price_max"] = price_range[1]

            metadatas.append(metadata)

        # 添加到ChromaDB
        self.collection.add(
            ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
        )

    @log_performance
    def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        查询向量存储

        Args:
            query_embeddings: 查询嵌入向量列表
            n_results: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档过滤条件
            include: 包含的字段

        Returns:
            查询结果
        """
        start_time = time.time()

        if include is None:
            include = ["metadatas", "documents", "distances", "embeddings"]

        try:
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include,
            )

            query_time = time.time() - start_time
            self.stats["query_time"] += query_time
            self.stats["query_count"] += 1

            return results

        except Exception as e:
            self.logger.error(f"查询失败: {e}")
            raise

    def query_by_metadata(self, where: Dict[str, Any], n_results: int = 100) -> Dict[str, Any]:
        """
        基于元数据查询

        Args:
            where: 过滤条件
            n_results: 返回结果数量

        Returns:
            查询结果
        """
        try:
            results = self.collection.get(
                where=where, limit=n_results, include=["metadatas", "documents"]
            )
            return results
        except Exception as e:
            self.logger.error(f"元数据查询失败: {e}")
            raise

    def get_vehicle_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取车辆数据

        Args:
            doc_id: 文档ID

        Returns:
            车辆数据或None
        """
        try:
            results = self.collection.get(ids=[doc_id], include=["metadatas", "documents"])

            if results["ids"] and results["ids"][0]:
                return {
                    "id": results["ids"][0],
                    "metadata": results["metadatas"][0],
                    "document": results["documents"][0],
                }

            return None

        except Exception as e:
            self.logger.error(f"根据ID查询失败: {e}")
            return None

    def update_vehicle(self, doc_id: str, vehicle: Vehicle, embedding: List[float]) -> None:
        """
        更新车辆数据

        Args:
            doc_id: 文档ID
            vehicle: 新的车辆数据
            embedding: 新的嵌入向量
        """
        try:
            document = vehicle.get_search_text()
            metadata = {
                "car_model": vehicle.car_model,
                "brand": vehicle.precise_labels.brand or "",
                "category": vehicle.precise_labels.vehicle_category_bottom or "",
                "price": vehicle.precise_labels.prize or "",
                "powertrain_type": vehicle.precise_labels.powertrain_type or "",
                "size": vehicle.ambiguous_labels.size or "",
                "family_friendliness": vehicle.ambiguous_labels.family_friendliness or "",
                "comfort_level": vehicle.ambiguous_labels.comfort_level or "",
            }

            # 添加价格区间信息
            price_range = vehicle.get_price_range()
            if price_range:
                metadata["price_min"] = price_range[0]
                metadata["price_max"] = price_range[1]

            self.collection.update(
                ids=[doc_id], documents=[document], metadatas=[metadata], embeddings=[embedding]
            )

            self.logger.info(f"已更新车辆数据: {doc_id}")

        except Exception as e:
            self.logger.error(f"更新车辆数据失败: {e}")
            raise

    def delete_vehicle(self, doc_id: str) -> None:
        """
        删除车辆数据

        Args:
            doc_id: 文档ID
        """
        try:
            self.collection.delete(ids=[doc_id])
            self.stats["total_documents"] = self.collection.count()
            self.logger.info(f"已删除车辆数据: {doc_id}")
        except Exception as e:
            self.logger.error(f"删除车辆数据失败: {e}")
            raise

    def clear_collection(self) -> None:
        """清空集合"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self._initialize_collection()
            self.stats["total_documents"] = 0
            self.logger.info(f"已清空集合: {self.collection_name}")
        except Exception as e:
            self.logger.error(f"清空集合失败: {e}")
            raise

    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            count = self.collection.count()

            return {
                "name": self.collection_name,
                "count": count,
                "distance_metric": self.distance_metric,
                "persist_directory": str(self.persist_directory),
                "metadata": self.collection.metadata,
            }
        except Exception as e:
            self.logger.error(f"获取集合信息失败: {e}")
            return {}

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "avg_query_time": self.stats["query_time"] / max(self.stats["query_count"], 1),
            "collection_info": self.get_collection_info(),
        }

    def backup_collection(self, backup_path: Optional[Path] = None) -> None:
        """
        备份集合

        Args:
            backup_path: 备份路径
        """
        if backup_path is None:
            backup_path = (
                self.persist_directory.parent / f"backup_{self.collection_name}_{int(time.time())}"
            )

        try:
            # 获取所有数据
            all_data = self.collection.get(include=["metadatas", "documents", "embeddings"])

            # 创建备份集合
            backup_client = chromadb.PersistentClient(path=str(backup_path))
            backup_collection = backup_client.create_collection(
                name=self.collection_name, metadata=self.collection.metadata
            )

            # 添加数据到备份集合
            if all_data["ids"]:
                backup_collection.add(
                    ids=all_data["ids"],
                    documents=all_data["documents"],
                    metadatas=all_data["metadatas"],
                    embeddings=all_data["embeddings"],
                )

            self.logger.info(f"集合备份完成: {backup_path}")

        except Exception as e:
            self.logger.error(f"备份集合失败: {e}")
            raise

    def __del__(self):
        """析构函数"""
        try:
            # 确保连接关闭
            if hasattr(self.client, "close"):
                self.client.close()
        except Exception:
            pass
