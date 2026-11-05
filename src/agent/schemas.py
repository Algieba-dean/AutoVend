"""
Agent-level schemas — the protocol boundary between Agent and Backend.

All domain models (Stage, UserProfile, VehicleNeeds, etc.) live here.
The backend imports these; the agent uses them internally.
Neither package imports from the other's internal modules.
"""

from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

# ── Stage ──────────────────────────────────────────────────────


class Stage(str, Enum):
    """Conversation stage enumeration."""

    WELCOME = "welcome"
    PROFILE_ANALYSIS = "profile_analysis"
    NEEDS_ANALYSIS = "needs_analysis"
    CAR_SELECTION = "car_selection_confirmation"
    RESERVATION_4S = "reservation4s"
    RESERVATION_CONFIRMATION = "reservation_confirmation"
    FAREWELL = "farewell"


class UserRole(str, Enum):
    """User role for RBAC permissions."""

    CUSTOMER = "customer"
    SALESPERSON = "salesperson"
    ADMIN = "admin"


class StageInfo(BaseModel):
    """Stage transition info included in API responses."""

    previous_stage: str = ""
    current_stage: str = Stage.WELCOME.value


# ── User Profile ───────────────────────────────────────────────


class UserProfile(BaseModel):
    """User profile extracted from conversation."""

    phone_number: str = ""
    name: str = ""
    title: str = ""
    age: str = ""
    target_driver: str = ""
    expertise: str = ""
    family_size: str = ""
    price_sensitivity: str = ""
    residence: str = ""
    parking_conditions: str = ""


# ── Vehicle Needs ──────────────────────────────────────────────


class ExplicitNeeds(BaseModel):
    """Explicit needs directly stated by the user."""

    # Strongly-typed domain attributes (Industrial grade)
    budget_min: Optional[float] = Field(None, ge=0.0, le=5000.0, description="最低预算(万元)")
    budget_max: Optional[float] = Field(None, ge=0.0, le=5000.0, description="最高预算(万元)")
    airbag_count: Optional[int] = Field(None, ge=0, le=20, description="安全气囊数")
    battery_kwh: Optional[float] = Field(None, ge=0.0, le=300.0, description="电池度数")
    acceleration_0_100: Optional[float] = Field(None, ge=1.5, le=30.0, description="零百加速(秒)")
    electric_range_km: Optional[int] = Field(None, ge=0, le=2000, description="纯电续航(公里)")

    # Legacy attributes maintained for backward compatibility
    price: str = ""
    vehicle_category_bottom: str = ""
    brand: str = ""
    powertrain_type: str = ""
    design_style: str = ""
    drive_type: str = ""
    seat_layout: str = ""
    autonomous_driving_level: str = ""
    ABS: str = ""
    ESP: str = ""
    horsepower: str = ""
    torque: str = ""
    max_speed: str = ""
    fuel_consumption: str = ""
    electric_range: str = ""
    battery_capacity: str = ""
    cargo_volume: str = ""
    wheelbase: str = ""
    ground_clearance: str = ""

    @field_validator(
        "budget_min",
        "budget_max",
        "airbag_count",
        "battery_kwh",
        "acceleration_0_100",
        "electric_range_km",
        mode="before",
    )
    @classmethod
    def parse_numeric_strings(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            v_clean = v.strip().rstrip("万kmKM公里秒个度kwhKWh")
            try:
                return float(v_clean)
            except ValueError:
                return None
        return v

    @field_validator("budget_max")
    @classmethod
    def validate_budget_range(cls, v, info):
        min_val = info.data.get("budget_min")
        if v is not None and min_val is not None and v < min_val:
            raise ValueError("最高预算不能低于最低预算")
        return v


class ImplicitNeeds(BaseModel):
    """Implicit needs inferred from user profile and conversation context."""

    size: str = ""
    vehicle_usability: str = ""
    aesthetics: str = ""
    comfort_level: str = ""
    smartness: str = ""
    family_friendliness: str = ""
    energy_consumption_level: str = ""
    road_performance: str = ""
    brand_grade: str = ""
    driving_range: str = ""
    power_performance: str = ""
    safety: str = ""
    cost_performance: str = ""
    space: str = ""
    cargo_space: str = ""


class VehicleNeeds(BaseModel):
    """Combined explicit and implicit vehicle needs."""

    explicit: ExplicitNeeds = Field(default_factory=ExplicitNeeds)
    implicit: ImplicitNeeds = Field(default_factory=ImplicitNeeds)


# ── Reservation ────────────────────────────────────────────────


class ISODate(date):
    """
    Subclass of datetime.date that provides seamless string equality and
    string-like strip/len/contains behavior for backwards-compatibility while maintaining
    strict ISO-8601 typing.
    """

    raw_text: str = ""

    def __new__(cls, *args, raw_text: str = "", **kwargs):
        inst = super().__new__(cls, *args, **kwargs)
        inst.raw_text = raw_text
        return inst

    def __reduce__(self):
        return (self.__class__, (self.year, self.month, self.day), {"raw_text": self.raw_text})

    def __hash__(self) -> int:
        return super().__hash__()

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False
        if isinstance(other, str):
            if other == "":
                return False
            if self.isoformat() == other:
                return True
            if self.raw_text and self.raw_text == other:
                return True
            return False
        return super().__eq__(other)

    def __contains__(self, item: str) -> bool:
        if not isinstance(item, str):
            return False
        return (bool(self.raw_text) and item in self.raw_text) or (item in self.isoformat())

    def __str__(self) -> str:
        return self.raw_text if self.raw_text else self.isoformat()

    def strip(self, *args, **kwargs) -> str:
        return str(self).strip(*args, **kwargs)

    def lower(self) -> str:
        return str(self).lower()

    def upper(self) -> str:
        return str(self).upper()

    def startswith(self, prefix, *args) -> bool:
        return str(self).startswith(prefix, *args) or self.isoformat().startswith(prefix, *args)

    def endswith(self, suffix, *args) -> bool:
        return str(self).endswith(suffix, *args) or self.isoformat().endswith(suffix, *args)

    def replace(self, *args, **kwargs):
        if kwargs and any(k in kwargs for k in ("year", "month", "day")):
            return super().replace(*args, **kwargs)
        if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], str):
            return str(self).replace(args[0], args[1], *args[2:])
        return super().replace(*args, **kwargs)

    def split(self, *args, **kwargs) -> list:
        return str(self).split(*args, **kwargs)

    def __len__(self) -> int:
        return len(str(self))

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return handler(date)


