"""
Self-Reflection & Hallucination Defense Engine for AutoVend Agent (src/agent/reflection.py).

Performs multi-tier faithfulness & compliance auditing of generated responses against
RAG ground truth (`matched_cars`, `evidence_anchors`):
1. Sales compliance & prompt-leakage guardrails.
2. Generalized multi-attribute spec verification (price, range, 0-100s, battery kWh,
   power kW/Ps, dimensions mm, seating) against retrieved vehicle evidence.
3. Optional model-backed NLI / LLM-as-Judge claim-level faithfulness verification
   (`auditor_llm` via `with_structured_output` or `nli_scorer` cross-encoder).
"""

import logging
import re
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

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

# Multi-attribute numeric spec extractors for evidence cross-checking
_RANGE_CLAIM_PATTERN = re.compile(r"(\d{3,4})\s*(?:km|公里|公里续航|km续航)", re.IGNORECASE)
_ACC_CLAIM_PATTERN = re.compile(r"(\d(?:\.\d)?)\s*(?:秒破百|秒级破百|s破百|秒(?:百公里)?加速)", re.IGNORECASE)
_BATTERY_CLAIM_PATTERN = re.compile(r"(\d{2,3}(?:\.\d)?)\s*(?:kWh|kwh|度电|度电池)", re.IGNORECASE)
_POWER_CLAIM_PATTERN = re.compile(r"(\d{2,4})\s*(?:马力|匹|Ps|ps|kW|kw|千瓦)", re.IGNORECASE)
_PRICE_CLAIM_RE = re.compile(
    r"(?:售价|指导价|裸车价|落地价|报价|只要|仅需|约)\s*(\d{1,3}(?:\.\d{1,2})?)\s*万(?:元)?"
)
_DIGIT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")
_MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")


class ClaimVerdict(BaseModel):
    """NLI verdict for a single factual claim against retrieved evidence."""

    claim: str
    label: Literal["ENTAILED", "CONTRADICTED", "UNSUPPORTED"] = "ENTAILED"
    reason: str = ""


class FaithfulnessAuditOutput(BaseModel):
    """Structured output schema for LLM/NLI-backed faithfulness verification."""

    claim_verdicts: List[ClaimVerdict] = Field(default_factory=list)
    overall_faithful: bool = True
    summary: str = ""


class ReflectionReport(BaseModel):
    """Structured report of pre-response self-reflection inspection."""

    is_compliant: bool = True
    hallucination_detected: bool = False
    prompt_leak_detected: bool = False
    sanitized_text: str = ""
    grounding_score: float = 1.0
    faithfulness_method: str = "evidence_ledger_cross_check"
    claim_verdicts: List[ClaimVerdict] = Field(default_factory=list)
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

    sanitized = _MULTI_NEWLINE_PATTERN.sub("\n\n", sanitized).strip()
    return sanitized, warnings


def _extract_car_field_numbers(
    matched_cars: List[Dict[str, Any]],
    keys: Tuple[str, ...],
) -> List[float]:
    values: List[float] = []
    for car in matched_cars:
        if not isinstance(car, dict):
            continue
        meta = car.get("metadata") if isinstance(car.get("metadata"), dict) else {}
        for k in keys:
            raw = car.get(k) if car.get(k) is not None else meta.get(k)
            if raw is not None:
                m = _DIGIT_PATTERN.search(str(raw))
                if m:
                    values.append(float(m.group(1)))
                    break
    return values


