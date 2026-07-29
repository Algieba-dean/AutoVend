"""
Unit tests for Constraint Reconciliation Engine in AutoVend Agent.
"""

from src.agent.reconciliation import reconcile_constraints
from src.agent.schemas import SessionState


def test_reconcile_budget_vs_brand():
    """Test budget limit conflict with luxury brand."""
    state = SessionState()
    state.needs.explicit.prize = "18万以内"
    state.needs.explicit.brand = "保时捷"

    conflicts = reconcile_constraints(state)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "BUDGET_VS_BRAND"
    assert "保时捷" in conflicts[0].description
    assert len(conflicts[0].suggested_options) == 2

    note = conflicts[0].to_system_note()
    assert "[系统约束提示 - 需求冲突通知]" in note


def test_reconcile_seat_vs_family():
    """Test seating layout conflict with large family."""
    state = SessionState()
    state.profile.family_size = "6人大家庭三代同堂"
    state.needs.explicit.seat_layout = "5座"

    conflicts = reconcile_constraints(state)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "SEATS_VS_FAMILY"
    assert "5座" in conflicts[0].description


def test_reconcile_size_vs_parking():
    """Test vehicle size conflict with narrow parking or novice driver."""
    state = SessionState()
    state.profile.parking_conditions = "老旧小区窄车位"
    state.needs.explicit.vehicle_category_bottom = "全尺寸大型SUV"

    conflicts = reconcile_constraints(state)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "SIZE_VS_PARKING"


def test_no_conflicts_when_compatible():
    """Test state without conflicting constraints returns empty list."""
    state = SessionState()
    state.needs.explicit.prize = "30万以内"
    state.needs.explicit.brand = "比亚迪"
    state.profile.family_size = "3口之家"
    state.needs.explicit.seat_layout = "5座"

    conflicts = reconcile_constraints(state)
    assert len(conflicts) == 0
