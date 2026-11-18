"""
LangChain `@tool` definitions and contract metadata for the AutoVend LangGraph sales agent.

Keeps strict package isolation (no imports from `backend`, `fastapi`, or `chromadb`).
Delegates RAG retrieval to `ServiceContainer.get_rag_service()` and deterministic
pricing/valuation to `TruthEngineFacade` (wrapping `src/truth_engine/price_valuation.py`).
"""

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.agent.evidence_ledger import VerificationEvidenceLedger
from src.agent.reconciliation import reconcile_constraints
from src.agent.schemas import SessionState
from src.core.container import ServiceContainer
from src.core.interfaces import RAGQueryRequest
from src.core.truth_engine import TruthEngineFacade


@dataclass(frozen=True)
class ToolContract:
    """Execution contract metadata for a LangChain tool."""

    isReadOnly: bool = True
    isConcurrencySafe: bool = True
    needsApproval: bool = False
    maxResultSizeChars: int = 4000

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


TOOL_CONTRACTS: Dict[str, ToolContract] = {
    "search_vehicles": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        maxResultSizeChars=6000,
    ),
    "get_vehicle_detail": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        maxResultSizeChars=4000,
    ),
    "calculate_drive_away_price": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        maxResultSizeChars=4000,
    ),
    "check_constraint_conflicts": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        maxResultSizeChars=2000,
    ),
    "validate_test_drive_slot": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        maxResultSizeChars=2000,
    ),
    "submit_test_drive_reservation": ToolContract(
        isReadOnly=False,
        isConcurrencySafe=False,
        needsApproval=True,
        maxResultSizeChars=2000,
    ),
}


def get_tool_contract(tool_name: str) -> ToolContract:
    """Return the contract metadata for `tool_name` (defaults to safe read-only)."""
    return TOOL_CONTRACTS.get(tool_name, ToolContract())


def enforce_tool_result_limit(tool_name: str, result_str: str) -> str:
    """Truncate tool output if it exceeds the contract's `maxResultSizeChars`."""
    contract = get_tool_contract(tool_name)
    limit = contract.maxResultSizeChars
    if not isinstance(result_str, str):
        result_str = str(result_str)
    if len(result_str) <= limit:
        return result_str
    suffix = f"... [truncated to {limit} chars from {len(result_str)}]"
    keep = max(0, limit - len(suffix))
    return result_str[:keep] + suffix


class VehicleSearchInput(BaseModel):
    query: str = Field(..., description="Natural language vehicle search query")
    brand: Optional[str] = Field(default=None, description="Preferred vehicle brand")
    price: Optional[str] = Field(default=None, description="Budget range, e.g. '20万~30万'")
    power_type: Optional[str] = Field(default=None, description="Powertrain type (纯电/增程/插混/燃油)")
    top_k: int = Field(default=5, ge=1, le=20, description="Max number of candidates to return")


@tool("search_vehicles", args_schema=VehicleSearchInput)
def search_vehicles_tool(
    query: str,
    brand: Optional[str] = None,
    price: Optional[str] = None,
    power_type: Optional[str] = None,
    top_k: int = 5,
) -> str:
    """Search candidate vehicles using AutoVend's LlamaIndex + Hybrid RAG service."""
    rag_service = ServiceContainer.get_rag_service()
    if rag_service is None:
        return json.dumps({"results": [], "error": "RAGService not registered"}, ensure_ascii=False)

    explicit: Dict[str, Any] = {}
    if brand:
        explicit["brand"] = brand
    if price:
        explicit["price"] = price
    if power_type:
        explicit["powertrain_type"] = power_type

    req = RAGQueryRequest(query_text=query, explicit_conditions=explicit, top_k=top_k)
    resp = rag_service.search_vehicles(req)
    out = json.dumps(
        {
            "total_count": resp.total_count,
            "latency_ms": resp.latency_ms,
            "results": resp.results[:top_k],
        },
        ensure_ascii=False,
    )
    return enforce_tool_result_limit("search_vehicles", out)


@tool("get_vehicle_detail")
def get_vehicle_detail_tool(car_model: str) -> str:
    """Retrieve structured specifications for a specific car model."""
    rag_service = ServiceContainer.get_rag_service()
    if rag_service is None:
        return json.dumps({"error": "RAGService not registered"}, ensure_ascii=False)
    detail = rag_service.get_vehicle_detail(car_model)
    out = json.dumps(detail or {"car_model": car_model, "found": False}, ensure_ascii=False)
    return enforce_tool_result_limit("get_vehicle_detail", out)


