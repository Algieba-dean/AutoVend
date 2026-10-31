"""
Data models and schemas for Live Market Intelligence (src/search/models.py).

Defines structured representations of real-time automotive sales data,
retail discounts/promotions, news/reviews, and unified search results.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import time

from pydantic import BaseModel, Field


class SearchType(str, Enum):
    """Categorical type of market intelligence query."""

    SALES_VOLUME = "sales_volume"          # 月销量、交付量、同级销量榜单
    DISCOUNTS_PROMOTIONS = "discounts_promotions"  # 终端降价、限时权益、置换补贴
    NEWS_REVIEWS = "news_reviews"          # 改款上市、实测口碑、评测新闻
    ALL = "all"                            # 综合全维市场情报


class SalesVolumeData(BaseModel):
    """Structured monthly sales and delivery ranking intelligence."""

    car_model: str = Field(..., description="Vehicle model name")
    latest_monthly_sales: int = Field(0, description="Most recent monthly sales volume (units)")
    sales_period: str = Field("", description="Sales period label, e.g. '2025年1月'")
    total_annual_delivery: int = Field(0, description="Annual cumulative delivery (units)")
    segment_rank: str = Field("", description="Segment ranking, e.g. '中大型纯电轿车销量第1名'")
    overall_rank: str = Field("", description="Overall NEV sales ranking, e.g. '新能源全品类销量榜第5名'")
    yoy_growth: str = Field("", description="Year-on-year growth rate, e.g. '+35.8%'")
    mom_growth: str = Field("", description="Month-on-month growth rate, e.g. '+8.2%'")
    rankings_summary: str = Field("", description="Human-readable market sales commentary")


class DiscountPromotionData(BaseModel):
    """Structured retail discounts, subsidies, and promotional entitlements."""

    car_model: str = Field(..., description="Vehicle model name")
    official_guide_price_range: str = Field("", description="Official MSRP range, e.g. '21.59万 - 29.99万元'")
    terminal_discount: str = Field("", description="Direct cash discount, e.g. '全系限时直降15000元'")
    trade_in_subsidy: str = Field("", description="Government / OEM trade-in subsidy, e.g. '以旧换新置换补贴最高20000元'")
    financial_policy: str = Field("", description="Financing perks, e.g. '3年0息金融方案或5年超低息，首付低至15%'")
    limited_time_rights: List[str] = Field(default_factory=list, description="Limited-time benefits list")
    valid_until: str = Field("", description="Offer validity date, e.g. '2025-06-30'")
    summary: str = Field("", description="Concise sales pitch summary of pricing benefits")


class AutomotiveNewsItem(BaseModel):
    """Single vehicle news, launch review, or test-drive assessment."""

    title: str = Field(..., description="Headline of the news or review")
    source: str = Field("", description="Media outlet or official source, e.g. '汽车之家', '懂车帝'")
    publish_date: str = Field("", description="Publication date, e.g. '2025-02-18'")
    category: str = Field("实测口碑", description="News category: 改款上市, 实测口碑, 评测新闻, 行业快报")
    summary: str = Field(..., description="Concise content digest")
    url: str = Field("", description="Reference URL")


class MarketSearchResult(BaseModel):
    """Unified container for automotive market intelligence retrieval."""

    query: str = Field(..., description="Original search query text")
    car_model: str = Field("", description="Identified vehicle model")
    search_type: SearchType = Field(SearchType.ALL, description="Type of search executed")
    sales_volume: Optional[SalesVolumeData] = Field(None, description="Sales volume intelligence if requested")
    discount_promotion: Optional[DiscountPromotionData] = Field(None, description="Discounts and promotions if requested")
    news_reviews: List[AutomotiveNewsItem] = Field(default_factory=list, description="List of news and reviews")
    provider: str = Field("hermetic_mock", description="Name of the search provider that satisfied the query")
    sanitized: bool = Field(True, description="Whether query inputs and outputs have passed sanitization guards")
    retrieved_at: float = Field(default_factory=time.time, description="Retrieval timestamp (UNIX epoch)")
    summary_markdown: str = Field("", description="Formatted Markdown market briefing for agent conversational citation")
