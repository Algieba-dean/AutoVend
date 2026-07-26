"""
查询相关数据模型

定义用户查询、搜索结果等数据结构。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .vehicle import Vehicle


class Query(BaseModel):
    """用户查询模型"""

    text: str = Field(..., description="用户查询文本")
    top_k: int = Field(default=10, description="返回的最大结果数")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="过滤条件")

    # 解析出的查询意图
    price_range: Optional[tuple] = Field(default=None, description="价格区间")
    vehicle_type: Optional[str] = Field(default=None, description="车型类别")
    brand: Optional[str] = Field(default=None, description="品牌偏好")
    usage: Optional[str] = Field(default=None, description="使用场景")

    class Config:
        extra = "allow"


class MatchScore(BaseModel):
    """匹配度评分"""

    overall_score: float = Field(..., description="总体匹配度 (0-1)")
    semantic_score: float = Field(..., description="语义相似度 (0-1)")
    price_score: float = Field(..., description="价格匹配度 (0-1)")
    category_score: float = Field(..., description="类别匹配度 (0-1)")
    feature_score: float = Field(..., description="配置匹配度 (0-1)")

    # 匹配详情
    matched_features: List[str] = Field(default_factory=list, description="匹配的特征")
    missing_features: List[str] = Field(default_factory=list, description="缺失的特征")

    def __str__(self) -> str:
        return f"总分: {self.overall_score:.2f} (语义: {self.semantic_score:.2f}, 价格: {self.price_score:.2f}, 类别: {self.category_score:.2f}, 配置: {self.feature_score:.2f})"


class SearchResult(BaseModel):
    """搜索结果模型"""

    vehicle: Vehicle = Field(..., description="匹配的车辆")
    score: MatchScore = Field(..., description="匹配度评分")
    explanation: str = Field(..., description="匹配解释")

    class Config:
        extra = "allow"


class SearchResponse(BaseModel):
    """搜索响应模型"""

    query: Query = Field(..., description="原始查询")
    results: List[SearchResult] = Field(..., description="搜索结果列表")
    total_count: int = Field(..., description="总结果数")
    search_time: float = Field(..., description="搜索耗时（秒）")

    # 搜索统计
    semantic_threshold: float = Field(default=0.7, description="语义相似度阈值")
    price_tolerance: float = Field(default=0.2, description="价格容忍度")

    def get_top_results(self, n: int = 5) -> List[SearchResult]:
        """获取前N个结果"""
        return self.results[:n]

    def filter_by_score(self, min_score: float = 0.5) -> List[SearchResult]:
        """按分数过滤结果"""
        return [r for r in self.results if r.score.overall_score >= min_score]

    def get_summary(self) -> str:
        """获取搜索结果摘要"""
        if not self.results:
            return "未找到匹配的车辆"

        top_result = self.results[0]
        return f"找到 {self.total_count} 个匹配结果，最佳匹配: {top_result.vehicle.car_model} (匹配度: {top_result.score.overall_score:.2f})"


class SearchStats(BaseModel):
    """搜索统计信息"""

    total_queries: int = Field(default=0, description="总查询次数")
    avg_response_time: float = Field(default=0.0, description="平均响应时间")
    avg_similarity_score: float = Field(default=0.0, description="平均相似度分数")
    success_rate: float = Field(default=0.0, description="成功率（找到结果的比例）")

    # 按类别统计
    query_types: Dict[str, int] = Field(default_factory=dict, description="查询类型统计")
    brand_queries: Dict[str, int] = Field(default_factory=dict, description="品牌查询统计")

    def update_stats(self, response: SearchResponse) -> None:
        """更新统计信息"""
        self.total_queries += 1

        # 更新响应时间
        self.avg_response_time = (
            self.avg_response_time * (self.total_queries - 1) + response.search_time
        ) / self.total_queries

        # 更新成功率
        if response.results:
            self.success_rate = (
                self.success_rate * (self.total_queries - 1) + 1.0
            ) / self.total_queries
        else:
            self.success_rate = (self.success_rate * (self.total_queries - 1)) / self.total_queries

        # 更新平均相似度
        if response.results:
            avg_score = sum(r.score.semantic_score for r in response.results) / len(
                response.results
            )
            self.avg_similarity_score = (
                self.avg_similarity_score * (self.total_queries - 1) + avg_score
            ) / self.total_queries

        # 更新查询类型统计
        query_type = "general"
        if response.query.vehicle_type:
            query_type = response.query.vehicle_type
        elif response.query.brand:
            query_type = "brand"
        elif response.query.price_range:
            query_type = "price"

        self.query_types[query_type] = self.query_types.get(query_type, 0) + 1

        # 更新品牌统计
        if response.query.brand:
            self.brand_queries[response.query.brand] = (
                self.brand_queries.get(response.query.brand, 0) + 1
            )
