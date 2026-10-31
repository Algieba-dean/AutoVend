"""
Core Market Search Facade (src/core/market_search.py).

Provides architectural re-exports and facade access to the MarketSearchService
for cross-package integration without violating agent layer import boundaries.
"""

from typing import Any, Dict, List, Optional

from src.search.models import (
    AutomotiveNewsItem,
    DiscountPromotionData,
    MarketSearchResult,
    SalesVolumeData,
    SearchType,
)
from src.search.service import MarketSearchService


class MarketSearchFacade:
    """Facade for accessing market search functionality from agent and backend layers."""

    _instance: Optional["MarketSearchFacade"] = None

    def __init__(self):
        self._service = MarketSearchService.get_instance()

    @classmethod
    def get_instance(cls) -> "MarketSearchFacade":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def search(
        self,
        query: str,
        query_type: str = "all",
        car_model: Optional[str] = None,
    ) -> MarketSearchResult:
        """Search market intelligence by query type string."""
        type_mapping = {
            "sales": SearchType.SALES_VOLUME,
            "sales_volume": SearchType.SALES_VOLUME,
            "discount": SearchType.DISCOUNTS_PROMOTIONS,
            "promotion": SearchType.DISCOUNTS_PROMOTIONS,
            "news": SearchType.NEWS_REVIEWS,
            "review": SearchType.NEWS_REVIEWS,
            "all": SearchType.ALL,
        }
        st = type_mapping.get(query_type.lower().strip(), SearchType.ALL)
        return self._service.search(query=query, search_type=st, car_model=car_model)

    def get_market_note_for_model(self, car_model: str) -> str:
        """Get markdown note for prompt injection."""
        return self._service.extract_market_sales_pitch(car_model)


__all__ = [
    "SearchType",
    "SalesVolumeData",
    "DiscountPromotionData",
    "AutomotiveNewsItem",
    "MarketSearchResult",
    "MarketSearchService",
    "MarketSearchFacade",
]
