"""
Deterministic Policy-as-Code Engine for Tool Parameter Boundary Validation (src/agent/policy_engine.py).

Enforces hard business, financial, and scheduling boundaries on tool arguments
BEFORE `ToolNode` executes—never relying on LLM prompt adherence alone.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PolicyBoundaryConfig:
    """Hard deterministic boundaries for AutoVend tools."""

    max_cash_discount_wan: float = 5.0
    max_cash_discount_pct_of_msrp: float = 0.15
    max_perks_discount_wan: float = 2.0
    max_trade_in_subsidy_wan: float = 3.0
    min_annual_rate: float = 0.0
    max_annual_rate: float = 0.25
    max_loan_months: int = 84
    max_booking_days_ahead: int = 30
    business_hour_start: int = 9
    business_hour_end: int = 20
    max_search_top_k: int = 20


@dataclass
class PolicyValidationResult:
    allowed: bool
    violations: List[str] = field(default_factory=list)
    error_code: str = "POLICY_VIOLATION"

    @property
    def reason(self) -> str:
        return "; ".join(self.violations)


class ToolPolicyEngine:
    """Deterministic Policy-as-Code validator for tool call arguments."""

    def __init__(self, config: Optional[PolicyBoundaryConfig] = None):
        self.config = config or PolicyBoundaryConfig()

    @staticmethod
    def _parse_float(val: Any, default: float, field_name: str, violations: List[str]) -> float:
        if val is None or val == "":
            return default
        try:
            return float(val)
        except (TypeError, ValueError):
            violations.append(f"{field_name}={val!r} 非法数值类型")
            return default

    @staticmethod
    def _parse_int(val: Any, default: int, field_name: str, violations: List[str]) -> int:
        if val is None or val == "":
            return default
        try:
            return int(val)
        except (TypeError, ValueError):
            violations.append(f"{field_name}={val!r} 非法整数类型")
            return default

    def validate(
        self,
        tool_name: str,
        args: Optional[Dict[str, Any]],
        strict_idempotency: bool = False,
    ) -> PolicyValidationResult:
        a = dict(args or {})
        violations: List[str] = []
        cfg = self.config

        if tool_name == "calculate_drive_away_price":
            cash_disc = self._parse_float(a.get("cash_discount_wan"), 0.0, "cash_discount_wan", violations)
            perks_disc = self._parse_float(a.get("perks_discount_wan"), 0.0, "perks_discount_wan", violations)
            trade_in = self._parse_float(a.get("trade_in_subsidy_wan"), 0.0, "trade_in_subsidy_wan", violations)
            msrp_raw = a.get("msrp_wan")
            msrp = self._parse_float(msrp_raw, 0.0, "msrp_wan", violations) if msrp_raw is not None else None
            annual_rate = self._parse_float(
                a.get("annual_rate") if a.get("annual_rate") is not None else 0.035,
                0.035,
                "annual_rate",
                violations,
            )
            loan_months = self._parse_int(a.get("loan_months"), 0, "loan_months", violations)
            down_ratio = self._parse_float(
                a.get("down_payment_ratio") if a.get("down_payment_ratio") is not None else 0.2,
                0.2,
                "down_payment_ratio",
                violations,
            )

            if cash_disc < 0 or cash_disc > cfg.max_cash_discount_wan:
                violations.append(
                    f"cash_discount_wan={cash_disc} 越界，现金优惠权限上限为 {cfg.max_cash_discount_wan} 万"
                )
            if msrp is not None and float(msrp) > 0:
                max_by_pct = round(float(msrp) * cfg.max_cash_discount_pct_of_msrp, 2)
                if cash_disc > max_by_pct:
                    violations.append(
                        f"cash_discount_wan={cash_disc} 超过指导价 {msrp} 万的 {int(cfg.max_cash_discount_pct_of_msrp*100)}% 上限 ({max_by_pct}万)"
                    )
            if perks_disc < 0 or perks_disc > cfg.max_perks_discount_wan:
                violations.append(
                    f"perks_discount_wan={perks_disc} 越界，礼遇折现权限上限为 {cfg.max_perks_discount_wan} 万"
                )
            if trade_in < 0 or trade_in > cfg.max_trade_in_subsidy_wan:
                violations.append(
                    f"trade_in_subsidy_wan={trade_in} 越界，置换补贴上限为 {cfg.max_trade_in_subsidy_wan} 万"
                )
            if annual_rate < cfg.min_annual_rate or annual_rate > cfg.max_annual_rate:
                violations.append(
                    f"annual_rate={annual_rate} 越界，合法年化利率范围为 [{cfg.min_annual_rate}, {cfg.max_annual_rate}]"
                )
            if loan_months < 0 or loan_months > cfg.max_loan_months:
                violations.append(
                    f"loan_months={loan_months} 越界，分期月数须在 [0, {cfg.max_loan_months}] 之间"
                )
            if down_ratio < 0.0 or down_ratio > 1.0:
                violations.append(f"down_payment_ratio={down_ratio} 越界，首付比例须在 [0.0, 1.0]")

        elif tool_name in ("submit_test_drive_reservation", "validate_test_drive_slot"):
            if tool_name == "submit_test_drive_reservation" and strict_idempotency:
                if not str(a.get("idempotency_key") or "").strip():
                    violations.append("有副作用的预约写入必须携带非空 idempotency_key")

            raw_date = str(a.get("reservation_date") or "").strip()
            if raw_date:
                try:
                    parsed_d = date.fromisoformat(raw_date)
                    today = datetime.now(timezone(timedelta(hours=8))).date()
                    if parsed_d < today:
                        violations.append(f"reservation_date={raw_date} 不能早于今天 ({today.isoformat()})")
                    elif parsed_d > today + timedelta(days=cfg.max_booking_days_ahead):
                        violations.append(
                            f"reservation_date={raw_date} 超出未来 {cfg.max_booking_days_ahead} 天可预约窗口"
                        )
                except ValueError:
                    pass  # Relative dates like '明天' are handled by ReservationInfo/EvidenceLedger

            raw_time = str(a.get("reservation_time") or a.get("reservation_time_slot") or "").strip()
            if raw_time and ":" in raw_time:
                try:
                    hh, mm = raw_time.split(":", 1)
                    h_int = int(hh)
                    m_int = int(mm)
                    if not (0 <= m_int < 60) or h_int < cfg.business_hour_start or h_int > cfg.business_hour_end or (h_int == cfg.business_hour_end and m_int > 0):
                        violations.append(
                            f"reservation_time={raw_time} 超出门店营业试驾时段 ({cfg.business_hour_start:02d}:00-{cfg.business_hour_end:02d}:00)"
                        )
                except ValueError:
                    violations.append(f"reservation_time={raw_time} 时间格式非法")

        elif tool_name == "search_vehicles":
            top_k = a.get("top_k")
            if top_k is not None:
                parsed_k = self._parse_int(top_k, 5, "top_k", violations)
                if parsed_k < 1 or parsed_k > cfg.max_search_top_k:
                    violations.append(f"top_k={top_k} 越界，必须在 [1, {cfg.max_search_top_k}] 范围内")

        return PolicyValidationResult(allowed=len(violations) == 0, violations=violations)
