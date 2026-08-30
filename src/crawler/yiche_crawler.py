"""
Yiche.com (易车网) Dedicated Automotive Crawler Engine.
Uses Playwright with session priming, stealth evasions, API response interception,
and HTML DOM fallback parsing to extract full multi-tiered vehicle specifications.
"""

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.crawler.schemas import CrawlSummary, RawSerialSpecSheet, RawVehicleTrim
from src.crawler.storage import RawDataStorage
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Common BYD Series Slugs mapping on Yiche
BYD_DEFAULT_SERIALS = {
    "han": "汉",
    "haibao06": "海豹06",
    "qinplus": "秦PLUS",
    "qinl": "秦L",
    "songpro": "宋Pro",
    "songplusxinnengyuan": "宋PLUS新能源",
    "tang": "唐",
    "yuanplus": "元PLUS",
    "haiou": "海鸥",
    "haidun": "海豚",
    "haibao": "海豹",
    "fangchengbaobao5": "豹5",
    "tengshid9": "腾势D9",
    "yangwangu8": "仰望U8",
}


class YichePlaywrightCrawler:
    """Automated Playwright-based crawler for Yiche.com vehicle specifications."""

    def __init__(self, storage: Optional[RawDataStorage] = None, headless: bool = True):
        self.storage = storage or RawDataStorage()
        self.headless = headless
        self._pw = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._is_initialized = False

    async def start(self) -> None:
        """Launch headless browser, setup stealth parameters, and prime session."""
        if self._is_initialized:
            return

        logger.info("Initializing Playwright browser for Yiche crawler...")
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        self._page = await self._context.new_page()

        # Prime cookies and session from www.yiche.com
        logger.info("Priming Yiche session and security cookies...")
        try:
            await self._page.goto("https://www.yiche.com/", wait_until="domcontentloaded", timeout=15000)
            await self._page.wait_for_timeout(1500)
            logger.info("Session established successfully.")
        except Exception as e:
            logger.warning(f"Session priming warning (continuing): {e}")

        self._is_initialized = True

    async def close(self) -> None:
        """Release all Playwright resources."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._is_initialized = False
        logger.info("Playwright browser closed.")

    async def crawl_serial(
        self,
        serial_slug: str,
        serial_name: Optional[str] = None,
        brand: str = "比亚迪",
    ) -> Optional[RawSerialSpecSheet]:
        """
        Crawl full specification sheet for a specific vehicle series.
        Uses API response interception with HTML table fallback.
        """
        if not self._is_initialized:
            await self.start()

        page = self._page
        target_url = f"https://car.yiche.com/{serial_slug}/peizhi/"
        logger.info(f"Crawling series [{serial_name or serial_slug}] at {target_url}...")

        intercepted_api_json: Optional[Dict[str, Any]] = None

        async def on_response(response):
            nonlocal intercepted_api_json
            if "get_param_details" in response.url:
                try:
                    data = await response.json()
                    if data.get("status") == "1" and data.get("data"):
                        intercepted_api_json = data
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2500)
        except Exception as e:
            logger.warning(f"Page navigation note for {target_url}: {e}")

        # Strategy 1: Parse from Intercepted API JSON (Highest Precision)
        if intercepted_api_json:
            logger.info(f"Successfully intercepted get_param_details API for [{serial_slug}]")
            sheet = self._parse_api_payload(intercepted_api_json, brand, serial_slug, serial_name)
            if sheet and sheet.total_trims > 0:
                self.storage.save_serial_specs(sheet)
                return sheet

        # Strategy 2: Fallback to HTML Table parsing
        logger.info(f"API interception empty, falling back to HTML table parsing for [{serial_slug}]...")
        html = await page.content()
        sheet = self._parse_html_table(html, brand, serial_slug, serial_name)
        if sheet and sheet.total_trims > 0:
            self.storage.save_serial_specs(sheet)
            return sheet

        logger.warning(f"No trims found for [{serial_slug}] (page might be empty or invalid slug)")
        return None

    def _parse_api_payload(
        self,
        payload: Dict[str, Any],
        brand: str,
        serial_slug: str,
        serial_name: Optional[str],
    ) -> RawSerialSpecSheet:
        """Parse native get_param_details JSON payload into standard RawSerialSpecSheet."""
        data = payload.get("data", {})
        param_groups = data.get("list", [])
        if not param_groups:
            return RawSerialSpecSheet(brand=brand, serial=serial_name or serial_slug, serial_slug=serial_slug)

        # 1. Identify trims from first item
        trims_map: Dict[int, RawVehicleTrim] = {}
        detected_serial_name = serial_name or serial_slug

        for group in param_groups:
            items = group.get("items", [])
            for item in items:
                item_name = item.get("name", "")
                param_values = item.get("paramValues", [])
                for pv in param_values:
                    car_id = str(pv.get("id"))
                    val = str(pv.get("value", "")).strip()

                    if car_id not in trims_map:
                        # Parse base info if available
                        base_key_str = pv.get("baseInfoKey", "{}")
                        try:
                            base_info = json.loads(base_key_str) if isinstance(base_key_str, str) else base_key_str
                            detected_serial_name = base_info.get("serialName", detected_serial_name)
                        except Exception:
                            base_info = {}

                        trims_map[car_id] = RawVehicleTrim(
                            car_id=car_id,
                            brand=brand,
                            serial=detected_serial_name,
                            serial_slug=serial_slug,
                            trim_name=val,
                            raw_api_payload=pv,
                        )

        # 2. Populate specifications across all groups
        categories = []
        for group in param_groups:
            group_name = group.get("name", "未分类")
            if group_name not in categories:
                categories.append(group_name)

            for item in group.get("items", []):
                param_name = item.get("name", "").strip()
                if not param_name:
                    continue

                for pv in item.get("paramValues", []):
                    car_id = str(pv.get("id"))
                    val = str(pv.get("value", "")).strip().replace("●", "标配").replace("○", "选配").replace("-", "无")
                    if car_id in trims_map:
                        trim = trims_map[car_id]
                        if group_name not in trim.specs:
                            trim.specs[group_name] = {}
                        trim.specs[group_name][param_name] = val

                        # Enrich top-level shortcut fields
                        if param_name in ["厂商指导价", "指导价"]:
                            trim.price_guide = val
                        elif param_name in ["能源类型"]:
                            trim.powertrain_type = val
                        elif param_name in ["级别"]:
                            trim.category_bottom = val
                        elif param_name in ["车款名称"]:
                            trim.trim_name = val

        trims_list = list(trims_map.values())
        return RawSerialSpecSheet(
            brand=brand,
            serial=detected_serial_name,
            serial_slug=serial_slug,
            total_trims=len(trims_list),
            categories=categories,
            trims=trims_list,
        )

    def _parse_html_table(
        self,
        html: str,
        brand: str,
        serial_slug: str,
        serial_name: Optional[str],
    ) -> RawSerialSpecSheet:
        """Parse HTML table from rendered configuration page as fallback."""
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            return RawSerialSpecSheet(brand=brand, serial=serial_name or serial_slug, serial_slug=serial_slug)

        table = tables[0]
        rows = table.find_all("tr")
        if not rows:
            return RawSerialSpecSheet(brand=brand, serial=serial_name or serial_slug, serial_slug=serial_slug)

        header_row = rows[0]
        trim_cells = header_row.find_all(["th", "td"])[1:]
        trims: List[RawVehicleTrim] = []

        for cell in trim_cells:
            text = cell.get_text("\n").strip()
            lines = [l.strip() for l in text.split("\n") if l.strip() and "对比" not in l and "底价" not in l]
            trim_title = lines[0] if lines else f"{serial_name or serial_slug} 款型"
            price_str = lines[1] if len(lines) > 1 else ""

            trims.append(
                RawVehicleTrim(
                    brand=brand,
                    serial=serial_name or serial_slug,
                    serial_slug=serial_slug,
                    trim_name=trim_title,
                    price_guide=price_str,
                )
            )

        current_category = "基本信息"
        categories = [current_category]

        for r in rows[1:]:
            cells = r.find_all(["th", "td"])
            if not cells:
                continue
            if len(cells) == 1:
                cat = cells[0].get_text().strip()
                if cat:
                    current_category = cat
                    if cat not in categories:
                        categories.append(cat)
                continue

            param_name = re.sub(r"\s+", " ", cells[0].get_text().strip())
            if not param_name:
                continue

            for idx, vc in enumerate(cells[1:]):
                if idx < len(trims):
                    val = vc.get_text(" ").strip().replace("●", "标配").replace("○", "选配").replace("-", "无")
                    if current_category not in trims[idx].specs:
                        trims[idx].specs[current_category] = {}
                    trims[idx].specs[current_category][param_name] = val

                    if param_name in ["厂商指导价", "指导价"]:
                        trims[idx].price_guide = val
                    elif param_name in ["能源类型"]:
                        trims[idx].powertrain_type = val
                    elif param_name in ["级别"]:
                        trims[idx].category_bottom = val

        return RawSerialSpecSheet(
            brand=brand,
            serial=serial_name or serial_slug,
            serial_slug=serial_slug,
            total_trims=len(trims),
            categories=categories,
            trims=trims,
        )

    async def crawl_brand_serials(
        self,
        serials_map: Optional[Dict[str, str]] = None,
        brand: str = "比亚迪",
        delay_seconds: float = 1.5,
    ) -> CrawlSummary:
        """
        Crawl all specified car series under a brand.
        """
        start_time = time.time()
        serials = serials_map or BYD_DEFAULT_SERIALS
        total_trims = 0
        failed = []

        logger.info(f"Starting batch crawl for brand [{brand}] ({len(serials)} series)...")

        for slug, name in serials.items():
            try:
                sheet = await self.crawl_serial(serial_slug=slug, serial_name=name, brand=brand)
                if sheet:
                    total_trims += sheet.total_trims
                else:
                    failed.append(slug)
            except Exception as e:
                logger.error(f"Error crawling series {slug} ({name}): {e}")
                failed.append(slug)

            # Jitter delay
            await asyncio.sleep(delay_seconds)

        elapsed = time.time() - start_time
        summary = CrawlSummary(
            brand=brand,
            total_serials=len(serials) - len(failed),
            total_trims=total_trims,
            failed_serials=failed,
            elapsed_seconds=round(elapsed, 2),
            output_directory=str(self.storage.raw_dir),
        )

        logger.info(
            f"Batch crawl finished in {elapsed:.1f}s: {summary.total_serials} series succeeded, "
            f"{total_trims} vehicle trims extracted. Failed: {len(failed)}"
        )
        return summary
