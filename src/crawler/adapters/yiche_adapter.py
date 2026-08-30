"""
Yiche.com (易车网) Enterprise Dynamic Site Adapter.
Includes automated anti-bot avoidance, dynamic context recycling, session priming,
and multi-brand full-spectrum serial discovery.
"""

import asyncio
import json
import random
import re
import urllib.parse
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.crawler.adapters.base_adapter import BaseSiteAdapter
from src.crawler.schemas import BrandMeta, RawSerialSpecSheet, RawVehicleTrim, SerialMeta
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Master brand canonical dictionary (Dynamic fallback + brand slug normalization)
CANONICAL_BRAND_SLUGS = {
    "比亚迪": "byd",
    "特斯拉": "tesla",
    "理想": "li_auto",
    "蔚来": "nio",
    "小鹏": "xpeng",
    "极氪": "zeekr",
    "小米": "xiaomi",
    "问界": "aito",
    "零跑": "leapmotor",
    "腾势": "tengshi",
    "仰望": "yangwang",
    "方程豹": "fangchengbao",
    "吉利": "geely",
    "极狐": "arcfox",
    "智己": "im_motors",
    "阿维塔": "avatar",
    "大众": "volkswagen",
    "奥迪": "audi",
    "宝马": "bmw",
    "奔驰": "mercedes_benz",
    "丰田": "toyota",
    "本田": "honda",
    "长安": "changan",
    "长城": "gwm",
    "奇瑞": "chery",
    "红旗": "hongqi",
    "埃安": "aion",
    "别克": "buick",
    "保时捷": "porsche",
    "标致": "peugeot",
    "标志": "peugeot",
    "宝骏": "baojun",
    "宾利": "bentley",
    "布加迪": "bugatti",
    "长安启源": "changanqiyuan",
    "长安凯程": "changankaicheng",
    "长安欧尚": "changanoushang",
    "长安跨越": "changanhuayue",
    "东风风神": "dongfengfengshen",
    "东风奕派": "dongfengepai",
    "东风风行": "dongfengfengxing",
    "道奇": "dodge",
    "大运": "dayun",
    "高合": "hiphi",
    "鸿蒙智行": "hongmengzhixing",
    "哈弗": "haval",
    "华境": "huajing",
    "悍马": "hummer",
    "捷豹": "jaguar",
    "捷达": "jetta",
    "捷尼赛思": "genesis",
    "金杯": "jinbei",
    "五菱": "sgmw",
    "五菱汽车": "sgmw",
    "吉利几何": "geely_geometry",
    "几何汽车": "geely_geometry",
    "铃木": "suzuki",
    "雷诺": "renault",
    "力帆": "lifan",
    "力帆汽车": "lifan",
    "莲花": "lotus",
    "莲花跑车": "lotus",
    "路特斯": "lotus",
    "迈巴赫": "maybach",
    "玛莎拉蒂": "maserati",
    "MG": "mg",
    "mg": "mg",
    "名爵": "mg",
    "马自达": "mazda",
    "迈凯伦": "mclaren",
    "帕加尼": "pagani",
    "启境": "qijing",
    "日产": "nissan",
    "深蓝": "shenlan",
    "深蓝汽车": "shenlan",
    "尚界": "shangjie",
    "沃尔沃": "volvo",
    "魏牌": "weypai",
    "享界": "xiangjie",
    "雪佛兰": "chevrolet",
    "福特": "ford",
    "现代": "hyundai",
    "凯迪拉克": "cadillac",
    "路虎": "land_rover",
    "兰博基尼": "lamborghini",
    "劳斯莱斯": "rolls_royce",
    "雪铁龙": "citroen",
}

# Brand official hub pages on car.yiche.com
BRAND_HUB_MAP = {
    "比亚迪": "bydauto",
    "理想": "li",
    "零跑": "leapmotor",
    "方程豹": "biyadifpinpai",
    "五菱": "sgmw",
    "五菱汽车": "sgmw",
    "别克": "buick",
    "保时捷": "porsche",
    "标致": "peugeot",
    "宝骏": "baojun",
    "宾利": "bentley",
    "布加迪": "bugatti",
    "哈弗": "hafu-196",
    "捷豹": "jaguar",
    "捷达": "jetta",
    "捷尼赛思": "genesis",
    "MG": "mg-79",
    "名爵": "mg-79",
    "马自达": "mazda",
    "迈凯伦": "mclaren",
    "玛莎拉蒂": "maserati",
    "日产": "nissan",
    "沃尔沃": "volvo",
    "雪佛兰": "chevrolet",
    "鸿蒙智行": "hongmengzhixing",
    "长安启源": "changanqiyuan",
    "福特": "ford",
    "现代": "hyundai",
    "凯迪拉克": "cadillac",
    "路虎": "landrover",
    "兰博基尼": "lamborghini",
    "劳斯莱斯": "rollsroyce",
    "雪铁龙": "citroen",
}

