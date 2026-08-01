"""
Tests for Tool-level Transactional Rollback (dispatch_transactional & dispatch_all(atomic=True)).
"""

import pytest
from src.agent.schemas import SessionState, Stage
from src.agent.tools import dispatch_all, dispatch_transactional


def _state(stage=Stage.PROFILE_ANALYSIS):
    return SessionState(session_id="test_tx_session", stage=stage)


class TestTransactionalRollback:
    def test_non_atomic_best_effort_retains_prior_patches_on_failure(self):
        """
        Default Best-effort mode: Tool 1 succeeds and patches state.
        Tool 2 fails (disallowed tool). Tool 1's state modification persists.
        """
        state = _state(Stage.PROFILE_ANALYSIS)
        calls = [
            {"tool": "record_profile", "args": {"fields": {"name": "张三", "phone_number": "13800138000"}}},
            {"tool": "select_vehicle", "args": {"car_model": "Tesla Model Y"}},  # Disallowed in PROFILE_ANALYSIS
        ]

        results = dispatch_all(state, calls, atomic=False)

        assert len(results) == 2
        assert results[0].ok is True
        assert results[1].ok is False
        # Profile field applied
        assert state.profile.name == "张三"
        assert state.profile.phone_number == "13800138000"

    def test_atomic_transactional_rollback_reverts_prior_patches_on_failure(self):
        """
        Atomic mode: Tool 1 succeeds and patches state.
        Tool 2 fails (disallowed tool). Transaction aborts and Tool 1's patches are completely rolled back!
        """
        state = _state(Stage.PROFILE_ANALYSIS)
        calls = [
            {"tool": "record_profile", "args": {"fields": {"name": "李四", "phone_number": "13900139000"}}},
            {"tool": "select_vehicle", "args": {"car_model": "Porsche Cayenne"}},  # Disallowed in PROFILE_ANALYSIS
        ]

        results = dispatch_transactional(state, calls)

        assert len(results) == 2
        assert results[0].ok is True
        assert results[1].ok is False
        assert results[1].rolled_back is True
        assert "事务已全额回滚" in results[1].message

        # State must be completely restored to initial empty state!
        assert state.profile.name == ""
        assert state.profile.phone_number == ""

    def test_atomic_transaction_succeeds_when_all_tools_pass(self):
        """Atomic mode: all valid tools succeed and patches remain in state."""
        state = _state(Stage.PROFILE_ANALYSIS)
        calls = [
            {"tool": "record_profile", "args": {"fields": {"name": "王五"}}},
            {"tool": "record_profile", "args": {"fields": {"phone_number": "13700137000"}}},
        ]

        results = dispatch_transactional(state, calls)

        assert len(results) == 2
        assert all(r.ok for r in results)
        assert state.profile.name == "王五"
        assert state.profile.phone_number == "13700137000"
