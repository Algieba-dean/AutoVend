"""
Market Search Service Orchestrator (src/search/service.py).

Unified facade providing real-time automotive market intelligence retrieval,
sales volume tracking, discount monitoring, and news synthesis for AutoVend.
"""

import logging
from typing import List, Optional

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

logger = logging.getLogger(__name__)


class MarketSearchService:
    """
    Enterprise Market Search Service.
    Integrates live web retrieval with resilient offline hermetic mock fallbacks.
    """

    _instance: Optional["MarketSearchService"] = None

    def __init__(self, provider: Optional[BaseSearchProvider] = None):
        self.provider: BaseSearchProvider = provider or LiveWebSearchProvider()

    @classmethod
    def get_instance(cls) -> "MarketSearchService":
        """Singleton accessor."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def search(
        self,
        query: str,
        search_type: SearchType = SearchType.ALL,
        car_model: Optional[str] = None,
    ) -> MarketSearchResult:
        """
        Execute end-to-end sanitized market search.
        """
        clean_query = SearchSanitizer.sanitize_query(query)
        clean_model = SearchSanitizer.sanitize_query(car_model) if car_model else None
        return self.provider.search(clean_query, search_type=search_type, car_model=clean_model)

    def search_sales_volume(
        self, car_model: str, timeframe: Optional[str] = None
    ) -> Optional[SalesVolumeData]:
        """Query specific vehicle monthly sales volume and ranking."""
        res = self.search(
            query=f"{car_model} {timeframe or ''} 销量 交付榜单",
            search_type=SearchType.SALES_VOLUME,
            car_model=car_model,
        )
        return res.sales_volume

    def search_discounts_and_promotions(
        self, car_model: str, city: Optional[str] = None
    ) -> Optional[DiscountPromotionData]:
        """Query retail discounts, trade-in subsidies, and limited-time benefits."""
        res = self.search(
            query=f"{car_model} {city or ''} 降价优惠 置换补贴 限时权益",
            search_type=SearchType.DISCOUNTS_PROMOTIONS,
            car_model=car_model,
        )
        return res.discount_promotion

    def search_news_and_reviews(
        self, car_model: str, limit: int = 5
    ) -> List[AutomotiveNewsItem]:
        """Query vehicle facelift launch news, recalls, and media reviews."""
        res = self.search(
            query=f"{car_model} 改款上市 实测口碑 评测新闻",
            search_type=SearchType.NEWS_REVIEWS,
            car_model=car_model,
        )
        return res.news_reviews[:limit]

    def extract_market_sales_pitch(self, car_model: str) -> str:
        """
        Generate concise sales briefing note for inclusion in agent prompt notes.
        """
        res = self.search(car_model, search_type=SearchType.ALL, car_model=car_model)
        return res.summary_markdown
