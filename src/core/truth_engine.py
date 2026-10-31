"""
Core Consumer Truth & Anti-Marketing Fluff Facade (src/core/truth_engine.py).

Provides architectural re-exports and facade access to TruthEngineService
for cross-package integration without violating agent layer import boundaries.
"""

from typing import Any, Dict, List, Optional

from src.truth_engine.models import (
    BatterySafetyRecord,
    BrakeChassisControversy,
    ChargingCurveReality,
    CrashTestSummary,
    DepreciationValuation,
    DriveAwayPriceCalculation,
    FluffCategory,
    FluffSeverity,
    InfotainmentReliability,
    MarketingFluffItem,
    MIITVehicleDeclaration,
    RealWorldRangeGap,
    VehicleTruthReport,
)
from src.truth_engine.service import TruthEngineService


class TruthEngineFacade:
    """Facade for accessing TruthEngine functionality from agent and backend layers."""

    _instance: Optional["TruthEngineFacade"] = None

    def __init__(self):
        self._service = TruthEngineService.get_instance()

    @classmethod
    def get_instance(cls) -> "TruthEngineFacade":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def deconstruct_vehicle_specs(self, car_model: str) -> Dict[str, Any]:
        """Dismantle public MIIT vehicle specifications and national standards."""
        return self._service.deconstruct_vehicle_specs(car_model)

    def uncover_marketing_fluff(
        self, claim_or_text: str, car_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Strip marketing fluff and calculate nominal vs real-world gaps."""
        return self._service.uncover_marketing_fluff(claim_or_text, car_model=car_model)

    def get_real_owner_feedback_and_safety_cases(
        self, car_model: str, query_filter: str = ""
    ) -> Dict[str, Any]:
        """Retrieve real owner defect cases, safety controversies, and crash tests."""
        return self._service.get_real_owner_feedback_and_safety_cases(
            car_model=car_model, query_filter=query_filter
        )

    def calculate_drive_away_price(
        self,
        car_model: str,
        msrp_wan: Optional[float] = None,
        cash_discount: float = 0.0,
        perks_discount: float = 0.0,
        trade_in_subsidy: float = 0.0,
    ) -> Dict[str, Any]:
        """Calculate transparent drive-away price and depreciation."""
        return self._service.calculate_drive_away_price(
            car_model=car_model,
            msrp_wan=msrp_wan,
            cash_discount=cash_discount,
            perks_discount=perks_discount,
            trade_in_subsidy=trade_in_subsidy,
        )

    def generate_truth_sales_note(
        self, query_text: str, car_model: Optional[str] = None
    ) -> Optional[str]:
        """Generate debiased consumer truth sales note for Agent prompt injection."""
        return self._service.generate_truth_sales_note(query_text, car_model=car_model)

    def build_full_truth_report(self, car_model: str) -> VehicleTruthReport:
        """Build full vehicle truth report object."""
        return self._service.build_full_truth_report(car_model)

    def format_full_truth_report_markdown(self, car_model: str) -> str:
        """Format an end-to-end comprehensive truth report in Markdown."""
        return self._service.format_full_truth_report_markdown(car_model)

    def extract_model_name_from_text(self, text: str) -> Optional[str]:
        """Extract canonical vehicle model name from free text."""
        return self._service.miit_platform.extract_model_name_from_text(text)

    def get_national_standards(self) -> Dict[str, Dict[str, Any]]:
        """Retrieve statutory national standards reference database."""
        return self._service.get_national_standards()

    def get_known_models(self) -> List[str]:
        """Retrieve list of all benchmark models in the truth engine."""
        return self._service.get_known_models()


__all__ = [
    "FluffCategory",
    "FluffSeverity",
    "MarketingFluffItem",
    "RealWorldRangeGap",
    "ChargingCurveReality",
    "InfotainmentReliability",
    "BatterySafetyRecord",
    "BrakeChassisControversy",
    "CrashTestSummary",
    "DepreciationValuation",
    "DriveAwayPriceCalculation",
    "MIITVehicleDeclaration",
    "VehicleTruthReport",
    "TruthEngineService",
    "TruthEngineFacade",
]
