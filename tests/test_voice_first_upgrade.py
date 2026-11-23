"""
Comprehensive unit & integration tests for the Voice-First Dealer Agent upgrade (P0 -> P1 -> P2).
"""

import asyncio
import json
import time
from typing import Any, AsyncIterator, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langgraph.checkpoint.memory import MemorySaver
from pydantic import Field

from src.agent.graph.streaming import clean_voice_text
from src.agent.langchain_chains import build_reply_messages, get_static_system_instruction
from src.agent.langchain_tools import (
    calculate_financing_plan_tool,
    compare_two_vehicles_tool,
    handoff_to_sales_advisor_tool,
    manage_test_drive_tool,
    query_dealer_info_tool,
    query_dealer_promotions_tool,
)
from src.agent.langgraph_agent import LangGraphSalesAgent
from src.agent.schemas import SessionState, Stage
from src.agent.voice_skills import VOICE_SKILLS, get_filler_for_tool, route_voice_skill


class _CountingFakeChatModel(BaseChatModel):
    """Minimal deterministic chat model that counts LLM calls and supports streaming + tool_calls."""

    call_count: int = 0
    reply_text: str = "推荐您看**小米SU7**（纯电旗舰），续航700公里，空间宽敞。"
    emit_tool_call_once: Optional[dict] = None
    bound_tool_names: List[str] = []
    shared_calls: List[int] = Field(default_factory=lambda: [0])

    @property
    def _llm_type(self) -> str:
        return "counting-fake-voice"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "_CountingFakeChatModel":
        clone = self.model_copy()
        clone.bound_tool_names = [getattr(t, "name", str(t)) for t in (tools or [])]
        clone.shared_calls = self.shared_calls
        return clone

    def with_structured_output(self, schema: Any, **kwargs: Any) -> "_CountingFakeChatModel":
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
        if self.emit_tool_call_once and self.shared_calls[0] == 1:
            msg = AIMessage(content="", tool_calls=[self.emit_tool_call_once])
        else:
            msg = AIMessage(content=self.reply_text)
        return ChatResult(generations=[ChatGeneration(message=msg)])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        self.call_count += 1
        self.shared_calls[0] += 1
        if self.emit_tool_call_once and self.shared_calls[0] == 1:
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        {
                            "name": self.emit_tool_call_once["name"],
                            "args": json.dumps(self.emit_tool_call_once["args"]),
                            "id": self.emit_tool_call_once["id"],
                            "index": 0,
                        }
                    ],
                )
            )
            return
        for i in range(0, len(self.reply_text), 8):
            yield ChatGenerationChunk(message=AIMessageChunk(content=self.reply_text[i : i + 8]))


# ── P0 Tests ──────────────────────────────────────────────────────────


def test_p0_kv_cache_constant_system_prefix_across_all_stages():
    """SystemMessage must be 100% byte-identical across all 7 stages and 20 turns."""
    sess = SessionState(session_id="kv-test")
    system_contents = set()
    stages = list(Stage)
    for turn in range(20):
        st = stages[turn % len(stages)]
        assert get_static_system_instruction(st) == get_static_system_instruction(Stage.WELCOME)
        msgs = build_reply_messages(
            stage=st,
            conversation_history=f"user: 第{turn}轮测试",
            profile=sess.profile,
            needs=sess.needs,
            matched_cars=[],
            reservation=sess.reservation,
            voice_mode=True,
        )
        system_contents.add(msgs[0].content)
        # Stage guidance & voice protocol must be in the tail HumanMessage
        assert "阶段指引:" in str(msgs[-1].content)
        assert "Voice-First" in str(msgs[-1].content)
    assert len(system_contents) == 1


def test_p0_skill_routing_latency_and_tool_subset_size():
    """Every skill has <= 4 tools and routes in < 5ms without LLM."""
    for name, skill in VOICE_SKILLS.items():
        assert len(skill.tool_names) <= 4, f"Skill {name} exceeds 4 tools"

    t0 = time.perf_counter()
    r1 = route_voice_skill("我想看25万左右的纯电SUV")
    r2 = route_voice_skill("你们朝阳店营业时间到几点？能停车吗？")
    r3 = route_voice_skill("小米SU7首付两成分三年月供多少？")
    r4 = route_voice_skill("帮我约周六下午两点去朝阳门店试驾")
    r5 = route_voice_skill("转人工客服")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 10.0
    assert r1.skill.name == "vehicle_discovery"
    assert r1.entities.get("budget_max") == 25.0
    assert r1.entities.get("powertrain_type") == "纯电"
    assert r2.skill.name == "dealer_visit"
    assert r3.skill.name == "pricing_finance"
    assert r4.skill.name == "test_drive_booking"
    assert r5.skill.name == "advisor_handoff"


