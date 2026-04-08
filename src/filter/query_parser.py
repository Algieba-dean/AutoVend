"""
规则引擎意图解析器

将用户自然语言查询解析为结构化查询 dict，供 FilterEngine 使用。
支持中英文价格、品牌、车型、功能、性能等关键词提取。
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from src.filter.label_registry import LabelRegistry
from src.utils.logger import get_logger


class ParsedQuery:
    """解析结果"""

    def __init__(self):
        self.conditions: Dict[str, Any] = {}
        self.raw_text: str = ""
        self.matched_keywords: List[str] = []
        self.unmatched_text: str = ""

    def add(self, key: str, value: Any) -> None:
        self.conditions[key] = value

    def add_keyword(self, keyword: str) -> None:
        self.matched_keywords.append(keyword)

    def is_empty(self) -> bool:
        return len(self.conditions) == 0

    def __repr__(self) -> str:
        return f"ParsedQuery({self.conditions})"


# ======================================================================
# 中英文品牌别名
# ======================================================================
BRAND_ALIASES: Dict[str, str] = {
    # 中文 → 英文小写
    "奔驰": "mercedes-benz",
    "梅赛德斯": "mercedes-benz",
    "宝马": "bmw",
    "奥迪": "audi",
    "大众": "volkswagen",
    "保时捷": "porsche",
    "宾利": "bentley",
    "布加迪": "bugatti",
    "兰博基尼": "lamborghini",
    "捷豹": "jaguar",
    "路虎": "land rover",
    "劳斯莱斯": "rolls-royce",
    "沃尔沃": "volvo",
    "标致": "peugeot",
    "雷诺": "renault",
    "雪佛兰": "chevrolet",
    "别克": "buick",
    "凯迪拉克": "cadillac",
    "福特": "ford",
    "特斯拉": "tesla",
    "丰田": "toyota",
    "本田": "honda",
    "日产": "nissan",
    "铃木": "suzuki",
    "马自达": "mazda",
    "现代": "hyundai",
    "比亚迪": "byd",
    "吉利": "geely",
    "长安": "changan",
    "长城": "great wall motor",
    "哈弗": "great wall motor",
    "蔚来": "nio",
    "小米": "xiaomi",
    "小鹏": "xpeng",
    # 英文缩写/变体
    "benz": "mercedes-benz",
    "mercedes": "mercedes-benz",
    "vw": "volkswagen",
    "landrover": "land rover",
    "rolls royce": "rolls-royce",
    "rollsroyce": "rolls-royce",
}

# ======================================================================
# 车型层级关键词
# ======================================================================
CATEGORY_ALIASES: Dict[str, Tuple[str, str]] = {
    # 中/英文 → (tree_level_key, tree_value)
    "轿车": ("vehicle_category_top", "sedan"),
    "sedan": ("vehicle_category_top", "sedan"),
    "suv": ("vehicle_category_top", "suv"),
    "越野": ("vehicle_category_top", "suv"),
    "越野车": ("vehicle_category_top", "suv"),
    "mpv": ("vehicle_category_top", "mpv"),
    "商务车": ("vehicle_category_top", "mpv"),
    "跑车": ("vehicle_category_top", "sports car"),
    "sports car": ("vehicle_category_top", "sports car"),
    "敞篷": ("vehicle_category_middle", "convertible sports car"),
    "敞篷车": ("vehicle_category_middle", "convertible sports car"),
    "硬顶跑车": ("vehicle_category_middle", "hardtop sports car"),
    # 尺寸
    "小型轿车": ("vehicle_category_middle", "small sedan"),
    "紧凑型轿车": ("vehicle_category_bottom", "compact sedan"),
    "中型轿车": ("vehicle_category_middle", "mid-size sedan"),
    "中大型轿车": ("vehicle_category_middle", "mid-large sedan"),
    "紧凑型suv": ("vehicle_category_bottom", "compact suv"),
    "紧凑suv": ("vehicle_category_bottom", "compact suv"),
    "中型suv": ("vehicle_category_bottom", "mid-size suv"),
    "中大型suv": ("vehicle_category_bottom", "mid-to-large suv"),
    "越野suv": ("vehicle_category_bottom", "off-road suv"),
    "硬派越野": ("vehicle_category_bottom", "off-road suv"),
    "全地形": ("vehicle_category_bottom", "all-terrain suv"),
    "家用mpv": ("vehicle_category_middle", "family mpv"),
    "商务mpv": ("vehicle_category_middle", "business mpv"),
    # 地区
    "欧洲车": ("brand_area", "european"),
    "德系": ("brand_country", "germany"),
    "德国车": ("brand_country", "germany"),
    "法系": ("brand_country", "france"),
    "英系": ("brand_country", "united kingdom"),
    "瑞典车": ("brand_country", "sweden"),
    "美系": ("brand_country", "usa"),
    "美国车": ("brand_country", "usa"),
    "日系": ("brand_country", "japan"),
    "日本车": ("brand_country", "japan"),
    "韩系": ("brand_country", "korea"),
    "国产": ("brand_country", "china"),
    "国产车": ("brand_country", "china"),
    "自主品牌": ("brand_country", "china"),
    "中国品牌": ("brand_country", "china"),
}

# ======================================================================
# 功能 / 性能关键词 → 标签映射
# ======================================================================
FEATURE_KEYWORDS: Dict[str, Tuple[str, Any]] = {
    # 动力类型
    "电动": ("powertrain_type", "battery electric vehicle"),
    "纯电": ("powertrain_type", "battery electric vehicle"),
    "纯电动": ("powertrain_type", "battery electric vehicle"),
    "bev": ("powertrain_type", "battery electric vehicle"),
    "ev": ("powertrain_type", "battery electric vehicle"),
    "electric": ("powertrain_type", "battery electric vehicle"),
    "混动": ("powertrain_type", "hybrid electric vehicle"),
    "油电混合": ("powertrain_type", "hybrid electric vehicle"),
    "插电混动": ("powertrain_type", "plug-in hybrid electric vehicle"),
    "插混": ("powertrain_type", "plug-in hybrid electric vehicle"),
    "phev": ("powertrain_type", "plug-in hybrid electric vehicle"),
    "增程": ("powertrain_type", "range-extended electric vehicle"),
    "增程式": ("powertrain_type", "range-extended electric vehicle"),
    "汽油": ("powertrain_type", "gasoline engine"),
    "燃油": ("powertrain_type", "gasoline engine"),
    "柴油": ("powertrain_type", "diesel engine"),
    # 座位
    "两座": ("seat_layout", "2-seat"),
    "2座": ("seat_layout", "2-seat"),
    "四座": ("seat_layout", "4-seat"),
    "4座": ("seat_layout", "4-seat"),
    "五座": ("seat_layout", "5-seat"),
    "5座": ("seat_layout", "5-seat"),
    "六座": ("seat_layout", "6-seat"),
    "6座": ("seat_layout", "6-seat"),
    "七座": ("seat_layout", "7-seat"),
    "7座": ("seat_layout", "7-seat"),
    "7-seat": ("seat_layout", "7-seat"),
    # 驱动
    "四驱": ("drive_type", "all-wheel drive"),
    "全驱": ("drive_type", "all-wheel drive"),
    "awd": ("drive_type", "all-wheel drive"),
    "4wd": ("drive_type", "all-wheel drive"),
    "前驱": ("drive_type", "front-wheel drive"),
    "fwd": ("drive_type", "front-wheel drive"),
    "后驱": ("drive_type", "rear-wheel drive"),
    "rwd": ("drive_type", "rear-wheel drive"),
    # 风格
    "运动": ("design_style", "sporty"),
    "运动风": ("design_style", "sporty"),
    "sporty": ("design_style", "sporty"),
    "商务": ("design_style", "business"),
    "商务风": ("design_style", "business"),
    # 布尔功能
    "自动泊车": ("auto_parking", "yes"),
    "远程泊车": ("remote_parking", "yes"),
    "自动驾驶": ("autonomous_driving_level", "l3"),
    "辅助驾驶": ("autonomous_driving_level", "l2"),
    "l2": ("autonomous_driving_level", "l2"),
    "l3": ("autonomous_driving_level", "l3"),
    "语音控制": ("voice_interaction", "yes"),
    "语音交互": ("voice_interaction", "yes"),
    "ota": ("ota_updates", "yes"),
    "自动刹车": ("automatic_emergency_braking", "yes"),
    "aeb": ("automatic_emergency_braking", "yes"),
    "车道保持": ("lane_keep_assist", "yes"),
    "盲区监测": ("blind_spot_detection", "yes"),
    "疲劳检测": ("fatigue_driving_detection", "yes"),
    "巡航": ("adaptive_cruise_control", "yes"),
    "acc": ("adaptive_cruise_control", "yes"),
    "真皮座椅": ("seat_material", "leather"),
    "真皮": ("seat_material", "leather"),
    "织物座椅": ("seat_material", "fabric"),
    # 用途
    "城市通勤": ("city_commuting", "yes"),
    "通勤": ("city_commuting", "yes"),
    "长途": ("highway_long_distance", "yes"),
    "高速": ("highway_long_distance", "yes"),
    "拉货": ("cargo_capability", "yes"),
    "载货": ("cargo_capability", "yes"),
}

# ======================================================================
# 性能别名关键词（映射到 range label alias）
# ======================================================================
PERFORMANCE_ALIASES: Dict[str, Tuple[str, str, str]] = {
    # keyword → (label_name, op, alias_value)
    "省油": ("fuel_consumption", "lte", "low"),
    "油耗低": ("fuel_consumption", "lte", "low"),
    "费油": ("fuel_consumption", "gte", "high"),
    "省电": ("electric_consumption", "lte", "low"),
    "快": ("zero_to_one_hundred_km_h_acceleration_time", "lte", "fast"),
    "加速快": ("zero_to_one_hundred_km_h_acceleration_time", "lte", "fast"),
    "动力强": ("horsepower", "gte", "high"),
    "动力强劲": ("horsepower", "gte", "high"),
    "大马力": ("horsepower", "gte", "high"),
    "高速度": ("top_speed", "gte", "high"),
    "长续航": ("driving_range", "gte", "long"),
    "续航长": ("driving_range", "gte", "long"),
    "大空间": ("passenger_space_volume", "gte", "large"),
    "空间大": ("passenger_space_volume", "gte", "large"),
    "大后备箱": ("trunk_volume", "gte", "large"),
    "底盘高": ("chassis_height", "gte", "high ride height"),
    "低底盘": ("chassis_height", "lte", "low ride height"),
}


class QueryParser:
    """
    规则引擎查询解析器

    将用户自然语言解析为结构化查询 dict。
    """

    def __init__(self, registry: Optional[LabelRegistry] = None):
        self.logger = get_logger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self.registry = registry or LabelRegistry()

    def parse(self, text: str) -> ParsedQuery:
        """
        解析用户查询文本

        Args:
            text: 用户原始查询文本

        Returns:
            ParsedQuery 结构化结果
        """
        result = ParsedQuery()
        result.raw_text = text
        remaining = text.lower().strip()

        # 1. 价格提取
        remaining = self._extract_price(remaining, result)

        # 2. 品牌提取
        remaining = self._extract_brand(remaining, result)

        # 3. 车型/地区提取
        remaining = self._extract_category(remaining, result)

        # 4. 功能/特性提取
        remaining = self._extract_features(remaining, result)

        # 5. 性能别名提取
        remaining = self._extract_performance(remaining, result)

        result.unmatched_text = remaining.strip()
        return result

    # ------------------------------------------------------------------
    # 价格解析
    # ------------------------------------------------------------------

    def _extract_price(self, text: str, result: ParsedQuery) -> str:
        """提取价格信息"""
        # 中文：X万 ~ Y万 / X-Y万 / X到Y万
        patterns_cn = [
            # "20万到30万" / "20-30万" / "20~30万"
            r"(\d+(?:\.\d+)?)\s*[万w]\s*[到至~\-]\s*(\d+(?:\.\d+)?)\s*[万w]",
            # "20到30万" / "20-30万"
            r"(\d+(?:\.\d+)?)\s*[到至~\-]\s*(\d+(?:\.\d+)?)\s*[万w]",
            # "预算X万" / "X万左右" / "X万以内"
            r"(?:预算|budget)\s*(\d+(?:\.\d+)?)\s*[万w]",
            r"(\d+(?:\.\d+)?)\s*[万w]\s*(?:左右|上下)",
            r"(\d+(?:\.\d+)?)\s*[万w]\s*(?:以内|以下|内)",
            r"(\d+(?:\.\d+)?)\s*[万w]\s*(?:以上|起)",
            # 单独 "X万"
            r"(\d+(?:\.\d+)?)\s*[万w]",
        ]

        # 英文：$Xk, X,000
        patterns_en = [
            r"\$?\s*(\d+(?:\.\d+)?)\s*k\s*[~\-to]+\s*\$?\s*(\d+(?:\.\d+)?)\s*k",
            r"(\d{1,3}(?:,\d{3})+)\s*[~\-to]+\s*(\d{1,3}(?:,\d{3})+)",
            r"(?:budget|under|below)\s*\$?\s*(\d+(?:\.\d+)?)\s*k",
            r"(?:above|over|from)\s*\$?\s*(\d+(?:\.\d+)?)\s*k",
        ]

        # 中文价格区间
        for pattern in patterns_cn[:2]:
            m = re.search(pattern, text)
            if m:
                min_val = float(m.group(1)) * 1000
                max_val = float(m.group(2)) * 1000
                result.add(
                    "prize",
                    {
                        "op": "between",
                        "min": self._price_to_bucket(min_val),
                        "max": self._price_to_bucket(max_val),
                    },
                )
                result.add_keyword(m.group(0))
                return text[: m.start()] + text[m.end() :]

        # 预算 / 左右
        m = re.search(patterns_cn[2], text) or re.search(patterns_cn[3], text)
        if m:
            val = float(m.group(1)) * 1000
            lo = self._price_to_bucket(val * 0.8)
            hi = self._price_to_bucket(val * 1.2)
            result.add("prize", {"op": "between", "min": lo, "max": hi})
            result.add_keyword(m.group(0))
            return text[: m.start()] + text[m.end() :]

        # 以内/以下
        m = re.search(patterns_cn[4], text)
        if m:
            val = float(m.group(1)) * 1000
            result.add(
                "prize",
                {
                    "op": "lte",
                    "value": self._price_to_bucket(val),
                },
            )
            result.add_keyword(m.group(0))
            return text[: m.start()] + text[m.end() :]

        # 以上/起
        m = re.search(patterns_cn[5], text)
        if m:
            val = float(m.group(1)) * 1000
            result.add(
                "prize",
                {
                    "op": "gte",
                    "value": self._price_to_bucket(val),
                },
            )
            result.add_keyword(m.group(0))
            return text[: m.start()] + text[m.end() :]

        # 单独 X万
        m = re.search(patterns_cn[6], text)
        if m:
            val = float(m.group(1)) * 1000
            lo = self._price_to_bucket(val * 0.8)
            hi = self._price_to_bucket(val * 1.2)
            result.add("prize", {"op": "between", "min": lo, "max": hi})
            result.add_keyword(m.group(0))
            return text[: m.start()] + text[m.end() :]

        # 英文价格区间
        for pattern in patterns_en[:2]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                v1 = m.group(1).replace(",", "")
                v2 = m.group(2).replace(",", "")
                min_val = float(v1) * (1000 if "k" in pattern else 1)
                max_val = float(v2) * (1000 if "k" in pattern else 1)
                result.add(
                    "prize",
                    {
                        "op": "between",
                        "min": self._price_to_bucket(min_val),
                        "max": self._price_to_bucket(max_val),
                    },
                )
                result.add_keyword(m.group(0))
                return text[: m.start()] + text[m.end() :]

        return text

    def _price_to_bucket(self, price: float) -> str:
        """将数值价格映射到最近的 registry 候选值"""
        label = self.registry.get_label("prize")
        if not label:
            return str(int(price))

        # prize candidates 是有序的区间字符串
        # 解析每个候选值的数值范围并找到最接近的
        for candidate in label.candidates:
            nums = re.findall(r"[\d,]+", candidate)
            nums = [int(n.replace(",", "")) for n in nums]
            if "below" in candidate and nums:
                if price <= nums[0]:
                    return candidate
            elif "above" in candidate and nums:
                if price >= nums[0]:
                    return candidate
            elif len(nums) == 2:
                if nums[0] <= price <= nums[1]:
                    return candidate

        # 默认返回最后一个（above X）
        return label.candidates[-1]

    # ------------------------------------------------------------------
    # 品牌提取
    # ------------------------------------------------------------------

    def _extract_brand(self, text: str, result: ParsedQuery) -> str:
        """提取品牌信息"""
        text_lower = text.lower()

        # 按别名长度降序匹配（长的优先，避免部分匹配）
        sorted_aliases = sorted(
            BRAND_ALIASES.items(), key=lambda x: len(x[0]), reverse=True
        )
        for alias, brand in sorted_aliases:
            if alias in text_lower:
                result.add("brand", brand)
                result.add_keyword(alias)
                return text_lower.replace(alias, " ", 1)

        # 直接品牌名匹配（英文全名）
        all_brands = set(BRAND_ALIASES.values())
        # 从 registry 获取所有品牌叶子节点
        brand_leaves = set()
        for area in self.registry.brand_tree.values():
            for country_brands in area.values():
                brand_leaves.update(b.lower() for b in country_brands)
        all_brands.update(brand_leaves)

        for brand in sorted(all_brands, key=len, reverse=True):
            if brand in text_lower:
                result.add("brand", brand)
                result.add_keyword(brand)
                return text_lower.replace(brand, " ", 1)

        return text

    # ------------------------------------------------------------------
    # 车型 / 地区提取
    # ------------------------------------------------------------------

    def _extract_category(self, text: str, result: ParsedQuery) -> str:
        """提取车型类别和地区"""
        text_lower = text.lower()

        # 按关键词长度降序匹配
        sorted_kw = sorted(
            CATEGORY_ALIASES.items(), key=lambda x: len(x[0]), reverse=True
        )
        for keyword, (level_key, value) in sorted_kw:
            if keyword in text_lower:
                result.add(level_key, value)
                result.add_keyword(keyword)
                text_lower = text_lower.replace(keyword, " ", 1)

        return text_lower

    # ------------------------------------------------------------------
    # 功能特性提取
    # ------------------------------------------------------------------

    def _extract_features(self, text: str, result: ParsedQuery) -> str:
        """提取功能/特性关键词"""
        text_lower = text.lower()

        sorted_kw = sorted(
            FEATURE_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True
        )
        for keyword, (label_name, value) in sorted_kw:
            if keyword in text_lower:
                result.add(label_name, value)
                result.add_keyword(keyword)
                text_lower = text_lower.replace(keyword, " ", 1)

        return text_lower

    # ------------------------------------------------------------------
    # 性能别名提取
    # ------------------------------------------------------------------

    def _extract_performance(self, text: str, result: ParsedQuery) -> str:
        """提取性能相关的别名关键词"""
        text_lower = text.lower()

        sorted_kw = sorted(
            PERFORMANCE_ALIASES.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        )
        for keyword, (label_name, op, alias_val) in sorted_kw:
            if keyword in text_lower:
                # 解析别名为实际值
                resolved = self.registry.resolve_alias(label_name, alias_val)
                result.add(label_name, {"op": op, "value": resolved})
                result.add_keyword(keyword)
                text_lower = text_lower.replace(keyword, " ", 1)

        return text_lower
