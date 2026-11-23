"""
Unified Tool Schema & Slot Update Reducer for AutoVend Agent (Battle 3).

Enables single-flight / two-stage tool calling where slot extraction and dialogue generation
are unified in a single turn, eliminating 5-6 serial LLM round trips.
Supports explicit retraction of fields (avoiding monotonic lock-in bugs).
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from src.agent.schemas import SessionState


class UpdateSessionSlotsTool(BaseModel):
    """
    当客户在交谈中透露了个人背景、车型诉求、预算、或试驾意愿时调用。
    所有字段支持明确的 None 与清空机制，彻底解决单调覆盖无法反悔的缺陷。
    """

    @model_validator(mode="before")
    @classmethod
    def _flatten_nested_sections(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        flattened: Dict[str, Any] = dict(data)
        for section in ("profile", "needs", "explicit_needs", "explicit", "implicit", "reservation"):
            sub = data.get(section)
            if isinstance(sub, dict):
                for k, v in sub.items():
                    if k not in flattened or flattened[k] is None:
                        flattened[k] = v
        return flattened

    # 1. 用户画像与偏好
    name: Optional[str] = Field(None, description="客户姓名或称谓")
    customer_name: Optional[str] = Field(None, description="客户真实姓名或称谓 (别名)")
    age: Optional[int] = Field(None, ge=18, le=100, description="年龄")
    city: Optional[str] = Field(None, description="常驻城市，如'杭州'")
    phone_number: Optional[str] = Field(None, description="联系电话")

    # 2. 结构化汽车需求（数值强类型）
    budget_min_wan: Optional[float] = Field(None, ge=0.0, le=5000.0, description="预算下限(万)")
    budget_max_wan: Optional[float] = Field(None, ge=0.0, le=5000.0, description="预算上限(万)")
    preferred_powertrain: Optional[str] = Field(
        None, description="动力形式：纯电 / 插混 / 增程 / 燃油"
    )
    seat_count: Optional[int] = Field(None, ge=2, le=9, description="座位数需求")
    brand_preference: Optional[str] = Field(None, description="意向品牌")
    vehicle_category: Optional[str] = Field(None, description="车型类别 (轿车/SUV/MPV等)")

    # 3. 试驾预约（ISO-8601 标准日期）
    reservation_date: Optional[str] = Field(None, description="标准化预约日期 (YYYY-MM-DD 或相对日期如'明天')")
    reservation_time_slot: Optional[str] = Field(None, description="预约时间段，如'14:00'或'下午'")
    reservation_store: Optional[str] = Field(None, description="预约具体 4S 门店")
    preferred_4s_store: Optional[str] = Field(None, description="意向试驾的 4S 门店标准全称")

    # 4. 反悔与排除特性（解决单调覆盖 Bug）
    retracted_fields: Optional[List[str]] = Field(
        None,
        description="客户明确表示反悔、取消或不要的配置或属性（如：['sunroof', 'suv', 'budget']）",
    )

    # 5. 负向硬排除与软偏好权重
    excluded_powertrains: Optional[List[str]] = Field(
        None, description="客户明确排除的动力类型，如 ['纯电']"
    )
    excluded_brands: Optional[List[str]] = Field(
        None, description="客户明确排除的品牌，如 ['特斯拉']"
    )
    excluded_models: Optional[List[str]] = Field(
        None, description="客户明确排除的具体车型，如 ['Model Y']"
    )
    soft_preferences: Optional[Dict[str, float]] = Field(
        None, description="软偏好及权重(0.0~1.0)，如 {'space': 0.8, 'comfort_level': 0.7}"
    )

    # 6. 提取置信度（Confidence-Gated State Update）
    extraction_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="本次提取置信度(0.0~1.0)，歧义或不确定时<0.65"
    )
    ambiguous_fields: Optional[List[str]] = Field(
        None, description="存在歧义或低置信度的字段名列表"
    )


CONFIDENCE_GATE_THRESHOLD = 0.65


def _is_low_confidence_overwrite(
    field_name: str,
    old_value: Any,
    new_value: Any,
    confidence: float,
    ambiguous_fields: List[str],
) -> bool:
    """Return True if updating `field_name` would overwrite a confirmed value with low confidence."""
    if new_value is None or new_value == "":
        return False
    if old_value is None or old_value == "":
        return False
    if str(old_value) == str(new_value):
        return False
    return confidence < CONFIDENCE_GATE_THRESHOLD or field_name in ambiguous_fields


def resolve_pending_confirmation(state: SessionState, confirmed: bool) -> SessionState:
    """Apply or discard `state.pending_confirmation` once the user confirms or rejects."""
    if not state.pending_confirmation:
        return state
    updated = state.model_copy(deep=True)
    if confirmed:
        for field_path, info in updated.pending_confirmation.items():
            cand = info.get("candidate_value") if isinstance(info, dict) else info
            if field_path == "needs.explicit.budget_max" and cand is not None:
                updated.needs.explicit.budget_max = float(cand)
                updated.needs.explicit.price = f"{cand}万以内"
            elif field_path == "needs.explicit.budget_min" and cand is not None:
                updated.needs.explicit.budget_min = float(cand)
            elif field_path == "needs.explicit.powertrain_type" and cand:
                updated.needs.explicit.powertrain_type = str(cand)
            elif field_path == "needs.explicit.brand" and cand:
                updated.needs.explicit.brand = str(cand)
            elif field_path == "needs.explicit.vehicle_category_bottom" and cand:
                updated.needs.explicit.vehicle_category_bottom = str(cand)
            elif field_path == "needs.explicit.seat_layout" and cand:
                updated.needs.explicit.seat_layout = str(cand)
            elif field_path == "profile.name" and cand:
                updated.profile.name = str(cand)
            elif field_path == "profile.residence" and cand:
                updated.profile.residence = str(cand)
            elif field_path == "reservation.reservation_date" and cand:
                updated.reservation.reservation_date = str(cand)
            elif field_path == "reservation.reservation_time" and cand:
                updated.reservation.reservation_time = str(cand)
            elif field_path == "reservation.reservation_time_slot" and cand:
                updated.reservation.reservation_time_slot = str(cand)
            elif field_path == "reservation.reservation_location" and cand:
                updated.reservation.reservation_location = str(cand)
            elif field_path == "reservation.test_driver" and cand:
                updated.reservation.test_driver = str(cand)
            elif field_path == "reservation.reservation_phone_number" and cand:
                updated.reservation.reservation_phone_number = str(cand)
    updated.pending_confirmation = {}
    if updated.active_loop is not None:
        updated.active_loop.pending_confirmation = {}
    return updated


def apply_slot_updates(
    state: SessionState,
    tool_call_data: UpdateSessionSlotsTool,
) -> SessionState:
    """
    Safely apply unified slots to SessionState with explicit field retraction support.
    """
    updated = state.model_copy(deep=True)

    # 1. Handle retracted fields first
    if tool_call_data.retracted_fields:
        for raw_field in tool_call_data.retracted_fields:
            field = raw_field.lower().strip()
            # Retract budget
            if field in ("budget", "price", "budget_min_wan", "budget_max_wan"):
                updated.needs.explicit.budget_min = None
                updated.needs.explicit.budget_max = None
                updated.needs.explicit.price = ""
            # Retract powertrain
            elif field in ("powertrain", "preferred_powertrain", "powertrain_type"):
                updated.needs.explicit.powertrain_type = ""
            # Retract category
            elif field in ("category", "suv", "sedan", "mpv", "vehicle_category"):
                updated.needs.explicit.vehicle_category_bottom = ""
            # Retract brand
            elif field in ("brand", "brand_preference"):
                updated.needs.explicit.brand = ""
            # Retract reservation
            elif field in ("reservation", "reservation_date", "reservation_time", "store"):
                updated.reservation.reservation_date = None
                updated.reservation.reservation_time_slot = None
                updated.reservation.reservation_time = ""
                updated.reservation.reservation_location = ""
                updated.reservation.store_id = None
            else:
                if hasattr(updated.needs.explicit, field):
                    setattr(
                        updated.needs.explicit,
                        field,
                        None
                        if isinstance(getattr(updated.needs.explicit, field), (int, float, type(None)))
                        else "",
                    )
                if hasattr(updated.profile, field):
                    setattr(updated.profile, field, "")

    # 2. Forward updates to Profile (confidence-gated for existing confirmed fields)
    conf = float(getattr(tool_call_data, "extraction_confidence", 1.0))
    ambiguous = [f.lower().strip() for f in (tool_call_data.ambiguous_fields or [])]

    def _gate_or_set(
        field_key: str,
        field_path: str,
        old_val: Any,
        new_val: Any,
        setter,
    ) -> None:
        if _is_low_confidence_overwrite(field_key, old_val, new_val, conf, ambiguous):
            updated.pending_confirmation[field_path] = {
                "old_value": old_val,
                "candidate_value": new_val,
                "confidence": conf,
            }
            note = (
                f"[低置信度待确认] 客户提到的 {field_key} 可能是「{new_val}」"
                f"（当前已确认为「{old_val}」），请礼貌反问确认，暂不覆盖历史状态。"
            )
            if note not in updated.system_notes:
                updated.system_notes.append(note)
        else:
            setter(new_val)

    cust_name = tool_call_data.customer_name or tool_call_data.name
    if cust_name:
        _gate_or_set(
            "name", "profile.name", updated.profile.name, cust_name,
            lambda v: setattr(updated.profile, "name", v),
        )
    if tool_call_data.age is not None:
        updated.profile.age = str(tool_call_data.age)
    if tool_call_data.city:
        _gate_or_set(
            "city", "profile.residence", updated.profile.residence, tool_call_data.city,
            lambda v: setattr(updated.profile, "residence", v),
        )
    if tool_call_data.phone_number:
        updated.profile.phone_number = tool_call_data.phone_number

    # 3. Forward updates to Explicit Needs (confidence-gated)
    budget_changed = False
    if tool_call_data.budget_min_wan is not None:
        if _is_low_confidence_overwrite(
            "budget_min_wan", updated.needs.explicit.budget_min, tool_call_data.budget_min_wan, conf, ambiguous
        ):
            updated.pending_confirmation["needs.explicit.budget_min"] = {
                "old_value": updated.needs.explicit.budget_min,
                "candidate_value": tool_call_data.budget_min_wan,
                "confidence": conf,
            }
        else:
            updated.needs.explicit.budget_min = tool_call_data.budget_min_wan
            budget_changed = True
    if tool_call_data.budget_max_wan is not None:
        if _is_low_confidence_overwrite(
            "budget_max_wan", updated.needs.explicit.budget_max, tool_call_data.budget_max_wan, conf, ambiguous
        ):
            updated.pending_confirmation["needs.explicit.budget_max"] = {
                "old_value": updated.needs.explicit.budget_max,
                "candidate_value": tool_call_data.budget_max_wan,
                "confidence": conf,
            }
            note = (
                f"[低置信度待确认] 客户提到的预算上限可能是「{tool_call_data.budget_max_wan}万」"
                f"（当前已确认为「{updated.needs.explicit.budget_max}万」），请礼貌反问确认，暂不覆盖历史状态。"
            )
            if note not in updated.system_notes:
                updated.system_notes.append(note)
        else:
            updated.needs.explicit.budget_max = tool_call_data.budget_max_wan
            budget_changed = True
    if budget_changed:
        # Also sync legacy price string representation
        min_w = updated.needs.explicit.budget_min
        max_w = updated.needs.explicit.budget_max
        if min_w is not None and max_w is not None:
            updated.needs.explicit.price = f"{min_w}-{max_w}万"
        elif max_w is not None:
            updated.needs.explicit.price = f"{max_w}万以内"
        elif min_w is not None:
            updated.needs.explicit.price = f"{min_w}万以上"

    if tool_call_data.preferred_powertrain:
        _gate_or_set(
            "preferred_powertrain",
            "needs.explicit.powertrain_type",
            updated.needs.explicit.powertrain_type,
            tool_call_data.preferred_powertrain,
            lambda v: setattr(updated.needs.explicit, "powertrain_type", v),
        )
    if tool_call_data.seat_count is not None:
        _gate_or_set(
            "seat_count",
            "needs.explicit.seat_layout",
            updated.needs.explicit.seat_layout,
            f"{tool_call_data.seat_count}座",
            lambda v: setattr(updated.needs.explicit, "seat_layout", v),
        )
    if tool_call_data.brand_preference:
        _gate_or_set(
            "brand_preference",
            "needs.explicit.brand",
            updated.needs.explicit.brand,
            tool_call_data.brand_preference,
            lambda v: setattr(updated.needs.explicit, "brand", v),
        )
    if tool_call_data.vehicle_category:
        _gate_or_set(
            "vehicle_category",
            "needs.explicit.vehicle_category_bottom",
            updated.needs.explicit.vehicle_category_bottom,
            tool_call_data.vehicle_category,
            lambda v: setattr(updated.needs.explicit, "vehicle_category_bottom", v),
        )

    # 4. Forward updates to Reservation Info
    if tool_call_data.reservation_date:
        updated.reservation.reservation_date = tool_call_data.reservation_date
    if tool_call_data.reservation_time_slot:
        updated.reservation.reservation_time_slot = tool_call_data.reservation_time_slot
        updated.reservation.reservation_time = tool_call_data.reservation_time_slot

    store = tool_call_data.preferred_4s_store or tool_call_data.reservation_store
    if store:
        updated.reservation.reservation_location = store
        updated.reservation.store_id = store

    # 5. Apply negative exclusions & soft preferences into PreferenceModel
    from src.agent.preference_model import PreferenceEngine

    turn_idx = int(getattr(updated, "turn_count", 0))
    for pt in tool_call_data.excluded_powertrains or []:
        PreferenceEngine.add_negative_exclusion(updated.preferences, "powertrain", pt, turn_index=turn_idx)
    for br in tool_call_data.excluded_brands or []:
        PreferenceEngine.add_negative_exclusion(updated.preferences, "brand", br, turn_index=turn_idx)
    for md in tool_call_data.excluded_models or []:
        PreferenceEngine.add_negative_exclusion(updated.preferences, "model", md, turn_index=turn_idx)
    for sp_key, sp_weight in (tool_call_data.soft_preferences or {}).items():
        PreferenceEngine.add_soft_preference(updated.preferences, sp_key, sp_key, weight=sp_weight, turn_index=turn_idx)
    PreferenceEngine.sync_from_needs(updated, turn_index=turn_idx)

    return updated
