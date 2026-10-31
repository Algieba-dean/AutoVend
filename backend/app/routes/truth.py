"""
Consumer Truth, Anti-Marketing Fluff & Regulatory Deconstruction API Routes.
(backend/app/routes/truth.py)

Provides REST endpoints for querying MIIT regulatory specifications,
debunking marketing fluff, retrieving real owner defect records and crash ratings,
calculating transparent zero-markup drive-away pricing, and fetching statutory GB standards.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.truth_engine import TruthEngineFacade

router = APIRouter(prefix="/api/truth", tags=["truth_engine"])


class DebiasRequest(BaseModel):
    claim: str = Field(..., description="Marketing claim or feature text to deconstruct")
    car_model: Optional[str] = Field(None, description="Optional vehicle model name")


class PricingRequest(BaseModel):
    car_model: str = Field(..., description="Target vehicle model name")
    msrp_wan: Optional[float] = Field(None, description="Official MSRP in 10,000 RMB (万)")
    cash_discount: float = Field(0.0, description="Direct cash discount in 10,000 RMB (万)")
    perks_discount: float = Field(0.0, description="Option pack/perks discount in 10,000 RMB (万)")
    trade_in_subsidy: float = Field(0.0, description="Trade-in subsidy in 10,000 RMB (万)")


@router.get("/deconstruct")
def deconstruct_specs(
    car_model: str = Query(..., description="Vehicle model name, e.g. '小米SU7 Max', '比亚迪汉EV'")
) -> Dict[str, Any]:
    """
    Deconstruct public MIIT vehicle specifications against statutory national standards (GB).
    Exposes real curb weight, battery net mass ratio, motor rated continuous power, and top speed.
    """
    car_model_clean = car_model.strip()
    if not car_model_clean:
        raise HTTPException(status_code=400, detail="car_model parameter must not be empty")

    facade = TruthEngineFacade.get_instance()
    return facade.deconstruct_vehicle_specs(car_model_clean)


@router.post("/debias")
def debias_marketing(request: DebiasRequest) -> Dict[str, Any]:
    """
    Identify and expose invalid/misleading marketing fluff, revealing nominal vs real-world physical gaps.
    """
    claim = request.claim.strip()
    if not claim and not request.car_model:
        raise HTTPException(status_code=400, detail="claim or car_model must be provided")

    facade = TruthEngineFacade.get_instance()
    return facade.uncover_marketing_fluff(claim, car_model=request.car_model)


@router.get("/reliability")
def get_reliability_and_safety(
    car_model: str = Query(..., description="Vehicle model name"),
    query_filter: str = Query("", description="Optional filter keyword (e.g. '黑屏', '刹车踏板', '自燃')"),
) -> Dict[str, Any]:
    """
    Retrieve real owner failure rates (infotainment blackouts, OTA regressions),
    battery safety records, brake/chassis engineering controversies, and C-IASI crash test ratings.
    """
    car_model_clean = car_model.strip()
    if not car_model_clean:
        raise HTTPException(status_code=400, detail="car_model parameter must not be empty")

    facade = TruthEngineFacade.get_instance()
    return facade.get_real_owner_feedback_and_safety_cases(car_model_clean, query_filter=query_filter)


@router.post("/pricing")
def calculate_transparent_price(request: PricingRequest) -> Dict[str, Any]:
    """
    Calculate transparent real drive-away price, detail purchase tax, insurance,
    and expose 4S dealership hidden fees (outbound fees, finance service charges).
    """
    car_model_clean = request.car_model.strip()
    if not car_model_clean:
        raise HTTPException(status_code=400, detail="car_model must not be empty")

    facade = TruthEngineFacade.get_instance()
    return facade.calculate_drive_away_price(
        car_model=car_model_clean,
        msrp_wan=request.msrp_wan,
        cash_discount=request.cash_discount,
        perks_discount=request.perks_discount,
        trade_in_subsidy=request.trade_in_subsidy,
    )


@router.get("/standards")
def get_national_standards() -> Dict[str, Any]:
    """
    Retrieve statutory national standards reference database (GB 38031, GB 7258, GB/T 18386, GB/T 31498)
    and their engineering reality vs statutory threshold gaps.
    """
    facade = TruthEngineFacade.get_instance()
    return {
        "count": len(facade.get_national_standards()),
        "standards": facade.get_national_standards(),
    }


@router.get("/models")
def list_known_models() -> Dict[str, Any]:
    """
    Retrieve all cataloged benchmark models available in the Consumer Truth Engine.
    """
    facade = TruthEngineFacade.get_instance()
    models = facade.get_known_models()
    return {
        "count": len(models),
        "models": models,
    }


@router.get("/report/{car_model}")
def get_full_truth_report(car_model: str) -> Dict[str, Any]:
    """
    Generate an end-to-end comprehensive truth report for a vehicle model.
    """
    car_model_clean = car_model.strip()
    if not car_model_clean:
        raise HTTPException(status_code=400, detail="car_model must not be empty")

    facade = TruthEngineFacade.get_instance()
    report = facade.build_full_truth_report(car_model_clean)
    report_md = facade.format_full_truth_report_markdown(car_model_clean)

    return {
        "car_model": car_model_clean,
        "report": report.model_dump(),
        "report_markdown": report_md,
    }
