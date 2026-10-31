"""
Comprehensive Automated Unit and Integration Tests for Real-time Market Intelligence Search
(tests/test_market_search.py).

Covers:
1. SearchSanitizer: SQLi, XSS, Shell metachars, length bounds, ad spam removal, URL validation.
2. HermeticMockSearchProvider: Curated database queries, fallback synthesis, search type filtering.
3. LiveWebSearchProvider: Graceful fallback on network failure or offline mode.
4. MarketSearchService: High-level search orchestration and extraction utilities.
5. MarketSearchFacade: Architectural boundary compliance and facade dispatch.
6. Agent Tool Integration: 'search_market_intelligence' dispatch, state note injection, schema checks.
"""

import time
import pytest

from src.agent.schemas import SessionState, Stage, UserRole
from src.agent.tools import (
    ROLE_ALLOWED_TOOLS,
    STAGE_TOOLS,
    TOOLS,
    dispatch,
    is_allowed,
    tools_for,
)
from src.core.market_search import MarketSearchFacade
from src.search.models import (
    AutomotiveNewsItem,
    DiscountPromotionData,
    MarketSearchResult,
    SalesVolumeData,
    SearchType,
)
from src.search.providers.hermetic_mock import (
    MOCK_AUTOMOTIVE_DATABASE,
    HermeticMockSearchProvider,
)
from src.search.providers.live_search import LiveWebSearchProvider
from src.search.sanitizer import SearchSanitizer
from src.search.service import MarketSearchService


# =============================================================================
# 1. SearchSanitizer Security & Cleansing Tests
# =============================================================================

class TestSearchSanitizer:
    def test_empty_and_whitespace_query(self):
        assert SearchSanitizer.sanitize_query("") == ""
        assert SearchSanitizer.sanitize_query("   ") == ""
        assert SearchSanitizer.sanitize_snippet("") == ""
        assert SearchSanitizer.sanitize_url("") == ""

    def test_query_truncation(self):
        long_query = "小米SU7" * 100
        sanitized = SearchSanitizer.sanitize_query(long_query, max_length=50)
        assert len(sanitized) <= 50

    def test_html_and_xss_removal(self):
        malicious = "小米SU7 <script>alert('xss')</script> 最新价格 <img src=x onerror=alert(1)>"
        sanitized = SearchSanitizer.sanitize_query(malicious)
        assert "<script>" not in sanitized
        assert "<img" not in sanitized
        assert "alert('xss')" in sanitized or "alert" in sanitized
        assert "小米SU7" in sanitized

    def test_sql_injection_filtering(self):
        sqli = "小米SU7' UNION SELECT 1, password, 3 FROM users; DROP TABLE cars; --"
        sanitized = SearchSanitizer.sanitize_query(sqli)
        assert "UNION" not in sanitized
        assert "SELECT" not in sanitized
        assert "DROP" not in sanitized
        assert "--" not in sanitized

    def test_shell_metacharacters_filtering(self):
        shell = "小米SU7; cat /etc/passwd | grep root `id` $(whoami) & echo ok"
        sanitized = SearchSanitizer.sanitize_query(shell)
        for char in [";", "|", "`", "$", "&"]:
            assert char not in sanitized
        assert "小米SU7" in sanitized

    def test_snippet_ad_filtering(self):
        ad_text = (
            "这款车目前极受欢迎！加微信：car_dealer_888 享受万元补贴！"
            "另招募代理兼职赚钱！点击立即购买！广告合作：13800138000"
        )
        cleaned = SearchSanitizer.sanitize_snippet(ad_text)
        assert "加微信" not in cleaned
        assert "car_dealer_888" not in cleaned
        assert "兼职赚钱" not in cleaned
        assert "[推广内容已过滤]" in cleaned

    def test_url_sanitization(self):
        assert SearchSanitizer.sanitize_url("https://www.autohome.com.cn/news/123") == "https://www.autohome.com.cn/news/123"
        assert SearchSanitizer.sanitize_url("http://dongchedi.com/article/456") == "http://dongchedi.com/article/456"
        assert SearchSanitizer.sanitize_url("javascript:alert(1)") == ""
        assert SearchSanitizer.sanitize_url("file:///etc/passwd") == ""
        assert SearchSanitizer.sanitize_url("ftp://server/file") == ""


# =============================================================================
# 2. HermeticMockSearchProvider Deterministic Data Tests
# =============================================================================