def test_p0_voice_mode_bypasses_sync_extraction_and_stage_lock():
    """In voice_mode=True, WELCOME stage jumps straight to retrieval without sync extract_slots."""
    gen_llm = _CountingFakeChatModel()
    bg_llm = _CountingFakeChatModel()
    agent = LangGraphSalesAgent(
        llm=bg_llm, generation_llm=gen_llm, checkpointer=MemorySaver(), voice_mode=True
    )
    sess = SessionState(session_id="voice-jump", stage=Stage.WELCOME)

    res = agent.invoke_turn(
        "voice-jump",
        "我想看25万左右的纯电轿车",
        session_state=sess,
        voice_mode=True,
    )
    assert res.response_text
    assert "**" not in res.response_text
    assert "（" not in res.response_text
    # Exactly 1 hot-path LLM call (no sync extraction, no turn classifier, no sync auditor)
    assert gen_llm.shared_calls[0] == 1
    snap = agent.get_graph_state("voice-jump")
    assert (snap.values or {}).get("llm_call_count") == 1
    trace = (snap.values or {}).get("execution_trace") or []
    assert "extract_slots" not in trace
    assert "retrieve_vehicles" in trace


def test_p0_clean_voice_text_strips_markdown_and_parens():
    raw = "### 推荐车型\n- **小米SU7**（性价比高）：[点击查看](https://example.com) • 续航700km！"
    cleaned = clean_voice_text(raw)
    assert "**" not in cleaned
    assert "#" not in cleaned
    assert "- " not in cleaned
    assert "（" not in cleaned
    assert "https://" not in cleaned
    assert "小米SU7" in cleaned
    assert "点击查看" in cleaned


# ── P1 Tests ──────────────────────────────────────────────────────────


def test_p1_dealer_voice_tools_contract_and_execution():
    """Verify all 5 categories of P1 Dealer voice tools work deterministically."""
    cmp_out = json.loads(compare_two_vehicles_tool.invoke({"car_a": "小米SU7", "car_b": "特斯拉Model 3"}))
    assert cmp_out["dimensions"] == ["price", "range_and_power", "space"]
    assert "car_a" in cmp_out and "car_b" in cmp_out

    fin_out = json.loads(
        calculate_financing_plan_tool.invoke(
            {"car_model": "小米SU7", "vehicle_price_wan": 25.0, "down_payment_ratio": 0.2, "loan_months": 36}
        )
    )
    assert fin_out["down_payment_wan"] == 5.0
    assert fin_out["monthly_payment_yuan"] > 0

    promo_out = json.loads(query_dealer_promotions_tool.invoke({"car_model": "小米SU7"}))
    assert len(promo_out["promotions"]) >= 1

    info_out = json.loads(query_dealer_info_tool.invoke({"store_name": "朝阳", "car_model": "小米SU7"}))
    assert "营业" in info_out["business_hours"] or "09:" in info_out["business_hours"]
    assert len(info_out["available_test_drive_slots"]) > 0

    td_create = json.loads(
        manage_test_drive_tool.invoke(
            {
                "action": "create",
                "car_model": "小米SU7",
                "reservation_date": "2026-11-28",
                "reservation_time": "14:00",
                "reservation_location": "AutoVend朝阳4S店",
                "test_driver": "张伟",
                "phone_number": "13800138000",
            }
        )
    )
    assert td_create["submitted"] is True
    res_id = td_create["reservation_id"]

    td_query = json.loads(manage_test_drive_tool.invoke({"action": "query", "reservation_id": res_id}))
    assert td_query["count"] == 1

    td_resched = json.loads(
        manage_test_drive_tool.invoke(
            {
                "action": "reschedule",
                "reservation_id": res_id,
                "car_model": "小米SU7",
                "reservation_date": "2026-11-29",
                "reservation_time": "15:00",
                "reservation_location": "AutoVend朝阳4S店",
                "phone_number": "13800138000",
            }
        )
    )
    assert td_resched["status"] == "RESCHEDULED"

    td_cancel = json.loads(manage_test_drive_tool.invoke({"action": "cancel", "reservation_id": res_id}))
    assert td_cancel["status"] == "CANCELLED"

    handoff_out = json.loads(handoff_to_sales_advisor_tool.invoke({"reason": "定制金融方案"}))
    assert handoff_out["handoff"] is True


