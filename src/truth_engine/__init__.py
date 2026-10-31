"""
Consumer Truth & Anti-Marketing Fluff Engine (src/truth_engine).
"""

from src.truth_engine.debiaser import MarketingDebiaser
from src.truth_engine.miit_platform import MIITSpecsPlatform
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
from src.truth_engine.price_valuation import PriceValuationEngine
from src.truth_engine.reliability_cases import ReliabilityCaseRepository
from src.truth_engine.service import TruthEngineService

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
    "MarketingDebiaser",
    "MIITSpecsPlatform",
    "ReliabilityCaseRepository",
    "PriceValuationEngine",
    "TruthEngineService",
]
