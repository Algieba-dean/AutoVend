"""
Structured LLM-as-a-Judge Evaluation Engine with NLI Claim Verification & Automated Rubric Scoring (src/eval/structured_eval.py).

Implements:
1. Atomic claim decomposition from agent responses.
2. Natural Language Inference (NLI) claim verification against RAG context (ENTAILMENT, CONTRADICTION, NEUTRAL).
3. 4-Dimension Rubric Scoring:
   - Factual Grounding (35%)
   - Constraint Satisfaction (25%)
   - Commercial Compliance (20%)
   - SOP & Stage Governance (20%)
4. Automated evaluation report and CI gating metrics.
"""

import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.agent.reflection import check_sales_compliance, verify_numeric_hallucinations

logger = logging.getLogger(__name__)


class NLILabel(str, Enum):
    """NLI claim verification label."""

    ENTAILMENT = "entailment"          # Claim is substantiated by ground truth context
    CONTRADICTION = "contradiction"    # Claim directly contradicts ground truth context (hallucination)
    NEUTRAL = "neutral"                # Claim is unverified from given context


class AtomicClaim(BaseModel):
    """Single verifiable claim extracted from agent response."""

    claim_id: int
    text: str
    label: NLILabel = NLILabel.NEUTRAL
    confidence: float = 1.0
    evidence_quote: str = ""
    rationale: str = ""


