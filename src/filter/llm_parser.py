"""
LLM 意图解析器（fallback）

当规则引擎无法充分解析用户查询时，使用 LLM 将自然语言转为结构化查询 JSON。
输出 schema 与 LabelRegistry 对齐，结果经过验证确保合法。
"""

import json
from typing import Any, Dict, Optional

from src.filter.label_registry import LabelRegistry
from src.utils.logger import get_logger

SYSTEM_PROMPT = """\
You are a vehicle query intent parser. Given a user's natural language query \
about cars, extract structured filter conditions as a JSON object.

## Available filter keys and their valid values:

### Tree labels (use any level):
- vehicle_category_top: sedan, suv, mpv, sports car
- vehicle_category_middle: small sedan, mid-size sedan, mid-large sedan, \
crossover suv, body-on-frame suv, family mpv, business mpv, \
convertible sports car, hardtop sports car
- vehicle_category_bottom: micro sedan, compact sedan, b-segment sedan, \
c-segment sedan, d-segment sedan, compact suv, mid-size suv, \
mid-to-large suv, off-road suv, all-terrain suv, compact mpv, \
mid-size mpv, large mpv, mid-size business mpv, large-size business mpv, \
two-door convertible sports car, four-door convertible sports car, \
two-door hardtop sports car, four-door hardtop sports car
- brand_area: european, american, asian
- brand_country: germany, france, united kingdom, sweden, usa, japan, \
korea, china
- brand: volkswagen, audi, porsche, bentley, bugatti, lamborghini, bmw, \
mercedes-benz, peugeot, renault, jaguar, land rover, rolls-royce, volvo, \
chevrolet, buick, cadillac, ford, tesla, toyota, honda, nissan, suzuki, \
mazda, hyundai, byd, geely, changan, great wall motor, nio, xiaomi, xpeng

### Range labels (use value or alias):
- prize: below 10,000 / 10,000 ~ 20,000 / 20,000 ~ 30,000 / \
30,000 ~ 40,000 / 40,000 ~ 60,000 / 60,000 ~ 100,000 / above 100,000
  aliases: cheap, economy, mid-range low-end, mid-range, \
mid-range high-end, high-end, luxury
- horsepower: below 100 hp / 100-200 hp / 200-300 hp / 300-400 hp / \
above 400 hp
  aliases: low, lower-medium, medium, high, extra-high
- driving_range: 300-400km / 400-800km / above 800km
  aliases: short, medium, long

### Range operators:
For range labels, you can use operators:
- exact: {"op": "eq", "value": "30,000 ~ 40,000"}
- at least: {"op": "gte", "value": "30,000 ~ 40,000"}
- at most: {"op": "lte", "value": "30,000 ~ 40,000"}
- between: {"op": "between", "min": "20,000 ~ 30,000", \
"max": "40,000 ~ 60,000"}

### Enum labels:
- powertrain_type: gasoline engine, diesel engine, \
hybrid electric vehicle, plug-in hybrid electric vehicle, \
range-extended electric vehicle, battery electric vehicle
- design_style: sporty, business
- drive_type: front-wheel drive, rear-wheel drive, all-wheel drive
- seat_layout: 2-seat, 4-seat, 5-seat, 6-seat, 7-seat
- seat_material: leather, fabric

### Boolean labels (yes/no):
adaptive_cruise_control, auto_parking, automatic_emergency_braking, \
blind_spot_detection, cargo_capability, city_commuting, esp, \
fatigue_driving_detection, highway_long_distance, lane_keep_assist, \
ota_updates, remote_parking, traffic_jam_assist, voice_interaction

## Rules:
1. Only output valid JSON with keys from the lists above.
2. All string values must be lowercase.
3. If a condition cannot be mapped, omit it.
4. For price in Chinese "万" (wan), multiply by 1000 for system units. \
Example: "30万" = 30,000 system units → "20,000 ~ 30,000" bucket.
5. Return ONLY the JSON object, no explanation.
"""


class LLMParser:
    """
    LLM 意图解析器

    作为规则引擎的 fallback，处理复杂/模糊的自然语言查询。
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        registry: Optional[LabelRegistry] = None,
    ):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.registry = registry or LabelRegistry()
        self.llm = llm

    def is_available(self) -> bool:
        """检查 LLM 是否可用"""
        if self.llm is None:
            return False
        try:
            return self.llm.is_available()
        except Exception:
            return False

    def parse(self, text: str) -> Dict[str, Any]:
        """
        使用 LLM 将自然语言查询解析为结构化条件

        Args:
            text: 用户原始查询文本

        Returns:
            结构化查询 dict（与 FilterEngine 兼容）
        """
        if not self.is_available():
            self.logger.warning("LLM 不可用，返回空查询")
            return {}

        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ]
            raw_response = self.llm.chat(messages)
            parsed = self._extract_json(raw_response)

            if parsed:
                validated = self._validate(parsed)
                self.logger.info(f"LLM 解析结果: {len(validated)} 个条件")
                return validated

        except Exception as e:
            self.logger.error(f"LLM 解析失败: {e}")

        return {}

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """从 LLM 响应中提取 JSON"""
        text = text.strip()

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 代码块
        import re

        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取第一个 { ... }
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _validate(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """验证并清洗 LLM 输出，确保 key/value 合法"""
        from src.filter.filter_engine import FilterEngine

        valid_keys = (
            set(self.registry.labels.keys())
            | set(FilterEngine.TREE_LEVEL_KEYS.keys())
            | {"brand", "vehicle_category_bottom"}
        )

        result: Dict[str, Any] = {}

        for key, value in parsed.items():
            key_lower = key.lower()
            if key_lower not in valid_keys:
                continue

            # 树形 key
            if key_lower in FilterEngine.TREE_LEVEL_KEYS:
                if isinstance(value, str):
                    if self.registry.is_tree_value(value.lower()):
                        result[key_lower] = value.lower()
                continue

            # brand / vehicle_category_bottom 直接值
            if key_lower in ("brand", "vehicle_category_bottom"):
                if isinstance(value, str):
                    result[key_lower] = value.lower()
                continue

            # 已知标签
            label = self.registry.get_label(key_lower)
            if label is None:
                continue

            if isinstance(value, dict):
                # 范围操作
                op = value.get("op", "eq")
                if op in ("eq", "gte", "lte", "between"):
                    result[key_lower] = value
            elif isinstance(value, str):
                val = value.lower()
                # 检查是否是合法候选值或别名
                if val in label.value_index or val in label.alias_to_value:
                    result[key_lower] = val
            elif isinstance(value, list):
                valid_vals = []
                for v in value:
                    if isinstance(v, str):
                        vl = v.lower()
                        if vl in label.value_index or vl in label.alias_to_value:
                            valid_vals.append(vl)
                if valid_vals:
                    result[key_lower] = valid_vals

        return result
