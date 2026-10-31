import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from src.search.models import (
    AutomotiveNewsItem,
    DiscountPromotionData,
    MarketSearchResult,
    SalesVolumeData,
    SearchType,
)
from src.search.providers.base import BaseSearchProvider
from src.search.providers.hermetic_mock import HermeticMockSearchProvider
from src.search.sanitizer import SearchSanitizer

logger = logging.getLogger(__name__)


class LiveWebSearchProvider(BaseSearchProvider):
    """
    Live web search provider for automotive market intelligence.
    Executes real HTTP requests against external search engines (Tavily, Serper, or Custom JSON API)
    with strict timeout guards and automatic sanitization.
    Automatically degrades gracefully to hermetic mock if offline or unconfigured.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        search_url: Optional[str] = None,
        timeout_seconds: float = 2.0,
        fallback_provider: Optional[BaseSearchProvider] = None,
    ):
        self.api_key = api_key or os.getenv("AUTOVEND_SEARCH_API_KEY", "")
        self.search_url = search_url or os.getenv("AUTOVEND_SEARCH_URL", "https://api.tavily.com/search")
        self.timeout_seconds = timeout_seconds
        self.fallback = fallback_provider or HermeticMockSearchProvider()
        self.is_live_enabled = bool(os.getenv("AUTOVEND_ENABLE_LIVE_SEARCH", "0") == "1" and self.api_key)

    def search(
        self,
        query: str,
        search_type: SearchType = SearchType.ALL,
        car_model: Optional[str] = None,
    ) -> MarketSearchResult:
        """Execute search, attempting live provider first and falling back seamlessly."""
        sanitized_query = SearchSanitizer.sanitize_query(query)

        if not self.is_live_enabled:
            logger.debug("Live web search disabled or key unset, using hermetic fallback.")
            res = self.fallback.search(sanitized_query, search_type=search_type, car_model=car_model)
            res.provider = "live_search_fallback"
            return res

        # Attempt live API call within timeout
        try:
            live_result = self._execute_http_search(sanitized_query, search_type, car_model)
            if live_result:
                return live_result
        except Exception as e:
            logger.warning(f"Live search failed ({e}), falling back to hermetic data.")

        res = self.fallback.search(sanitized_query, search_type=search_type, car_model=car_model)
        res.provider = "live_search_fallback"
        return res

    def _execute_http_search(
        self,
        query: str,
        search_type: SearchType,
        car_model: Optional[str],
    ) -> Optional[MarketSearchResult]:
        """Perform HTTP POST/GET request against live search engine."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AutoVend-MarketSearch/1.0",
        }

        # Check if Serper, Tavily, or custom endpoint
        is_serper = "serper.dev" in self.search_url
        if is_serper:
            headers["X-API-KEY"] = self.api_key
            payload = {"q": query, "num": 5}
        else:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": 5,
                "search_depth": "basic",
                "include_answer": True,
            }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(self.search_url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Search API returned HTTP {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()

        return self._parse_live_response(data, query, search_type, car_model)

    def _parse_live_response(
        self,
        data: Dict[str, Any],
        query: str,
        search_type: SearchType,
        car_model: Optional[str],
    ) -> MarketSearchResult:
        """Parse, sanitize, and structure raw search API response."""
        news_items: List[AutomotiveNewsItem] = []
        raw_results = data.get("results") or data.get("organic") or []

        for item in raw_results[:5]:
            raw_title = item.get("title", "")
            raw_snippet = item.get("content") or item.get("snippet", "")
            raw_url = item.get("url", "")
            raw_source = item.get("source") or item.get("domain", "网络媒体")
            pub_date = item.get("published_date") or item.get("date", "最新发布")

            clean_title = SearchSanitizer.sanitize_snippet(raw_title, max_length=150)
            clean_snippet = SearchSanitizer.sanitize_snippet(raw_snippet, max_length=500)
            clean_source = SearchSanitizer.sanitize_snippet(raw_source, max_length=50) or "网络媒体"
            clean_url = SearchSanitizer.sanitize_url(raw_url)

            if clean_title and clean_snippet:
                news_items.append(
                    AutomotiveNewsItem(
                        title=clean_title,
                        source=clean_source,
                        publish_date=pub_date,
                        category="行业快报",
                        summary=clean_snippet,
                        url=clean_url,
                    )
                )

        target_model = car_model or SearchSanitizer.sanitize_query(query.split()[0] if query else "热销汽车")

        # Supplement with baseline figures if live engine only provided text snippets
        fallback_entry = self.fallback.search(query, search_type=search_type, car_model=target_model)
        sales_vol = fallback_entry.sales_volume if search_type in (SearchType.SALES_VOLUME, SearchType.ALL) else None
        discount_promo = fallback_entry.discount_promotion if search_type in (SearchType.DISCOUNTS_PROMOTIONS, SearchType.ALL) else None

        # Format markdown summary
        briefing_parts = [f"### 🌐 【{target_model}】实时网络检索情报速递 (来源: Live Web)\n"]
        if sales_vol:
            briefing_parts.append(
                f"**📊 实时销量参考**：最新月销量约 **{sales_vol.latest_monthly_sales:,}** 台（{sales_vol.segment_rank}）\n"
            )
        if discount_promo:
            briefing_parts.append(
                f"**💰 终端优惠情报**：{discount_promo.terminal_discount}；{discount_promo.trade_in_subsidy}\n"
            )
        if news_items:
            briefing_parts.append(f"**📰 实时全网热点资讯**：\n")
            for item in news_items[:3]:
                briefing_parts.append(f"- **{item.title}**（{item.source}）：{item.summary}\n")

        return MarketSearchResult(
            query=query,
            car_model=target_model,
            search_type=search_type,
            sales_volume=sales_vol,
            discount_promotion=discount_promo,
            news_reviews=news_items,
            provider="live_web",
            sanitized=True,
            retrieved_at=time.time(),
            summary_markdown="\n".join(briefing_parts),
        )
