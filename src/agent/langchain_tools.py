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
from typing import Any, Dict, List, Literal, Optional, Tuple

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
    "compare_two_vehicles": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        requiresIdempotencyKey=False,
        maxResultSizeChars=2000,
    ),
    "calculate_financing_plan": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        requiresIdempotencyKey=False,
        maxResultSizeChars=2500,
    ),
    "query_dealer_promotions": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        requiresIdempotencyKey=False,
        maxResultSizeChars=2500,
    ),
    "query_dealer_info": ToolContract(
        isReadOnly=True,
        isConcurrencySafe=True,
        needsApproval=False,
        requiresIdempotencyKey=False,
        maxResultSizeChars=2500,
    ),
    "manage_test_drive": ToolContract(
        isReadOnly=False,
        isConcurrencySafe=False,
        needsApproval=True,
        requiresIdempotencyKey=True,
        maxResultSizeChars=2500,
    ),
    "handoff_to_sales_advisor": ToolContract(
        isReadOnly=False,
        isConcurrencySafe=False,
        needsApproval=False,
        requiresIdempotencyKey=False,
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


# ── P1 Dealer Voice-First Tools ──────────────────────────────────────


def _lookup_car_3d_summary(car_model: str) -> Dict[str, str]:
    """Fetch price, range/power, and space summary for `car_model` from RAG/Tier0."""
    detail: Dict[str, Any] = {}
    rag_service = ServiceContainer.get_rag_service()
    if rag_service is not None:
        try:
            detail = rag_service.get_vehicle_detail(car_model) or {}
        except Exception:
            detail = {}
    if not detail:
        try:
            from src.core.tiered_engine import TieredRetrievalEngine

            t0 = TieredRetrievalEngine.get_instance().search_tier0(car_model)
            if t0 is not None and t0.results:
                meta = dict(t0.results[0].metadata or {})
                detail = {**meta, "car_model": t0.results[0].car_model or car_model}
        except Exception:
            pass

    price = str(
        detail.get("price")
        or (f"{detail['price_wan']}万" if detail.get("price_wan") else "")
        or (f"{detail['msrp_wan']}万" if detail.get("msrp_wan") else "")
        or "暂无官方报价"
    )
    range_parts = [
        str(detail.get("powertrain_type") or detail.get("power_type") or "").strip(),
        str(detail.get("electric_range") or (f"续航{detail['electric_range_km']}km" if detail.get("electric_range_km") else "")).strip(),
        str(detail.get("acceleration_0_100") or "").strip(),
    ]
    range_and_power = " / ".join([p for p in range_parts if p]) or "暂无详细动力参数"
    space_parts = [
        str(detail.get("vehicle_category_bottom") or detail.get("body_style") or "").strip(),
        str(detail.get("seat_layout") or "").strip(),
        str(detail.get("wheelbase") or "").strip(),
    ]
    space = " / ".join([p for p in space_parts if p]) or "暂无详细空间参数"
    return {
        "car_model": str(detail.get("car_model") or car_model),
        "price": price,
        "range_and_power": range_and_power,
        "space": space,
    }


class CompareTwoVehiclesInput(BaseModel):
    car_a: str = Field(..., description="First vehicle model name")
    car_b: str = Field(..., description="Second vehicle model name")


@tool("compare_two_vehicles", args_schema=CompareTwoVehiclesInput)
def compare_two_vehicles_tool(car_a: str, car_b: str) -> str:
    """Compare two vehicles on ONLY 3 core voice dimensions: price, range/power, and space."""
    summary_a = _lookup_car_3d_summary(car_a)
    summary_b = _lookup_car_3d_summary(car_b)
    out = json.dumps(
        {
            "dimensions": ["price", "range_and_power", "space"],
            "car_a": summary_a,
            "car_b": summary_b,
        },
        ensure_ascii=False,
    )
    return enforce_tool_result_limit("compare_two_vehicles", out)


class FinancingPlanInput(BaseModel):
    car_model: str = Field(..., description="Vehicle model name")
    vehicle_price_wan: Optional[float] = Field(default=None, ge=0.0, description="Vehicle price in 万元")
    down_payment_ratio: float = Field(default=0.2, ge=0.0, le=0.9, description="Down payment ratio (e.g. 0.2)")
    loan_months: int = Field(default=36, ge=12, le=84, description="Loan term in months (e.g. 36 or 60)")
    annual_rate: float = Field(default=0.035, ge=0.0, le=0.25, description="Annual interest rate (e.g. 0.035)")


@tool("calculate_financing_plan", args_schema=FinancingPlanInput)
def calculate_financing_plan_tool(
    car_model: str,
    vehicle_price_wan: Optional[float] = None,
    down_payment_ratio: float = 0.2,
    loan_months: int = 36,
    annual_rate: float = 0.035,
) -> str:
    """Calculate deterministic auto financing plan (down payment, monthly payment, total interest)."""
    price_wan = vehicle_price_wan
    if price_wan is None or price_wan <= 0:
        dap_res = TruthEngineFacade.get_instance().calculate_drive_away_price(car_model=car_model)
        dap = (
            (dap_res.get("calculation") or dap_res.get("drive_away_price") or {})
            if isinstance(dap_res, dict)
            else {}
        )
        price_wan = float(dap.get("net_car_price_wan") or dap.get("total_drive_away_price_wan") or 20.0)

    down_payment_wan = round(price_wan * down_payment_ratio, 2)
    principal_yuan = max(0.0, (price_wan - down_payment_wan) * 10000.0)

    def _calc_monthly(months: int) -> Tuple[float, float]:
        if principal_yuan <= 0:
            return 0.0, 0.0
        if annual_rate <= 0:
            m = round(principal_yuan / months, 2)
            return m, 0.0
        r = annual_rate / 12.0
        f = (1.0 + r) ** months
        m = round(principal_yuan * r * f / (f - 1.0), 2)
        return m, round(m * months - principal_yuan, 2)

    monthly_yuan, total_interest_yuan = _calc_monthly(loan_months)
    m36, _ = _calc_monthly(36)
    m60, _ = _calc_monthly(60)
    out = json.dumps(
        {
            "car_model": car_model,
            "vehicle_price_wan": round(price_wan, 2),
            "down_payment_ratio": down_payment_ratio,
            "down_payment_wan": down_payment_wan,
            "loan_principal_wan": round(principal_yuan / 10000.0, 2),
            "loan_months": loan_months,
            "annual_rate": annual_rate,
            "monthly_payment_yuan": monthly_yuan,
            "total_interest_yuan": total_interest_yuan,
            "compare_36m_monthly_yuan": m36,
            "compare_60m_monthly_yuan": m60,
        },
        ensure_ascii=False,
    )
    return enforce_tool_result_limit("calculate_financing_plan", out)


@tool("query_dealer_promotions")
def query_dealer_promotions_tool(
    car_model: Optional[str] = None,
    store_name: Optional[str] = None,
) -> str:
    """Query current dealership promotions, trade-in subsidies, and low-interest finance perks."""
    out = json.dumps(
        {
            "car_model": car_model or "全系热门车型",
            "store_name": store_name or "AutoVend 旗舰体验中心",
            "promotions": [
                {"type": "置换补贴", "benefit": "旧车置换至高补贴1.5万元"},
                {"type": "金融礼遇", "benefit": "指定车型享2年0息或3.5%低息方案"},
                {"type": "充电/保养礼包", "benefit": "本月下订赠家用充电桩或3次基础保养"},
            ],
            "valid_until": "本月底前有效",
        },
        ensure_ascii=False,
    )
    return enforce_tool_result_limit("query_dealer_promotions", out)


_DEALER_INFO_CATALOG: Dict[str, Dict[str, Any]] = {
    "朝阳": {
        "store_name": "AutoVend 朝阳旗舰4S店",
        "address": "北京市朝阳区东四环北路88号汽车大道1号馆",
        "parking": "院内专属地面及地下免费停车场，支持2小时免费充电",
        "business_hours": "每日 09:00 - 20:30（周末及节假日正常营业）",
        "showroom_models": ["小米SU7 Max", "特斯拉Model Y", "理想L6", "比亚迪海豹", "问界M7"],
        "available_test_drive_slots": ["10:00", "11:30", "14:00", "15:30", "17:00", "18:30"],
    },
    "海淀": {
        "store_name": "AutoVend 海淀中关村体验中心",
        "address": "北京市海淀区北四环西路66号",
        "parking": "大厦B2层专属客户停车位，凭试驾短信免费停3小时",
        "business_hours": "每日 09:30 - 21:00",
        "showroom_models": ["小米SU7", "特斯拉Model 3", "极氪001", "理想L6"],
        "available_test_drive_slots": ["10:30", "13:30", "15:00", "16:30", "19:00"],
    },
}


@tool("query_dealer_info")
def query_dealer_info_tool(
    store_name: Optional[str] = None,
    car_model: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """Query dealership address, parking, business hours, showroom cars, and today's test-drive slots."""
    selected = _DEALER_INFO_CATALOG["朝阳"]
    if store_name:
        for key, info in _DEALER_INFO_CATALOG.items():
            if key in store_name or store_name in info["store_name"]:
                selected = info
                break
    has_showroom_car = True
    if car_model:
        has_showroom_car = any(
            car_model.lower() in m.lower() or m.lower() in car_model.lower()
            for m in selected["showroom_models"]
        )
    out = json.dumps(
        {
            **selected,
            "query_date": date or "今日",
            "requested_car_model": car_model,
            "showroom_car_available": has_showroom_car,
        },
        ensure_ascii=False,
    )
    return enforce_tool_result_limit("query_dealer_info", out)


_TEST_DRIVE_BOOKINGS: Dict[str, Dict[str, Any]] = {}
_TEST_DRIVE_LOCK = threading.RLock()


class ManageTestDriveInput(BaseModel):
    action: Literal["query", "create", "reschedule", "cancel"] = Field(
        ..., description="Operation: query, create, reschedule, or cancel"
    )
    car_model: Optional[str] = Field(default=None, description="Vehicle model name")
    reservation_date: Optional[str] = Field(default=None, description="Date e.g. 2026-11-24 or 周六")
    reservation_time: Optional[str] = Field(default=None, description="Time slot e.g. 14:00")
    reservation_location: Optional[str] = Field(default=None, description="4S store name")
    test_driver: Optional[str] = Field(default=None, description="Driver name")
    phone_number: Optional[str] = Field(default=None, description="Customer phone number")
    reservation_id: Optional[str] = Field(default=None, description="Existing reservation ID")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key for write ops")


@tool("manage_test_drive", args_schema=ManageTestDriveInput)
def manage_test_drive_tool(
    action: Literal["query", "create", "reschedule", "cancel"],
    car_model: Optional[str] = None,
    reservation_date: Optional[str] = None,
    reservation_time: Optional[str] = None,
    reservation_location: Optional[str] = None,
    test_driver: Optional[str] = None,
    phone_number: Optional[str] = None,
    reservation_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> str:
    """Query, create, reschedule, or cancel a 4S test-drive booking with validation and idempotency."""
    if action == "query":
        with _TEST_DRIVE_LOCK:
            matches = [
                b
                for b in _TEST_DRIVE_BOOKINGS.values()
                if (not reservation_id or b["reservation_id"] == reservation_id)
                and (not phone_number or b["phone_number"] == phone_number)
            ]
        return enforce_tool_result_limit(
            "manage_test_drive",
            json.dumps({"action": "query", "bookings": matches, "count": len(matches)}, ensure_ascii=False),
        )

    effective_key = str(idempotency_key).strip() if idempotency_key else hashlib.sha256(
        f"{action}|{reservation_id}|{car_model}|{reservation_date}|{reservation_time}|{reservation_location}|{phone_number}".encode("utf-8")
    ).hexdigest()[:24]

    cached = IdempotencyStore.get(effective_key)
    if cached is not None:
        try:
            parsed = json.loads(cached)
            parsed["idempotent_replay"] = True
            return enforce_tool_result_limit("manage_test_drive", json.dumps(parsed, ensure_ascii=False))
        except Exception:
            return cached

    if action == "cancel":
        with _TEST_DRIVE_LOCK:
            target = None
            if reservation_id and reservation_id in _TEST_DRIVE_BOOKINGS:
                target = _TEST_DRIVE_BOOKINGS[reservation_id]
            elif phone_number:
                for b in _TEST_DRIVE_BOOKINGS.values():
                    if b.get("phone_number") == phone_number and b.get("status") != "CANCELLED":
                        target = b
                        break
            if target is not None:
                target["status"] = "CANCELLED"
        res_payload = {
            "submitted": True,
            "action": "cancel",
            "status": "CANCELLED",
            "reservation_id": reservation_id or (target["reservation_id"] if target else ""),
            "idempotency_key": effective_key,
            "idempotent_replay": False,
        }
        out = json.dumps(res_payload, ensure_ascii=False)
        IdempotencyStore.set(effective_key, out)
        return enforce_tool_result_limit("manage_test_drive", out)

    # create or reschedule requires valid phone, store, and date/time
    ledger = VerificationEvidenceLedger()
    phone_ok = ledger.verify_phone_number(phone_number or "")
    store_ok = ledger.verify_4s_store(reservation_location or "")
    dt_ok = ledger.verify_date_time(reservation_date or "", reservation_time or "")
    can_confirm, missing = ledger.can_confirm_reservation()
    if not (phone_ok and store_ok and dt_ok and can_confirm):
        return enforce_tool_result_limit(
            "manage_test_drive",
            json.dumps(
                {
                    "submitted": False,
                    "action": action,
                    "error_code": "RESERVATION_VALIDATION_FAILED",
                    "error": "预约信息校验未通过，需提供有效手机号、门店和试驾时间",
                    "missing_or_invalid": missing,
                    "idempotency_key": effective_key,
                },
                ensure_ascii=False,
            ),
        )

    res_id = reservation_id or f"TD-{effective_key[:8].upper()}"
    booking = {
        "submitted": True,
        "action": action,
        "status": "RESCHEDULED" if action == "reschedule" else "CONFIRMED",
        "reservation_id": res_id,
        "idempotency_key": effective_key,
        "idempotent_replay": False,
        "car_model": car_model or "待定车型",
        "reservation_date": reservation_date,
        "reservation_time": reservation_time,
        "reservation_location": reservation_location,
        "test_driver": test_driver or "贵宾",
        "phone_number": phone_number,
    }
    with _TEST_DRIVE_LOCK:
        _TEST_DRIVE_BOOKINGS[res_id] = booking
    out = json.dumps(booking, ensure_ascii=False)
    IdempotencyStore.set(effective_key, out)
    return enforce_tool_result_limit("manage_test_drive", out)


@tool("handoff_to_sales_advisor")
def handoff_to_sales_advisor_tool(
    reason: str,
    customer_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> str:
    """Escalate conversation to a human sales advisor with structured customer summary."""
    out = json.dumps(
        {
            "handoff": True,
            "status": "QUEUED_FOR_ADVISOR",
            "reason": reason,
            "customer_name": customer_name or "客户",
            "phone_number": phone_number or "",
            "preferred_model": preferred_model or "",
            "message": "已为您转接专属销售顾问，顾问将在第一时间联系您。",
        },
        ensure_ascii=False,
    )
    return enforce_tool_result_limit("handoff_to_sales_advisor", out)


_ALL_TOOLS = [
    search_vehicles_tool,
    get_vehicle_detail_tool,
    compare_two_vehicles_tool,
    calculate_drive_away_price_tool,
    calculate_financing_plan_tool,
    query_dealer_promotions_tool,
    query_dealer_info_tool,
    check_constraint_conflicts_tool,
    validate_test_drive_slot_tool,
    submit_test_drive_reservation_tool,
    manage_test_drive_tool,
    handoff_to_sales_advisor_tool,
]

for _t in _ALL_TOOLS:
    _contract = get_tool_contract(_t.name)
    _t.metadata = {**(_t.metadata or {}), **_contract.to_dict()}


def get_autovend_tools():
    """Return the standard list of contract-annotated LangChain tools for the AutoVend agent."""
    return list(_ALL_TOOLS)
