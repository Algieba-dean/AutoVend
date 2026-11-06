"""
ChromaDB向量存储

基于ChromaDB的向量数据库实现，提供高效的向量存储和检索功能。
"""

import hashlib
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from src.models.vehicle import Vehicle
from src.utils.config import config
from src.utils.logger import get_logger, log_performance


def extract_vehicle_trim(vehicle: Vehicle) -> str:
    """Extract vehicle trim / version / configuration to guarantee unique deterministic IDs."""
    if hasattr(vehicle, "trim") and vehicle.trim:
        return str(vehicle.trim).strip()
    if hasattr(vehicle, "raw_data") and isinstance(vehicle.raw_data, dict):
        for k in ["trim", "trim_name", "version", "config_name", "model_version"]:
            val = vehicle.raw_data.get(k)
            if val:
                return str(val).strip()
    if hasattr(vehicle, "precise_labels") and vehicle.precise_labels:
        trim_lbl = getattr(vehicle.precise_labels, "trim", None) or getattr(vehicle.precise_labels, "version", None)
        if trim_lbl:
            return str(trim_lbl).strip()
        if hasattr(vehicle.precise_labels, "model_extra") and isinstance(vehicle.precise_labels.model_extra, dict):
            for k in ["trim", "trim_name", "version", "config_name"]:
                val = vehicle.precise_labels.model_extra.get(k)
                if val:
                    return str(val).strip()
    if hasattr(vehicle, "model_extra") and isinstance(vehicle.model_extra, dict):
        for k in ["trim", "trim_name", "version", "config_name"]:
            val = vehicle.model_extra.get(k)
            if val:
                return str(val).strip()
    return ""