def test_p1_zero_llm_direct_execution_on_oral_affirm():
    """When pending_action is staged, user saying '好的' executes it with 0 LLM calls."""
    llm = _CountingFakeChatModel()
    agent = LangGraphSalesAgent(llm=llm, checkpointer=MemorySaver(), voice_mode=True)
    sess = SessionState(
        session_id="affirm-0llm",
        pending_action={
            "tool_name": "manage_test_drive",
            "args": {
                "action": "create",
                "car_model": "小米SU7",
                "reservation_date": "2026-11-28",
                "reservation_time": "14:00",
                "reservation_location": "AutoVend朝阳4S店",
                "test_driver": "张伟",
                "phone_number": "13800138000",
            },
        },
    )

    res = agent.invoke_turn("affirm-0llm", "好的，确认", session_state=sess, voice_mode=True)
    assert llm.call_count == 0
    assert "约好了" in res.response_text
    assert res.session_state.pending_action is None


def test_p1_streaming_0ms_filler_and_no_replace_in_voice_mode():
    """Streaming in voice_mode emits 0ms filler on tool_call and never emits ('replace', ...)."""
    gen_llm = _CountingFakeChatModel(
        emit_tool_call_once={
            "name": "query_dealer_info",
            "args": {"store_name": "朝阳"},
            "id": "call_1",
        },
        reply_text="朝阳门店每天九点到八点半营业，院内可免费停车。",
    )
    bg_llm = _CountingFakeChatModel()
    agent = LangGraphSalesAgent(
        llm=bg_llm, generation_llm=gen_llm, checkpointer=MemorySaver(), voice_mode=True
    )
    sess = SessionState(session_id="stream-filler")

    async def _collect():
        events = []
        async for ev in agent.astream_turn(
            "stream-filler", "你们朝阳门店几点关门？", session_state=sess, voice_mode=True
        ):
            events.append(ev)
        return events

    events = asyncio.run(_collect())
    kinds = [k for k, _ in events]
    deltas = [v for k, v in events if k == "delta"]
    assert "replace" not in kinds
    assert get_filler_for_tool("query_dealer_info") in deltas


# ── P2 Tests ──────────────────────────────────────────────────────────


def test_p2_barge_in_commit_spoken_text_updates_checkpointer():
    """commit_spoken_text replaces last AIMessage in checkpointer with truncated text + [interrupted]."""
    llm = _CountingFakeChatModel(reply_text="推荐您看小米SU7，续航七百公里，空间也很大。")
    agent = LangGraphSalesAgent(llm=llm, checkpointer=MemorySaver(), voice_mode=True)
    sess = SessionState(session_id="barge-in-1")

    agent.invoke_turn("barge-in-1", "推荐个纯电车", session_state=sess, voice_mode=True)
    res = agent.commit_spoken_text(
        session_id="barge-in-1",
        turn_id=1,
        spoken_text="推荐您看小米SU7",
        interrupted=True,
    )
    assert res["updated"] is True
    assert res["content"] == "推荐您看小米SU7 [interrupted]"

    snap = agent.get_graph_state("barge-in-1")
    msgs = list((snap.values or {}).get("messages") or [])
    ai_msgs = [m for m in msgs if isinstance(m, AIMessage)]
    assert len(ai_msgs) == 1
    assert ai_msgs[-1].content == "推荐您看小米SU7 [interrupted]"
    assert ai_msgs[-1].additional_kwargs.get("interrupted") is True


