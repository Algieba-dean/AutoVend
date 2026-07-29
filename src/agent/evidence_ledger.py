"""
Verification Evidence Ledger for AutoVend Agent (src/agent/evidence_ledger.py).

Inspired by NousResearch Hermes-Agent verification_evidence.py.
Collects empirical evidence (phone number validation, 4S dealership verification, vehicle existence check)
before allowing Agent to claim task completion or confirm test drive reservations.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

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
        """Verify phone number format (11-digit Chinese mobile)."""
        if not phone:
            return False
        clean_phone = re.sub(r"\D", "", phone)
        is_valid = bool(re.match(r"^1[3-9]\d{9}$", clean_phone))

        self.evidences.append(
            VerificationEvidence(
                evidence_type="PHONE_VALIDATED",
                target_value=phone,
                verified=is_valid,
                details="符合中国大陆11位手机号标准" if is_valid else "手机号码格式无效",
            )
        )
        return is_valid

    def verify_car_model_exists(self, car_model: str, candidate_models: List[str]) -> bool:
        """Verify that selected car model exists in repository candidate models."""
        if not car_model:
            return False
        is_valid = any(car_model.lower() in candidate.lower() or candidate.lower() in car_model.lower() for candidate in candidate_models)

        self.evidences.append(
            VerificationEvidence(
                evidence_type="CAR_MODEL_VERIFIED",
                target_value=car_model,
                verified=is_valid,
                details=f"在候选库 {len(candidate_models)} 款车型中核验匹配成功" if is_valid else "未在数据库中找到该车型",
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
                details="已核验试驾4S店名称" if is_valid else "缺缺试驾门店信息",
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