def generate_vehicle_doc_id(car_model: str, trim: str = "") -> str:
    """Generate deterministic, idempotent document ID for vector stores."""
    raw_key = f"{car_model.strip().lower()}::{trim.strip().lower()}"
    digest = hashlib.md5(raw_key.encode("utf-8")).hexdigest()[:16]
    return f"veh_{digest}"


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
        try:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # 初始化ChromaDB客户端（沙箱或只读环境下支持自动镜像至可写临时目录或降级至 EphemeralClient）
        client = None
        try:
            client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )
            # 探测持久化连接健康状态，避免延迟只读报错
            client.heartbeat()
        except Exception as e:
            self.logger.warning(
                f"Persistent ChromaDB 初始路径不可写或失败 ({e})，尝试镜像或内存降级"
            )
            # 若源目录存在已有持久化数据，则复制到可写 /tmp 目录以保留全部向量索引
            if self.persist_directory.exists() and any(self.persist_directory.iterdir()):
                try:
                    import shutil
                    import tempfile

                    mirror_dir = (
                        Path(tempfile.gettempdir())
                        / f"chroma_mirror_{self.persist_directory.name}"
                    )
                    if not mirror_dir.exists():
                        shutil.copytree(
                            str(self.persist_directory), str(mirror_dir), dirs_exist_ok=True
                        )
                    self.persist_directory = mirror_dir
                    client = chromadb.PersistentClient(
                        path=str(mirror_dir),
                        settings=Settings(anonymized_telemetry=False, allow_reset=True),
                    )
                    self.logger.info(f"已成功将只读 ChromaDB 镜像至可写临时目录: {mirror_dir}")
                except Exception as mirror_err:
                    self.logger.warning(
                        f"镜像只读 ChromaDB 失败 ({mirror_err})，降级使用内存 EphemeralClient"
                    )
                    client = chromadb.EphemeralClient(
                        settings=Settings(anonymized_telemetry=False, allow_reset=True)
                    )
            else:
                client = chromadb.EphemeralClient(
                    settings=Settings(anonymized_telemetry=False, allow_reset=True)
                )

        self.client = client

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
            try:
                self.collection = self.client.create_collection(
                    name=self.collection_name, metadata={"distance_metric": self.distance_metric}
                )
                self.logger.info(f"已创建新集合: {self.collection_name}")
            except Exception as create_err:
                self.logger.warning(
                    f"创建集合失败 ({create_err})，降级使用内存 EphemeralClient"
                )
                self.client = chromadb.EphemeralClient(
                    settings=Settings(anonymized_telemetry=False, allow_reset=True)
                )
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name, metadata={"distance_metric": self.distance_metric}
                )

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
            # 基于车型名称与款型生成确定性ID，确保幂等更新与多款型配置隔离
            trim = extract_vehicle_trim(vehicle)
            doc_id = generate_vehicle_doc_id(vehicle.car_model or str(uuid.uuid4()), trim=trim)
            ids.append(doc_id)

            # 文档内容（用于检索）
            documents.append(vehicle.get_search_text())

            # 元数据
            metadata = {
                "car_model": vehicle.car_model,
                "trim": trim,
                "brand": vehicle.precise_labels.brand or "",
                "category": vehicle.precise_labels.vehicle_category_bottom or "",
                "price": vehicle.precise_labels.price or "",
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

        # 幂等写入ChromaDB (优先使用upsert防止重复插入与幽灵数据膨胀)
        if hasattr(self.collection, "upsert"):
            self.collection.upsert(
                ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
            )
        else:
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
            trim = extract_vehicle_trim(vehicle)
            metadata = {
                "car_model": vehicle.car_model,
                "trim": trim,
                "brand": vehicle.precise_labels.brand or "",
                "category": vehicle.precise_labels.vehicle_category_bottom or "",
                "price": vehicle.precise_labels.price or "",
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

    def upsert_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """
        幂等更新或插入单篇文档/车辆到向量存储中（对齐 Ingestion Pipeline 契约）。

        Args:
            doc_id: 文档唯一标识 (如 vehicle car_model 或 chunk_id)
            text: 文档正文内容
            metadata: 文档元数据字典
            embedding: 可选的嵌入向量。若未提供，优先由绑定模型生成，或使用匹配维度的安全向量
        """
        try:
            if embedding is None and hasattr(self, "embedding_model") and self.embedding_model:
                try:
                    if not getattr(self.embedding_model, "is_degraded", False):
                        embedding = self.embedding_model.get_text_embedding(text)
                except Exception as emb_err:
                    self.logger.warning(f"生成嵌入向量失败 ({doc_id}): {emb_err}")

            clean_metadata: Dict[str, Any] = {}
            if metadata:
                for k, v in metadata.items():
                    if isinstance(v, (str, int, float, bool)):
                        clean_metadata[k] = v
                    elif v is not None:
                        clean_metadata[k] = str(v)
            if not clean_metadata:
                clean_metadata = {"doc_id": doc_id}

            kwargs: Dict[str, Any] = {
                "ids": [doc_id],
                "documents": [text or " "],
                "metadatas": [clean_metadata],
            }
            if embedding is not None:
                kwargs["embeddings"] = [embedding]
            else:
                dim = 1024
                if self.collection:
                    try:
                        peek = self.collection.peek(limit=1)
                        if peek and peek.get("embeddings") is not None and len(peek["embeddings"]) > 0:
                            dim = len(peek["embeddings"][0])
                    except Exception:
                        pass
                kwargs["embeddings"] = [[0.0] * dim]

            if hasattr(self.collection, "upsert"):
                self.collection.upsert(**kwargs)
            else:
                self.collection.add(**kwargs)

            self.stats["total_documents"] = self.collection.count()
            self.logger.info(f"已成功 upsert 向量文档: {doc_id}")
        except Exception as e:
            self.logger.error(f"upsert 向量文档失败 ({doc_id}): {e}")
            raise

    def delete_document(self, doc_id: str) -> None:
        """
        根据 ID 删除文档（对齐 Ingestion Pipeline 契约）。

        Args:
            doc_id: 文档ID
        """
        try:
            self.collection.delete(ids=[doc_id])
            self.stats["total_documents"] = self.collection.count()
            self.logger.info(f"已删除向量文档: {doc_id}")
        except Exception as e:
            self.logger.error(f"删除向量文档失败 ({doc_id}): {e}")
            raise

    def delete_vehicle(self, doc_id: str) -> None:
        """
        删除车辆数据

        Args:
            doc_id: 文档ID
        """
        self.delete_document(doc_id)

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

    # 这里刻意没有 __del__。
    #
    # 曾经有一个 __del__ 调用 self.client.close()，但 ChromaDB 按持久化路径缓存
    # 并共享 PersistentClient：任意一个 ChromaVectorStore 被 GC，都会关掉所有实例
    # 共用的那个 Rust 客户端，其余实例随后全部报
    # `'RustBindingsAPI' object has no attribute 'bindings'`。
    #
    # 触发方式可以非常隐蔽 —— `ChromaVectorStore().collection.count()` 里，临时
    # 对象在取到 .collection 之后就没有引用了，可能在 count() 执行前被回收，于是
    # 一行表达式内部自己把自己弄坏。
    #
    # PersistentClient 的生命周期由进程管理，不需要显式关闭。
