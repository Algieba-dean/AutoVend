"""
Shared utilities for AutoVend empirical benchmark & post-mortem suites.
"""

import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from dotenv import dotenv_values

from src.llm.openai_llm import OpenAILLM

try:
    import tiktoken

    _TIKTOKEN_ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_ENC = None

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


SAMPLE_VEHICLE_POOL: List[Dict[str, Any]] = [
    {
        "id": "veh_lixiang_l6",
        "name": "理想L6 Pro",
        "brand": "理想",
        "powertrain": "增程",
        "price_wan": 24.98,
        "seats": 5,
        "range_km": 1390,
        "zero_to_hundred_s": 5.4,
        "content": "理想L6 Pro 24.98万元，增程式电动SUV，大五座家用空间宽敞，CLTC综合续航1390km，纯电续航212km，零百加速5.4s，标配双电机四驱与激光雷达智驾。",
    },
    {
        "id": "veh_aito_m7",
        "name": "问界M7 Plus 五座后驱版",
        "brand": "问界",
        "powertrain": "增程",
        "price_wan": 24.98,
        "seats": 5,
        "range_km": 1300,
        "zero_to_hundred_s": 7.8,
        "content": "问界M7 Plus 24.98万元，增程SUV，5座/6座可选，CLTC综合续航1300km，搭载华为鸿蒙座舱与HUAWEI ADS智驾系统。",
    },
    {
        "id": "veh_leapmotor_c16",
        "name": "零跑C16 增程 200尊享版",
        "brand": "零跑",
        "powertrain": "增程",
        "price_wan": 16.28,
        "seats": 6,
        "range_km": 1095,
        "zero_to_hundred_s": 8.4,
        "content": "零跑C16 增程版 16.28万元，6座中大型SUV，家用带娃空间充裕，CLTC综合续航1095km，高通8295座舱芯片。",
    },
    {
        "id": "veh_geely_l7",
        "name": "吉利银河L7 115km 星舰版",
        "brand": "吉利",
        "powertrain": "插混",
        "price_wan": 15.37,
        "seats": 5,
        "range_km": 1370,
        "zero_to_hundred_s": 6.9,
        "content": "吉利银河L7 插混SUV 15.37万元，雷神电混8848，CLTC综合续航1370km，零百加速6.9s，支持快充。",
    },
    {
        "id": "veh_byd_han_dmi",
        "name": "比亚迪汉DM-i 荣耀版",
        "brand": "比亚迪",
        "powertrain": "插混",
        "price_wan": 16.98,
        "seats": 5,
        "range_km": 1260,
        "zero_to_hundred_s": 7.9,
        "content": "比亚迪汉DM-i 16.98万元，插电式混动中大型轿车，CLTC综合续航1260km，亏电油耗4.2L/100km。",
    },
    {
        "id": "veh_byd_han_ev",
        "name": "比亚迪汉EV 荣耀版",
        "brand": "比亚迪",
        "powertrain": "纯电",
        "price_wan": 17.98,
        "seats": 5,
        "range_km": 605,
        "zero_to_hundred_s": 7.9,
        "content": "比亚迪汉EV 17.98万元，纯电中大型轿车，CLTC纯电续航605km，刀片电池。",
    },
    {
        "id": "veh_xiaomi_su7_max",
        "name": "小米SU7 Max",
        "brand": "小米",
        "powertrain": "纯电",
        "price_wan": 29.99,
        "seats": 5,
        "range_km": 800,
        "zero_to_hundred_s": 2.78,
        "content": "小米SU7 Max 29.99万元，纯电轿跑，800V高压平台，101度麒麟电池，CLTC续航800km，零百加速2.78s，双电机四驱，双Orin-X智驾。",
    },
    {
        "id": "veh_zeekr_001",
        "name": "极氪001 WE版",
        "brand": "极氪",
        "powertrain": "纯电",
        "price_wan": 25.90,
        "seats": 5,
        "range_km": 750,
        "zero_to_hundred_s": 3.5,
        "content": "极氪001 WE版 25.90万元，纯电猎装轿跑，800V架构，100度麒麟电池，CLTC续航750km，零百加速3.5s。",
    },
]


def estimate_tokens(text: str) -> int:
    """Count tokens using tiktoken cl100k_base if available, else CJK-aware heuristic."""
    if not text:
        return 0
    if _TIKTOKEN_ENC is not None:
        return len(_TIKTOKEN_ENC.encode(text))
    cjk_count = len(_CJK_RE.findall(text))
    ascii_chars = max(0, len(text) - cjk_count)
    return max(1, int(math.ceil(cjk_count * 1.35 + ascii_chars / 3.8)))


def compute_percentile(values: List[float], p: float) -> float:
    """Compute linear-interpolated percentile p in [0, 100] over sorted values."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    rank = (p / 100.0) * (len(s) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return float(s[lo])
    frac = rank - lo
    return float(s[lo] + (s[hi] - s[lo]) * frac)


def resolve_live_llm_config(provider: Optional[str] = None) -> Tuple[str, str, str, str]:
    """
    Resolve (provider, model, api_key, base_url) from process env and .env.
    Prefers explicit LLM_* or DEEPSEEK_* when available.
    """
    dotenv_map = dotenv_values(".env")

    def _get(k: str, default: str = "") -> str:
        return (os.getenv(k) or dotenv_map.get(k) or default).strip()

    prov = (provider or _get("LLM_PROVIDER")).lower()

    if prov == "deepseek" or (not prov and _get("DEEPSEEK_API_KEY")):
        api_key = _get("DEEPSEEK_API_KEY") or _get("LLM_API_KEY")
        base_url = _get("DEEPSEEK_URL", "https://api.deepseek.com")
        # deepseek-v4-flash is a reasoning model that consumes tokens on <think>;
        # deepseek-chat is fast, non-reasoning, and reports prompt_cache_hit_tokens.
        raw_model = _get("LLM_MODEL") or _get("DEEPSEEK_MODEL", "deepseek-chat")
        model = "deepseek-chat" if "flash" in raw_model.lower() else raw_model
        return "deepseek", model, api_key, base_url

    if _get("LLM_API_KEY"):
        return (
            prov or "openai",
            _get("LLM_MODEL", "gpt-4o-mini"),
            _get("LLM_API_KEY"),
            _get("LLM_BASE_URL", "https://api.openai.com/v1"),
        )

    if _get("GROQ_API_KEY"):
        return (
            "groq",
            _get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            _get("GROQ_API_KEY"),
            _get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        )

    raise RuntimeError("No live LLM API key found in environment or .env.")


def build_live_llm_from_env(provider: Optional[str] = None, timeout: int = 45) -> OpenAILLM:
    """Instantiate a live OpenAILLM client from environment / .env."""
    _, model, api_key, base_url = resolve_live_llm_config(provider=provider)
    return OpenAILLM(model=model, api_key=api_key, base_url=base_url, timeout=timeout)