def verify_numeric_hallucinations(text: str, matched_cars: List[Dict[str, Any]]) -> List[str]:
    """
    Cross-check numerical vehicle specifications (range, acceleration, battery kWh,
    power/horsepower) in generated text against retrieved `matched_cars` evidence.
    """
    warnings: List[str] = []
    if not matched_cars or not text:
        return warnings

    # 1. Range verification (km)
    range_claims = _RANGE_CLAIM_PATTERN.findall(text)
    if range_claims:
        claimed_ranges = [float(r) for r in range_claims]
        actual_ranges = _extract_car_field_numbers(
            matched_cars, ("electric_range", "pure_electric_range", "cltc_range", "range_km")
        )
        if actual_ranges:
            max_actual = max(actual_ranges)
            for claim in claimed_ranges:
                if claim > max_actual * 1.35 and claim > 500:
                    warnings.append(
                        f"可能存在续航参数幻觉: 生成话术提及 {claim:.0f}km 续航，而匹配车型实际最大续航仅为 {max_actual:.0f}km"
                    )

    # 2. 0-100 km/h acceleration verification (seconds)
    acc_claims = _ACC_CLAIM_PATTERN.findall(text)
    if acc_claims:
        actual_accs = _extract_car_field_numbers(
            matched_cars, ("acceleration_0_100", "zero_to_hundred", "acc_0_100")
        )
        for acc in acc_claims:
            val = float(acc)
            if actual_accs:
                min_actual = min(actual_accs)
                if val < min_actual * 0.7:
                    warnings.append(
                        f"可能存在零百加速参数幻觉: 提及 {val}秒破百，而匹配车型最快为 {min_actual}秒"
                    )
            elif val < 2.2:
                warnings.append(f"可能存在零百加速参数幻觉: 提到了过于激进的超跑级破百时间 ({val}秒)")

    # 3. Battery capacity verification (kWh)
    battery_claims = _BATTERY_CLAIM_PATTERN.findall(text)
    if battery_claims:
        actual_batteries = _extract_car_field_numbers(
            matched_cars, ("battery_capacity", "battery_kwh", "battery")
        )
        if actual_batteries:
            max_bat = max(actual_batteries)
            for b_str in battery_claims:
                b_val = float(b_str)
                if b_val > max_bat * 1.35 and b_val > 110:
                    warnings.append(
                        f"可能存在电池容量幻觉: 提及 {b_val:.1f}kWh，而匹配车型最大电池容量为 {max_bat:.1f}kWh"
                    )

    # 4. Power / horsepower verification
    power_claims = _POWER_CLAIM_PATTERN.findall(text)
    if power_claims:
        actual_powers = _extract_car_field_numbers(
            matched_cars, ("horsepower", "max_power_kw", "power_kw", "power")
        )
        if actual_powers:
            max_pwr = max(actual_powers)
            for p_str in power_claims:
                p_val = float(p_str)
                if p_val > max_pwr * 1.5 and p_val > 500:
                    warnings.append(
                        f"可能存在动力参数幻觉: 提及 {p_val:.0f}，而匹配车型最大动力参数为 {max_pwr:.0f}"
                    )

    return warnings


