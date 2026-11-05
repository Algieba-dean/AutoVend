"""
Comprehensive unit and integration tests for Architectural Refactoring (Battles 1, 2, 3, 4).
"""

import asyncio
import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.models.schemas import ChatRequest
from backend.app.routes.chat import set_agent
from src.agent.guardrail.compliance import (
    COMPLIANCE_FALLBACK_RESPONSE,
    DualStreamComplianceGuard,
)
from src.agent.sales_agent import SalesAgent
from src.agent.schemas import (
    ExplicitNeeds,
    ReservationInfo,
    SessionState,
    Stage,
    UserProfile,
    VehicleNeeds,
)
from src.agent.storage.distributed_session import (
    DistributedSessionStore,
    SessionLockTimeoutError,
    get_distributed_session_store,
)
from src.agent.tools import sanitize_tool_args
from src.agent.unified_schema import (
    UpdateSessionSlotsTool,
    apply_slot_updates,
)
from src.agent.extractors.unified_extractor import extract_unified_slots


# ============================================================
# Helpers & Mocks
# ============================================================


def _create_mock_llm():
    mock = MagicMock()
    mock.complete.return_value = MagicMock(text="尊敬的客户您好，欢迎咨询 AutoVend！")
    return mock


# ============================================================
# Battle 1: Native Async Generator & Streaming API Tests
# ============================================================


class TestBattle1AsyncStreaming:
    @pytest.mark.asyncio
    async def test_sales_agent_respond_stream_native_async(self):
        """SalesAgent.respond_stream must be an async generator yielding metadata, delta, and done."""
        llm = _create_mock_llm()
        agent = SalesAgent(llm=llm)
        state = SessionState(session_id="test_stream_1", stage=Stage.WELCOME)

        events = []
        async for event_type, payload in agent.respond_stream(state):
            events.append((event_type, payload))

        event_types = [e[0] for e in events]
        assert "metadata" in event_types
        assert "done" in event_types
        assert event_types[0] == "metadata"
        assert event_types[-1] == "done"

        # Verify metadata payload
        meta_event = next(p for t, p in events if t == "metadata")
        assert "session_state" in meta_event
        assert meta_event["session_state"].session_id == "test_stream_1"

        # Verify memory updated asynchronously
        history = agent.memory.get_history("test_stream_1")
        assert len(history) == 1
        assert history[0].role.value == "assistant"

    @pytest.mark.asyncio
    async def test_sales_agent_cancellation_propagation(self):
        """When client cancels, asyncio.CancelledError must be re-raised cleanly for resource teardown."""
        llm = MagicMock()

        async def cancelled_stream(*args, **kwargs):
            yield MagicMock(delta="chunk1")
            raise asyncio.CancelledError("Client disconnected")

        llm.astream_chat = cancelled_stream
        agent = SalesAgent(llm=llm)
        state = SessionState(session_id="test_cancel_1", stage=Stage.WELCOME)

        with pytest.raises(asyncio.CancelledError):
            async for _ in agent.respond_stream(state):
                pass

    @pytest.mark.asyncio
    async def test_api_stream_endpoint_sse_flow(self, monkeypatch, tmp_path):
        """Test /api/chat/stream SSE bridge yields metadata, tokens, done with proper SSE headers."""
        from backend.app.main import app, _startup_status

        llm = _create_mock_llm()
        agent = SalesAgent(llm=llm)
        set_agent(agent)
        _startup_status["agent_ready"] = True

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/chat/stream",
                json={"session_id": "sse_stream_test", "message": "我想买一辆车"},
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            assert resp.headers.get("x-accel-buffering") == "no"
            assert "no-cache" in resp.headers.get("cache-control", "")

            body = resp.text
            assert "event: metadata" in body
            assert "event: done" in body


# ============================================================
# Battle 2: Distributed Session Store & OCC Versioning Tests
# ============================================================


class TestBattle2DistributedStorage:
    @pytest.mark.asyncio
    async def test_distributed_store_lifecycle_and_occ(self):
        """Test get_or_create, save increments version, and get retrieves updated state."""
        store = DistributedSessionStore()
        session_id = "occ_session_1"

        state = await store.get_or_create(session_id)
        assert state.session_id == session_id
        initial_version = state.version

        state.profile.name = "张三"
        await store.save(session_id, state)
        assert state.version == initial_version + 1

        loaded = await store.get(session_id)
        assert loaded is not None
        assert loaded.profile.name == "张三"
        assert loaded.version == initial_version + 1

    @pytest.mark.asyncio
    async def test_distributed_lease_lock_contention(self):
        """Test that lock_session raises SessionLockTimeoutError when lock is already acquired."""
        store = DistributedSessionStore()
        session_id = "lock_test_1"

        # Hold the lock in one context
        async with store.lock_session(session_id, timeout=2.0, wait_timeout=0.1):
            # Attempt to acquire same session lock concurrently with small wait_timeout
            with pytest.raises(SessionLockTimeoutError) as exc_info:
                async with store.lock_session(session_id, timeout=2.0, wait_timeout=0.05):
                    pass
            assert exc_info.value.status_code == 429


