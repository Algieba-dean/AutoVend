"""
Industrial-Grade Dual-Check Guardrail (src/agent/guardrail/compliance.py).

Prevents ungrammatical regex inline replacements by using complete safe fallbacks
when severe legal or sales compliance redlines are crossed.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

COMPLIANCE_FALLBACK_RESPONSE = (
    "关于您咨询的具体购车优惠与限时购车权益，由于不同车型的区域补贴和门店金融方案实时变动，"
    "我建议为您预约就近的官方授权 4S 体验中心，由专属产品专家为您出具精准的现场合同报价单。所有开票及过户流程严格遵循国家税法规定。"
)

PROHIBITED_COMPLIANCE_KEYWORDS: List[str] = [
    "保证全网最低价",
    "保证全国最低价",
    "保证最低价",
    "全网最低",
    "绝对第一",
    "百分百包过",
    "零故障",
    "承诺包过户避税",
    "保证终身免费充加电",
    "零首付免征信秒批",
    "免征信包批",
    "免息无门槛",
    "黑户也能办",
    "黑户可办",
    "绝对不会自燃",
    "永不自燃",
    "任何碰撞保不死",
    "自动驾驶出事车企全赔",
    "出事车企全赔",
    "假一赔十",
    "买贵包退差价",
]

_COMPILED_COMPLIANCE_RE = re.compile(
    "|".join(re.escape(kw) for kw in PROHIBITED_COMPLIANCE_KEYWORDS)
    + r"|(?:100%|百分百)(?:安全|不坏|通过|批准)|(?:绝对|肯定|保证)(?:最低|第一|全赔|免税)"
)


@dataclass
class OutboundGuardrailResult:
    guarded_text: str
    is_compliant: bool
    violations: List[str] = field(default_factory=list)


class DualStreamComplianceGuard:
    """
    Independent, low-latency outbound compliance guardrail (<1ms precompiled regex).
    Decoupled from streaming and full hallucination reflection so it can guard
    any final response before delivery.
    """

    @classmethod
    def inspect(cls, generated_text: str) -> OutboundGuardrailResult:
        if not generated_text:
            return OutboundGuardrailResult(guarded_text=generated_text, is_compliant=True)
        matches = _COMPILED_COMPLIANCE_RE.findall(generated_text)
        if matches:
            unique = list(dict.fromkeys(str(m) for m in matches if m))
            logger.warning(
                f"DualStreamComplianceGuard intercepted outbound compliance violation(s): {unique}"
            )
            return OutboundGuardrailResult(
                guarded_text=COMPLIANCE_FALLBACK_RESPONSE,
                is_compliant=False,
                violations=unique,
            )
        return OutboundGuardrailResult(guarded_text=generated_text, is_compliant=True)

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
        res = cls.inspect(generated_text)
        return res.guarded_text, res.is_compliant
