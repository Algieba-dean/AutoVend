"""
Regression tests for all 5 code review fixes (#1-#5).
"""

import json
import time
from typing import Any, List, Optional
from unittest.mock import patch

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import MemorySaver
from pydantic import Field

from src.agent.graph.generation_nodes import _schedule_async_hallucination_audit
from src.agent.graph.routing_nodes import _schedule_async_slot_extraction
from src.agent.langchain_tools import (
    IdempotencyStore,
    manage_test_drive_tool,
    query_dealer_info_tool,
    query_dealer_promotions_tool,
    submit_test_drive_reservation_tool,
)
from src.agent.langgraph_agent import LangGraphSalesAgent
from src.agent.schemas import SessionState
from src.agent.voice_skills import extract_lightweight_entities, route_voice_skill
from src.core.agentops import (
    get_current_artifact_bundle_version,
    reset_artifact_bundle_cache,
)
from src.core.dealer_store import DealerStore, TestDriveStore
from src.mlops.registry import ArtifactBundleRegistry


class _StubChatModel(BaseChatModel):
    call_count: int = 0
    reply_text: str = "好的，请问还有什么可以帮您？"
    shared_calls: List[int] = Field(default_factory=lambda: [0])

    @property
    def _llm_type(self) -> str:
        return "stub-chat"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "_StubChatModel":
        return self

    def with_structured_output(self, schema: Any, **kwargs: Any) -> "_StubChatModel":
        return self

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.call_count += 1
        self.shared_calls[0] += 1
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.reply_text))])


# ── #1 [P0] Async Sidecar Race & Event-Sourcing Consistency ──────────


def test_p0_async_slot_extraction_monotonic_merge_and_events():
    """Stale _bg_extract must not overwrite newer turn fields, must fill empty fields, and emit events."""
    llm = _StubChatModel()
    agent = LangGraphSalesAgent(llm=llm, checkpointer=MemorySaver(), voice_mode=True)
    session_id = "race-extract-1"

    # Turn 1 snapshot
    s1 = SessionState(session_id=session_id, turn_count=1)
    # Newer Turn 2 already updated budget_max=35.0 in checkpointer
    s2 = SessionState(session_id=session_id, turn_count=2)
    s2.needs.explicit.budget_max = 35.0

    from src.agent.events import SlotUpdated

    agent.graph.update_state(
        {"configurable": {"thread_id": session_id}},
        {
            "session_state": s2,
            "events": [
                SlotUpdated(
                    turn_id=2,
                    source="voice_lightweight_entity",
                    field_path="needs.explicit.budget_max",
                    value=35.0,
                )
            ],
        },
    )

    # Mock extract_unified_slots to return stale budget_max=20.0 and new profile.name="张三"
    def _fake_extract(_model, _conv, sess_copy):
        sess_copy.needs.explicit.budget_max = 20.0
        sess_copy.profile.name = "张三"
        return sess_copy, None

    with patch("src.agent.extractors.unified_extractor.extract_unified_slots", side_effect=_fake_extract):
        _schedule_async_slot_extraction(agent, session_id, "user: 20万左右，我叫张三", s1, origin_turn_id=1)
        agent._sync_executor.shutdown(wait=True)

    snap = agent.get_graph_state(session_id)
    vals = snap.values or {}
    final_sess: SessionState = vals["session_state"]
    events = vals.get("events") or []

    # Newer turn field preserved; empty field monotonically filled
    assert final_sess.needs.explicit.budget_max == 35.0
    assert final_sess.profile.name == "张三"
    # Event emitted for profile.name with origin_turn_id=1
    assert any(
        getattr(ev, "event_type", "") == "slot_updated"
        and getattr(ev, "field_path", "") == "profile.name"
        and getattr(ev, "value", "") == "张三"
        and getattr(ev, "turn_id", -1) == 1
        for ev in events
    )


