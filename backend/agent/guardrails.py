"""
Guardrails — fact-consistency checking and circuit-breaker fallback.

Aligned with architecture "对齐与校验防线 Guardrails":
1. Fact consistency check: verify generated response against retrieved
   vehicle data using rule-based NLI (Natural Language Inference).
2. Circuit breaker: if hallucination is detected, replace with a safe
   degraded response instead of passing through incorrect information.

This module sits between response generation and final output.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class GuardrailResult:
    """Result of the guardrail check."""

    passed: bool = True
    original_response: str = ""
    final_response: str = ""
    violations: List[str] = field(default_factory=list)
    was_degraded: bool = False


# ── Price claim patterns ─────────────────────────────────────────────
PRICE_PATTERN = re.compile(
    r"(?:售价|价格|起售价|指导价|官方价|定价|报价)"
    r"[为是约大概]?"
    r"[\s]*"
    r"([\d,.]+\s*[万元]+)",
    re.UNICODE,
)

# ── Spec claim patterns (horsepower, torque, range, etc.) ────────────
SPEC_PATTERNS = {
    "horsepower": re.compile(
        r"(\d+)\s*(?:马力|hp|匹)", re.IGNORECASE
    ),
    "torque": re.compile(
        r"(\d+)\s*(?:牛·?米|N·?m|Nm)", re.IGNORECASE
    ),
    "electric_range": re.compile(
        r"(?:续航|纯电续航|CLTC续航)[\s]*(?:为|达到|约)?"
        r"[\s]*([\d,.]+)\s*(?:km|公里|千米)",
        re.IGNORECASE,
    ),
    "acceleration_0_100": re.compile(
        r"(?:百公里加速|0-100|零百)[\s]*(?:为|仅需|约)?"
        r"[\s]*([\d,.]+)\s*秒",
    ),
    "fuel_consumption": re.compile(
        r"(?:油耗|百公里油耗|综合油耗)[\s]*(?:为|约|仅)?"
        r"[\s]*([\d,.]+)\s*(?:L|升)",
        re.IGNORECASE,
    ),
}


def _extract_mentioned_models(
    response: str,
    known_models: List[str],
) -> List[str]:
    """Find which known car models are mentioned in the response."""
    mentioned = []
    resp_lower = response.lower()
    for model in known_models:
        if model.lower() in resp_lower:
            mentioned.append(model)
    return mentioned


def _check_model_in_results(
    response: str,
    matched_cars: List[Dict[str, Any]],
) -> List[str]:
    """
    Check if the response mentions car models not in retrieval results.

    This catches hallucinated vehicle recommendations.
    """
    violations = []

    if not matched_cars:
        return violations

    known_models = [
        car.get("car_model", "") for car in matched_cars
    ]
    known_brands = {
        car.get("metadata", {}).get("brand", "")
        for car in matched_cars
        if car.get("metadata", {}).get("brand")
    }

    # Check for specific brand mentions that aren't in results
    brand_keywords = [
        "Tesla", "BMW", "Mercedes", "Audi", "Toyota",
        "Honda", "BYD", "Geely", "Changan", "Nio",
        "XPeng", "XiaoMi", "特斯拉", "宝马", "奔驰",
        "奥迪", "丰田", "本田", "比亚迪", "吉利",
        "长安", "蔚来", "小鹏", "小米",
    ]

    for brand in brand_keywords:
        if brand.lower() in response.lower():
            # Check if this brand is in any of the matched results
            brand_in_results = any(
                brand.lower() in m.lower()
                for m in known_models
            ) or any(
                brand.lower() in b.lower()
                for b in known_brands
            )
            if not brand_in_results:
                violations.append(
                    f"Mentioned brand '{brand}' not in "
                    f"retrieval results"
                )

    return violations


def _check_spec_claims(
    response: str,
    matched_cars: List[Dict[str, Any]],
) -> List[str]:
    """
    Check if numeric spec claims in the response are grounded
    in the retrieved vehicle data.

    This is a lightweight NLI check using regex + metadata comparison.
    """
    violations = []

    if not matched_cars:
        return violations

    # Collect all known specs from matched cars
    all_snippets = " ".join(
        car.get("text_snippet", "") for car in matched_cars
    ).lower()

    for spec_name, pattern in SPEC_PATTERNS.items():
        for match in pattern.finditer(response):
            claimed_value = match.group(1)
            # Check if this value appears in any retrieved data
            if claimed_value not in all_snippets:
                violations.append(
                    f"Claimed {spec_name}={claimed_value} "
                    f"not found in retrieved data"
                )

    return violations


DEGRADED_RESPONSES = {
    "zh": (
        "感谢您的耐心！根据您的需求，我为您找到了一些匹配的车型。"
        "为了给您最准确的信息，建议您查看我们提供的车型详情，"
        "或者联系我们的销售顾问获取最新参数和报价。"
        "请问您想了解哪款车型的具体信息？"
    ),
    "en": (
        "Thank you for your patience! Based on your needs, "
        "I've found some matching vehicles. "
        "For the most accurate specifications and pricing, "
        "I'd recommend checking the detailed listings "
        "or contacting our sales team. "
        "Which model would you like to learn more about?"
    ),
}


def _detect_language(text: str) -> str:
    """Simple language detection: Chinese vs English."""
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return "zh" if chinese_chars > len(text) * 0.1 else "en"


def check_response(
    response: str,
    matched_cars: List[Dict[str, Any]],
    max_violations: int = 2,
) -> GuardrailResult:
    """
    Run the full guardrail pipeline on a generated response.

    Steps:
    1. Check for hallucinated car models/brands
    2. Check for ungrounded spec claims
    3. If violations exceed threshold, trigger circuit breaker

    Args:
        response: Generated response text.
        matched_cars: Retrieved vehicle data for grounding.
        max_violations: Threshold to trigger circuit breaker.

    Returns:
        GuardrailResult with pass/fail status and final response.
    """
    result = GuardrailResult(original_response=response)
    violations: List[str] = []

    # Check 1: Model/brand hallucination
    violations.extend(
        _check_model_in_results(response, matched_cars)
    )

    # Check 2: Spec claim grounding
    violations.extend(
        _check_spec_claims(response, matched_cars)
    )

    result.violations = violations

    if len(violations) > max_violations:
        # Circuit breaker: too many violations → degraded response
        lang = _detect_language(response)
        result.passed = False
        result.was_degraded = True
        result.final_response = DEGRADED_RESPONSES.get(lang, DEGRADED_RESPONSES["zh"])
        logger.warning(
            f"Guardrail BLOCKED: {len(violations)} violations "
            f"(threshold={max_violations}). "
            f"Violations: {violations}"
        )
    elif violations:
        # Some violations but below threshold → pass with warning
        result.passed = True
        result.final_response = response
        logger.info(
            f"Guardrail WARNING: {len(violations)} violations "
            f"(below threshold). Violations: {violations}"
        )
    else:
        # Clean pass
        result.passed = True
        result.final_response = response
        logger.debug("Guardrail PASSED: no violations detected")

    return result