# ============================================================
# Battle 3: Unified Schema & Slot Retraction Tests
# ============================================================


class TestBattle3UnifiedSchema:
    def test_update_session_slots_application(self):
        """Test applying unified slot tool updates to SessionState."""
        state = SessionState(session_id="unified_1")
        tool = UpdateSessionSlotsTool(
            customer_name="李四",
            age=32,
            city="杭州",
            budget_min_wan=25.0,
            budget_max_wan=35.0,
            preferred_powertrain="纯电",
            seat_count=5,
            reservation_date="2026-11-20",
            reservation_time_slot="上午",
            preferred_4s_store="杭州西湖体验中心",
        )

        updated = apply_slot_updates(state, tool)
        assert updated.profile.name == "李四"
        assert updated.profile.age == "32"
        assert updated.profile.residence == "杭州"
        assert updated.needs.explicit.budget_min == 25.0
        assert updated.needs.explicit.budget_max == 35.0
        assert updated.needs.explicit.powertrain_type == "纯电"
        assert updated.needs.explicit.seat_layout == "5座"
        assert updated.reservation.reservation_date == "2026-11-20"
        assert updated.reservation.reservation_time_slot == "上午"
        assert updated.reservation.reservation_location == "杭州西湖体验中心"

    def test_slot_retraction_clears_constraints(self):
        """Test that retracted_fields resets explicitly cancelled slots to avoid monotonic lock-in."""
        state = SessionState(session_id="retract_1")
        state.needs.explicit.budget_min = 20.0
        state.needs.explicit.budget_max = 30.0
        state.needs.explicit.price = "20-30万"
        state.needs.explicit.powertrain_type = "纯电"
        state.needs.explicit.vehicle_category_bottom = "SUV"

        tool = UpdateSessionSlotsTool(
            retracted_fields=["budget", "suv"],
            preferred_powertrain="插电混动",
        )

        updated = apply_slot_updates(state, tool)
        assert updated.needs.explicit.budget_min is None
        assert updated.needs.explicit.budget_max is None
        assert updated.needs.explicit.price == ""
        assert updated.needs.explicit.vehicle_category_bottom == ""
        # Newly updated slot remains
        assert updated.needs.explicit.powertrain_type == "插电混动"

    def test_extract_unified_slots_single_flight(self):
        """Test single-flight unified extraction using mock LLM."""
        llm = MagicMock()
        llm.complete.return_value = MagicMock(
            text=json.dumps(
                {
                    "customer_name": "王五",
                    "budget_min_wan": 15.0,
                    "budget_max_wan": 20.0,
                    "preferred_powertrain": "增程",
                    "retracted_fields": ["sedan"],
                }
            )
        )
        state = SessionState(session_id="single_flight_1")
        updated, tool_data = extract_unified_slots(llm, "User: 我叫王五，想看15到20万的增程车，不要轿车", state)

        assert tool_data.customer_name == "王五"
        assert updated.profile.name == "王五"
        assert updated.needs.explicit.budget_min == 15.0
        assert updated.needs.explicit.budget_max == 20.0
        assert updated.needs.explicit.powertrain_type == "增程"


# ============================================================
# Battle 4: Strong Typing, Relative Date, & Security Guardrails
# ============================================================