def test_p0_async_sidecar_retraction_revert_and_caller_state_preservation():
    """Verify retract_field guard, TurnReverted guard, prior-slot update, and caller_state sidecar preservation."""
    from concurrent.futures import ThreadPoolExecutor

    from src.agent.events import ConstraintNegated, TurnReverted, project_state

    llm = _StubChatModel()
    agent = LangGraphSalesAgent(llm=llm, checkpointer=MemorySaver(), voice_mode=True)
    sid = "race-retract-1"

    # Case A: Turn 1 updates existing residence "北京" -> "上海", while Turn 2 retracts budget
    s1 = SessionState(session_id=sid, turn_count=1)
    s1.profile.residence = "北京"
    s2 = SessionState(session_id=sid, turn_count=2)
    s2.profile.residence = "北京"
    s2.needs.explicit.budget_max = None  # retracted in Turn 2!

    agent.graph.update_state(
        {"configurable": {"thread_id": sid}},
        {
            "session_state": s2,
            "events": [
                ConstraintNegated(
                    turn_id=2,
                    source="extractor",
                    category="retract_field",
                    value="budget",
                )
            ],
        },
    )

    def _fake_extract_retract(_model, _conv, sess_copy):
        sess_copy.needs.explicit.budget_max = 25.0  # stale Turn 1 budget
        sess_copy.profile.residence = "上海"  # updated non-empty Turn 1 field
        sess_copy.preferences.negative_exclusions.brands.append("比亚迪")
        return sess_copy, None

    with patch(
        "src.agent.extractors.unified_extractor.extract_unified_slots",
        side_effect=_fake_extract_retract,
    ):
        _schedule_async_slot_extraction(agent, sid, "搬到上海了，25万，不要比亚迪", s1, origin_turn_id=1)
        agent._sync_executor.shutdown(wait=True)

    vals = agent.get_graph_state(sid).values or {}
    merged_sess: SessionState = vals["session_state"]
    assert merged_sess.needs.explicit.budget_max is None  # Turn 2 retraction NOT overwritten!
    assert merged_sess.profile.residence == "上海"  # Turn 1 non-empty slot update preserved!

    # Case B: TurnReverted blocks late sidecar write
    sid_rev = "race-revert-1"
    agent._sync_executor = ThreadPoolExecutor(max_workers=2)
    s_rev = SessionState(session_id=sid_rev, turn_count=1)
    agent.graph.update_state(
        {"configurable": {"thread_id": sid_rev}},
        {
            "session_state": s_rev,
            "events": [TurnReverted(turn_id=2, target_turn_id=1, reason="rollback")],
        },
    )
    with patch(
        "src.agent.extractors.unified_extractor.extract_unified_slots",
        side_effect=_fake_extract_retract,
    ):
        _schedule_async_slot_extraction(agent, sid_rev, "stale", s_rev, origin_turn_id=1)
        agent._sync_executor.shutdown(wait=True)
    vals_rev = agent.get_graph_state(sid_rev).values or {}
    assert vals_rev["session_state"].profile.residence == ""

    # Case C: Caller passing pre-sidecar res1.session_state into Turn 2 preserves sidecar updates
    sid_caller = "caller-sidecar-1"
    agent._sync_executor = ThreadPoolExecutor(max_workers=2)
    res1 = agent.invoke_turn(sid_caller, "你好", voice_mode=True)
    stale_caller_sess = res1.session_state.model_copy(deep=True)
    assert stale_caller_sess.profile.name == ""

    def _fill_name(_model, _conv, sess_copy):
        sess_copy.profile.name = "赵六"
        return sess_copy, None

    with patch("src.agent.extractors.unified_extractor.extract_unified_slots", side_effect=_fill_name):
        _schedule_async_slot_extraction(
            agent, sid_caller, "我叫赵六", stale_caller_sess, origin_turn_id=stale_caller_sess.turn_count
        )
        agent._sync_executor.shutdown(wait=True)

    agent._sync_executor = ThreadPoolExecutor(max_workers=2)
    res2 = agent.invoke_turn(sid_caller, "推荐纯电轿车", session_state=stale_caller_sess, voice_mode=True)
    assert res2.session_state.profile.name == "赵六"
    proj = project_state(agent.get_graph_state(sid_caller).values["events"])
    assert proj.profile.name == "赵六"


