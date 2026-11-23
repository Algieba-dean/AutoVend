"""
LangChain `@tool` definitions and contract metadata for the AutoVend LangGraph sales agent.

Keeps strict package isolation (no imports from `backend`, `fastapi`, or `chromadb`).
Delegates RAG retrieval to `ServiceContainer.get_rag_service()` and deterministic
pricing/valuation to `TruthEngineFacade` (wrapping `src/truth_engine/price_valuation.py`).
"""

import hashlib
import json
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

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
    requiresIdempotencyKey: bool = False
    maxResultSizeChars: int = 4000

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IdempotencyStore:
    """Thread-safe in-memory TTL cache ensuring side-effecting tools execute at most once per idempotency_key."""

    _entries: Dict[str, Tuple[float, str]] = {}
    _lock: threading.RLock = threading.RLock()
    _default_ttl_s: float = 3600.0
    _max_entries: int = 2048

    @classmethod
    def _evict_expired_locked(cls, now: float, ttl_s: float) -> None:
        expired = [k for k, (ts, _) in cls._entries.items() if now - ts > ttl_s]
        for k in expired:
            cls._entries.pop(k, None)
        if len(cls._entries) > cls._max_entries:
            # Evict oldest entries
            by_age = sorted(cls._entries.items(), key=lambda item: item[1][0])
            for k, _ in by_age[: len(cls._entries) - cls._max_entries]:
                cls._entries.pop(k, None)

    @classmethod
    def get(cls, key: str, ttl_s: float = 3600.0) -> Optional[str]:
        if not key:
            return None
        now = time.monotonic()
        with cls._lock:
            entry = cls._entries.get(key)
            if entry is None:
                return None
            ts, payload = entry
            if now - ts > ttl_s:
                cls._entries.pop(key, None)
                return None
            return payload

    @classmethod
    def set(cls, key: str, payload: str, ttl_s: Optional[float] = None) -> None:
        if not key:
            return
        now = time.monotonic()
        effective_ttl = cls._default_ttl_s if ttl_s is None else ttl_s
        with cls._lock:
            cls._entries[key] = (now, payload)
            cls._evict_expired_locked(now, effective_ttl)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._entries.clear()


TOOL_CONTRACTS: Dict[str, ToolContract] = {
    "search_vehicles": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        requiresIdempotencyKey=False,
        maxResultSizeChars=6000,
    ),
    "get_vehicle_detail": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        requiresIdempotencyKey=False,
        maxResultSizeChars=4000,
    ),
    "calculate_drive_away_price": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        requiresIdempotencyKey=False,
        maxResultSizeChars=4000,
    ),
    "check_constraint_conflicts": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        requiresIdempotencyKey=False,
        maxResultSizeChars=2000,
    ),
    "validate_test_drive_slot": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        requiresIdempotencyKey=False,
        maxResultSizeChars=2000,
    ),
    "submit_test_drive_reservation": ToolContract(
        isReadOnly=False,
        isConcurrencySafe=False,
        needsApproval=True,
        requiresIdempotencyKey=True,
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
    payload = []
    for c in conflicts:
        opts_text = " 或 ".join(c.suggested_options) if getattr(c, "suggested_options", None) else ""
        trade_offs = getattr(c, "trade_off_options", None) or []
        if not opts_text and trade_offs:
            opts_text = "；".join(
                f"{t.get('description', '')}({t.get('action', '')})".strip("()")
                for t in trade_offs
                if isinstance(t, dict)
            )
        payload.append(
            {
                "conflict_type": c.conflict_type,
                "severity": c.severity,
                "description": c.description,
                "suggested_options": list(getattr(c, "suggested_options", None) or []),
                "trade_off_options": list(trade_offs),
                "suggestion": opts_text,
            }
        )
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
                "suggested_options": ["重点核实周边快充站覆盖情况", "考虑增程/插混车型作为备选"],
                "suggestion": "建议重点核实周边快充站覆盖情况，或考虑增程/插混车型作为备选。",
            }
        )

    out = json.dumps(
        {
            "has_conflicts": len(payload) > 0,
            "conflict_count": len(payload),
            "conflicts": payload,
        },
        ensure_ascii=False,
    )
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
    idempotency_key: Optional[str] = None,
) -> str:
    """Submit a verified 4S test-drive reservation (write operation requiring approval, evidence, and idempotency_key)."""
    if idempotency_key is not None and not str(idempotency_key).strip():
        out = json.dumps(
            {
                "submitted": False,
                "error_code": "MISSING_IDEMPOTENCY_KEY",
                "error": "有副作用的预约写入工具必须携带有效的 idempotency_key",
            },
            ensure_ascii=False,
        )
        return enforce_tool_result_limit("submit_test_drive_reservation", out)

    effective_key = str(idempotency_key).strip() if idempotency_key else hashlib.sha256(
        f"{car_model}|{reservation_date}|{reservation_time}|{reservation_location}|{phone_number}".encode("utf-8")
    ).hexdigest()[:24]

    cached = IdempotencyStore.get(effective_key)
    if cached is not None:
        try:
            parsed = json.loads(cached)
            parsed["idempotent_replay"] = True
            return enforce_tool_result_limit(
                "submit_test_drive_reservation", json.dumps(parsed, ensure_ascii=False)
            )
        except Exception:
            return cached

    ledger = VerificationEvidenceLedger()
    phone_ok = ledger.verify_phone_number(phone_number)
    store_ok = ledger.verify_4s_store(reservation_location)
    dt_ok = ledger.verify_date_time(reservation_date, reservation_time)
    can_confirm, missing = ledger.can_confirm_reservation()

    if not (phone_ok and store_ok and dt_ok and can_confirm):
        out = json.dumps(
            {
                "submitted": False,
                "error_code": "RESERVATION_VALIDATION_FAILED",
                "error": "预约凭证核验未通过",
                "missing_or_invalid": missing,
                "idempotency_key": effective_key,
            },
            ensure_ascii=False,
        )
        return enforce_tool_result_limit("submit_test_drive_reservation", out)

    out = json.dumps(
        {
            "submitted": True,
            "status": "CONFIRMED",
            "idempotency_key": effective_key,
            "idempotent_replay": False,
            "car_model": car_model,
            "reservation_date": reservation_date,
            "reservation_time": reservation_time,
            "reservation_location": reservation_location,
            "test_driver": test_driver,
            "phone_number": phone_number,
        },
        ensure_ascii=False,
    )
    IdempotencyStore.set(effective_key, out)
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