def _build_evidence_context(
    matched_cars: List[Dict[str, Any]],
    evidence_anchors: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Assemble concise factual evidence text from matched_cars and evidence anchors."""
    lines: List[str] = []
    for idx, car in enumerate(matched_cars[:6], 1):
        if not isinstance(car, dict):
            continue
        meta = car.get("metadata") if isinstance(car.get("metadata"), dict) else {}
        model = car.get("car_model") or car.get("model") or meta.get("car_model") or f"Vehicle#{idx}"
        price = car.get("price_wan") or car.get("price") or meta.get("price") or "未知"
        power = car.get("powertrain_type") or meta.get("powertrain_type") or ""
        rng = car.get("electric_range") or meta.get("electric_range") or ""
        snippet = str(car.get("text_snippet") or "")[:240]
        lines.append(
            f"[证据{idx}] 车型={model}, 价格={price}, 动力={power}, 续航={rng}, 摘要={snippet}"
        )
    for anchor in (evidence_anchors or [])[:5]:
        if isinstance(anchor, dict):
            lines.append(f"[账本锚点] {anchor.get('car_model', '')}: {anchor.get('metadata', {})}")
    return "\n".join(lines)


def verify_claims_with_nli(
    response_text: str,
    matched_cars: List[Dict[str, Any]],
    evidence_anchors: Optional[List[Dict[str, Any]]] = None,
    auditor_llm: Optional[Any] = None,
    nli_scorer: Optional[Callable[[str, str], float]] = None,
) -> Tuple[List[ClaimVerdict], List[str], str]:
    """
    Verify generated claims against retrieved evidence using either:
    - `auditor_llm` (`BaseChatModel.with_structured_output(FaithfulnessAuditOutput)`), or
    - `nli_scorer(premise, hypothesis) -> entailment_prob in [0, 1]`.

    Returns `(claim_verdicts, warnings, method_name)`.
    """
    evidence_text = _build_evidence_context(matched_cars, evidence_anchors)
    if not evidence_text or not response_text:
        return [], [], "evidence_ledger_cross_check"

    # Tier 1: Cross-encoder / NLI scorer function if injected
    if nli_scorer is not None:
        sentences = [
            s.strip()
            for s in re.split(r"[。！？!?;\n]+", response_text)
            if len(s.strip()) >= 8
        ]
        verdicts: List[ClaimVerdict] = []
        warnings: List[str] = []
        for sent in sentences[:8]:
            try:
                score = float(nli_scorer(evidence_text, sent))
            except Exception as exc:
                logger.debug(f"nli_scorer failed on sentence: {exc}")
                continue
            if score < 0.35:
                verdicts.append(
                    ClaimVerdict(
                        claim=sent,
                        label="CONTRADICTED" if score < 0.15 else "UNSUPPORTED",
                        reason=f"NLI entailment score={score:.2f}",
                    )
                )
                warnings.append(f"NLI 事实验证未通过 (score={score:.2f}): {sent[:60]}")
            else:
                verdicts.append(ClaimVerdict(claim=sent, label="ENTAILED", reason=f"score={score:.2f}"))
        return verdicts, warnings, "cross_encoder_nli"

    # Tier 2: LLM-as-Judge structured NLI audit
    if auditor_llm is not None and hasattr(auditor_llm, "with_structured_output"):
        try:
            structured = auditor_llm.with_structured_output(FaithfulnessAuditOutput)
            prompt = (
                "你是汽车导购系统的严格事实验证审计员（NLI Faithfulness Auditor）。\n"
                "请逐条核对【生成回复】中的车型参数、价格、配置和权益声明是否被【检索证据】严格支持。\n"
                "若回复中出现与证据矛盾的数字/配置（CONTRADICTED）或凭空捏造的车型/参数（UNSUPPORTED），请如实标注。\n\n"
                f"【检索证据】\n{evidence_text}\n\n"
                f"【生成回复】\n{response_text}\n"
            )
            audit_out = structured.invoke(prompt)
            if isinstance(audit_out, FaithfulnessAuditOutput):
                warnings = [
                    f"LLM-NLI 审计发现{v.label}: {v.claim[:50]} ({v.reason})"
                    for v in audit_out.claim_verdicts
                    if v.label in ("CONTRADICTED", "UNSUPPORTED")
                ]
                return audit_out.claim_verdicts, warnings, "llm_nli"
        except Exception as exc:
            logger.debug(f"auditor_llm structured NLI skipped/failed: {exc}")

    return [], [], "evidence_ledger_cross_check"


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
        evidence_anchors: Optional[List[Dict[str, Any]]] = None,
        auditor_llm: Optional[Any] = None,
        nli_scorer: Optional[Callable[[str, str], float]] = None,
    ) -> ReflectionReport:
        """Execute comprehensive online reflection review."""
        if not response_text:
            return ReflectionReport(sanitized_text="")

        matched_cars = matched_cars or []
        corrections: List[Dict[str, str]] = []

        # 1. Compliance guard
        compliant_text, compliance_warnings = check_sales_compliance(response_text)
        if compliant_text != response_text:
            corrections.append(
                {
                    "type": "COMPLIANCE_SANITIZATION",
                    "original": response_text[:100],
                    "replacement": compliant_text[:100],
                }
            )

        # 2. Prompt leak filter
        safe_text, leak_warnings = sanitize_prompt_leakage(compliant_text)
        if safe_text != compliant_text:
            corrections.append(
                {
                    "type": "PROMPT_LEAK_STRIPPED",
                    "original": compliant_text[:100],
                    "replacement": safe_text[:100],
                }
            )

        # 3. Multi-attribute numeric & spec hallucination check
        hallucination_warnings = verify_numeric_hallucinations(safe_text, matched_cars)

        # 4. Optional model-backed NLI / LLM faithfulness verification
        claim_verdicts, nli_warnings, method_name = verify_claims_with_nli(
            safe_text,
            matched_cars=matched_cars,
            evidence_anchors=evidence_anchors,
            auditor_llm=auditor_llm,
            nli_scorer=nli_scorer,
        )
        hallucination_warnings.extend(nli_warnings)

        all_warnings = compliance_warnings + leak_warnings + hallucination_warnings
        grounding_score = 1.0
        if claim_verdicts:
            entailed = sum(1 for v in claim_verdicts if v.label == "ENTAILED")
            grounding_score = round(entailed / max(len(claim_verdicts), 1), 2)
        if hallucination_warnings and not claim_verdicts:
            grounding_score -= 0.40 * len(hallucination_warnings)
        if compliance_warnings:
            grounding_score -= 0.30 * len(compliance_warnings)
        if leak_warnings:
            grounding_score -= 0.20 * len(leak_warnings)
        grounding_score = max(0.0, min(1.0, round(grounding_score, 2)))

        final_text = safe_text
        if hallucination_warnings and "官方参数" not in final_text:
            final_text += "\n（注：车辆具体续航、配置与权益以车企官方最新公布规格为准）"

        return ReflectionReport(
            is_compliant=len(compliance_warnings) == 0,
            hallucination_detected=len(hallucination_warnings) > 0,
            prompt_leak_detected=len(leak_warnings) > 0,
            sanitized_text=final_text,
            grounding_score=grounding_score,
            faithfulness_method=method_name,
            claim_verdicts=claim_verdicts,
            warnings=all_warnings,
            corrections=corrections,
        )


def reflect_and_guard(
    response_text: str, matched_cars: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, List[str]]:
    """Main entry point for Self-Reflection & Hallucination Defense."""
    report = ReflectionGate.evaluate(response_text, matched_cars)
    if report.warnings:
        logger.warning(f"Self-reflection triggered warnings: {report.warnings}")
    return report.sanitized_text, report.warnings


def audit_response_against_evidence(
    response_text: str,
    matched_cars: Optional[List[Dict[str, Any]]] = None,
    evidence_anchors: Optional[List[Dict[str, Any]]] = None,
    auditor_llm: Optional[Any] = None,
    nli_scorer: Optional[Callable[[str, str], float]] = None,
) -> ReflectionReport:
    """
    Audit generated reply against retrieved vehicles and evidence ledger anchors
    for price, range, spec consistency, and optional NLI faithfulness.
    """
    report = ReflectionGate.evaluate(
        response_text,
        matched_cars,
        evidence_anchors=evidence_anchors,
        auditor_llm=auditor_llm,
        nli_scorer=nli_scorer,
    )
    cars = matched_cars or []
    if not cars or not response_text:
        return report

    known_prices: List[float] = []
    for car in cars:
        if not isinstance(car, dict):
            continue
        meta = car.get("metadata") if isinstance(car.get("metadata"), dict) else {}
        for key in ("price_wan", "msrp_wan", "price"):
            val = car.get(key) if car.get(key) is not None else meta.get(key)
            if val is not None:
                m = _DIGIT_PATTERN.search(str(val))
                if m:
                    num = float(m.group(1))
                    if num > 1000:
                        num = num / 10000.0
                    if 1.0 <= num <= 500.0:
                        known_prices.append(num)
    for anchor in evidence_anchors or []:
        meta = anchor.get("metadata") if isinstance(anchor, dict) else {}
        if isinstance(meta, dict) and meta.get("price"):
            m = _DIGIT_PATTERN.search(str(meta["price"]))
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
            if claimed < min_p * 0.65 or claimed > max_p * 1.45:
                report.hallucination_detected = True
                report.warnings.append(
                    f"可能存在价格幻觉: 回复提及 {claimed:.2f} 万元，与证据账本已知车型价格区间 ({min_p:.2f}~{max_p:.2f} 万元) 存在较大偏差"
                )
                report.grounding_score = max(0.0, round(report.grounding_score - 0.35, 2))

    return report
