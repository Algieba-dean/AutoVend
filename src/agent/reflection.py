"""
Self-Reflection & Hallucination Defense Engine for AutoVend Agent.

Inspects generated response text for parameter hallucinations against RAG ground truth
(retrieved vehicles) and enforces commercial compliance guardrails.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Prohibited illegal / unauthorized sales compliance keywords
COMPLIANCE_RISK_PATTERNS = [
    (r"保证(?:全网|全国)?最低价", "抱歉，最终优惠方案需以 4S 店现场签单合同为准"),
    (r"承诺包过户避税", "抱歉，所有开票及过户流程严格遵循国家税法规定"),
    (r"保证终身免费充加电", "抱歉，具体充电权益以车企官方最新发布政策为准"),
]


class ReflectionResult(BaseModel if "BaseModel" in globals() else object):
    """Result of inspecting a generated response."""

    is_compliant: bool = True
    hallucination_detected: bool = False
    sanitized_text: str = ""
    warnings: List[str] = []


def check_sales_compliance(text: str) -> Tuple[str, List[str]]:
    """
    Sanitize unauthorized sales promises or compliance risks in generated text.
    Returns (sanitized_text, warnings).
    """
    sanitized = text
    warnings: List[str] = []

    for pattern, replacement in COMPLIANCE_RISK_PATTERNS:
        if re.search(pattern, sanitized):
            warnings.append(f"检测到违规销售承诺匹配: '{pattern}'")
            sanitized = re.sub(pattern, replacement, sanitized)

    return sanitized, warnings


def verify_numeric_hallucinations(
    text: str, matched_cars: List[Dict[str, Any]]
) -> List[str]:
    """
    Inspect generated text for numerical vehicle specifications (e.g., range in km, price in 万)
    and verify if they exceed reasonable boundaries of matched_cars.
    """
    warnings: List[str] = []
    if not matched_cars or not text:
        return warnings

    # Extract claims like "续航 700 km" or "700公里续航"
    range_claims = re.findall(r"(\d{3,4})\s*(?:km|公里|公里续航|km续航)", text, re.IGNORECASE)
    if range_claims:
        claimed_ranges = [float(r) for r in range_claims]
        # Get max actual range from matched cars
        actual_ranges = []
        for car in matched_cars:
            r_val = car.get("electric_range") or car.get("pure_electric_range") or car.get("cltc_range")
            if r_val:
                r_match = re.search(r"(\d+)", str(r_val))
                if r_match:
                    actual_ranges.append(float(r_match.group(1)))

        if actual_ranges:
            max_actual = max(actual_ranges)
            for claim in claimed_ranges:
                # If generated text claims range > 1.3x maximum actual range in candidates
                if claim > max_actual * 1.35 and claim > 500:
                    warnings.append(
                        f"可能存在续航参数幻觉: 生成话术提及 {claim:.0f}km 续航，而匹配车型实际最大续航仅为 {max_actual:.0f}km"
                    )

    return warnings


def reflect_and_guard(
    response_text: str, matched_cars: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, List[str]]:
    """
    Main entry point for Self-Reflection & Hallucination Defense.

    Returns:
        (sanitized_response_text, list_of_warning_messages)
    """
    if not response_text:
        return response_text, []

    sanitized, compliance_warnings = check_sales_compliance(response_text)
    hallucination_warnings = verify_numeric_hallucinations(sanitized, matched_cars or [])

    all_warnings = compliance_warnings + hallucination_warnings
    if all_warnings:
        logger.warning(f"Self-reflection triggered warnings: {all_warnings}")

    return sanitized, all_warnings