def test_p0_async_hallucination_audit_turn_guard_and_event_emission():
    """_bg_audit emits SlotUpdated(pending_correction) on matching turn, and skips on stale turn."""
    llm = _StubChatModel()
    agent = LangGraphSalesAgent(llm=llm, checkpointer=MemorySaver(), voice_mode=True)
    session_id = "race-audit-1"

    s1 = SessionState(session_id=session_id, turn_count=1)
    agent.graph.update_state({"configurable": {"thread_id": session_id}}, {"session_state": s1})

    class _BadReport:
        is_clean = False
        warnings = ["续航参数与官方数据不符"]

    with patch("src.agent.graph.generation_nodes.audit_response_against_evidence", return_value=_BadReport()):
        _schedule_async_hallucination_audit(agent, s1, "续航1000公里", [], origin_turn_id=1)
        agent._sync_executor.shutdown(wait=True)

    vals = agent.get_graph_state(session_id).values or {}
    assert vals["session_state"].pending_correction == "续航参数与官方数据不符"
    assert any(
        getattr(ev, "field_path", "") == "pending_correction"
        and getattr(ev, "value", "") == "续航参数与官方数据不符"
        for ev in (vals.get("events") or [])
    )

    # Now simulate stale audit from turn 1 arriving when turn 2 is already active
    from concurrent.futures import ThreadPoolExecutor

    agent._sync_executor = ThreadPoolExecutor(max_workers=2)
    s2 = SessionState(session_id=session_id, turn_count=2, pending_correction=None)
    agent.graph.update_state({"configurable": {"thread_id": session_id}}, {"session_state": s2})

    with patch("src.agent.graph.generation_nodes.audit_response_against_evidence", return_value=_BadReport()):
        _schedule_async_hallucination_audit(agent, s1, "旧轮回复", [], origin_turn_id=1)
        agent._sync_executor.shutdown(wait=True)

    vals_after = agent.get_graph_state(session_id).values or {}
    assert vals_after["session_state"].pending_correction is None


# ── #2 [P0] _build_run_config Fail-Open & TTL Cache ──────────────────


def test_p0_artifact_bundle_version_fail_open_and_cached():
    """ArtifactBundleRegistry & agentops fail-open to v1.0.0-local when PG raises RuntimeError."""
    reset_artifact_bundle_cache()
    reg = ArtifactBundleRegistry(cache_ttl_s=60.0)
    with patch("src.mlops.registry.prompt_registry.get_active_prompt", side_effect=RuntimeError("PG down")) as mock_p:
        b1 = reg.get_current()
        assert b1.bundle_version == "v1.0.0-local"
        assert mock_p.call_count == 1
        # Second call uses TTL cache (zero DB/registry round-trips, instant)
        b2 = reg.get_current()
        assert b2.bundle_version == "v1.0.0-local"
        assert mock_p.call_count == 1

    with patch("src.core.agentops.artifact_bundle_registry", reg):
        v = get_current_artifact_bundle_version()
        assert v == "v1.0.0-local"

    agent = LangGraphSalesAgent(llm=_StubChatModel(), checkpointer=MemorySaver(), voice_mode=True)
    t0 = time.perf_counter()
    cfg = agent._build_run_config("cfg-test")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 20.0
    assert cfg["metadata"]["artifact_bundle_version"]


# ── #3 [P1] Unified Dealer Data & Test-Drive Persistence ─────────────