GENERIC_EXCLUDE_SLUGS = {
    "lease", "cheshi", "pingce", "daogou", "global", "gouchejisuanqi",
    "qichedaikuanjisuanqi", "sell", "download", "publiccms", "brandsales",
    "about", "contact", "legal-notices", "yiche", "wap", "xuanche", "peizhi",
    "tuku", "wenda", "baojia", "kouchai", "elec", "chexingduibi", "newcar",
    "yuanchuang", "index", "bydauto", "volkswagen", "toyota", "mercedesbenz",
    "bmw", "audi", "sgmw", "honda", "hongmengzhixing", "yinhe", "nissan",
    "chery", "geely", "mg-79", "qiruifengyun", "biyadifpinpai", "buick",
    "faw-hongqi", "hafu-196", "ford", "gq", "cajc", "audi-819", "leapmotor", "li",
    "xiaopengqiche", "weilaiqiche", "jike", "xiaomiqiche"
}


class YicheSiteAdapter(BaseSiteAdapter):
    """Enterprise Yiche Site Adapter with automatic context recycling and anti-bot evasions."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._is_initialized = False
        self._request_count = 0
        self._max_requests_per_context = 15  # Anti-leak and anti-tracking context recycling

    async def initialize(self) -> None:
        """Start Playwright and initialize stealth context."""
        if self._is_initialized and self._page:
            return

        if not self._pw:
            self._pw = await async_playwright().start()

        if not self._browser:
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

        await self._create_stealth_context()
        self._is_initialized = True

    async def _create_stealth_context(self) -> None:
        """Create fresh browser context with stealth scripts and primed cookies."""
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass

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
        self._request_count = 0

        # Prime cookies
        try:
            await self._page.goto("https://www.yiche.com/", wait_until="domcontentloaded", timeout=15000)
            await self._page.wait_for_timeout(1500)
            logger.info("Yiche session primed successfully.")
        except Exception as e:
            logger.warning(f"Session priming warning: {e}")

    async def _check_and_recycle_context(self) -> None:
        """Recycle browser context if request threshold reached to prevent memory growth & bot detection."""
        self._request_count += 1
        if self._request_count >= self._max_requests_per_context:
            logger.info(f"Recycling browser context (handled {self._request_count} requests)...")
            await self._create_stealth_context()

    async def close(self) -> None:
        """Clean up browser resources."""
        if self._page:
            try:
                await self._page.close()
            except Exception:
                pass
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass
        self._is_initialized = False

    async def discover_all_brands(self) -> List[BrandMeta]:
        """Dynamically discover all 700+ automotive brands from live car.yiche.com site."""
        if not self._is_initialized:
            await self.initialize()

        page = self._page
        await page.goto("https://car.yiche.com/", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(random.uniform(1500, 2000))

        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        brands = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            txt = a.get_text().strip()
            m = re.search(r"mid=(\d+)", href)
            if m and txt and len(txt) < 20 and not any(k in txt for k in ["车型", "排行榜", "计算器", "选车"]):
                if txt not in seen:
                    seen.add(txt)
                    mid = m.group(1)
                    slug = CANONICAL_BRAND_SLUGS.get(txt, f"brand_{mid}")
                    brands.append(BrandMeta(name=txt, slug=slug, master_id=mid))

        logger.info(f"Dynamically discovered {len(brands)} automotive brands from live site.")
        return brands

    async def discover_serials_by_brand(self, brand: BrandMeta) -> List[SerialMeta]:
        """Dynamically resolve all car series for ANY brand from live Master Tree."""
        if not self._is_initialized:
            await self.initialize()

        b_slug = brand.slug or CANONICAL_BRAND_SLUGS.get(brand.name, brand.name.lower())
        serials_dict: Dict[str, SerialMeta] = {}

        # 1. Dynamic extraction via Brand Hub Page (e.g. /leapmotor/, /li/, /bydauto/, /jike/)
        try:
            await self._check_and_recycle_context()
            page = self._page

            brand_hub_slugs = []
            if brand.name in BRAND_HUB_MAP:
                brand_hub_slugs.append(BRAND_HUB_MAP[brand.name])
            if b_slug in BRAND_HUB_MAP.values():
                brand_hub_slugs.append(b_slug)
            brand_hub_slugs.extend([
                b_slug,
                brand.name.lower().replace(" ", ""),
            ])

            for hub_slug in set(s for s in brand_hub_slugs if s):
                hub_url = f"https://car.yiche.com/{hub_slug}/"
                await page.goto(hub_url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(random.uniform(1500, 2000))

                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                for a in soup.find_all("a", href=True):
                    href = a.get("href")
                    txt = a.get_text().strip()
                    m = re.search(r"/([a-zA-Z0-9_\-]+)/?$", href)
                    if m:
                        s_slug = m.group(1)
                        if s_slug not in GENERIC_EXCLUDE_SLUGS and s_slug != hub_slug:
                            if txt and len(txt) < 25 and not any(k in txt for k in ["论坛", "二手车", "图片", "报价", "口碑", "降价", "文章", "参数", "分期", "关于", "联系", "法律", "客户端", "估值", "计算器", "金融", "车市", "评测", "导购", "国际站", "出版", "榜单"]):
                                if s_slug not in serials_dict:
                                    serials_dict[s_slug] = SerialMeta(
                                        brand_name=brand.name,
                                        brand_slug=b_slug,
                                        serial_name=txt,
                                        serial_slug=s_slug,
                                    )
                if serials_dict:
                    logger.info(f"Brand Hub ({hub_url}) extracted {len(serials_dict)} series dynamically for [{brand.name}]")
                    break
        except Exception as e:
            logger.warning(f"Brand Hub dynamic discovery note for {brand.name}: {e}")

        # 2. Dynamic extraction via official Brand MID tree
        try:
            mid = brand.master_id
            if not mid:
                # Fast lookup from local cached brands file if present
                import os
                if os.path.exists("data/yiche_all_brands.json"):
                    try:
                        with open("data/yiche_all_brands.json", "r", encoding="utf-8") as f:
                            all_b = json.load(f)
                        for item in all_b:
                            if item["name"] == brand.name or brand.name in item["name"]:
                                mid = str(item["mid"])
                                break
                    except Exception:
                        pass

            if not mid:
                await page.goto("https://car.yiche.com/", wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(1000)
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                for a in soup.find_all("a", href=True):
                    txt = a.get_text().strip()
                    if txt == brand.name or (brand.name in txt and len(txt) <= len(brand.name) + 2):
                        m = re.search(r"mid=(\d+)", a.get("href", ""))
                        if m:
                            mid = m.group(1)
                            break

            if mid:
                url = f"https://car.yiche.com/xuanchegongju/?mid={mid}"
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(random.uniform(1500, 2000))

                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                for a in soup.find_all("a", href=True):
                    href = a.get("href")
                    m = re.search(r"(?:car\.yiche\.com)?/([a-zA-Z0-9_\-]+)(?:/peizhi)?/?$", href)
                    if m:
                        slug = m.group(1)
                        if (
                            slug not in GENERIC_EXCLUDE_SLUGS
                            and not slug.startswith("photolist")
                            and not slug.startswith("tuku")
                            and not slug.startswith("news")
                            and not slug.startswith("video")
                            and slug not in ["xuanchegongju", "elec", "newcar", "cheshi", "pingce", "daogou", "global", "sell", "download", "publiccms", "brandsales", "wenda", "tuku", "baojia", "salesrank", "xinche", "qichebaojiadaquan", "app", "login", "register"]
                        ):
                            parent = a.find_parent("div") or a.find_parent("li")
                            txt = parent.get_text(" ").strip() if parent else slug
                            lines = [l.strip() for l in txt.split() if l.strip() and "参数" not in l and "图片" not in l and "文章" not in l and "二手车" not in l and "询底价" not in l and "未上市" not in l and "暂无" not in l and "app" not in l.lower()]
                            name = lines[0] if lines else slug
                            if len(name) < 30 and not any(k in name for k in ["易车", "下载", "排行榜", "销量", "计算器", "对比", "降价"]) and slug not in serials_dict:
                                serials_dict[slug] = SerialMeta(
                                    brand_name=brand.name,
                                    brand_slug=b_slug,
                                    serial_name=name,
                                    serial_slug=slug,
                                )
                logger.info(f"MID Tree extracted {len(serials_dict)} total series for [{brand.name}] (mid={mid})")
        except Exception as e:
            logger.warning(f"MID dynamic tree discovery note for {brand.name}: {e}")

        # 3. Dynamic extraction via Semantic Search Route (e.g. /chexing/{brand}/)
        try:
            search_url = f"https://so.yiche.com/chexing/{urllib.parse.quote(brand.name)}/"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(random.uniform(1500, 2000))

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a.get("href")
                txt = a.get_text().strip()
                m = re.search(r"car\.yiche\.com/([a-zA-Z0-9_\-]+)/?$", href)
                if m:
                    slug = m.group(1)
                    if (
                        slug not in GENERIC_EXCLUDE_SLUGS
                        and not slug.startswith("photolist")
                        and not slug.startswith("tuku")
                        and slug not in ["xuanchegongju", "elec", "newcar", "cheshi", "pingce", "daogou", "global", "sell", "download", "publiccms", "brandsales", "wenda", "tuku", "baojia", "salesrank", "xinche", "qichebaojiadaquan"]
                        and slug not in serials_dict
                    ):
                        if txt and len(txt) < 30 and not any(k in txt for k in ["论坛", "二手车", "图片", "报价", "口碑", "降价", "文章", "参数", "分期", "关于", "联系", "app", "易车", "计算器", "排行榜"]):
                            clean_name = txt.split()[0] if txt.split() else txt
                            serials_dict[slug] = SerialMeta(
                                brand_name=brand.name,
                                brand_slug=b_slug,
                                serial_name=clean_name,
                                serial_slug=slug,
                            )
            logger.info(f"Tri-Channel dynamic discovery yielded {len(serials_dict)} total series for [{brand.name}]")
        except Exception as e:
            logger.warning(f"Semantic Search dynamic discovery note for {brand.name}: {e}")

        logger.info(f"Discovered {len(serials_dict)} total series dynamically for brand [{brand.name}]")
        return list(serials_dict.values())

    async def extract_serial_full_specs(
        self,
        serial: SerialMeta,
        include_discontinued: bool = True,
    ) -> Optional[RawSerialSpecSheet]:
        """Extract full multi-tiered specification sheet with exhaustive year & discontinued penetration."""
        if not self._is_initialized:
            await self.initialize()

        await self._check_and_recycle_context()
        page = self._page
        target_url = f"https://car.yiche.com/{serial.serial_slug}/peizhi/"
        logger.info(f"Extracting specs for [{serial.serial_name}] ({serial.serial_slug})...")

        intercepted_payloads = []

        async def on_response(response):
            if "get_param_details" in response.url:
                try:
                    data = await response.json()
                    if data.get("status") == "1" and data.get("data"):
                        intercepted_payloads.append(data)
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
            # Wait for dynamic network response or initial table
            for _ in range(16):
                if intercepted_payloads:
                    break
                await page.wait_for_timeout(250)
            await page.wait_for_timeout(random.uniform(1500, 2500))
        except Exception as e:
            logger.warning(f"Navigation warning for {target_url}: {e}")

        # Exhaustive year & discontinued model penetration
        if include_discontinued:
            try:
                year_buttons = await page.query_selector_all(
                    ".year-box a, .drop-down a, [class*='year'] a, button[class*='year'], li[class*='year'], a[class*='tab'], span[class*='tab']"
                )
                seen_btn_text = set()
                for btn in year_buttons:
                    try:
                        txt = (await btn.inner_text()).strip()
                        if re.search(r"20\d\d|停售|全部|未上市|预售", txt) and len(txt) < 15 and txt not in seen_btn_text:
                            seen_btn_text.add(txt)
                            await btn.click()
                            await page.wait_for_timeout(random.uniform(1200, 1800))
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Year penetration note for {serial.serial_slug}: {e}")

        # Primary: Multi-payload merging
        if intercepted_payloads:
            sheet = self._parse_multiple_api_payloads(intercepted_payloads, serial)
            if sheet and sheet.total_trims > 0:
                return sheet

        # Fallback: HTML table
        html = await page.content()
        sheet = self._parse_html_table(html, serial)
        if sheet and sheet.total_trims > 0:
            return sheet

        return None

    def _parse_api_payload(self, payload: Dict[str, Any], serial: SerialMeta) -> RawSerialSpecSheet:
        """Parse single get_param_details JSON payload (wrapper around multi-payload parser)."""
        return self._parse_multiple_api_payloads([payload], serial)

    def _parse_multiple_api_payloads(
        self, payloads: List[Dict[str, Any]], serial: SerialMeta
    ) -> RawSerialSpecSheet:
        """Merge multiple get_param_details JSON payloads across all historical & upcoming years."""
        merged_trims: Dict[str, RawVehicleTrim] = {}
        all_categories: List[str] = []
        detected_serial_name = serial.serial_name

        for payload in payloads:
            data = payload.get("data", {})
            param_groups = data.get("list", [])
            for group in param_groups:
                g_name = group.get("name", "未分类")
                if g_name not in all_categories:
                    all_categories.append(g_name)

                for item in group.get("items", []):
                    p_name = item.get("name", "").strip()
                    for pv in item.get("paramValues", []):
                        car_id = str(pv.get("id"))
                        val = str(pv.get("value", "")).strip()

                        if car_id not in merged_trims:
                            base_key_str = pv.get("baseInfoKey", "{}")
                            try:
                                base_info = json.loads(base_key_str) if isinstance(base_key_str, str) else base_key_str
                                detected_serial_name = base_info.get("serialName", detected_serial_name)
                            except Exception:
                                pass

                            merged_trims[car_id] = RawVehicleTrim(
                                car_id=car_id,
                                brand=serial.brand_name,
                                brand_slug=serial.brand_slug,
                                serial=detected_serial_name,
                                serial_slug=serial.serial_slug,
                                trim_name=val,
                                raw_api_payload=pv,
                            )

                        if p_name:
                            merged_trims[car_id].specs.setdefault(g_name, {})[p_name] = val
                            if p_name in ["指导价", "厂商指导价", "厂商指导价(元)"]:
                                merged_trims[car_id].price_guide = val
                            elif p_name in ["参考价", "经销商参考价"]:
                                merged_trims[car_id].price_reference = val
                            elif p_name in ["年款", "上市年份"]:
                                merged_trims[car_id].year = val
                            elif p_name in ["能源类型", "动力类型"]:
                                merged_trims[car_id].powertrain_type = val
                            elif p_name in ["级别", "车身结构"]:
                                merged_trims[car_id].category_bottom = val

        return RawSerialSpecSheet(
            brand=serial.brand_name,
            brand_slug=serial.brand_slug,
            serial=detected_serial_name,
            serial_slug=serial.serial_slug,
            total_trims=len(merged_trims),
            categories=all_categories,
            trims=list(merged_trims.values()),
        )

    def _parse_html_table(self, html: str, serial: SerialMeta) -> RawSerialSpecSheet:
        """Parse HTML table fallback."""
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            return RawSerialSpecSheet(
                brand=serial.brand_name,
                brand_slug=serial.brand_slug,
                serial=serial.serial_name,
                serial_slug=serial.serial_slug,
            )

        table = tables[0]
        rows = table.find_all("tr")
        if not rows:
            return RawSerialSpecSheet(
                brand=serial.brand_name,
                brand_slug=serial.brand_slug,
                serial=serial.serial_name,
                serial_slug=serial.serial_slug,
            )

        header_row = rows[0]
        trim_cells = header_row.find_all(["th", "td"])[1:]
        trims: List[RawVehicleTrim] = []

        for cell in trim_cells:
            text = cell.get_text("\n").strip()
            lines = [l.strip() for l in text.split("\n") if l.strip() and "对比" not in l and "底价" not in l]
            trim_title = lines[0] if lines else f"{serial.serial_name} 款型"
            price_str = lines[1] if len(lines) > 1 else ""

            trims.append(
                RawVehicleTrim(
                    brand=serial.brand_name,
                    brand_slug=serial.brand_slug,
                    serial=serial.serial_name,
                    serial_slug=serial.serial_slug,
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
            brand=serial.brand_name,
            brand_slug=serial.brand_slug,
            serial=serial.serial_name,
            serial_slug=serial.serial_slug,
            total_trims=len(trims),
            categories=categories,
            trims=trims,
        )