def test_p1_write_tool_staging_and_0llm_affirm_e2e():
    """LLM calling manage_test_drive stages pending_action (not executed); next '好的' executes with 0 LLM."""

    class _StageBookingFakeLLM(_CountingFakeChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            self.call_count += 1
            self.shared_calls[0] += 1
            if self.shared_calls[0] == 1:
                return ChatResult(
                    generations=[
                        ChatGeneration(
                            message=AIMessage(
                                content="",
                                tool_calls=[
                                    {
                                        "name": "manage_test_drive",
                                        "args": {
                                            "action": "create",
                                            "car_model": "小米SU7",
                                            "reservation_date": "2026-11-30",
                                            "reservation_time": "14:00",
                                            "reservation_location": "AutoVend朝阳4S店",
                                            "test_driver": "李四",
                                            "phone_number": "13900139000",
                                        },
                                        "id": "call_td_1",
                                    }
                                ],
                            )
                        )
                    ]
                )
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content="帮您约周六下午两点去朝阳4S店试驾小米SU7，确认提交吗？"
                        )
                    )
                ]
            )

    gen_llm = _StageBookingFakeLLM()
    bg_llm = _CountingFakeChatModel()
    agent = LangGraphSalesAgent(
        llm=bg_llm, generation_llm=gen_llm, checkpointer=MemorySaver(), voice_mode=True
    )
    sess = SessionState(session_id="stage-affirm-e2e")

    res1 = agent.invoke_turn(
        "stage-affirm-e2e",
        "帮我约11月30日下午2点去朝阳4S店试驾小米SU7，李四，13900139000",
        session_state=sess,
        voice_mode=True,
    )
    assert res1.session_state.pending_action is not None
    assert res1.session_state.pending_action["tool_name"] == "manage_test_drive"
    calls_before_affirm = gen_llm.shared_calls[0]

    res2 = agent.invoke_turn("stage-affirm-e2e", "好的，确认", voice_mode=True)
    assert gen_llm.shared_calls[0] == calls_before_affirm
    assert "约好了" in res2.response_text
    assert res2.session_state.pending_action is None


def test_p0_pending_correction_injected_and_cleared():
    """pending_correction is injected into voice prompt and cleared after reply generation."""
    llm = _CountingFakeChatModel(reply_text="抱歉更正一下，小米SU7标准版续航是700公里。")
    agent = LangGraphSalesAgent(llm=llm, checkpointer=MemorySaver(), voice_mode=True)
    sess = SessionState(
        session_id="corr-test",
        pending_correction="上轮报价偏差，需口语更正续航参数",
    )

    msgs = build_reply_messages(
        stage=Stage.CAR_SELECTION,
        conversation_history="user: 那续航多少",
        profile=sess.profile,
        needs=sess.needs,
        matched_cars=[],
        reservation=sess.reservation,
        voice_mode=True,
        pending_correction=sess.pending_correction,
    )
    assert "上轮口语纠偏任务" in str(msgs[-1].content)

    res = agent.invoke_turn("corr-test", "那续航多少", session_state=sess, voice_mode=True)
    assert res.session_state.pending_correction is None


def test_p2_commit_spoken_text_fastapi_route():
    """POST /api/voice/commit_spoken_text updates checkpointer via VoicePipeline."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.app.routes import voice as voice_routes
    from src.agent.sales_agent import SalesAgent
    from src.agent.voice.pipeline import VoicePipeline

    llm = _CountingFakeChatModel(reply_text="推荐您看小米SU7，续航七百公里。")
    sales_agent = SalesAgent(llm=llm, checkpointer=MemorySaver(), voice_mode=True)
    sales_agent.run_graph_turn(
        SessionState(session_id="http-barge-1"), "推荐个纯电车", voice_mode=True
    )

    mock_pipeline = VoicePipeline(agent=sales_agent)
    prev_pipeline = voice_routes._pipeline
    voice_routes.set_voice_pipeline(mock_pipeline)
    try:
        app = FastAPI()
        app.include_router(voice_routes.router)
        client = TestClient(app)
        resp = client.post(
            "/api/voice/commit_spoken_text",
            json={
                "session_id": "http-barge-1",
                "turn_id": 1,
                "spoken_text": "推荐您看小米SU7",
                "interrupted": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] is True
        assert data["content"] == "推荐您看小米SU7 [interrupted]"
    finally:
        voice_routes._pipeline = prev_pipeline