class DriveAwayPriceInput(BaseModel):
    car_model: str = Field(..., description="Vehicle model name, e.g. '小米SU7 Max' or '特斯拉Model Y'")
    msrp_wan: Optional[float] = Field(default=None, ge=0.0, description="Official MSRP in 万元 (optional)")
    cash_discount_wan: float = Field(default=0.0, ge=0.0, description="Cash discount in 万元")
    perks_discount_wan: float = Field(default=0.0, ge=0.0, description="Optional perks value in 万元")
    trade_in_subsidy_wan: float = Field(default=0.0, ge=0.0, description="Government/OEM trade-in subsidy in 万元")
    down_payment_ratio: float = Field(default=0.2, ge=0.0, le=1.0, description="Down payment ratio (0.0~1.0)")
    loan_months: int = Field(default=0, ge=0, le=84, description="Loan term in months (e.g. 36 or 60; 0 for cash)")
    annual_rate: float = Field(default=0.035, ge=0.0, le=0.25, description="Annual loan interest rate (e.g. 0.035)")


@tool("calculate_drive_away_price", args_schema=DriveAwayPriceInput)
def calculate_drive_away_price_tool(
    car_model: str,
    msrp_wan: Optional[float] = None,
    cash_discount_wan: float = 0.0,
    perks_discount_wan: float = 0.0,
    trade_in_subsidy_wan: float = 0.0,
    down_payment_ratio: float = 0.2,
    loan_months: int = 0,
    annual_rate: float = 0.035,
) -> str:
    """Calculate transparent drive-away price (purchase tax, insurance, fees) and optional monthly loan payment."""
    facade = TruthEngineFacade.get_instance()
    result = facade.calculate_drive_away_price(
        car_model=car_model,
        msrp_wan=msrp_wan,
        cash_discount=cash_discount_wan,
        perks_discount=perks_discount_wan,
        trade_in_subsidy=trade_in_subsidy_wan,
    )

    # Deterministic loan calculation if loan_months > 0
    dap = (
        (result.get("calculation") or result.get("drive_away_price") or {})
        if isinstance(result, dict)
        else {}
    )
    total_wan = float(dap.get("total_drive_away_price_wan") or 0.0)
    net_wan = float(dap.get("net_car_price_wan") or total_wan)
    if loan_months > 0 and net_wan > 0:
        down_payment_wan = round(net_wan * down_payment_ratio, 2)
        principal_yuan = (net_wan - down_payment_wan) * 10000.0
        if principal_yuan <= 0:
            monthly_yuan = 0.0
            total_interest_yuan = 0.0
        elif annual_rate <= 0:
            monthly_yuan = round(principal_yuan / loan_months, 2)
            total_interest_yuan = 0.0
        else:
            monthly_rate = annual_rate / 12.0
            factor = (1.0 + monthly_rate) ** loan_months
            monthly_yuan = round(principal_yuan * monthly_rate * factor / (factor - 1.0), 2)
            total_interest_yuan = round(monthly_yuan * loan_months - principal_yuan, 2)
        result["loan_plan"] = {
            "down_payment_ratio": down_payment_ratio,
            "down_payment_wan": down_payment_wan,
            "loan_principal_wan": round(principal_yuan / 10000.0, 2),
            "loan_months": loan_months,
            "annual_rate": annual_rate,
            "monthly_payment_yuan": monthly_yuan,
            "total_interest_yuan": total_interest_yuan,
        }

    out = json.dumps(result, ensure_ascii=False)
    return enforce_tool_result_limit("calculate_drive_away_price", out)


class ConstraintCheckInput(BaseModel):
    budget_wan: Optional[float] = Field(default=None, description="Max budget in 万元")
    price_str: Optional[str] = Field(default=None, description="Budget string e.g. '15万'")
    powertrain_type: Optional[str] = Field(default=None, description="Powertrain type (纯电/增程/插混/燃油)")
    seat_layout: Optional[str] = Field(default=None, description="Seat layout e.g. '7座'")
    electric_range_km: Optional[int] = Field(default=None, description="Required pure electric range in km")
    parking_conditions: Optional[str] = Field(default=None, description="Parking/charging condition e.g. '无固定车位'")