def test_p1_unified_test_drive_submit_and_manage_persistence():
    """Bookings created via submit_test_drive_reservation are queryable/reschedulable/cancellable via manage_test_drive."""
    TestDriveStore.reset_for_tests()
    IdempotencyStore.clear()

    sub_out = json.loads(
        submit_test_drive_reservation_tool.invoke(
            {
                "car_model": "小米SU7 Max",
                "reservation_date": "2026-11-28",
                "reservation_time": "14:00",
                "reservation_location": "AutoVend朝阳4S店",
                "test_driver": "王五",
                "phone_number": "13700137000",
            }
        )
    )
    assert sub_out["submitted"] is True
    res_id = sub_out["reservation_id"]
    assert res_id.startswith("TD-")

    q_out = json.loads(
        manage_test_drive_tool.invoke({"action": "query", "phone_number": "13700137000"})
    )
    assert q_out["count"] == 1
    assert q_out["bookings"][0]["reservation_id"] == res_id

    r_out = json.loads(
        manage_test_drive_tool.invoke(
            {
                "action": "reschedule",
                "reservation_id": res_id,
                "reservation_date": "2026-11-29",
                "reservation_time": "16:00",
            }
        )
    )
    assert r_out["submitted"] is True
    assert r_out["status"] == "RESCHEDULED"
    assert r_out["car_model"] == "小米SU7 Max"

    c_out = json.loads(manage_test_drive_tool.invoke({"action": "cancel", "reservation_id": res_id}))
    assert c_out["status"] == "CANCELLED"

    # Cancelling a non-existent booking fails cleanly instead of phantom CANCELLED
    not_found = json.loads(
        manage_test_drive_tool.invoke({"action": "cancel", "reservation_id": "TD-NONEXISTENT"})
    )
    assert not_found["submitted"] is False
    assert not_found["status"] == "NOT_FOUND"

    # Vice-versa: booking created via manage_test_drive(create) deduplicates with submit_test_drive_reservation
    m_create = json.loads(
        manage_test_drive_tool.invoke(
            {
                "action": "create",
                "car_model": "理想L6",
                "reservation_date": "2026-12-01",
                "reservation_time": "10:00",
                "reservation_location": "AutoVend海淀体验中心",
                "test_driver": "孙七",
                "phone_number": "13600136000",
            }
        )
    )
    sub_dup = json.loads(
        submit_test_drive_reservation_tool.invoke(
            {
                "car_model": "理想L6",
                "reservation_date": "2026-12-01",
                "reservation_time": "10:00",
                "reservation_location": "AutoVend海淀体验中心",
                "test_driver": "孙七",
                "phone_number": "13600136000",
            }
        )
    )
    assert sub_dup["reservation_id"] == m_create["reservation_id"]
    assert sub_dup["idempotent_replay"] is True

    # Dealer info & promotions come from unified DealerStore
    info = json.loads(query_dealer_info_tool.invoke({"store_name": "海淀"}))
    assert "海淀" in info["store_name"]
    promos = json.loads(query_dealer_promotions_tool.invoke({"car_model": "小米SU7"}))
    assert len(promos["promotions"]) >= 1


# ── #4 [P1] Multi-Skill Routing, Dynamic Stores & Prefetch ───────────


def test_p1_multi_skill_routing_dynamic_stores_and_prefetch():
    """Composite utterance merges tools within <=4 budget; dynamic store & prefetch work in <20ms."""
    TestDriveStore.reset_for_tests()
    route = route_voice_skill("我去门店试驾，顺便问下小米 SU7 落地价")
    assert len(route.skill.tool_names) <= 4
    assert "manage_test_drive" in route.skill.tool_names
    assert "calculate_drive_away_price" in route.skill.tool_names
    assert "test_drive_booking" in route.matched_skills
    assert "pricing_finance" in route.matched_skills

    # Sub-intent tool prioritization within <=4 budget (trade-in + test drive)
    route_trade = route_voice_skill("我去门店试驾，顺便算下二手车置换估价")
    assert len(route_trade.skill.tool_names) <= 4
    assert "manage_test_drive" in route_trade.skill.tool_names
    assert "estimate_trade_in_valuation" in route_trade.skill.tool_names

    # Dynamic store matched by store_name even when store_key is an ASCII slug
    DealerStore.upsert_store(
        store_key="store_sz_01",
        store_name="深圳南山旗舰店",
        address="深圳市南山区科技园南区8号",
        parking="免费停车2小时",
        business_hours="09:30 - 21:30",
        showroom_models=["极氪001"],
        available_test_drive_slots=["10:30", "14:30"],
    )
    assert extract_lightweight_entities("我去深圳南山旗舰店试驾").get("store_name") == "深圳南山旗舰店"

    # Dynamic store added to DealerStore is picked up by extract_lightweight_entities
    DealerStore.upsert_store(
        store_key="国贸",
        store_name="AutoVend 国贸CBD展厅",
        address="北京市朝阳区建国门外大街1号",
        parking="地下车库免费2小时",
        business_hours="10:00 - 22:00",
        showroom_models=["小米SU7 Max"],
        available_test_drive_slots=["11:00", "15:00"],
    )
    ents = extract_lightweight_entities("我想去国贸店看看车")
    assert ents.get("store_name") == "国贸"

    # Fast read-only prefetch itself runs in <20ms and injects factual context into system_notes
    from src.agent.graph.retrieval_nodes import prefetch_dealer_and_promo_context

    t0 = time.perf_counter()
    pf_sess = SessionState(session_id="prefetch-unit")
    pf_events = prefetch_dealer_and_promo_context(
        ("dealer_visit", "pricing_finance"),
        {"store_name": "朝阳", "brands": ["小米"]},
        pf_sess,
        turn_id=1,
    )
    assert (time.perf_counter() - t0) * 1000.0 < 20.0
    assert len(pf_events) == 2

    agent = LangGraphSalesAgent(llm=_StubChatModel(), checkpointer=MemorySaver(), voice_mode=True)
    sess = SessionState(session_id="prefetch-test")
    res = agent.invoke_turn(
        "prefetch-test",
        "朝阳门店几点开门？小米SU7有什么优惠？",
        session_state=sess,
        voice_mode=True,
    )
    snap = agent.get_graph_state("prefetch-test")
    events = (snap.values or {}).get("events") or []
    prefetched_notes = [
        getattr(ev, "note", "")
        for ev in events
        if getattr(ev, "source", "") == "voice_prefetch"
    ]
    assert any("[门店信息预取]" in n for n in prefetched_notes)
    assert any("[优惠政策预取]" in n for n in prefetched_notes)
    assert res.response_text


