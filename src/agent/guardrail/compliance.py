"""
Industrial-Grade Dual-Check Guardrail (src/agent/guardrail/compliance.py).

Prevents ungrammatical regex inline replacements by using complete safe fallbacks
when severe legal or sales compliance redlines are crossed.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

COMPLIANCE_FALLBACK_RESPONSE = (
    "关于您咨询的具体购车优惠与限时购车权益，由于不同车型的区域补贴和门店金融方案实时变动，"
    "我建议为您预约就近的官方授权 4S 体验中心，由专属产品专家为您出具精准的现场合同报价单。所有开票及过户流程严格遵循国家税法规定。"
)

# TOY IMPLEMENTATION: Hardcoded keyword string matching blacklist for sales and legal compliance.
# Completely blind to evasion tricks, homophones, or conversational rephrasing (e.g., "保你不死", "全网至低").
# In production, replace with a dedicated compliance guardrail LLM, NeMo Guardrails, or semantic moderation classifier.
PROHIBITED_COMPLIANCE_KEYWORDS: List[str] = [
    "保证全网最低价",
    "保证全国最低价",
    "保证最低价",
    "承诺包过户避税",
    "保证终身免费充加电",
    "零首付免征信秒批",
    "黑户也能办",
    "黑户可办",
    "绝对不会自燃",
    "任何碰撞保不死",
    "自动驾驶出事车企全赔",
    "出事车企全赔",
    "假一赔十",
    "买贵包退差价",
]


class DualStreamComplianceGuard:
    """
    Dual-check guardrail that intercepts generated replies before delivery to client.
    Replaces ungrammatical regex word slicing with clean professional fallback explanations.
    """

    @classmethod
    def guard_output(
        cls,
        generated_text: str,
        matched_cars: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, bool]:
        """
        Inspect generated response.
        If strict compliance violations are found, cleanly fallback rather than stitching broken text.
        Returns: (guarded_text, is_compliant)
        """
        if not generated_text:
            return generated_text, True

        violations = [kw for kw in PROHIBITED_COMPLIANCE_KEYWORDS if kw in generated_text]
        if violations:
            logger.warning(
                f"DualStreamComplianceGuard intercepted compliance violation(s): {violations}. "
                f"Falling back to compliant response."
            )
            return COMPLIANCE_FALLBACK_RESPONSE, False

        return generated_text, True
