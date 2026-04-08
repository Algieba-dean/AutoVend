"""
车辆检索器

实现高精度的车辆检索功能，结合语义相似度和多维度匹配。
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from src.models.vehicle import Vehicle
from src.models.query import Query, SearchResult, SearchResponse, MatchScore
from src.utils.logger import get_logger, log_performance
from src.utils.config import config
from src.rag.embeddings import BGEEmbeddingModel
from src.rag.vector_store import ChromaVectorStore


class VehicleRetriever:
    """车辆检索器"""

    def __init__(
        self,
        embedding_model: BGEEmbeddingModel,
        vector_store: ChromaVectorStore,
        similarity_threshold: float = 0.7,
        price_tolerance: float = 0.2,
    ):
        """
        初始化检索器

        Args:
            embedding_model: 嵌入模型
            vector_store: 向量存储
            similarity_threshold: 语义相似度阈值
            price_tolerance: 价格容忍度
        """
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.similarity_threshold = similarity_threshold
        self.price_tolerance = price_tolerance

        self.logger = get_logger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

        # 检索统计
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "avg_response_time": 0.0,
            "avg_similarity_score": 0.0,
        }

    @log_performance
    def search(self, query: Query) -> SearchResponse:
        """
        执行车辆搜索

        Args:
            query: 搜索查询

        Returns:
            搜索响应
        """
        start_time = time.time()

        try:
            # 解析查询意图
            parsed_query = self._parse_query(query)

            # 生成查询嵌入
            query_embedding = self.embedding_model._get_text_embedding(
                parsed_query.text
            )

            # 执行向量检索
            vector_results = self._vector_search(
                query_embedding, parsed_query.top_k, parsed_query.filters
            )

            # 计算详细匹配度
            search_results = self._calculate_match_scores(
                vector_results, query_embedding, parsed_query
            )

            # 过滤和排序
            filtered_results = self._filter_and_sort_results(search_results)

            # 构建响应
            search_time = time.time() - start_time
            response = SearchResponse(
                query=parsed_query,
                results=filtered_results,
                total_count=len(filtered_results),
                search_time=search_time,
                semantic_threshold=self.similarity_threshold,
                price_tolerance=self.price_tolerance,
            )

            # 更新统计
            self._update_stats(response)

            return response

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            raise

    def _parse_query(self, query: Query) -> Query:
        """
        解析查询意图

        Args:
            query: 原始查询

        Returns:
            解析后的查询
        """
        parsed = query.copy(deep=True)

        # 提取价格信息
        price_range = self._extract_price_range(query.text)
        if price_range:
            parsed.price_range = price_range

        # 提取车型信息
        vehicle_type = self._extract_vehicle_type(query.text)
        if vehicle_type:
            parsed.vehicle_type = vehicle_type

        # 提取品牌信息
        brand = self._extract_brand(query.text)
        if brand:
            parsed.brand = brand

        # 提取使用场景
        usage = self._extract_usage(query.text)
        if usage:
            parsed.usage = usage

        return parsed

    def _extract_price_range(self, text: str) -> Optional[Tuple[int, int]]:
        """提取价格区间"""
        # 价格模式匹配
        patterns = [
            r"(\d+)万?左右",  # "30万左右"
            r"(\d+)万?到(\d+)万?",  # "20万到30万"
            r"(\d+)万?-(\d+)万?",  # "20万-30万"
            r"(\d+)万?~(\d+)万?",  # "20万~30万"
            r"预算(\d+)万?",  # "预算30万"
            r"价格(\d+)万?",  # "价格30万"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    # 区间价格
                    min_price = int(match.group(1)) * 10000
                    max_price = int(match.group(2)) * 10000
                    return (min_price, max_price)
                else:
                    # 单一价格，创建一个区间
                    price = int(match.group(1)) * 10000
                    tolerance = int(price * 0.3)  # 30%容差
                    return (price - tolerance, price + tolerance)

        return None

    def _extract_vehicle_type(self, text: str) -> Optional[str]:
        """提取车型信息"""
        type_keywords = {
            "SUV": ["SUV", "suv", "越野车"],
            "轿车": ["轿车", "sedan", "三厢车"],
            "MPV": ["MPV", "mpv", "商务车", "面包车"],
            "跑车": ["跑车", "sports car", "轿跑"],
            "新能源": ["新能源", "电动", "EV", "混动", "hybrid"],
            "紧凑型": ["紧凑型", "小型", "A0级", "A级"],
            "中型": ["中型", "B级", "b级"],
            "大型": ["大型", "C级", "c级", "豪华"],
        }

        for vehicle_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return vehicle_type

        return None

    def _extract_brand(self, text: str) -> Optional[str]:
        """提取品牌信息"""
        # 常见品牌列表
        brands = [
            "丰田",
            "Toyota",
            "TOYOTA",
            "本田",
            "Honda",
            "HONDA",
            "大众",
            "Volkswagen",
            "VW",
            "奔驰",
            "Mercedes",
            "Benz",
            "Mercedes-Benz",
            "宝马",
            "BMW",
            "Bmw",
            "奥迪",
            "Audi",
            "AUDI",
            "特斯拉",
            "Tesla",
            "TESLA",
            "比亚迪",
            "BYD",
            "Byd",
            "吉利",
            "Geely",
            "GEELY",
            "长安",
            "Changan",
            "CHANGAN",
            "理想",
            "Li Auto",
            "理想汽车",
            "蔚来",
            "NIO",
            "Nio",
            "小鹏",
            "XPeng",
            "Xpeng",
        ]

        for brand in brands:
            if brand in text:
                return brand

        return None

    def _extract_usage(self, text: str) -> Optional[str]:
        """提取使用场景"""
        usage_patterns = {
            "家用": ["家用", "家庭", "日常", "代步"],
            "商务": ["商务", "商用", "接待", "公务"],
            "越野": ["越野", "户外", "山路", "off-road"],
            "城市": ["城市", "市区", "通勤", "urban"],
            "长途": ["长途", "高速", "旅行", "highway"],
            "运动": ["运动", "驾驶乐趣", "操控", "sport"],
        }

        for usage, keywords in usage_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    return usage

        return None

    def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行向量搜索

        支持 car_model_candidates 过滤：当 filters 中包含该 key 时，
        使用 ChromaDB $in 操作符限制搜索范围到候选车型列表。
        """
        try:
            where = None

            if filters and "car_model_candidates" in filters:
                candidates = filters["car_model_candidates"]
                if candidates:
                    where = {"car_model": {"$in": candidates}}
                    self.logger.debug(f"候选过滤: {len(candidates)} 辆车型")
            elif filters:
                where = filters

            results = self.vector_store.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2,  # 获取更多结果用于后续过滤
                where=where,
                include=["metadatas", "documents", "distances"],
            )
            return results
        except Exception as e:
            self.logger.error(f"向量搜索失败: {e}")
            return {"ids": [], "metadatas": [], "documents": [], "distances": []}

    def _calculate_match_scores(
        self, vector_results: Dict[str, Any], query_embedding: List[float], query: Query
    ) -> List[SearchResult]:
        """计算详细匹配度"""
        results = []

        if not vector_results["ids"]:
            return results

        for i in range(len(vector_results["ids"][0])):
            doc_id = vector_results["ids"][0][i]
            metadata = vector_results["metadatas"][0][i]
            document = vector_results["documents"][0][i]
            distance = vector_results["distances"][0][i]

            # 计算语义相似度
            semantic_score = 1.0 - distance  # ChromaDB返回的是距离

            # 计算各项匹配度
            price_score = self._calculate_price_match(query, metadata)
            category_score = self._calculate_category_match(query, metadata)
            feature_score = self._calculate_feature_match(query, metadata)

            # 计算总分
            overall_score = self._calculate_overall_score(
                semantic_score, price_score, category_score, feature_score
            )

            # 生成匹配解释
            explanation = self._generate_explanation(
                query,
                metadata,
                semantic_score,
                price_score,
                category_score,
                feature_score,
            )

            # 创建匹配度对象
            match_score = MatchScore(
                overall_score=overall_score,
                semantic_score=semantic_score,
                price_score=price_score,
                category_score=category_score,
                feature_score=feature_score,
                matched_features=self._get_matched_features(query, metadata),
                missing_features=self._get_missing_features(query, metadata),
            )

            # 创建搜索结果
            # 注意：这里需要根据doc_id重建Vehicle对象，简化处理
            vehicle = self._reconstruct_vehicle(metadata, document)

            result = SearchResult(
                vehicle=vehicle, score=match_score, explanation=explanation
            )

            results.append(result)

        return results

    def _calculate_price_match(self, query: Query, metadata: Dict[str, Any]) -> float:
        """计算价格匹配度"""
        if not query.price_range:
            return 1.0  # 如果没有价格要求，默认满分

        price_min = metadata.get("price_min")
        price_max = metadata.get("price_max")

        if not price_min or not price_max:
            return 0.5  # 如果没有价格信息，给中等分数

        query_min, query_max = query.price_range

        # 计算重叠度
        overlap_min = max(price_min, query_min)
        overlap_max = min(price_max, query_max)

        if overlap_min <= overlap_max:
            # 有重叠，计算重叠比例
            overlap_range = overlap_max - overlap_min
            query_range = query_max - query_min
            return min(1.0, overlap_range / query_range)
        else:
            # 没有重叠
            return 0.0

    def _calculate_category_match(
        self, query: Query, metadata: Dict[str, Any]
    ) -> float:
        """计算类别匹配度"""
        score = 1.0

        # 车型匹配
        if query.vehicle_type:
            category = metadata.get("category", "")
            if (
                query.vehicle_type.lower() in category.lower()
                or category.lower() in query.vehicle_type.lower()
            ):
                score *= 1.0
            else:
                score *= 0.5

        # 品牌匹配
        if query.brand:
            brand = metadata.get("brand", "")
            if (
                query.brand.lower() in brand.lower()
                or brand.lower() in query.brand.lower()
            ):
                score *= 1.0
            else:
                score *= 0.3

        return score

    def _calculate_feature_match(self, query: Query, metadata: Dict[str, Any]) -> float:
        """计算配置匹配度"""
        score = 0.5  # 基础分数

        # 使用场景匹配
        if query.usage:
            if query.usage == "家用" and metadata.get("family_friendliness") == "High":
                score += 0.3
            elif query.usage == "商务" and metadata.get("design_style") == "Business":
                score += 0.3
            elif (
                query.usage == "越野" and metadata.get("off_road_capability") == "High"
            ):
                score += 0.3
            elif query.usage == "城市" and metadata.get("city_commuting") == "Yes":
                score += 0.3

        # 舒适度匹配
        if metadata.get("comfort_level") == "High":
            score += 0.2

        return min(1.0, score)

    def _calculate_overall_score(
        self,
        semantic_score: float,
        price_score: float,
        category_score: float,
        feature_score: float,
    ) -> float:
        """计算总体匹配度"""
        # 权重配置
        weights = {
            "semantic": 0.4,  # 语义相似度权重最高
            "price": 0.2,
            "category": 0.2,
            "feature": 0.2,
        }

        overall = (
            semantic_score * weights["semantic"]
            + price_score * weights["price"]
            + category_score * weights["category"]
            + feature_score * weights["feature"]
        )

        return overall

    def _generate_explanation(
        self,
        query: Query,
        metadata: Dict[str, Any],
        semantic_score: float,
        price_score: float,
        category_score: float,
        feature_score: float,
    ) -> str:
        """生成匹配解释"""
        explanations = []

        # 语义匹配解释
        if semantic_score > 0.8:
            explanations.append("语义匹配度很高")
        elif semantic_score > 0.6:
            explanations.append("语义匹配度较高")
        else:
            explanations.append("语义匹配度一般")

        # 价格匹配解释
        if query.price_range:
            if price_score > 0.8:
                explanations.append("价格区间完全匹配")
            elif price_score > 0.5:
                explanations.append("价格区间部分匹配")
            else:
                explanations.append("价格区间不匹配")

        # 类别匹配解释
        if query.vehicle_type:
            if category_score > 0.8:
                explanations.append("车型类别匹配")
            elif category_score > 0.5:
                explanations.append("车型类别部分匹配")

        # 配置匹配解释
        if feature_score > 0.7:
            explanations.append("配置要求匹配良好")

        return "；".join(explanations) if explanations else "基本匹配"

    def _get_matched_features(
        self, query: Query, metadata: Dict[str, Any]
    ) -> List[str]:
        """获取匹配的特征"""
        matched = []

        if query.brand and query.brand.lower() in metadata.get("brand", "").lower():
            matched.append(f"品牌: {metadata.get('brand')}")

        if (
            query.vehicle_type
            and query.vehicle_type.lower() in metadata.get("category", "").lower()
        ):
            matched.append(f"车型: {metadata.get('category')}")

        return matched

    def _get_missing_features(
        self, query: Query, metadata: Dict[str, Any]
    ) -> List[str]:
        """获取缺失的特征"""
        missing = []

        if query.brand and query.brand.lower() not in metadata.get("brand", "").lower():
            missing.append(f"品牌偏好: {query.brand}")

        if (
            query.vehicle_type
            and query.vehicle_type.lower() not in metadata.get("category", "").lower()
        ):
            missing.append(f"车型偏好: {query.vehicle_type}")

        return missing

    def _reconstruct_vehicle(self, metadata: Dict[str, Any], document: str) -> Vehicle:
        """根据元数据重建车辆对象"""
        # 简化处理，创建一个基本的Vehicle对象
        # 在实际应用中，可能需要从原始数据中重建完整的对象

        from ..models.vehicle import PreciseLabels, AmbiguousLabels, KeyDetails

        precise_labels = PreciseLabels(
            brand=metadata.get("brand"),
            prize=metadata.get("price"),
            vehicle_category_bottom=metadata.get("category"),
        )

        ambiguous_labels = AmbiguousLabels(
            size=metadata.get("size"),
            family_friendliness=metadata.get("family_friendliness"),
            comfort_level=metadata.get("comfort_level"),
        )

        key_details = KeyDetails(key_details=document)

        vehicle = Vehicle(
            car_model=metadata.get("car_model", "Unknown"),
            PriciseLabels=precise_labels,
            AmbiguousLabels=ambiguous_labels,
            KeyDetails=key_details,
        )

        return vehicle

    def _filter_and_sort_results(
        self, results: List[SearchResult]
    ) -> List[SearchResult]:
        """过滤和排序结果"""
        # 过滤低分结果
        filtered = [
            result
            for result in results
            if result.score.overall_score >= self.similarity_threshold
        ]

        # 按总分排序
        filtered.sort(key=lambda x: x.score.overall_score, reverse=True)

        return filtered

    def _update_stats(self, response: SearchResponse) -> None:
        """更新统计信息"""
        self.stats["total_queries"] += 1

        if response.results:
            self.stats["successful_queries"] += 1

            # 更新平均相似度
            avg_score = sum(r.score.semantic_score for r in response.results) / len(
                response.results
            )
            self.stats["avg_similarity_score"] = (
                self.stats["avg_similarity_score"] * (self.stats["total_queries"] - 1)
                + avg_score
            ) / self.stats["total_queries"]

        # 更新平均响应时间
        self.stats["avg_response_time"] = (
            self.stats["avg_response_time"] * (self.stats["total_queries"] - 1)
            + response.search_time
        ) / self.stats["total_queries"]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "success_rate": self.stats["successful_queries"]
            / max(self.stats["total_queries"], 1),
            "similarity_threshold": self.similarity_threshold,
            "price_tolerance": self.price_tolerance,
        }
