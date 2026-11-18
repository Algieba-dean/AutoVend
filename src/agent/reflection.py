"""
Self-Reflection & Hallucination Defense Engine for AutoVend Agent (src/agent/reflection.py).

Inspects generated response text for parameter hallucinations against RAG ground truth
(retrieved vehicles), enforces commercial compliance guardrails, and prevents prompt leakage.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Prohibited illegal / unauthorized sales compliance keywords and compliant standard replacements
COMPLIANCE_RISK_PATTERNS: List[Tuple[str, str]] = [
    (r"保证(?:全网|全国)?最低价", "抱歉，最终优惠方案需以 4S 店现场签单合同为准"),
    (r"承诺包过户避税", "抱歉，所有开票及过户流程严格遵循国家税法规定"),
    (r"保证终身免费充加电", "抱歉，具体充电权益以车企官方最新发布政策为准"),
    (r"零首付免征信秒批|黑户(?:也能|可)办", "我们提供合规金融分期方案，具体资质审核以合作银行或金融机构审批为准"),
    (r"绝对不会自燃|任何碰撞保不死", "车辆具备高标准主被动安全防护体系与严苛安全认证"),
    (r"自动驾驶出事车企全赔", "当前高阶辅助驾驶需驾驶员全程保持监管，以国家法规及官方声明为准"),
    (r"假一赔十|买贵包退差价", "我们将为您争取门店最具竞争力的综合购车权益与官方补贴"),
]

# System prompt leakage and non-sales meta tokens
PROMPT_LEAK_PATTERNS: List[str] = [
    r"<system>.*?</system>",
    r"\[系统(?:指令|提示|状态)[^\]]*\]",
    r"作为(?:一个)?(?:AI|人工智能)?销售助手",
    r"根据我的系统指令",
    r"按照SOP流程要求",
    r"SYSTEM_PROMPT",
]

# Pre-compiled regex patterns for microsecond execution
_COMPILED_COMPLIANCE_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(p), repl, p) for p, repl in COMPLIANCE_RISK_PATTERNS
]
_COMPLIANCE_FAST_CHECK = re.compile(
    "|".join(f"(?:{p})" for p, _ in COMPLIANCE_RISK_PATTERNS)
)

_COMPILED_PROMPT_LEAK_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(p, re.IGNORECASE), p) for p in PROMPT_LEAK_PATTERNS
]
_PROMPT_LEAK_FAST_CHECK = re.compile(
    "|".join(f"(?:{p})" for p in PROMPT_LEAK_PATTERNS), re.IGNORECASE
)

# TOY IMPLEMENTATION: Hardcoded regex patterns for detecting numerical parameter hallucinations.
# Only inspects specific patterns (km, s破百); misses arbitrary hallucinated features or trims.
# In production, replace with NLI (Natural Language Inference) models or automated evidence verification against DB specs.
_RANGE_CLAIM_PATTERN = re.compile(r"(\d{3,4})\s*(?:km|公里|公里续航|km续航)", re.IGNORECASE)
_ACC_CLAIM_PATTERN = re.compile(r"(\d(?:\.\d)?)\s*(?:秒破百|秒级破百|s破百)", re.IGNORECASE)
_DIGIT_PATTERN = re.compile(r"(\d+)")
_MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")


class ReflectionReport(BaseModel):
    """Structured report of pre-response self-reflection inspection."""

    is_compliant: bool = True
    hallucination_detected: bool = False
    prompt_leak_detected: bool = False
    sanitized_text: str = ""
    grounding_score: float = 1.0  # 1.0 = fully grounded, 0.0 = severe hallucination
    warnings: List[str] = Field(default_factory=list)
    corrections: List[Dict[str, str]] = Field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return self.is_compliant and not self.hallucination_detected and not self.prompt_leak_detected


class ReflectionResult(BaseModel):
    """Backwards-compatible result model."""

    is_compliant: bool = True
    hallucination_detected: bool = False
    sanitized_text: str = ""
    warnings: List[str] = Field(default_factory=list)


def check_sales_compliance(text: str) -> Tuple[str, List[str]]:
    """
    Sanitize unauthorized sales promises or compliance risks in generated text.
    Returns (sanitized_text, warnings).
    """
    if not text or not _COMPLIANCE_FAST_CHECK.search(text):
        return text, []

    sanitized = text
    warnings: List[str] = []

    for pattern_re, replacement, raw_pattern in _COMPILED_COMPLIANCE_PATTERNS:
        if pattern_re.search(sanitized):
            warnings.append(f"检测到违规销售承诺匹配: '{raw_pattern}'")
            sanitized = pattern_re.sub(replacement, sanitized)

    return sanitized, warnings


def sanitize_prompt_leakage(text: str) -> Tuple[str, List[str]]:
    """Strip accidental leakage of internal system prompt directives or meta tokens."""
    if not text or not _PROMPT_LEAK_FAST_CHECK.search(text):
        return text, []

    sanitized = text
    warnings: List[str] = []

    for pattern_re, raw_pattern in _COMPILED_PROMPT_LEAK_PATTERNS:
        if pattern_re.search(sanitized):
            warnings.append(f"检测到系统指令/角色外泄露: '{raw_pattern}'")
            sanitized = pattern_re.sub("", sanitized)

    # Clean double spaces or broken lines caused by stripping
    sanitized = _MULTI_NEWLINE_PATTERN.sub("\n\n", sanitized).strip()
    return sanitized, warnings


def verify_numeric_hallucinations(text: str, matched_cars: List[Dict[str, Any]]) -> List[str]:
    """
    Inspect generated text for numerical vehicle specifications (e.g., range in km, price in 万)
    and verify if they exceed reasonable boundaries of matched_cars.
    """
    warnings: List[str] = []
    if not matched_cars or not text:
        return warnings

    # 1. Range verification: e.g. "续航 700 km" or "700公里续航"
    range_claims = _RANGE_CLAIM_PATTERN.findall(text)
    if range_claims:
        claimed_ranges = [float(r) for r in range_claims]
        actual_ranges = []
        for car in matched_cars:
            r_val = (
                car.get("electric_range")
                or car.get("pure_electric_range")
                or car.get("cltc_range")
                or (car.get("metadata", {}).get("electric_range") if isinstance(car.get("metadata"), dict) else None)
            )
            if r_val:
                r_match = _DIGIT_PATTERN.search(str(r_val))
                if r_match:
                    actual_ranges.append(float(r_match.group(1)))

        if actual_ranges:
            max_actual = max(actual_ranges)
            for claim in claimed_ranges:
                if claim > max_actual * 1.35 and claim > 500:
                    warnings.append(
                        f"可能存在续航参数幻觉: 生成话术提及 {claim:.0f}km 续航，而匹配车型实际最大续航仅为 {max_actual:.0f}km"
                    )

    # 2. Extreme 0-100 acceleration claims (e.g. 1.8秒破百 on family car)
    acc_claims = _ACC_CLAIM_PATTERN.findall(text)
    for acc in acc_claims:
        val = float(acc)
        if val < 2.2:
            warnings.append(f"可能存在零百加速参数幻觉: 提到了过于激进的超跑级破百时间 ({val}秒)")

    return warnings


class ReflectionGate:
    """
    Unified pre-response reflection gate for SalesAgent.
    Validates factual grounding, sales compliance, and system persona boundary.
    """

    @classmethod
    def evaluate(
        cls,
        response_text: str,
        matched_cars: Optional[List[Dict[str, Any]]] = None,
    ) -> ReflectionReport:
        """
        Execute comprehensive online reflection review.
        """
        if not response_text:
            return ReflectionReport(sanitized_text="")

        matched_cars = matched_cars or []
        corrections: List[Dict[str, str]] = []

        # 1. Compliance guard
        compliant_text, compliance_warnings = check_sales_compliance(response_text)
        if compliant_text != response_text:
            corrections.append({
                "type": "COMPLIANCE_SANITIZATION",
                "original": response_text[:100],
                "replacement": compliant_text[:100],
            })

        # 2. Prompt leak filter
        safe_text, leak_warnings = sanitize_prompt_leakage(compliant_text)
        if safe_text != compliant_text:
            corrections.append({
                "type": "PROMPT_LEAK_STRIPPED",
                "original": compliant_text[:100],
                "replacement": safe_text[:100],
            })

        # 3. Numeric hallucination check
        hallucination_warnings = verify_numeric_hallucinations(safe_text, matched_cars)

        # Grounding score estimation
        all_warnings = compliance_warnings + leak_warnings + hallucination_warnings
        grounding_score = 1.0
        if hallucination_warnings:
            grounding_score -= 0.40 * len(hallucination_warnings)
        if compliance_warnings:
            grounding_score -= 0.30 * len(compliance_warnings)
        if leak_warnings:
            grounding_score -= 0.20 * len(leak_warnings)
        grounding_score = max(0.0, min(1.0, round(grounding_score, 2)))

        # Append grounding caution disclaimer if severe hallucination was flagged
        final_text = safe_text
        if hallucination_warnings and not any("官方参数" in final_text for _ in [1]):
            final_text += "\n（注：车辆具体续航、配置与权益以车企官方最新公布规格为准）"

        return ReflectionReport(
            is_compliant=len(compliance_warnings) == 0,
            hallucination_detected=len(hallucination_warnings) > 0,
            prompt_leak_detected=len(leak_warnings) > 0,
            sanitized_text=final_text,
            grounding_score=grounding_score,
            warnings=all_warnings,
            corrections=corrections,
        )


def reflect_and_guard(
    response_text: str, matched_cars: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, List[str]]:
    """
    Main entry point for Self-Reflection & Hallucination Defense.

    Returns:
        (sanitized_response_text, list_of_warning_messages)
    """
    report = ReflectionGate.evaluate(response_text, matched_cars)
    if report.warnings:
        logger.warning(f"Self-reflection triggered warnings: {report.warnings}")
    return report.sanitized_text, report.warnings


_PRICE_CLAIM_RE = re.compile(r"(?:售价|指导价|裸车价|落地价|报价|只要|仅需|约)\s*(\d{1,3}(?:\.\d{1,2})?)\s*万(?:元)?")


def audit_response_against_evidence(
    response_text: str,
    matched_cars: Optional[List[Dict[str, Any]]] = None,
    evidence_anchors: Optional[List[Dict[str, Any]]] = None,
) -> ReflectionReport:
    """
    Audit generated reply against retrieved vehicles and evidence ledger anchors
    for price, range, and policy/compliance consistency.
    """
    report = ReflectionGate.evaluate(response_text, matched_cars)
    cars = matched_cars or []
    if not cars or not response_text:
        return report

    # Extract known prices (in 万元) from matched_cars & evidence_anchors
    known_prices: List[float] = []
    for car in cars:
        if not isinstance(car, dict):
            continue
        meta = car.get("metadata") if isinstance(car.get("metadata"), dict) else {}
        for key in ("price_wan", "msrp_wan", "price"):
            val = car.get(key) if car.get(key) is not None else meta.get(key)
            if val is not None:
                m = re.search(r"(\d+(?:\.\d+)?)", str(val))
                if m:
                    num = float(m.group(1))
                    if num > 1000:
                        num = num / 10000.0
                    if 1.0 <= num <= 500.0:
                        known_prices.append(num)
    for anchor in evidence_anchors or []:
        meta = anchor.get("metadata") if isinstance(anchor, dict) else {}
        if isinstance(meta, dict) and meta.get("price"):
            m = re.search(r"(\d+(?:\.\d+)?)", str(meta["price"]))
            if m:
                num = float(m.group(1))
                if num > 1000:
                    num = num / 10000.0
                if 1.0 <= num <= 500.0:
                    known_prices.append(num)

    if known_prices:
        min_p = min(known_prices)
        max_p = max(known_prices)
        for claimed_str in _PRICE_CLAIM_RE.findall(response_text):
            claimed = float(claimed_str)
            # Allow reasonable drive-away / discount variance (±35%)
            if claimed < min_p * 0.65 or claimed > max_p * 1.45:
                report.hallucination_detected = True
                report.warnings.append(
                    f"可能存在价格幻觉: 回复提及 {claimed:.2f} 万元，与证据账本已知车型价格区间 ({min_p:.2f}~{max_p:.2f} 万元) 存在较大偏差"
                )
                report.grounding_score = max(0.0, round(report.grounding_score - 0.35, 2))

    return report