@tool("check_constraint_conflicts", args_schema=ConstraintCheckInput)
def check_constraint_conflicts_tool(
    budget_wan: Optional[float] = None,
    price_str: Optional[str] = None,
    powertrain_type: Optional[str] = None,
    seat_layout: Optional[str] = None,
    electric_range_km: Optional[int] = None,
    parking_conditions: Optional[str] = None,
) -> str:
    """Deterministically check user vehicle constraints for hard/soft conflicts."""
    temp_state = SessionState(session_id="tool_check")
    if budget_wan is not None:
        temp_state.needs.explicit.budget_max = budget_wan
        if not price_str:
            temp_state.needs.explicit.price = f"{budget_wan}万以内"
    if price_str:
        temp_state.needs.explicit.price = price_str
    if powertrain_type:
        temp_state.needs.explicit.powertrain_type = powertrain_type
    if seat_layout:
        temp_state.needs.explicit.seat_layout = seat_layout
    if electric_range_km is not None:
        temp_state.needs.explicit.electric_range_km = electric_range_km
    if parking_conditions:
        temp_state.profile.parking_conditions = parking_conditions

    conflicts = reconcile_constraints(temp_state)
    payload = [
        {
            "conflict_type": c.conflict_type,
            "severity": c.severity,
            "description": c.description,
            "suggestion": c.suggestion,
        }
        for c in conflicts
    ]
    if (
        powertrain_type
        and any(k in powertrain_type for k in ("纯电", "EV", "BEV"))
        and parking_conditions
        and any(k in parking_conditions for k in ("无固定车位", "没有充电桩", "无法装桩", "路边停"))
    ):
        payload.append(
            {
                "conflict_type": "CHARGING_VS_PARKING",
                "severity": "soft",
                "description": f"用户偏好纯电车型，但停车条件为「{parking_conditions}」可能不便安装家充桩",
                "suggestion": "建议重点核实周边快充站覆盖情况，或考虑增程/插混车型作为备选。",
            }
        )

    out = json.dumps({"has_conflicts": len(payload) > 0, "conflicts": payload}, ensure_ascii=False)
    return enforce_tool_result_limit("check_constraint_conflicts", out)


@tool("validate_test_drive_slot")
def validate_test_drive_slot_tool(
    reservation_date: Optional[str] = None,
    reservation_time: Optional[str] = None,
    reservation_location: Optional[str] = None,
    test_driver: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> str:
    """Validate completeness and format of 4S test-drive reservation fields via EvidenceLedger."""
    ledger = VerificationEvidenceLedger()
    missing: List[str] = []
    invalid: List[str] = []

    if not reservation_date:
        missing.append("reservation_date")
    if not reservation_time:
        missing.append("reservation_time")
    if reservation_date and reservation_time:
        if not ledger.verify_date_time(reservation_date, reservation_time):
            invalid.append("reservation_date_time")

    if not reservation_location:
        missing.append("reservation_location")
    elif not ledger.verify_4s_store(reservation_location):
        invalid.append("reservation_location")

    if not test_driver:
        missing.append("test_driver")

    if not phone_number:
        missing.append("phone_number")
    elif not ledger.verify_phone_number(phone_number):
        invalid.append("phone_number")

    out = json.dumps(
        {
            "valid": len(missing) == 0 and len(invalid) == 0,
            "missing_fields": missing,
            "invalid_fields": invalid,
            "evidences": [e.model_dump() for e in ledger.evidences],
        },
        ensure_ascii=False,
    )
    return enforce_tool_result_limit("validate_test_drive_slot", out)


@tool("submit_test_drive_reservation")
def submit_test_drive_reservation_tool(
    car_model: str,
    reservation_date: str,
    reservation_time: str,
    reservation_location: str,
    test_driver: str,
    phone_number: str,
) -> str:
    """Submit a verified 4S test-drive reservation (write operation requiring approval/evidence)."""
    ledger = VerificationEvidenceLedger()
    phone_ok = ledger.verify_phone_number(phone_number)
    store_ok = ledger.verify_4s_store(reservation_location)
    dt_ok = ledger.verify_date_time(reservation_date, reservation_time)
    can_confirm, missing = ledger.can_confirm_reservation()

    if not (phone_ok and store_ok and dt_ok and can_confirm):
        out = json.dumps(
            {
                "submitted": False,
                "error": "预约凭证核验未通过",
                "missing_or_invalid": missing,
            },
            ensure_ascii=False,
        )
        return enforce_tool_result_limit("submit_test_drive_reservation", out)

    out = json.dumps(
        {
            "submitted": True,
            "status": "CONFIRMED",
            "car_model": car_model,
            "reservation_date": reservation_date,
            "reservation_time": reservation_time,
            "reservation_location": reservation_location,
            "test_driver": test_driver,
            "phone_number": phone_number,
        },
        ensure_ascii=False,
    )
    return enforce_tool_result_limit("submit_test_drive_reservation", out)


_ALL_TOOLS = [
    search_vehicles_tool,
    get_vehicle_detail_tool,
    calculate_drive_away_price_tool,
    check_constraint_conflicts_tool,
    validate_test_drive_slot_tool,
    submit_test_drive_reservation_tool,
]

for _t in _ALL_TOOLS:
    _contract = get_tool_contract(_t.name)
    _t.metadata = {**(_t.metadata or {}), **_contract.to_dict()}


def get_autovend_tools():
    """Return the standard list of contract-annotated LangChain tools for the AutoVend agent."""
    return list(_ALL_TOOLS)
