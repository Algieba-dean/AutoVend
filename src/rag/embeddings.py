"""
BGE-M3嵌入模型

集成BGE-M3模型，提供高质量的文本向量化服务。
"""

import time
from typing import List, Optional

import numpy as np
import torch
from llama_index.core.embeddings import BaseEmbedding
from sentence_transformers import SentenceTransformer

from src.utils.config import config
from src.utils.logger import get_logger, log_performance


class BGEEmbeddingModel(BaseEmbedding):
    """BGE-M3嵌入模型"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: int = 32,
        max_length: int = 512,
        normalize_embeddings: bool = True,
    ):
        """
        初始化BGE-M3嵌入模型

        Args:
            model_name: 模型名称，默认使用配置中的值
            device: 设备类型 (auto, cpu, cuda)
            batch_size: 批处理大小
            max_length: 最大序列长度
            normalize_embeddings: 是否归一化嵌入向量
        """
        super().__init__()

        # 存储配置
        self._model_name = model_name or config.embedding_model
        self._device = device or config.embedding_device
        self._batch_size = batch_size
        self._max_length = max_length
        self._normalize_embeddings = normalize_embeddings
        self._logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        self._model = None
        self._dimension = None

        # 统计信息
        self._stats = {"total_embeddings": 0, "total_time": 0.0, "avg_time_per_embedding": 0.0}

    @property
    def model(self) -> SentenceTransformer:
        """懒加载模型"""
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def embed_dimension(self) -> int:
        """嵌入向量维度"""
        if self._dimension is None:
            # 创建一个测试嵌入来获取维度
            test_embedding = self._get_text_embedding("test")
            self._dimension = len(test_embedding)
        return self._dimension

    @property
    def model_name(self) -> str:
        """模型名称"""
        return self._model_name

    @property
    def device(self) -> str:
        """设备类型"""
        return self._device

    def _load_model(self) -> None:
        """加载BGE-M3模型"""
        try:
            model_name = self._model_name  # 使用内部变量
            self._logger.info(f"正在加载BGE-M3模型: {model_name}")

            # 确定设备
            device = self.device
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"

            self._logger.info(f"使用设备: {device}")

            # 加载模型
            self._model = SentenceTransformer(model_name, device=device, trust_remote_code=True)

            # 设置模型参数
            self._model.max_seq_length = self._max_length

            self._logger.info(f"BGE-M3模型加载成功，嵌入维度: {self.embed_dimension}")

        except Exception as e:
            self._logger.error(f"加载BGE-M3模型失败: {e}")
            raise

    def _get_query_embedding(self, query: str) -> List[float]:
        """获取查询嵌入向量（LlamaIndex接口）"""
        return self._get_text_embedding(query)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """异步获取查询嵌入向量（LlamaIndex接口）"""
        return self._get_query_embedding(query)

    @log_performance
    def _get_text_embedding(self, text: str) -> List[float]:
        """
        获取单个文本的嵌入向量

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        start_time = time.time()

        try:
            # 预处理文本
            processed_text = self._preprocess_text(text)

            # 生成嵌入
            embedding = self.model.encode(
                processed_text,
                normalize_embeddings=self._normalize_embeddings,
                convert_to_numpy=True,
            )

            # 转换为列表
            embedding_list = embedding.tolist()

            # 更新统计信息
            embedding_time = time.time() - start_time
            self._update_stats(1, embedding_time)

            return embedding_list

        except Exception as e:
            self._logger.error(f"生成嵌入向量失败: {e}")
            raise

    @log_performance
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取文本嵌入向量

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        start_time = time.time()

        try:
            # 预处理文本
            processed_texts = [self._preprocess_text(text) for text in texts]

            # 批量生成嵌入
            embeddings = self.model.encode(
                processed_texts,
                batch_size=self._batch_size,
                normalize_embeddings=self._normalize_embeddings,
                convert_to_numpy=True,
                show_progress_bar=False,
            )

            # 转换为列表
            embedding_lists = embeddings.tolist()

            # 更新统计信息
            embedding_time = time.time() - start_time
            self._update_stats(len(texts), embedding_time)

            return embedding_lists

        except Exception as e:
            self._logger.error(f"批量生成嵌入向量失败: {e}")
            raise

    def _preprocess_text(self, text: str) -> str:
        """
        预处理文本

        Args:
            text: 原始文本

        Returns:
            预处理后的文本
        """
        if not text:
            return ""

        # 基本清理
        text = text.strip()

        # 可以在这里添加更多的预处理逻辑
        # 例如：特殊字符处理、标准化等

        return text

    def _update_stats(self, count: int, time_taken: float) -> None:
        """更新统计信息"""
        self._stats["total_embeddings"] += count
        self._stats["total_time"] += time_taken
        self._stats["avg_time_per_embedding"] = (
            self._stats["total_time"] / self._stats["total_embeddings"]
        )

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        计算两个嵌入向量的余弦相似度

        Args:
            embedding1: 第一个嵌入向量
            embedding2: 第二个嵌入向量

        Returns:
            相似度分数 (0-1)
        """
        try:
            # 转换为numpy数组
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # 确保结果在[0, 1]范围内
            return float(max(0.0, min(1.0, similarity)))

        except Exception as e:
            self._logger.error(f"计算相似度失败: {e}")
            return 0.0

    def batch_similarity(
        self, query_embedding: List[float], document_embeddings: List[List[float]]
    ) -> List[float]:
        """
        批量计算相似度

        Args:
            query_embedding: 查询嵌入向量
            document_embeddings: 文档嵌入向量列表

        Returns:
            相似度分数列表
        """
        try:
            similarities = []

            for doc_embedding in document_embeddings:
                similarity = self.similarity(query_embedding, doc_embedding)
                similarities.append(similarity)

            return similarities

        except Exception as e:
            self._logger.error(f"批量计算相似度失败: {e}")
            return [0.0] * len(document_embeddings)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            **self._stats,
            "model_name": self.model_name,
            "device": self.device,
            "embed_dimension": self.embed_dimension,
            "batch_size": self._batch_size,
        }

    def clear_cache(self) -> None:
        """清理缓存"""
        # BGE-M3模型的缓存清理
        if hasattr(self.model, "clear_cache"):
            self.model.clear_cache()

        # 清理GPU缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self._logger.info("嵌入模型缓存已清理")

    def __del__(self):
        """析构函数"""
        try:
            self.clear_cache()
        except Exception:
            pass


# 为了兼容LlamaIndex的接口
def get_embedding_model(
    model_name: Optional[str] = None, device: Optional[str] = None, **kwargs
) -> BGEEmbeddingModel:
    """
    获取BGE-M3嵌入模型实例

    Args:
        model_name: 模型名称
        device: 设备类型
        **kwargs: 其他参数

    Returns:
        BGE-M3嵌入模型实例
    """
    return BGEEmbeddingModel(model_name=model_name, device=device, **kwargs)