class TestHermeticMockSearchProvider:
    @pytest.fixture
    def provider(self):
        return HermeticMockSearchProvider()

    def test_curated_database_known_models(self, provider):
        """Verify high fidelity retrieval for all pre-seeded vehicle entries."""
        known_models = ["小米su7", "比亚迪汉", "问界m9", "理想l6", "极氪001", "特斯拉modely", "蔚来es6"]
        for model_key in known_models:
            res = provider.search(model_key, search_type=SearchType.ALL)
            assert res.sanitized is True
            assert res.provider == "hermetic_mock"
            assert res.sales_volume is not None
            assert res.sales_volume.latest_monthly_sales > 0
            assert res.discount_promotion is not None
            assert len(res.discount_promotion.official_guide_price_range) > 0
            assert len(res.news_reviews) >= 1
            assert "🚗" in res.summary_markdown
            assert "销量与交付排名" in res.summary_markdown
            assert "终端优惠与购车权益" in res.summary_markdown

    @pytest.mark.parametrize(
        "search_type,has_sales,has_discount,has_news",
        [
            (SearchType.SALES_VOLUME, True, False, False),
            (SearchType.DISCOUNTS_PROMOTIONS, False, True, False),
            (SearchType.NEWS_REVIEWS, False, False, True),
            (SearchType.ALL, True, True, True),
        ],
    )
    def test_search_type_filtering(self, provider, search_type, has_sales, has_discount, has_news):
        """Verify that provider only populates the requested data fields according to SearchType."""
        res = provider.search("小米SU7", search_type=search_type)
        assert (res.sales_volume is not None) == has_sales
        assert (res.discount_promotion is not None) == has_discount
        assert (len(res.news_reviews) > 0) == has_news

    def test_unlisted_model_dynamic_synthesis(self, provider):
        """Verify that searching for an unknown vehicle produces a realistic synthesized fallback."""
        res = provider.search("阿维塔12", search_type=SearchType.ALL, car_model="阿维塔12")
        assert res.car_model == "阿维塔12"
        assert res.sales_volume is not None
        assert res.sales_volume.latest_monthly_sales > 0
        assert res.discount_promotion is not None
        assert "以旧换新" in res.discount_promotion.trade_in_subsidy
        assert len(res.news_reviews) >= 1
        assert "阿维塔12" in res.news_reviews[0].title
        assert "阿维塔12" in res.summary_markdown

    def test_query_normalization_with_noise_words(self, provider):
        """Verify that queries with extra search keywords still resolve to the correct entry."""
        res1 = provider.search("小米SU7多少钱 优惠 补贴")
        assert res1.car_model == "小米SU7"

        res2 = provider.search("问界M9最新月销量排名榜单")
        assert res2.car_model == "问界M9"


# =============================================================================
# 3. LiveWebSearchProvider Resilience Tests
# =============================================================================

class TestLiveWebSearchProvider:
    def test_offline_mode_falls_back_to_hermetic(self, monkeypatch):
        """When live search is disabled (default in test/CI), fallback is used seamlessly."""
        monkeypatch.setenv("AUTOVEND_ENABLE_LIVE_SEARCH", "0")
        provider = LiveWebSearchProvider()
        res = provider.search("小米SU7", search_type=SearchType.ALL)
        assert res.provider == "live_search_fallback"
        assert res.sales_volume is not None
        assert res.car_model == "小米SU7"

    def test_live_search_error_fallback(self, monkeypatch):
        """When live search encounters an exception, it falls back without crashing."""
        monkeypatch.setenv("AUTOVEND_ENABLE_LIVE_SEARCH", "1")
        provider = LiveWebSearchProvider(api_key="mock_key")
        res = provider.search("比亚迪汉", search_type=SearchType.ALL)
        assert res.car_model == "比亚迪汉"
        assert res.discount_promotion is not None


# =============================================================================
# 4. MarketSearchService Orchestrator Tests
# =============================================================================

class TestMarketSearchService:
    @pytest.fixture
    def service(self):
        return MarketSearchService(provider=HermeticMockSearchProvider())

    def test_singleton_accessor(self):
        inst1 = MarketSearchService.get_instance()
        inst2 = MarketSearchService.get_instance()
        assert inst1 is inst2

    def test_search_sales_volume(self, service):
        sales = service.search_sales_volume("理想L6")
        assert sales is not None
        assert sales.car_model == "理想L6"
        assert sales.latest_monthly_sales > 20000
        assert "月销" in sales.rankings_summary or "月交付" in sales.rankings_summary or "畅销" in sales.rankings_summary

    def test_search_discounts_and_promotions(self, service):
        promo = service.search_discounts_and_promotions("极氪001")
        assert promo is not None
        assert promo.car_model == "极氪001"
        assert len(promo.limited_time_rights) >= 1
        assert "优惠" in promo.summary or "降价" in promo.summary or "权益" in promo.summary

    def test_search_news_and_reviews(self, service):
        news = service.search_news_and_reviews("问界M9", limit=2)
        assert isinstance(news, list)
        assert len(news) >= 1
        assert isinstance(news[0], AutomotiveNewsItem)
        assert "问界M9" in news[0].title or "玄武" in news[0].title

    def test_extract_market_sales_pitch(self, service):
        pitch = service.extract_market_sales_pitch("特斯拉Model Y")
        assert "特斯拉Model Y" in pitch
        assert "实时市场行情" in pitch
        assert "官方指导价" in pitch