class TestBattle4DomainStrongTypingAndSecurity:
    def test_explicit_needs_strong_typing_and_validation(self):
        """Test numerical types and budget_max >= budget_min constraint."""
        needs = ExplicitNeeds(
            budget_min=20.0,
            budget_max=30.0,
            airbag_count=6,
            battery_kwh=85.5,
            acceleration_0_100=3.9,
            electric_range_km=700,
        )
        assert isinstance(needs.budget_min, float)
        assert needs.budget_min == 20.0
        assert needs.airbag_count == 6
        assert needs.battery_kwh == 85.5

        # String parsing
        needs_str = ExplicitNeeds(
            budget_min="18.5万",
            airbag_count="8个",
            battery_kwh="100kwh",
        )
        assert needs_str.budget_min == 18.5
        assert needs_str.airbag_count == 8
        assert needs_str.battery_kwh == 100.0

        # Validate budget_max < budget_min
        with pytest.raises(ValueError, match="最高预算不能低于最低预算"):
            ExplicitNeeds(budget_min=30.0, budget_max=20.0)

    def test_reservation_relative_date_normalization(self):
        """Test resolve_relative_date correctly normalizes relative days."""
        today = date.today()

        tomorrow = ReservationInfo.resolve_relative_date("明天")
        assert tomorrow == today + timedelta(days=1)
        assert tomorrow == (today + timedelta(days=1)).isoformat()  # String equality support

        day_after = ReservationInfo.resolve_relative_date("后天")
        assert day_after == today + timedelta(days=2)

        iso_res = ReservationInfo.resolve_relative_date("2026-12-25")
        assert iso_res == date(2026, 12, 25)

    def test_dual_stream_compliance_guard_fallback(self):
        """Test that strict compliance violations trigger clean fallback instead of broken regex word splicing."""
        violated_text = "这款车你放心，我们保证全网最低价，出事车企全赔！"
        guarded, is_compliant = DualStreamComplianceGuard.guard_output(violated_text)

        assert not is_compliant
        assert guarded == COMPLIANCE_FALLBACK_RESPONSE
        assert "全网最低价" not in guarded
        assert "合同报价单" in guarded

        clean_text = "为您推荐这款 SUV，CLTC 纯电续航 600 公里，空间充裕。"
        guarded_clean, is_clean = DualStreamComplianceGuard.guard_output(clean_text)
        assert is_clean
        assert guarded_clean == clean_text

    def test_sanitize_tool_args_no_longer_blindly_deletes_sql_words(self):
        """Test that normal queries containing words like 'SELECT' or 'UPDATE' are not blindly mangled by regex."""
        state = SessionState(session_id="sec_test_1")
        args = {"query": "Please select the best configuration"}
        sanitized, was_sanitized = sanitize_tool_args("search", args, state)

        # 'select' should NOT be stripped away
        assert "select" in sanitized["query"].lower()

    def test_isodate_hashability_and_string_methods(self):
        """Test ISODate is fully hashable and provides string manipulation methods."""
        from src.agent.schemas import ISODate

        iso_d = ISODate(2026, 11, 7, raw_text="明天")

        # Hashable & usable in sets / dict keys
        s = {iso_d}
        assert iso_d in s
        d = {iso_d: "val"}
        assert d[iso_d] == "val"
        assert hash(iso_d) == hash(date(2026, 11, 7))

        # String helper methods
        assert iso_d.strip() == "明天"
        assert iso_d.lower() == "明天"
        assert iso_d.upper() == "明天"
        assert iso_d.startswith("明")
        assert iso_d.endswith("天")
        assert iso_d.split("天") == ["明", ""]
        assert len(iso_d) == 2

    def test_reservation_relative_date_comprehensive_cases(self):
        """Test Chinese calendar dates, week offsets, Chinese numbers, and weekends."""
        today = date.today()

        # Chinese numbers and days after
        three_days = ReservationInfo.resolve_relative_date("3天后")
        assert three_days == today + timedelta(days=3)
        three_days_cn = ReservationInfo.resolve_relative_date("三天后")
        assert three_days_cn == today + timedelta(days=3)

        one_week = ReservationInfo.resolve_relative_date("一周后")
        assert one_week == today + timedelta(days=7)

        # Calendar dates
        cal_date = ReservationInfo.resolve_relative_date("2026年12月25日")
        assert cal_date == date(2026, 12, 25)

        # Next weekend
        next_weekend = ReservationInfo.resolve_relative_date("下周末")
        assert next_weekend is not None
        # Must be next Saturday
        assert next_weekend.weekday() == 5
        assert next_weekend > today

    @pytest.mark.asyncio
    async def test_api_stream_endpoint_with_isodate_reservation(self, monkeypatch):
        """Test that /api/chat/stream handles sessions with ISODate without TypeError serialization failure."""
        from backend.app.main import app, _startup_status
        from backend.app.routes.chat import _sessions

        llm = _create_mock_llm()
        agent = SalesAgent(llm=llm)
        set_agent(agent)
        _startup_status["agent_ready"] = True

        state = SessionState(session_id="sse_isodate_test", stage=Stage.RESERVATION_4S)
        state.reservation.reservation_date = "下周六"
        _sessions["sse_isodate_test"] = state

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/chat/stream",
                json={"session_id": "sse_isodate_test", "message": "我想确认预约"},
            )
            assert resp.status_code == 200
            assert "event: metadata" in resp.text
            assert "event: done" in resp.text