# ── #5 [P2] Barge-in Edge Cases ──────────────────────────────────────


def test_p2_barge_in_skips_tool_call_ai_message_and_guards_pending_action():
    """commit_spoken_text skips empty tool-call AIMessages and guards interrupted pending_action."""
    llm = _StubChatModel(reply_text="帮您约周六下午两点试驾小米SU7，确认提交吗？")
    agent = LangGraphSalesAgent(llm=llm, checkpointer=MemorySaver(), voice_mode=True)
    sid = "barge-edge-1"

    pa = {
        "tool_name": "manage_test_drive",
        "args": {
            "action": "create",
            "car_model": "小米SU7",
            "reservation_date": "周六",
            "reservation_time": "14:00",
            "reservation_location": "AutoVend朝阳4S店",
            "test_driver": "张伟",
            "phone_number": "13800138000",
        },
    }
    sess = SessionState(session_id=sid, pending_action=pa)
    # Seed state with an intermediate tool-call AIMessage + ToolMessage + final spoken AIMessage
    agent.graph.update_state(
        {"configurable": {"thread_id": sid}},
        {
            "session_state": sess,
            "messages": [
                HumanMessage(content="约周六试驾"),
                AIMessage(
                    content="",
                    tool_calls=[{"name": "query_dealer_info", "args": {}, "id": "tc_1"}],
                ),
                ToolMessage(content='{"store_name": "朝阳"}', tool_call_id="tc_1", name="query_dealer_info"),
                AIMessage(content="帮您约周六下午两点试驾小米SU7，确认提交吗？"),
            ],
        },
    )

    commit_res = agent.commit_spoken_text(
        session_id=sid,
        turn_id=1,
        spoken_text="帮您约周六下午两点",
        interrupted=True,
    )
    assert commit_res["updated"] is True
    assert commit_res["interrupted_during_confirmation"] is True
    assert commit_res["content"] == "帮您约周六下午两点 [interrupted]"

    # Next turn user accidentally says "嗯" -> must NOT execute pending_action blindly!
    res_next = agent.invoke_turn(sid, "嗯", voice_mode=True)
    assert "约好了" not in res_next.response_text
    assert res_next.session_state.pending_action is not None
    assert "interrupted_during_confirmation" not in res_next.session_state.pending_action
    assert llm.call_count >= 1

    # Explicit rejection after interrupted confirmation clears pending_action cleanly
    commit_res2 = agent.commit_spoken_text(
        session_id=sid,
        turn_id=2,
        spoken_text="帮您约周六",
        interrupted=True,
    )
    assert commit_res2["interrupted_during_confirmation"] is True
    res_cancel = agent.invoke_turn(sid, "算了", voice_mode=True)
    assert res_cancel.session_state.pending_action is None

    # History with ONLY empty-content tool-call AIMessage returns no_ai_message without corrupting tool call
    sid_only_tc = "barge-only-tc"
    agent.graph.update_state(
        {"configurable": {"thread_id": sid_only_tc}},
        {
            "session_state": SessionState(session_id=sid_only_tc),
            "messages": [
                HumanMessage(content="查门店"),
                AIMessage(content="", tool_calls=[{"name": "query_dealer_info", "args": {}, "id": "tc_only"}]),
            ],
        },
    )
    res_no_ai = agent.commit_spoken_text(sid_only_tc, turn_id=1, spoken_text="你好", interrupted=True)
    assert res_no_ai["updated"] is False
    assert res_no_ai["reason"] == "no_ai_message_found"