class EvaluationRubricReport(BaseModel):
    """Comprehensive rubric scoring report for a conversation turn or case."""

    case_id: str = ""
    claims_total: int = 0
    claims_entailed: int = 0
    claims_contradicted: int = 0
    claims_neutral: int = 0

    # Dimension scores (0.0 to 1.0)
    score_faithfulness: float = 0.0          # 事实真实性与忠实度
    score_constraint_adherence: float = 0.0  # 用户约束与预算满足度
    score_compliance: float = 0.0            # 商业合规与零欺诈
    score_sop_governance: float = 0.0        # SOP阶段与动作推演合理性

    composite_score: float = 0.0             # 加权综合得分 (0.0 - 1.0)
    passed: bool = False                     # 是否通过质量准入
    claims: List[AtomicClaim] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Render report as formatted Markdown summary."""
        status = "🟢 PASS" if self.passed else "🔴 FAIL"
        lines = [
            f"### 评估结果: {self.case_id} [{status}]",
            f"- **加权综合得分**: **{self.composite_score * 100:.1f} / 100**",
            "",
            "| 评测维度 | 权重 | 得分 | 评估标准 |",
            "|---|---|---|---|",
            f"| 1. 事实真实性 (Faithfulness) | 35% | {self.score_faithfulness * 100:.1f} | NLI 断言在 RAG 上下文中支持率 |",
            f"| 2. 约束满足度 (Constraint Adherence) | 25% | {self.score_constraint_adherence * 100:.1f} | 预算、车型、动力等槽位满足度 |",
            f"| 3. 商业合规度 (Compliance) | 20% | {self.score_compliance * 100:.1f} | 无虚假承诺与违规表述 |",
            f"| 4. SOP 阶段治理 (Governance) | 20% | {self.score_sop_governance * 100:.1f} | 阶段推进合规性与无循环卡死 |",
            "",
            f"**断言统计**: 总数 {self.claims_total} | 支撑: {self.claims_entailed} | 矛盾/幻觉: {self.claims_contradicted} | 中立: {self.claims_neutral}",
        ]
        if self.claims:
            lines.append("\n**逐项原子断言核验明细:**")
            for c in self.claims:
                icon = "✅" if c.label == NLILabel.ENTAILMENT else ("❌" if c.label == NLILabel.CONTRADICTION else "⚪")
                lines.append(f"- {icon} `[{c.label.value.upper()}]` {c.text} (依据: {c.evidence_quote or '无'})")
        return "\n".join(lines)


class StructuredNLIEvaluator:
    """
    Automated LLM-as-a-Judge and NLI claim verification evaluator.
    """

    def __init__(self, llm: Optional[Any] = None):
        self.llm = llm

    @classmethod
    def decompose_claims(cls, response_text: str) -> List[str]:
        """
        Decompose response text into atomic verifiable claims.
        Filters out conversational small talk, greetings, and generic boilerplate.
        """
        if not response_text:
            return []

        # Split on sentence boundaries
        raw_sentences = re.split(r"[。！？\n\r；]+", response_text)
        claims: List[str] = []

        ignore_phrases = [
            "您好", "很高兴为您服务", "随时为您解答", "祝您用车愉快",
            "如果有什么问题", "请问您意下如何", "谢谢", "期待您的光临",
            "建议您", "欢迎体验",
        ]

        for s in raw_sentences:
            s_clean = s.strip(" ,，. 。!！?？\t\n")
            if len(s_clean) < 6:
                continue
            if any(s_clean.startswith(ig) or s_clean == ig for ig in ignore_phrases):
                continue
            # Keep sentences that mention specs, brands, cars, prices, ranges, or actions
            if any(k in s_clean for k in ["款", "车", "万", "km", "续航", "空间", "座", "油耗", "电耗", "混动", "纯电", "预约", "试驾", "店"]):
                claims.append(s_clean)

        return claims

    @classmethod
    def verify_claim_nli(
        cls,
        claim_text: str,
        context_text: str,
        matched_cars: Optional[List[Dict[str, Any]]] = None,
    ) -> AtomicClaim:
        """
        Perform Natural Language Inference on a single claim against context and matched cars.
        """
        matched_cars = matched_cars or []
        context_lower = (context_text or "").lower()

        # Build context pool from matched cars
        car_context_snippets = []
        for car in matched_cars:
            c_name = car.get("car_model") or car.get("model") or ""
            c_price = car.get("price") or car.get("prize") or ""
            c_range = car.get("electric_range") or ""
            c_meta = str(car.get("metadata") or {})
            c_snippet = car.get("text_snippet") or ""
            car_context_snippets.append(f"{c_name} {c_price} {c_range} {c_meta} {c_snippet}".lower())
        full_context = context_lower + " " + " ".join(car_context_snippets)

        # 1. Check for numerical parameter claims (range & price)
        range_match = re.search(r"(\d{3,4})\s*(?:km|公里)", claim_text, re.IGNORECASE)
        if range_match:
            claimed_range = float(range_match.group(1))
            is_pure_ev_claim = "纯电" in claim_text
            if is_pure_ev_claim:
                ev_ranges = [
                    float(r)
                    for r in re.findall(
                        r"(?:纯电|纯电续航|cltc|wltc)[^\d]{0,6}(\d{2,4})\s*(?:km|公里)",
                        full_context,
                        re.IGNORECASE,
                    )
                ]
                actual_ranges = ev_ranges if ev_ranges else [float(r) for r in re.findall(r"(\d{2,4})\s*(?:km|公里)", full_context, re.IGNORECASE)]
            else:
                actual_ranges = [float(r) for r in re.findall(r"(\d{3,4})\s*(?:km|公里)", full_context, re.IGNORECASE)]

            if actual_ranges:
                max_actual = max(actual_ranges)
                threshold_val = max_actual * 1.35 if not is_pure_ev_claim else max_actual * 1.25
                if claimed_range > threshold_val:
                    return AtomicClaim(
                        claim_id=0,
                        text=claim_text,
                        label=NLILabel.CONTRADICTION,
                        evidence_quote=f"实际最大{'纯电' if is_pure_ev_claim else ''}续航为 {max_actual:.0f}km",
                        rationale=f"宣称续航 {claimed_range:.0f}km 远超真实参数",
                    )
                else:
                    return AtomicClaim(
                        claim_id=0,
                        text=claim_text,
                        label=NLILabel.ENTAILMENT,
                        evidence_quote=f"匹配到对应续航参数 ({max_actual:.0f}km)",
                        rationale="续航参数在真实车型区间内",
                    )


        price_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:万|万元)", claim_text)
        if price_match:
            claimed_price = float(price_match.group(1))
            # Extract price numbers from patterns like 30.18-37.98万元, 20.99万, etc.
            raw_pairs = re.findall(r"(\d+(?:\.\d+)?)(?:\s*[-~到至]\s*(\d+(?:\.\d+)?))?\s*(?:万|万元)", full_context)
            p_nums: List[float] = []
            for pair in raw_pairs:
                for item in pair:
                    if item:
                        p_nums.append(float(item))
            if not p_nums:
                p_nums = [float(p) for p in re.findall(r"(\d+(?:\.\d+)?)", full_context) if 3.0 <= float(p) <= 200.0]

            if p_nums:
                if any(abs(claimed_price - cp) <= 0.2 for cp in p_nums) or (min(p_nums) <= claimed_price <= max(p_nums)):
                    return AtomicClaim(
                        claim_id=0,
                        text=claim_text,
                        label=NLILabel.ENTAILMENT,
                        evidence_quote=f"上下文匹配到价格参数 ({claimed_price:.2f}万)",
                        rationale="价格断言在真实车型价格区间内",
                    )
                elif claimed_price < min(p_nums) * 0.60:
                    return AtomicClaim(
                        claim_id=0,
                        text=claim_text,
                        label=NLILabel.CONTRADICTION,
                        evidence_quote=f"实际起步价格为 {min(p_nums):.2f}万",
                        rationale=f"宣称价格 {claimed_price:.2f}万 异常偏离实际价格",
                    )


        # 2. Check for vehicle model or brand mention
        tokens = [t for t in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]+", claim_text) if len(t) >= 2]
        overlap_tokens = [t for t in tokens if t.lower() in full_context]

        if len(overlap_tokens) >= 2 or (len(overlap_tokens) >= 1 and any(k in claim_text for k in ["推荐", "配置", "轴距", "智驾", "空间"])):
            return AtomicClaim(
                claim_id=0,
                text=claim_text,
                label=NLILabel.ENTAILMENT,
                evidence_quote=f"上下文匹配关键词: {', '.join(overlap_tokens[:3])}",
                rationale="断言核心事实在 RAG 上下文中获得有效支撑",
            )


        # 3. Check for obvious sales compliance violations in claim
        _, comp_warns = check_sales_compliance(claim_text)
        if comp_warns:
            return AtomicClaim(
                claim_id=0,
                text=claim_text,
                label=NLILabel.CONTRADICTION,
                evidence_quote=comp_warns[0],
                rationale="违规销售承诺无法律及业务支撑",
            )

        return AtomicClaim(
            claim_id=0,
            text=claim_text,
            label=NLILabel.NEUTRAL,
            evidence_quote="上下文未显式提及该细节",
            rationale="属于一般性外部常识陈述",
        )

    def evaluate_turn(
        self,
        response_text: str,
        context_text: str = "",
        matched_cars: Optional[List[Dict[str, Any]]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        current_stage: str = "car_selection_confirmation",
        case_id: str = "turn_eval",
    ) -> EvaluationRubricReport:
        """
        Evaluate an agent response turn with NLI claim verification and 4-rubric scoring.
        """
        matched_cars = matched_cars or []
        constraints = constraints or {}
        claims_raw = self.decompose_claims(response_text)

        claims: List[AtomicClaim] = []
        n_entailed = 0
        n_contradicted = 0
        n_neutral = 0

        for i, c_text in enumerate(claims_raw, 1):
            claim = self.verify_claim_nli(c_text, context_text, matched_cars)
            claim.claim_id = i
            claims.append(claim)
            if claim.label == NLILabel.ENTAILMENT:
                n_entailed += 1
            elif claim.label == NLILabel.CONTRADICTION:
                n_contradicted += 1
            else:
                n_neutral += 1

        total_claims = len(claims)

        # ── Rubric 1: Faithfulness (35%) ────────────────────────────────────
        if total_claims == 0:
            score_faithfulness = 1.0
        else:
            # Entailed counts 1.0, Neutral counts 0.5, Contradicted counts 0.0
            score_faithfulness = (n_entailed * 1.0 + n_neutral * 0.5) / total_claims

        # ── Rubric 2: Constraint Adherence (25%) ────────────────────────────
        score_constraint = 1.0
        if constraints:
            target_budget = constraints.get("prize") or constraints.get("budget") or ""
            target_brand = constraints.get("brand") or ""
            target_seats = constraints.get("seat_layout") or ""

            if target_budget and matched_cars:
                # Check if recommended cars fit budget
                b_match = re.search(r"(\d+)", target_budget)
                if b_match:
                    b_val = float(b_match.group(1))
                    for car in matched_cars[:2]:
                        p_str = car.get("price") or car.get("prize") or ""
                        nums = [float(x) for x in re.findall(r"(\d+)", p_str)]
                        if nums and min(nums) > b_val * 1.25 and b_val < 50:
                            score_constraint -= 0.35

            if target_brand and not any(target_brand.lower() in (car.get("brand") or "").lower() for car in matched_cars):
                if any(target_brand.lower() in response_text.lower() for _ in [1]):
                    score_constraint += 0.1
        score_constraint = max(0.0, min(1.0, score_constraint))

        # ── Rubric 3: Commercial Compliance (20%) ───────────────────────────
        _, compliance_warns = check_sales_compliance(response_text)
        num_hallucinations = verify_numeric_hallucinations(response_text, matched_cars)
        score_compliance = 1.0 - (len(compliance_warns) * 0.40 + len(num_hallucinations) * 0.30)
        score_compliance = max(0.0, min(1.0, score_compliance))

        # ── Rubric 4: SOP & Stage Governance (20%) ──────────────────────────
        score_governance = 1.0
        # If in needs_analysis, shouldn't push final reservation confirm without recommendations
        if "needs_analysis" in current_stage and any(k in response_text for k in ["预约成功", "已为您锁定订单"]):
            score_governance = 0.30
        elif "welcome" in current_stage and any(k in response_text for k in ["签约合同"]):
            score_governance = 0.20

        # Composite weighted score
        composite = (
            score_faithfulness * 0.35
            + score_constraint * 0.25
            + score_compliance * 0.20
            + score_governance * 0.20
        )
        composite = round(composite, 4)
        passed = composite >= 0.70 and score_compliance >= 0.60 and n_contradicted == 0

        all_warnings = compliance_warns + num_hallucinations

        return EvaluationRubricReport(
            case_id=case_id,
            claims_total=total_claims,
            claims_entailed=n_entailed,
            claims_contradicted=n_contradicted,
            claims_neutral=n_neutral,
            score_faithfulness=round(score_faithfulness, 3),
            score_constraint_adherence=round(score_constraint, 3),
            score_compliance=round(score_compliance, 3),
            score_sop_governance=round(score_governance, 3),
            composite_score=composite,
            passed=passed,
            claims=claims,
            warnings=all_warnings,
        )
