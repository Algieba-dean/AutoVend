"""
Market Intelligence & Real-time Web Search Package (src/search/__init__.py).
"""

from src.search.models import (
    AutomotiveNewsItem,
    DiscountPromotionData,
    MarketSearchResult,
    SalesVolumeData,
    SearchType,
)
from src.search.providers.base import BaseSearchProvider
from src.search.providers.hermetic_mock import HermeticMockSearchProvider
from src.search.providers.live_search import LiveWebSearchProvider
from src.search.sanitizer import SearchSanitizer
from src.search.service import MarketSearchService

__all__ = [
    "SearchType",
    "SalesVolumeData",
    "DiscountPromotionData",
    "AutomotiveNewsItem",
    "MarketSearchResult",
    "BaseSearchProvider",
    "HermeticMockSearchProvider",
    "LiveWebSearchProvider",
    "SearchSanitizer",
    "MarketSearchService",
]
