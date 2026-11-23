"""
Event-Sourced State & Lossless Rollback (`src/agent/events.py`).

Replaces ad-hoc `model_copy(deep=True)` + `diff()` mutations with an append-only
`DialogueEvent` log as the single source of truth. `project_state(events)` is a
pure function that folds events into a `SessionState` snapshot, supporting
lossless `TurnReverted` rollback across stage, needs, matched_cars, reservation,
preferences, and active_loop.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Sequence, Union

from pydantic import BaseModel, Field

from src.agent.schemas import (
    ActiveLoopState,
    ReservationInfo,
    SessionState,
    Stage,
    UserRole,
    WeightedConstraint,
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DialogueEvent(BaseModel):
    """Base class for all append-only dialogue state events."""

    event_type: str
    turn_id: int = 0
    source: str = "system"
    timestamp: str = Field(default_factory=_utc_iso)


class SessionInitialized(DialogueEvent):
    event_type: Literal["session_initialized"] = "session_initialized"
    session_id: str = ""
    tenant_id: str = "default_tenant"
    user_role: UserRole = UserRole.CUSTOMER
    initial_stage: Stage = Stage.WELCOME
    snapshot: Optional[Dict[str, Any]] = None


class SlotUpdated(DialogueEvent):
    event_type: Literal["slot_updated"] = "slot_updated"
    field_path: str
    value: Any = None
    confidence: float = 1.0
    old_value: Any = None


class ConstraintNegated(DialogueEvent):
    event_type: Literal["constraint_negated"] = "constraint_negated"
    category: str  # "powertrain" | "brand" | "model" | "category" | "feature" | "retract_field"
    value: str


class SoftPreferenceAdded(DialogueEvent):
    event_type: Literal["soft_preference_added"] = "soft_preference_added"
    key: str
    value: Any = None
    weight: float = 0.7
    tolerance_pct: Optional[float] = None
    is_hard: bool = False


class StageTransitioned(DialogueEvent):
    event_type: Literal["stage_transitioned"] = "stage_transitioned"
    from_stage: Stage
    to_stage: Stage
    reason: str = ""
    policy_name: str = ""


class MatchedCarsUpdated(DialogueEvent):
    event_type: Literal["matched_cars_updated"] = "matched_cars_updated"
    matched_cars: List[Dict[str, Any]] = Field(default_factory=list)


class ActiveLoopUpdated(DialogueEvent):
    event_type: Literal["active_loop_updated"] = "active_loop_updated"
    active_loop: Optional[Dict[str, Any]] = None


class PendingConfirmationUpdated(DialogueEvent):
    event_type: Literal["pending_confirmation_updated"] = "pending_confirmation_updated"
    pending_confirmation: Dict[str, Any] = Field(default_factory=dict)


class SystemNoteAdded(DialogueEvent):
    event_type: Literal["system_note_added"] = "system_note_added"
    note: str = ""


class SystemNotesCleared(DialogueEvent):
    event_type: Literal["system_notes_cleared"] = "system_notes_cleared"


class TurnReverted(DialogueEvent):
    """
    Lossless rollback event: invalidates all prior events with `turn_id >= target_turn_id`.
    Events appended *after* this `TurnReverted` remain active.
    """

    event_type: Literal["turn_reverted"] = "turn_reverted"
    target_turn_id: int
    reason: str = ""


AnyDialogueEvent = Union[
    SessionInitialized,
    SlotUpdated,
    ConstraintNegated,
    SoftPreferenceAdded,
    StageTransitioned,
    MatchedCarsUpdated,
    ActiveLoopUpdated,
    PendingConfirmationUpdated,
    SystemNoteAdded,
    SystemNotesCleared,
    TurnReverted,
    DialogueEvent,
]


def _append_events(
    existing: Optional[List[AnyDialogueEvent]],
    new: Optional[List[AnyDialogueEvent]],
) -> List[AnyDialogueEvent]:
    """LangGraph reducer for append-only `events` channel (avoids `operator` import)."""
    return [*(existing or []), *(new or [])]


def _set_nested_field(sess: SessionState, field_path: str, value: Any) -> None:
    """Set a dotted field path (e.g. 'needs.explicit.price' or 'turn_count') on SessionState."""
    parts = field_path.split(".")
    if len(parts) == 1:
        if hasattr(sess, parts[0]):
            setattr(sess, parts[0], value)
        return

    target: Any = sess
    for part in parts[:-1]:
        if not hasattr(target, part):
            return
        target = getattr(target, part)
    leaf = parts[-1]
    if hasattr(target, leaf):
        setattr(target, leaf, value)


def _get_nested_field(sess: SessionState, field_path: str) -> Any:
    parts = field_path.split(".")
    target: Any = sess
    for part in parts:
        if not hasattr(target, part):
            return None
        target = getattr(target, part)
    return target


def _apply_retract_field(sess: SessionState, field_name: str) -> None:
    f = field_name.lower().strip()
    if f in ("budget", "price", "budget_min_wan", "budget_max_wan"):
        sess.needs.explicit.budget_min = None
        sess.needs.explicit.budget_max = None
        sess.needs.explicit.price = ""
    elif f in ("powertrain", "preferred_powertrain", "powertrain_type"):
        sess.needs.explicit.powertrain_type = ""
    elif f in ("category", "suv", "sedan", "mpv", "vehicle_category", "vehicle_category_bottom"):
        sess.needs.explicit.vehicle_category_bottom = ""
    elif f in ("brand", "brand_preference"):
        sess.needs.explicit.brand = ""
    elif f in ("reservation", "reservation_date", "reservation_time", "store"):
        sess.reservation = ReservationInfo()


def project_state(
    events: Sequence[AnyDialogueEvent],
    base_state: Optional[SessionState] = None,
) -> SessionState:
    """
    Pure projection function: fold an append-only event sequence into `SessionState`.

    When `TurnReverted(target_turn_id=T)` appears at index `i`, all earlier events
    `j < i` with `event.turn_id >= T` are excluded from the fold, achieving lossless
    rollback across stage, needs, matched_cars, reservation, preferences, and active_loop.
    """
    sess = base_state.model_copy(deep=True) if base_state is not None else SessionState()
    if not events:
        return sess

    active_indices = set(range(len(events)))
    for i, ev in enumerate(events):
        if isinstance(ev, TurnReverted) or getattr(ev, "event_type", "") == "turn_reverted":
            target_t = int(getattr(ev, "target_turn_id", 0))
            ev_t = int(getattr(ev, "turn_id", 0))
            for j in range(i):
                j_t = int(getattr(events[j], "turn_id", 0))
                if target_t < ev_t:
                    if target_t <= j_t < ev_t:
                        active_indices.discard(j)
                else:
                    if j_t >= target_t:
                        active_indices.discard(j)

    last_patch: Dict[str, Any] = {}
    max_turn_seen = int(sess.turn_count or 0)

    for idx in sorted(active_indices):
        ev = events[idx]
        ev_turn = int(getattr(ev, "turn_id", 0))
        if ev_turn > max_turn_seen:
            max_turn_seen = ev_turn

        etype = getattr(ev, "event_type", "")
        if etype == "session_initialized":
            snap = getattr(ev, "snapshot", None)
            if isinstance(snap, dict) and snap:
                sess = SessionState.model_validate(snap)
            else:
                if getattr(ev, "session_id", ""):
                    sess.session_id = ev.session_id
                if getattr(ev, "tenant_id", ""):
                    sess.tenant_id = ev.tenant_id
                sess.user_role = getattr(ev, "user_role", UserRole.CUSTOMER)
                sess.stage = getattr(ev, "initial_stage", Stage.WELCOME)

        elif etype == "slot_updated":
            fp = getattr(ev, "field_path", "")
            val = getattr(ev, "value", None)
            if fp:
                _set_nested_field(sess, fp, val)
                last_patch[fp] = val

        elif etype == "constraint_negated":
            cat = getattr(ev, "category", "")
            val = str(getattr(ev, "value", "") or "")
            neg = sess.preferences.negative_exclusions
            if cat == "powertrain" and val and val not in neg.powertrains:
                neg.powertrains.append(val)
            elif cat == "brand" and val and val not in neg.brands:
                neg.brands.append(val)
            elif cat == "model" and val and val not in neg.models:
                neg.models.append(val)
            elif cat == "category" and val and val not in neg.categories:
                neg.categories.append(val)
            elif cat == "feature" and val and val not in neg.features:
                neg.features.append(val)
            elif cat == "retract_field" and val:
                _apply_retract_field(sess, val)
            if val:
                neg.exclusion_turns[val] = ev_turn

        elif etype == "soft_preference_added":
            key = getattr(ev, "key", "")
            if key:
                wc = WeightedConstraint(
                    key=key,
                    value=getattr(ev, "value", None),
                    weight=float(getattr(ev, "weight", 0.7)),
                    tolerance_pct=getattr(ev, "tolerance_pct", None),
                    turn_index=ev_turn,
                )
                if getattr(ev, "is_hard", False):
                    sess.preferences.hard_constraints[key] = wc
                else:
                    sess.preferences.soft_preferences[key] = wc

        elif etype == "stage_transitioned":
            to_stage = getattr(ev, "to_stage", None)
            if to_stage is not None:
                sess.previous_stage = sess.stage.value
                sess.stage = to_stage if isinstance(to_stage, Stage) else Stage(to_stage)

        elif etype == "matched_cars_updated":
            sess.matched_cars = [dict(c) for c in (getattr(ev, "matched_cars", None) or [])]

        elif etype == "active_loop_updated":
            loop_data = getattr(ev, "active_loop", None)
            if loop_data is None:
                sess.active_loop = None
            elif isinstance(loop_data, ActiveLoopState):
                sess.active_loop = loop_data.model_copy(deep=True)
            elif isinstance(loop_data, dict):
                sess.active_loop = ActiveLoopState.model_validate(loop_data)

        elif etype == "pending_confirmation_updated":
            sess.pending_confirmation = dict(getattr(ev, "pending_confirmation", None) or {})

        elif etype == "system_note_added":
            note = str(getattr(ev, "note", "") or "")
            if note and note not in sess.system_notes:
                sess.system_notes.append(note)

        elif etype == "system_notes_cleared":
            sess.system_notes = []

        elif etype == "turn_reverted":
            sess.stage_hold = True
            reason = str(getattr(ev, "reason", "") or "")
            if reason:
                note = f"[系统回滚] 已无损回退至第 {getattr(ev, 'target_turn_id', 0)} 轮前状态（原因：{reason}）。"
                if note not in sess.system_notes:
                    sess.system_notes.append(note)

    if last_patch:
        sess.last_patch = last_patch
    if max_turn_seen > int(sess.turn_count or 0):
        sess.turn_count = max_turn_seen
    return sess


def project_state_incremental(
    events: Sequence[AnyDialogueEvent],
    snapshot_state: Optional[SessionState] = None,
    snapshot_index: int = 0,
    base_state: Optional[SessionState] = None,
) -> tuple[SessionState, int]:
    """
    Incremental state projection using a prior snapshot at `snapshot_index`.
    Falls back to full replay only when a `TurnReverted` event appears in the new tail.
    Returns `(projected_state, new_snapshot_index)`.
    """
    if (
        snapshot_state is not None
        and 0 < snapshot_index <= len(events)
        and not any(
            isinstance(ev, TurnReverted) or getattr(ev, "event_type", "") == "turn_reverted"
            for ev in events[snapshot_index:]
        )
    ):
        if snapshot_index == len(events):
            return snapshot_state.model_copy(deep=True), snapshot_index
        next_state = project_state(events[snapshot_index:], base_state=snapshot_state)
        return next_state, len(events)

    full_state = project_state(events, base_state=base_state)
    return full_state, len(events)


_DIFF_SECTIONS = (
    ("profile", (
        "phone_number", "name", "title", "age", "target_driver", "expertise",
        "family_size", "price_sensitivity", "residence", "parking_conditions",
    )),
    ("needs.explicit", (
        "budget_min", "budget_max", "airbag_count", "battery_kwh",
        "acceleration_0_100", "electric_range_km", "price", "vehicle_category_bottom",
        "brand", "powertrain_type", "design_style", "drive_type", "seat_layout",
        "autonomous_driving_level",
    )),
    ("needs.implicit", (
        "size", "vehicle_usability", "aesthetics", "comfort_level", "smartness",
        "family_friendliness", "energy_consumption_level", "road_performance",
        "brand_grade", "driving_range", "power_performance", "safety",
        "cost_performance", "space", "cargo_space",
    )),
    ("reservation", (
        "test_driver", "reservation_date", "reservation_time_slot", "store_id",
        "reservation_time", "reservation_location", "reservation_phone_number", "salesman",
    )),
)


def _values_differ(old_v: Any, new_v: Any) -> bool:
    if old_v is None and new_v == "":
        return False
    if old_v == "" and new_v is None:
        return False
    return old_v != new_v


def diff_to_events(
    before: SessionState,
    after: SessionState,
    turn_id: int,
    source: str = "extractor",
) -> List[AnyDialogueEvent]:
    """Convert state differences between `before` and `after` into typed `DialogueEvent`s."""
    events: List[AnyDialogueEvent] = []
    for section, fields in _DIFF_SECTIONS:
        for fname in fields:
            fpath = f"{section}.{fname}"
            old_v = _get_nested_field(before, fpath)
            new_v = _get_nested_field(after, fpath)
            if _values_differ(old_v, new_v):
                serial_val = str(new_v) if hasattr(new_v, "isoformat") else new_v
                serial_old = str(old_v) if hasattr(old_v, "isoformat") else old_v
                events.append(
                    SlotUpdated(
                        turn_id=turn_id,
                        source=source,
                        field_path=fpath,
                        value=serial_val,
                        old_value=serial_old,
                    )
                )

    for top_field in (
        "stage_hold",
        "consecutive_ask_turns",
        "last_nba_action",
        "interrupted_goals",
        "subdag_state",
        "handoff_context",
    ):
        old_v = getattr(before, top_field, None)
        new_v = getattr(after, top_field, None)
        if _values_differ(old_v, new_v):
            events.append(
                SlotUpdated(
                    turn_id=turn_id,
                    source=source,
                    field_path=top_field,
                    value=new_v,
                    old_value=old_v,
                )
            )

    # Negative exclusions delta
    b_neg = before.preferences.negative_exclusions
    a_neg = after.preferences.negative_exclusions
    for cat, attr in (
        ("powertrain", "powertrains"),
        ("brand", "brands"),
        ("model", "models"),
        ("category", "categories"),
        ("feature", "features"),
    ):
        old_set = set(getattr(b_neg, attr, []) or [])
        for item in getattr(a_neg, attr, []) or []:
            if item not in old_set:
                events.append(
                    ConstraintNegated(
                        turn_id=turn_id,
                        source=source,
                        category=cat,
                        value=item,
                    )
                )

    if after.pending_confirmation != before.pending_confirmation:
        events.append(
            PendingConfirmationUpdated(
                turn_id=turn_id,
                source=source,
                pending_confirmation=dict(after.pending_confirmation),
            )
        )

    if after.pending_action != before.pending_action:
        events.append(
            SlotUpdated(
                turn_id=turn_id,
                source=source,
                field_path="pending_action",
                value=dict(after.pending_action) if after.pending_action is not None else None,
            )
        )

    if after.pending_correction != before.pending_correction:
        events.append(
            SlotUpdated(
                turn_id=turn_id,
                source=source,
                field_path="pending_correction",
                value=after.pending_correction,
            )
        )

    if after.active_loop != before.active_loop:
        events.append(
            ActiveLoopUpdated(
                turn_id=turn_id,
                source=source,
                active_loop=after.active_loop.model_dump() if after.active_loop is not None else None,
            )
        )

    old_notes = set(before.system_notes or [])
    for note in after.system_notes or []:
        if note and note not in old_notes:
            events.append(
                SystemNoteAdded(
                    turn_id=turn_id,
                    source=source,
                    note=note,
                )
            )

    if after.matched_cars != before.matched_cars:
        events.append(
            MatchedCarsUpdated(
                turn_id=turn_id,
                source=source,
                matched_cars=list(after.matched_cars),
            )
        )

    if after.stage != before.stage:
        events.append(
            StageTransitioned(
                turn_id=turn_id,
                source=source,
                from_stage=before.stage,
                to_stage=after.stage,
            )
        )

    return events