# =============================================================================
# 5. MarketSearchFacade & Architecture Boundaries
# =============================================================================

class TestMarketSearchFacade:
    def test_facade_singleton_and_dispatch(self):
        facade = MarketSearchFacade.get_instance()
        res_sales = facade.search("小米SU7", query_type="sales", car_model="小米SU7")
        assert res_sales.sales_volume is not None
        assert res_sales.discount_promotion is None

        res_promo = facade.search("小米SU7", query_type="discount", car_model="小米SU7")
        assert res_promo.discount_promotion is not None
        assert res_promo.sales_volume is None

        res_all = facade.search("小米SU7", query_type="all", car_model="小米SU7")
        assert res_all.sales_volume is not None
        assert res_all.discount_promotion is not None

    def test_get_market_note_for_model(self):
        facade = MarketSearchFacade.get_instance()
        note = facade.get_market_note_for_model("蔚来ES6")
        assert "蔚来ES6" in note
        assert "换电" in note or "BaaS" in note


# =============================================================================
# 6. Agent Tool Integration Tests ('search_market_intelligence')
# =============================================================================

class TestSearchMarketIntelligenceTool:
    def test_tool_registered_in_all_roles(self):
        """Tool must be accessible to CUSTOMER, SALESPERSON, and ADMIN roles."""
        assert "search_market_intelligence" in ROLE_ALLOWED_TOOLS[UserRole.CUSTOMER]
        assert "search_market_intelligence" in ROLE_ALLOWED_TOOLS[UserRole.SALESPERSON]
        assert "search_market_intelligence" in ROLE_ALLOWED_TOOLS[UserRole.ADMIN]

    def test_tool_in_appropriate_stages(self):
        """Tool should be present in needs analysis and car selection stages."""
        assert is_allowed(Stage.NEEDS_ANALYSIS, "search_market_intelligence")
        assert is_allowed(Stage.CAR_SELECTION, "search_market_intelligence")

    def test_dispatch_with_valid_model(self):
        """Successful execution injects market briefing into state.system_notes."""
        state = SessionState(session_id="test_sess", stage=Stage.CAR_SELECTION)
        res = dispatch(
            state,
            "search_market_intelligence",
            {"car_model": "小米SU7", "query_type": "all"},
        )
        assert res.ok is True
        assert res.tool == "search_market_intelligence"
        assert "小米SU7" in res.message
        assert len(state.system_notes) == 1
        assert "小米SU7" in state.system_notes[0]
        assert "市场行情" in state.system_notes[0]

    def test_dispatch_missing_model_returns_error(self):
        """Missing car_model argument should return error ToolResult."""
        state = SessionState(session_id="test_sess", stage=Stage.CAR_SELECTION)
        res = dispatch(
            state,
            "search_market_intelligence",
            {"car_model": ""},
        )
        assert res.ok is False
        assert "缺少必需参数" in res.message or "缺少车型名称" in res.message

    def test_dispatch_tool_outside_stage_is_refused(self):
        """Stage.FAREWELL has no tools; dispatching search should be refused."""
        state = SessionState(session_id="test_sess", stage=Stage.FAREWELL)
        res = dispatch(
            state,
            "search_market_intelligence",
            {"car_model": "小米SU7"},
        )
        assert res.ok is False
        assert "不允许调用" in res.message or "不可用" in res.message


# =============================================================================
# 7. Advanced Sanitization, Mock Edge Cases, and Live HTTP Provider Tests
# =============================================================================