class ReservationInfo(BaseModel):
    """Test drive reservation information."""

    # Strongly-typed reservation slots
    test_driver: Optional[str] = ""
    reservation_date: Optional[Union[date, str]] = ""
    reservation_time_slot: Optional[str] = Field(
        None, pattern=r"^(上午|下午|晚上|\d{2}:\d{2})$", description="标准时间段"
    )
    store_id: Optional[str] = Field(None, description="必须绑定真实 4S 店经销商编码，如 'DEALER_HZ_001'")

    # Legacy attributes
    reservation_time: str = ""
    reservation_location: str = ""
    reservation_phone_number: str = ""
    salesman: str = ""

    @classmethod
    def resolve_relative_date(cls, raw_text: str, user_tz: str = "Asia/Shanghai") -> Optional[ISODate]:
        """将 '明天', '这周末', '下周六', '周日', '11月15日', '3天后' 等依托当前自然日标准化为真实标准公历日期."""
        if not raw_text:
            return None
        raw_text = raw_text.strip()
        try:
            d = date.fromisoformat(raw_text)
            return ISODate(d.year, d.month, d.day, raw_text=raw_text)
        except ValueError:
            pass

        import re
        now = datetime.now(timezone(timedelta(hours=8)))
        today = now.date()

        # 1. Direct pattern matching for Chinese relative day words
        if "今天" in raw_text or "当日" in raw_text:
            return ISODate(today.year, today.month, today.day, raw_text=raw_text)
        elif "大大后天" in raw_text:
            td = today + timedelta(days=4)
            return ISODate(td.year, td.month, td.day, raw_text=raw_text)
        elif "大后天" in raw_text:
            td = today + timedelta(days=3)
            return ISODate(td.year, td.month, td.day, raw_text=raw_text)
        elif "后天" in raw_text:
            td = today + timedelta(days=2)
            return ISODate(td.year, td.month, td.day, raw_text=raw_text)
        elif "明天" in raw_text or "次日" in raw_text:
            td = today + timedelta(days=1)
            return ISODate(td.year, td.month, td.day, raw_text=raw_text)

        # 2. "N天后" / "N周后"
        cn_num = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        days_after_match = re.search(r"(\d+|[一两二三四五六七八九十]+)\s*天后", raw_text)
        if days_after_match:
            n_str = days_after_match.group(1)
            n_days = int(n_str) if n_str.isdigit() else cn_num.get(n_str, 0)
            if n_days > 0:
                td = today + timedelta(days=n_days)
                return ISODate(td.year, td.month, td.day, raw_text=raw_text)

        weeks_after_match = re.search(r"(\d+|[一两二三四五六七八九十]+)\s*(?:个)?周后", raw_text)
        if weeks_after_match:
            n_str = weeks_after_match.group(1)
            n_weeks = int(n_str) if n_str.isdigit() else cn_num.get(n_str, 0)
            if n_weeks > 0:
                td = today + timedelta(days=n_weeks * 7)
                return ISODate(td.year, td.month, td.day, raw_text=raw_text)

        # 3. Explicit Calendar Dates (e.g. "2026年11月20日", "11月15日", "11月15号")
        full_date_match = re.search(r"(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日号]?", raw_text)
        if full_date_match:
            y, m, d = int(full_date_match.group(1)), int(full_date_match.group(2)), int(full_date_match.group(3))
            try:
                td = date(y, m, d)
                return ISODate(td.year, td.month, td.day, raw_text=raw_text)
            except ValueError:
                pass

        month_day_match = re.search(r"(\d{1,2})[月\-/](\d{1,2})[日号]?", raw_text)
        if month_day_match:
            m, d = int(month_day_match.group(1)), int(month_day_match.group(2))
            y = today.year
            if m < today.month or (m == today.month and d < today.day):
                y += 1
            try:
                td = date(y, m, d)
                return ISODate(td.year, td.month, td.day, raw_text=raw_text)
            except ValueError:
                pass

        # 4. Weekday handling
        weekday_map = {
            "周一": 0, "星期一": 0, "礼拜一": 0,
            "周二": 1, "星期二": 1, "礼拜二": 1,
            "周三": 2, "星期三": 2, "礼拜三": 2,
            "周四": 3, "星期四": 3, "礼拜四": 3,
            "周五": 4, "星期五": 4, "礼拜五": 4,
            "周六": 5, "星期六": 5, "礼拜六": 5,
            "周日": 6, "星期日": 6, "礼拜天": 6, "周天": 6, "星期天": 6,
        }

        target_weekday = None
        for k, w in weekday_map.items():
            if k in raw_text:
                target_weekday = w
                break

        if target_weekday is not None:
            cur_weekday = today.weekday()
            is_after_next = any(k in raw_text for k in ["下下周", "下下星期", "下下礼拜", "下下个周", "下下个星期"])
            is_next_week = not is_after_next and any(k in raw_text for k in ["下周", "下星期", "下礼拜", "下个周", "下个星期"])
            is_this_week = any(k in raw_text for k in ["本周", "这周", "本星期", "这星期", "这个周", "这个星期"])

            if is_after_next:
                days_ahead = (target_weekday - cur_weekday) + 14
            elif is_next_week:
                days_ahead = (target_weekday - cur_weekday) + 7
            elif is_this_week:
                days_ahead = target_weekday - cur_weekday
                if days_ahead < 0:
                    days_ahead += 7
            else:
                days_ahead = (target_weekday - cur_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7

            td = today + timedelta(days=days_ahead)
            return ISODate(td.year, td.month, td.day, raw_text=raw_text)

        # 5. Weekend handling ("下周末", "这周末", "周末")
        is_next_weekend = any(k in raw_text for k in ["下周末", "下个周末", "下周的周末"])
        if is_next_weekend or any(k in raw_text for k in ["本周末", "这周末", "周末"]):
            cur_weekday = today.weekday()
            if is_next_weekend:
                days_ahead = (5 - cur_weekday) + 7
            else:
                if cur_weekday in (5, 6):
                    days_ahead = 0
                else:
                    days_ahead = 5 - cur_weekday
            td = today + timedelta(days=days_ahead)
            return ISODate(td.year, td.month, td.day, raw_text=raw_text)

        try:
            dp = __import__("dateparser")
            parsed = dp.parse(
                raw_text,
                settings={
                    "RELATIVE_BASE": now,
                    "PREFER_DATES_FROM": "future",
                },
            )
            if parsed:
                pd = parsed.date()
                return ISODate(pd.year, pd.month, pd.day, raw_text=raw_text)
        except Exception:
            pass

        return None

    @field_validator("reservation_date", mode="before")
    @classmethod
    def parse_reservation_date(cls, v):
        if v is None or v == "":
            return ""
        if isinstance(v, str):
            resolved = cls.resolve_relative_date(v)
            if resolved:
                return resolved
            try:
                d = date.fromisoformat(v.strip())
                return ISODate(d.year, d.month, d.day, raw_text=v)
            except ValueError:
                return v
        if isinstance(v, date) and not isinstance(v, ISODate):
            return ISODate(v.year, v.month, v.day)
        return v


# ── Agent Protocol ─────────────────────────────────────────────


class SessionState(BaseModel):
    """
    Serializable snapshot of all session-level state.
    Passed in and out of the Agent on every turn.
    """

    session_id: str = ""
    version: int = 1
    tenant_id: str = "default_tenant"
    trace_id: str = ""
    user_role: UserRole = UserRole.CUSTOMER
    stage: Stage = Stage.WELCOME
    previous_stage: str = ""
    profile: UserProfile = Field(default_factory=UserProfile)
    needs: VehicleNeeds = Field(default_factory=VehicleNeeds)
    matched_cars: List[Dict[str, Any]] = Field(default_factory=list)
    reservation: ReservationInfo = Field(default_factory=ReservationInfo)

    #: Instructions for the generator produced by this turn's arbitration —
    #: a blocked transition explains what is missing, a rollback explains that
    #: the customer changed their mind. Appended after the stable generation
    #: prompt prefix and cleared each turn, so a stale note cannot leak forward.
    system_notes: List[str] = Field(default_factory=list)

    #: What this turn changed, as {field_path: new_value}. Kept as a flat map
    #: for callers that only need "did anything change"; `patch_log` carries the
    #: same information with operations and provenance.
    last_patch: Dict[str, Any] = Field(default_factory=dict)

    #: Every change ever made to the structured state, oldest first, as
    #: serialised `StatePatch` dicts. The transcript scrolls out of the sliding
    #: window; this does not, so a budget stated on turn 2 stays attributable on
    #: turn 20. Also lets a rollback revert exactly what a stage introduced
    #: instead of clearing whole sub-objects.
    patch_log: List[Dict[str, Any]] = Field(default_factory=list)

    #: Intents raised by tools that the agent cannot fulfil itself — retrieval,
    #: stage changes. The orchestrator drains these; the agent only states them,
    #: which is what keeps this package free of backend imports.
    pending_requests: List[Dict[str, Any]] = Field(default_factory=list)

    #: Set by a rollback to suppress forward transitions for one turn.
    #:
    #: "我想改一下预算" announces a change without stating the new value, so the
    #: old budget is still in state and the forward guard still passes. Without
    #: this flag the rollback is undone in the same turn — the FSM steps back to
    #: needs analysis and immediately returns to recommendations, re-running
    #: retrieval against the constraints the customer just disowned.
    stage_hold: bool = False

    #: Incremental dialogue summary history.
    #: Stores list of dicts: [{"start_turn": 1, "end_turn": 6, "summary": "..."}, ...]
    summary_history: List[Dict[str, Any]] = Field(default_factory=list)

    #: Last dialogue turn index that has been compressed into summary_history.
    last_compressed_turn: int = 0

    #: Sub-DAG execution state for complex local stage workflows.
    subdag_state: Dict[str, Any] = Field(default_factory=dict)

    #: Interrupted sales goal stack for topic hopping & seamless resumption.
    #: Each entry: {"stage": "Stage value", "topic_label": "...", "target_action": "...", "turn_index": int}
    interrupted_goals: List[Dict[str, Any]] = Field(default_factory=list)



class AgentInput(BaseModel):
    """
    Everything the Agent needs to process one conversation turn.

    The backend is responsible for:
    - Managing session lifecycle
    - Running RAG retrieval and passing results as `retrieved_cars`
    - Serializing/deserializing SessionState
    """

    session_state: SessionState
    user_message: str
    retrieved_cars: List[Dict[str, Any]] = Field(default_factory=list)


class AgentResult(BaseModel):
    """
    Everything the Agent returns after processing one turn.

    The backend uses this to:
    - Update stored session state
    - Build the API response
    """

    session_state: SessionState
    response_text: str = ""
    stage_changed: bool = False
