"""
Active Form Loop & Two-Stage Fallback (`src/agent/active_loop.py`).

Makes `ActiveLoopState` (`name`, `required_slots`, `is_interrupted`, `retry_counts`,
`pending_confirmation`) a first-class state machine primitive with:
1. Deterministic Python validators (phone format, dealership business hours).
2. Side-QA interruption (`is_interrupted=True`) with automatic deterministic
   `next_missing_slot()` prompt recovery after RAG answers.
3. Two-Stage Fallback:
   - Stage 1 (`0.4 <= conf < 0.8`): writes `pending_confirmation` & asks for explicit confirmation.
   - Stage 2 (`conf < 0.4` or `retry_count >= 2`): returns structured enum options or triggers HITL `interrupt()`.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from src.agent.schemas import ActiveLoopState, SessionState, Stage

_MOBILE_RE = re.compile(r"^1[3-9]\d{9}$")
_LANDLINE_RE = re.compile(r"^0\d{2,3}-?\d{7,8}$")

# Default form schemas keyed by form name
FORM_REQUIRED_SLOTS: Dict[str, List[str]] = {
    "test_drive_reservation": [
        "reservation.reservation_date",
        "reservation.reservation_time",
        "reservation.reservation_location",
        "reservation.test_driver",
        "reservation.reservation_phone_number",
    ],
    "needs_collection": [
        "needs.explicit.price",
        "needs.explicit.vehicle_category_bottom",
    ],
}

_SLOT_PROMPTS: Dict[str, str] = {
    "reservation.reservation_date": "请问您希望预约哪一天到店试驾（如明天、后天或本周末）？",
    "reservation.reservation_time": "请问您方便哪个时段到店（门店营业时间为 09:00-20:00，如上午、下午 14:00）？",
    "reservation.reservation_location": "请问您方便前往哪家 4S 门店试驾（请告知城市或门店名称）？",
    "reservation.test_driver": "请问试驾人怎么称呼？",
    "reservation.reservation_phone_number": "请留下您的 11 位手机号码，方便门店顾问为您锁定试驾名额并发送预约短信。",
    "needs.explicit.price": "请问您的购车预算大概在什么区间呢？",
    "needs.explicit.vehicle_category_bottom": "请问您更倾向哪种车型（如 SUV、轿车、MPV）或动力形式（纯电、增程、插混）？",
}

_STRUCTURED_ENUM_OPTIONS: Dict[str, List[str]] = {
    "reservation.reservation_date": ["明天", "后天", "本周末"],
    "reservation.reservation_time": ["10:00（上午）", "14:00（下午）", "16:30（下午）"],
    "needs.explicit.price": ["15万以内", "15-25万", "25-35万", "35万以上"],
    "needs.explicit.vehicle_category_bottom": ["SUV", "轿车", "MPV"],
    "needs.explicit.powertrain_type": ["纯电", "增程", "插混", "燃油"],
}


def validate_phone_number(phone: Any) -> Tuple[bool, Optional[str]]:
    """Deterministic validator for Chinese mobile/landline phone numbers."""
    raw = re.sub(r"[\s\-()]+", "", str(phone or "").strip())
    if not raw:
        return False, "联系电话不能为空，请提供 11 位有效手机号码。"
    if _MOBILE_RE.match(raw) or _LANDLINE_RE.match(str(phone or "").strip()):
        return True, None
    return (
        False,
        f"联系电话 '{phone}' 格式不正确，请提供 11 位有效手机号码（例如 13800138000）。",
    )


def validate_business_hours(
    time_val: Any,
    start_hour: int = 9,
    end_hour: int = 20,
) -> Tuple[bool, Optional[str]]:
    """Deterministic validator for dealership test-drive business hours (default 09:00-20:00)."""
    raw = str(time_val or "").strip()
    if not raw:
        return False, "预约时段不能为空，请选择营业时间（09:00-20:00）内的时段。"
    if raw in ("上午", "下午"):
        return True, None
    if raw == "晚上":
        return (
            False,
            f"试驾仅支持白天营业时段（{start_hour:02d}:00-{end_hour:02d}:00），请选择上午或下午具体时间。",
        )

    m = re.search(r"(\d{1,2})\s*[:点时]\s*(\d{1,2})?", raw)
    if not m:
        return False, f"预约时间 '{raw}' 格式无法识别，请提供具体时刻（如 14:00）或上午/下午。"

    hh = int(m.group(1))
    mm = int(m.group(2) or 0)
    if ("下午" in raw or "晚上" in raw) and 1 <= hh <= 11:
        hh += 12
    if not (0 <= mm < 60) or hh < start_hour or hh > end_hour or (hh == end_hour and mm > 0):
        return (
            False,
            f"预约时间 {hh:02d}:{mm:02d} 超出门店营业时间（{start_hour:02d}:00-{end_hour:02d}:00），请重新选择时段。",
        )
    return True, None


def validate_slot_value(slot_path: str, value: Any) -> Tuple[bool, Optional[str]]:
    """Dispatch deterministic Python validation by slot path."""
    if slot_path in ("reservation.reservation_phone_number", "profile.phone_number", "phone_number"):
        return validate_phone_number(value)
    if slot_path in ("reservation.reservation_time", "reservation.reservation_time_slot", "reservation_time"):
        return validate_business_hours(value)
    if value is None or str(value).strip() == "":
        return False, f"槽位 {slot_path} 不能为空。"
    return True, None


def _read_slot(sess: SessionState, slot_path: str) -> Any:
    target: Any = sess
    for part in slot_path.split("."):
        if not hasattr(target, part):
            return None
        target = getattr(target, part)
    return target


def next_missing_slot(sess: SessionState, loop: ActiveLoopState) -> Optional[str]:
    """Return the first required slot in `loop.required_slots` that is still empty."""
    for slot_path in loop.required_slots:
        val = _read_slot(sess, slot_path)
        if val is None or str(val).strip() == "":
            return slot_path
    return None


def build_slot_prompt(slot_path: str, retry_count: int = 0) -> str:
    """Deterministic prompt for a missing or invalid slot."""
    base = _SLOT_PROMPTS.get(slot_path, f"请提供 {slot_path} 信息。")
    if retry_count > 0:
        return f"抱歉刚才未准确记录该信息，{base}"
    return base


def get_structured_enum_options(slot_path: str) -> List[str]:
    """Return structured enum options for Stage-2 Fallback."""
    return list(_STRUCTURED_ENUM_OPTIONS.get(slot_path, []))


class TwoStageFallbackDecision(BaseModel):
    """Result of Two-Stage Fallback evaluation for an uncertain or failing slot."""

    stage: int = 0  # 0 = accepted, 1 = confirm, 2 = structured options or HITL
    accepted: bool = True
    slot_path: str = ""
    pending_confirmation: Dict[str, Any] = Field(default_factory=dict)
    structured_options: List[str] = Field(default_factory=list)
    trigger_hitl: bool = False
    directive: str = ""


def evaluate_two_stage_fallback(
    slot_path: str,
    candidate_value: Any,
    confidence: float,
    loop: ActiveLoopState,
) -> TwoStageFallbackDecision:
    """
    Two-Stage Fallback policy:
    - `confidence >= 0.8` and `retry_count < 2`: accept directly.
    - `0.4 <= confidence < 0.8` (and `retry_count < 2`): Stage 1 -> `pending_confirmation`.
    - `confidence < 0.4` or `retry_count >= 2`: Stage 2 -> structured enum options or HITL `interrupt()`.
    """
    retries = int(loop.retry_counts.get(slot_path, 0))

    if retries >= 2 or confidence < 0.4:
        options = get_structured_enum_options(slot_path)
        if retries >= 2 and not options:
            return TwoStageFallbackDecision(
                stage=2,
                accepted=False,
                slot_path=slot_path,
                trigger_hitl=True,
                directive=f"[ActiveLoop 二级兜底] 槽位 {slot_path} 连续 {retries} 次校验失败或置信度过低（{confidence:.2f}），升级人工接管。",
            )
        if retries >= 3:
            return TwoStageFallbackDecision(
                stage=2,
                accepted=False,
                slot_path=slot_path,
                structured_options=options,
                trigger_hitl=True,
                directive=f"[ActiveLoop 二级兜底] 槽位 {slot_path} 多次尝试仍未完成，升级人工顾问协助。",
            )
        opt_str = " / ".join(options) if options else "请直接告知您的偏好"
        return TwoStageFallbackDecision(
            stage=2,
            accepted=False,
            slot_path=slot_path,
            structured_options=options,
            trigger_hitl=False,
            directive=f"[ActiveLoop 二级兜底] 请向客户给出结构化选项以确认 {slot_path}：{opt_str}。",
        )

    if 0.4 <= confidence < 0.8:
        pending = {
            slot_path: {
                "candidate_value": candidate_value,
                "confidence": confidence,
            }
        }
        return TwoStageFallbackDecision(
            stage=1,
            accepted=False,
            slot_path=slot_path,
            pending_confirmation=pending,
            directive=f"[ActiveLoop 一级确认] 置信度 {confidence:.2f}，请向客户二次确认 {slot_path} 是否为「{candidate_value}」。",
        )

    return TwoStageFallbackDecision(stage=0, accepted=True, slot_path=slot_path)


def ensure_active_loop_for_stage(sess: SessionState) -> Optional[ActiveLoopState]:
    """Return existing `sess.active_loop` or initialize one when entering a form-filling stage."""
    if sess.active_loop is not None:
        return sess.active_loop.model_copy(deep=True)
    if sess.stage in (Stage.RESERVATION_4S, Stage.RESERVATION_CONFIRMATION):
        return ActiveLoopState(
            name="test_drive_reservation",
            required_slots=list(FORM_REQUIRED_SLOTS["test_drive_reservation"]),
        )
    return None
