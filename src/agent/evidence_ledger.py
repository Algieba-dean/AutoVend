"""
Verification Evidence Ledger for AutoVend Agent (src/agent/evidence_ledger.py).

Inspired by NousResearch Hermes-Agent verification_evidence.py.
Collects empirical evidence (phone number validation, 4S dealership verification, vehicle existence check)
before allowing Agent to claim task completion or confirm test drive reservations.
"""

import logging
import re
from typing import Any, List, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class VerificationEvidence(BaseModel):
    """A classified ground-truth verification fact."""

    evidence_type: str  # e.g., "PHONE_VALIDATED", "CAR_MODEL_VERIFIED", "STORE_VERIFIED"
    target_value: str
    verified: bool = False
    details: str = ""


class VerificationEvidenceLedger:
    """
    Evidence ledger ensuring Agent collects empirical ground truth before stage progression.
    """

    def __init__(self):
        self.evidences: List[VerificationEvidence] = []

    def verify_phone_number(self, phone: str) -> bool:
        """Verify phone number format (standard 11-digit mobile or fixed line)."""
        if not phone:
            return False
        clean_phone = re.sub(r"\D", "", phone)
        is_standard_mobile = bool(re.match(r"^1[3-9]\d{9}$", clean_phone))
        is_standard_landline = bool(re.match(r"^0\d{9,11}$", clean_phone))

        is_valid = is_standard_mobile or is_standard_landline

        self.evidences.append(
            VerificationEvidence(
                evidence_type="PHONE_VALIDATED",
                target_value=phone,
                verified=is_valid,
                details="符合联系电话核验标准" if is_valid else "手机号码格式无效",
            )
        )
        return is_valid

    def verify_car_model_exists(self, car_model: str, candidate_models: List[str]) -> bool:
        """Verify that selected car model exists in repository candidate models."""
        if not car_model:
            return False
        is_valid = any(
            car_model.lower() in candidate.lower() or candidate.lower() in car_model.lower()
            for candidate in candidate_models
        )

        self.evidences.append(
            VerificationEvidence(
                evidence_type="CAR_MODEL_VERIFIED",
                target_value=car_model,
                verified=is_valid,
                details=f"在候选库 {len(candidate_models)} 款车型中核验匹配成功"
                if is_valid
                else "未在数据库中找到该车型",
            )
        )
        return is_valid

    def verify_4s_store(self, store_name: str) -> bool:
        """Verify 4S dealership name is not empty."""
        is_valid = bool(store_name and len(store_name.strip()) >= 2)
        self.evidences.append(
            VerificationEvidence(
                evidence_type="STORE_VERIFIED",
                target_value=store_name,
                verified=is_valid,
                details="已核验试驾4S店名称" if is_valid else "缺少试驾门店信息",
            )
        )
        return is_valid

    def verify_budget(self, budget_str: str) -> bool:
        """Verify budget string contains a valid positive price bound in 万元 or 元."""
        if not budget_str:
            return False
        nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", budget_str)]
        is_valid = bool(nums and any((0 < n <= 2000) or (1000 <= n <= 50_000_000) for n in nums))

        self.evidences.append(
            VerificationEvidence(
                evidence_type="BUDGET_VERIFIED",
                target_value=budget_str,
                verified=is_valid,
                details=f"已核验购车预算数值 ({budget_str})" if is_valid else "预算格式无效或未指定明确区间",
            )
        )
        return is_valid


    def verify_date_time(self, date_str: Any, time_str: Any) -> bool:
        """Verify reservation date and time are provided and plausible."""
        d_val = str(date_str).strip() if date_str is not None else ""
        t_val = str(time_str).strip() if time_str is not None else ""
        valid_date = bool(d_val and len(d_val) >= 2)
        valid_time = bool(t_val and len(t_val) >= 2)
        is_valid = valid_date and valid_time

        self.evidences.append(
            VerificationEvidence(
                evidence_type="DATE_TIME_VERIFIED",
                target_value=f"{date_str} {time_str}".strip(),
                verified=is_valid,
                details="已核验试驾日期与具体时段" if is_valid else f"预约时段缺失 (日期:{date_str}, 时间:{time_str})",
            )
        )
        return is_valid

    def can_confirm_reservation(self) -> Tuple[bool, List[str]]:
        """
        Check if all required reservation evidences are present and verified.
        Returns (can_confirm: bool, missing_evidences: List[str]).
        """
        required = ["PHONE_VALIDATED", "STORE_VERIFIED"]
        verified_types = {e.evidence_type for e in self.evidences if e.verified}
        missing = [r for r in required if r not in verified_types]

        return len(missing) == 0, missing

    def validate_stage_transition(
        self,
        from_stage: Any,
        to_stage: Any,
        state: Any,
    ) -> Tuple[bool, List[str]]:
        """
        Enforce evidence-ledger facts before allowing stage progression.
        Auto-audits current state fields into the ledger if not already recorded.
        Returns (is_allowed: bool, missing_evidence_reasons: List[str]).
        """
        from src.agent.schemas import Stage

        # Auto-audit state attributes into evidence ledger
        if getattr(state, "needs", None) and state.needs.explicit.price:
            if not any(e.evidence_type == "BUDGET_VERIFIED" and e.verified for e in self.evidences):
                self.verify_budget(state.needs.explicit.price)

        if getattr(state, "matched_cars", None):
            candidate_names = [c.get("car_model", "") for c in state.matched_cars if c.get("car_model")]
            car_selected = getattr(state, "selected_car", None) or (
                candidate_names[0] if candidate_names else ""
            )
            if car_selected and not any(e.evidence_type == "CAR_MODEL_VERIFIED" and e.verified for e in self.evidences):
                self.verify_car_model_exists(car_selected, candidate_names)

        if getattr(state, "reservation", None):
            res = state.reservation
            if res.reservation_phone_number and not any(e.evidence_type == "PHONE_VALIDATED" and e.verified for e in self.evidences):
                self.verify_phone_number(res.reservation_phone_number)
            if res.reservation_location and not any(e.evidence_type == "STORE_VERIFIED" and e.verified for e in self.evidences):
                self.verify_4s_store(res.reservation_location)
            if res.reservation_date and res.reservation_time and not any(e.evidence_type == "DATE_TIME_VERIFIED" and e.verified for e in self.evidences):
                self.verify_date_time(res.reservation_date, res.reservation_time)

        verified_types = {e.evidence_type for e in self.evidences if e.verified}
        missing_reasons: List[str] = []

        if to_stage == Stage.CAR_SELECTION and from_stage == Stage.NEEDS_ANALYSIS:
            if "BUDGET_VERIFIED" not in verified_types:
                missing_reasons.append("证据账本缺失已核验的购车预算凭证 (BUDGET_VERIFIED)")

        elif to_stage == Stage.RESERVATION_4S and from_stage == Stage.CAR_SELECTION:
            if not getattr(state, "matched_cars", None) or len(state.matched_cars) == 0:
                missing_reasons.append("证据账本缺失已推荐并核验的候选车型凭证 (CAR_MODEL_VERIFIED)")

        elif to_stage == Stage.RESERVATION_CONFIRMATION and from_stage == Stage.RESERVATION_4S:
            if "STORE_VERIFIED" not in verified_types:
                missing_reasons.append("证据账本缺失已核验的4S门店凭证 (STORE_VERIFIED)")
            if "DATE_TIME_VERIFIED" not in verified_types:
                missing_reasons.append("证据账本缺失已核验的预约时段凭证 (DATE_TIME_VERIFIED)")

        elif to_stage == Stage.FAREWELL and from_stage == Stage.RESERVATION_CONFIRMATION:
            res = getattr(state, "reservation", None)
            if not res or not res.reservation_phone_number:
                missing_reasons.append("证据账本缺失有效的客户联系电话凭证 (PHONE_VALIDATED)")
            if not res or not res.reservation_location:
                missing_reasons.append("证据账本缺失已核验的4S门店凭证 (STORE_VERIFIED)")

        return len(missing_reasons) == 0, missing_reasons

