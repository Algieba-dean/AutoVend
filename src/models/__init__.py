"""
数据模型模块

包含车辆数据、查询结果等核心数据结构。
"""

from .vehicle import Vehicle, PreciseLabels, AmbiguousLabels
from .query import Query, SearchResult, MatchScore

__all__ = [
    "Vehicle",
    "PreciseLabels",
    "AmbiguousLabels",
    "Query",
    "SearchResult",
    "MatchScore",
]
