"""
Unified Tool Schema & Slot Update Reducer for AutoVend Agent (Battle 3).

Enables single-flight / two-stage tool calling where slot extraction and dialogue generation
are unified in a single turn, eliminating 5-6 serial LLM round trips.
Supports explicit retraction of fields (avoiding monotonic lock-in bugs).
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from src.agent.schemas import SessionState


class UpdateSessionSlotsTool(BaseModel):
    """
    当客户在交谈中透露了个人背景、车型诉求、预算、或试驾意愿时调用。
    所有字段支持明确的 None 与清空机制，彻底解决单调覆盖无法反悔的缺陷。
    """

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

    # 2. Forward updates to Profile
    cust_name = tool_call_data.customer_name or tool_call_data.name
    if cust_name:
        updated.profile.name = cust_name
    if tool_call_data.age is not None:
        updated.profile.age = str(tool_call_data.age)
    if tool_call_data.city:
        updated.profile.residence = tool_call_data.city
    if tool_call_data.phone_number:
        updated.profile.phone_number = tool_call_data.phone_number

    # 3. Forward updates to Explicit Needs
    if tool_call_data.budget_min_wan is not None:
        updated.needs.explicit.budget_min = tool_call_data.budget_min_wan
    if tool_call_data.budget_max_wan is not None:
        updated.needs.explicit.budget_max = tool_call_data.budget_max_wan
    if tool_call_data.budget_min_wan is not None or tool_call_data.budget_max_wan is not None:
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
        updated.needs.explicit.powertrain_type = tool_call_data.preferred_powertrain
    if tool_call_data.seat_count is not None:
        updated.needs.explicit.seat_layout = f"{tool_call_data.seat_count}座"
    if tool_call_data.brand_preference:
        updated.needs.explicit.brand = tool_call_data.brand_preference
    if tool_call_data.vehicle_category:
        updated.needs.explicit.vehicle_category_bottom = tool_call_data.vehicle_category

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

    return updated
