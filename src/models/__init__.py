"""
数据模型模块

包含车辆数据、查询结果等核心数据结构。
"""

from .query import MatchScore, Query, SearchResult
from .vehicle import AmbiguousLabels, PreciseLabels, Vehicle

__all__ = [
    "Vehicle",
    "PreciseLabels",
    "AmbiguousLabels",
    "Query",
    "SearchResult",
    "MatchScore",
]