class TestSearchSanitizerAdvanced:
    def test_strip_control_characters_and_ansi_escapes(self):
        """Verify non-printable control characters and terminal escape codes are stripped."""
        dirty = "🚗 小米SU7 \x00\x08\x1b[31m红字\x1b[0m \u200b\u202e逆向文本"
        clean = SearchSanitizer.sanitize_query(dirty)
        assert "\x00" not in clean
        assert "\x08" not in clean
        assert "\x1b[31m" not in clean
        assert "\x1b[0m" not in clean
        assert "\u200b" not in clean
        assert "\u202e" not in clean
        assert "小米SU7" in clean

    def test_strip_boolean_sql_injection(self):
        """Verify boolean SQL injection patterns like 'OR 1=1' are filtered."""
        sqli_queries = [
            "小米SU7' OR 1=1 --",
            "比亚迪汉' OR '1'='1",
            "问界M9' AND 1=1 --",
        ]
        for q in sqli_queries:
            clean = SearchSanitizer.sanitize_query(q)
            assert "1=1" not in clean
            assert "OR" not in clean.split()
            assert "AND" not in clean.split()


class TestHermeticMockSearchRobustness:
    def test_generic_query_does_not_false_match_first_entry(self):
        """Query containing only generic auxiliary terms must not false-match Xiaomi SU7."""
        provider = HermeticMockSearchProvider()
        res = provider.search("降价优惠多少钱")
        assert res.car_model != "小米SU7"
        assert res.car_model == "主流热销车型"

    def test_sentence_query_extracts_clean_subject(self):
        """Sentence queries should not produce whole question as car_model title."""
        provider = HermeticMockSearchProvider()
        res = provider.search("我想了解20万左右SUV最近销量排行榜")
        assert res.car_model == "20万左右SUV"
        assert "我想了解" not in res.car_model
        assert "排行榜" not in res.car_model

    def test_expanded_models_curated_data(self):
        """Verify newly added models: IM L6, AION S, Tank 400, Chery T9, Maextro S800."""
        provider = HermeticMockSearchProvider()

        # 1. 智己L6
        res_im = provider.search("智己L6")
        assert res_im.car_model == "智己L6"
        assert res_im.sales_volume.latest_monthly_sales == 6800
        assert "灵蜥数字底盘" in res_im.sales_volume.rankings_summary

        # 2. 广汽埃安AION S
        res_aion = provider.search("广汽埃安AION S")
        assert res_aion.car_model == "广汽埃安AION S"
        assert "弹匣电池" in res_aion.discount_promotion.summary

        # 3. 坦克400 Hi4-T
        res_tank = provider.search("坦克400")
        assert res_tank.car_model == "坦克400 Hi4-T"
        assert "Hi4-T" in res_tank.sales_volume.rankings_summary

        # 4. 奇瑞风云T9
        res_chery = provider.search("奇瑞风云T9")
        assert res_chery.car_model == "奇瑞风云T9"
        assert "鲲鹏超能混动" in res_chery.sales_volume.rankings_summary

        # 5. 尊界S800
        res_maextro = provider.search("尊界S800")
        assert res_maextro.car_model == "尊界S800"
        assert "100.00万" in res_maextro.discount_promotion.official_guide_price_range


class TestLiveWebSearchProviderExecution:
    def test_live_search_http_success_and_parsing(self, monkeypatch):
        """Simulate successful HTTP API response from external search provider."""
        from unittest.mock import MagicMock
        import httpx

        mock_payload = {
            "results": [
                {
                    "title": "小米SU7 Ultra测试成绩公布 <script>alert(1)</script>",
                    "content": "在纽北赛道创造了惊人成绩，三电机系统表现出色！加微信：dealer888",
                    "url": "https://autohome.com.cn/news/su7_ultra",
                    "source": "汽车之家",
                    "published_date": "2025-02-16",
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

        provider = LiveWebSearchProvider(api_key="mock_live_key")
        provider.is_live_enabled = True

        result = provider.search("小米SU7 Ultra 实测", car_model="小米SU7 Ultra")
        assert result.provider == "live_web"
        assert len(result.news_reviews) == 1
        news = result.news_reviews[0]
        assert "<script>" not in news.title
        assert "dealer888" not in news.summary
        assert "[推广内容已过滤]" in news.summary
        assert "实时网络检索情报速递" in result.summary_markdown

    def test_live_search_http_failure_falls_back(self, monkeypatch):
        """Simulate HTTP 500 server error triggering graceful hermetic fallback."""
        from unittest.mock import MagicMock
        import httpx

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

        provider = LiveWebSearchProvider(api_key="mock_key")
        provider.is_live_enabled = True

        result = provider.search("小米SU7 优惠", car_model="小米SU7")
        assert result.provider == "live_search_fallback"
        assert result.car_model == "小米SU7"
        assert result.discount_promotion is not None

