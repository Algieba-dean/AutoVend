"""
Comprehensive tests for the LangGraph + LangChain + LlamaIndex backend architecture.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.langchain_tools import (
    get_autovend_tools,
    get_vehicle_detail_tool,
    search_vehicles_tool,
    validate_test_drive_slot_tool,
)
from src.agent.langgraph_agent import LangGraphSalesAgent
from src.agent.sales_agent import SalesAgent
from src.agent.schemas import SessionState, Stage
from src.core.container import ServiceContainer
from src.core.interfaces import BaseRAGService, RAGQueryRequest, RAGQueryResponse
from src.llm.langchain_adapter import (
    LegacyLLMChatAdapter,
    RoutedChatModel,
    build_langchain_llms,
    ensure_chat_model,
)
from src.llm.router import HybridRouter
from src.retrieval.langchain_retriever import (
    LlamaIndexHybridRetriever,
    documents_to_car_dicts,
)


def _make_mock_llm() -> MagicMock:
    mock = MagicMock()

    def side_effect(prompt: str):
        resp = MagicMock()
        low = prompt.lower()
        if "unified" in low or "extract" in low:
            resp.text = json.dumps(
                {
                    "profile": {"name": "李明"},
                    "explicit_needs": {"brand": "比亚迪", "price": "20万~30万"},
                    "implicit_needs": {"comfort_level": "高"},
                    "reservation": {},
                },
                ensure_ascii=False,
            )
        else:
            resp.text = "您好李明！为您推荐比亚迪汉EV，续航表现非常出色。"
        return resp

    mock.complete.side_effect = side_effect
    return mock


class _FakeBackend:
    def __init__(self, model: str, prefix: str):
        self.model = model
        self.prefix = prefix

    def is_available(self) -> bool:
        return True

    def chat(self, messages, max_tokens=512, **kwargs):
        return f"{self.prefix}:{messages[-1]['content']}"

    def stream_chat(self, messages, max_tokens=512, **kwargs):
        yield self.prefix
        yield ":"
        yield messages[-1]["content"]

    def complete(self, prompt, max_tokens=512, **kwargs):
        return f"{self.prefix}:{prompt}"


class TestLangChainAdapter:
    def test_routed_chat_model_sync_and_stream(self):
        router = HybridRouter(
            local=_FakeBackend("qwen-local", "LOCAL"),
            cloud=_FakeBackend("gpt-cloud", "CLOUD"),
        )
        ext_model, gen_model = build_langchain_llms(router)
        assert isinstance(ext_model, RoutedChatModel)
        assert isinstance(gen_model, RoutedChatModel)

        ext_res = ext_model.invoke([HumanMessage(content="hi")])
        gen_res = gen_model.invoke([HumanMessage(content="hi")])
        assert ext_res.content == "LOCAL:hi"
        assert gen_res.content == "CLOUD:hi"

        streamed = "".join(chunk.content for chunk in gen_model.stream([HumanMessage(content="car")]))
        assert streamed == "CLOUD:car"

    @pytest.mark.asyncio
    async def test_routed_chat_model_async_and_astream(self):
        router = HybridRouter(
            local=_FakeBackend("qwen-local", "LOCAL"),
            cloud=_FakeBackend("gpt-cloud", "CLOUD"),
        )
        _, gen_model = build_langchain_llms(router)
        res = await gen_model.ainvoke([HumanMessage(content="async")])
        assert res.content == "CLOUD:async"

        chunks = []
        async for ch in gen_model.astream([HumanMessage(content="stream")]):
            chunks.append(ch.content)
        assert "".join(chunks) == "CLOUD:stream"

    def test_ensure_chat_model_wraps_legacy_llm(self):
        legacy = _make_mock_llm()
        adapted = ensure_chat_model(legacy)
        assert isinstance(adapted, LegacyLLMChatAdapter)
        out = adapted.invoke([HumanMessage(content="hello")])
        assert "比亚迪汉EV" in out.content


class TestLlamaIndexLangChainBridge:
    def test_hybrid_pipeline_retriever_returns_documents(self):
        @dataclass
        class _Item:
            car_model: str
            score: float
            source: str
            text_snippet: str
            metadata: Dict[str, Any] = field(default_factory=dict)

        @dataclass
        class _Res:
            results: List[_Item]

        class _MockPipeline:
            def search(self, query: str, top_k: int = 5):
                return _Res(
                    results=[
                        _Item(
                            car_model="比亚迪汉EV",
                            score=0.92,
                            source="hybrid",
                            text_snippet="比亚迪汉EV 纯电中大型轿车 续航715km",
                            metadata={"brand": "比亚迪", "price": "22万"},
                        )
                    ]
                )

        retriever = LlamaIndexHybridRetriever(pipeline=_MockPipeline(), top_k=3)
        docs = retriever.invoke("20万纯电轿车")
        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert docs[0].metadata["car_model"] == "比亚迪汉EV"
        assert docs[0].metadata["score"] == pytest.approx(0.92)

        cars = documents_to_car_dicts(docs)
        assert cars[0]["car_model"] == "比亚迪汉EV"
        assert cars[0]["brand"] == "比亚迪"

    def test_llamaindex_vector_index_fallback(self):
        class _MockNode:
            def __init__(self):
                self.metadata = {"car_model": "极氪001", "brand": "极氪"}

            def get_content(self):
                return "极氪001 猎装纯电"

        class _MockNodeWithScore:
            def __init__(self):
                self.node = _MockNode()
                self.score = 0.88

        class _MockLlamaRetriever:
            def retrieve(self, query: str):
                return [_MockNodeWithScore()]

        class _MockLlamaIndex:
            def as_retriever(self, similarity_top_k: int = 5):
                return _MockLlamaRetriever()

        retriever = LlamaIndexHybridRetriever(llama_index=_MockLlamaIndex(), top_k=3)
        docs = retriever.invoke("猎装车")
        assert len(docs) == 1
        assert docs[0].metadata["car_model"] == "极氪001"
        assert docs[0].metadata["source"] == "llamaindex_vector_store"


class TestLangChainTools:
    def test_autovend_tools_with_rag_service(self):
        class _DummyRAG(BaseRAGService):
            def search_vehicles(self, request: RAGQueryRequest) -> RAGQueryResponse:
                return RAGQueryResponse(
                    results=[{"car_model": "理想L6", "brand": "理想"}],
                    total_count=1,
                    latency_ms=1.5,
                )

            def get_vehicle_detail(self, car_model: str):
                return {"car_model": car_model, "brand": "理想", "powertrain": "增程"}

        ServiceContainer.reset()
        ServiceContainer.register_rag_service(_DummyRAG())
        try:
            tools = get_autovend_tools()
            assert len(tools) == 6

            search_out = json.loads(search_vehicles_tool.invoke({"query": "家用SUV", "brand": "理想"}))
            assert search_out["total_count"] == 1
            assert search_out["results"][0]["car_model"] == "理想L6"

            detail_out = json.loads(get_vehicle_detail_tool.invoke({"car_model": "理想L6"}))
            assert detail_out["powertrain"] == "增程"

            booking_out = json.loads(
                validate_test_drive_slot_tool.invoke({"reservation_date": "2026-12-01"})
            )
            assert booking_out["valid"] is False
            assert "reservation_time" in booking_out["missing_fields"]
        finally:
            ServiceContainer.reset()


class TestLangGraphSalesAgent:
    def test_graph_mermaid_and_multi_turn_checkpointing(self):
        llm = _make_mock_llm()
        lg_agent = LangGraphSalesAgent(llm=llm, use_unified_extraction=True)
        mermaid = lg_agent.get_graph_mermaid()
        assert "guard_and_route" in mermaid
        assert "extract_slots" in mermaid
        assert "arbitrate_stage" in mermaid
        assert "retrieve_vehicles" in mermaid
        assert "generate_reply" in mermaid

        r1 = lg_agent.invoke_turn("lg-s1", "你好，我叫李明，想看20万到30万的比亚迪")
        assert r1.response_text
        assert r1.session_state.profile.name == "李明"

        # Fast-path skip extraction on second turn
        r2 = lg_agent.invoke_turn(
            "lg-s1",
            "好的，谢谢",
            session_state=r1.session_state,
            skip_extraction=True,
        )
        assert r2.response_text

        snap = lg_agent.get_graph_state("lg-s1")
        msgs = snap.values["messages"]
        assert len(msgs) == 4  # 2 HumanMessage + 2 AIMessage
        assert isinstance(msgs[0], HumanMessage)
        assert isinstance(msgs[1], AIMessage)

    def test_graph_retrieves_via_langchain_llamaindex_retriever(self):
        @dataclass
        class _Item:
            car_model: str
            score: float
            source: str
            text_snippet: str
            metadata: Dict[str, Any] = field(default_factory=dict)

        @dataclass
        class _Res:
            results: List[_Item]

        class _MockPipeline:
            def search(self, query: str, top_k: int = 5):
                return _Res(
                    results=[
                        _Item(
                            car_model="比亚迪海豹",
                            score=0.95,
                            source="hybrid",
                            text_snippet="比亚迪海豹 纯电运动轿车",
                            metadata={"brand": "比亚迪"},
                        )
                    ]
                )

        retriever = LlamaIndexHybridRetriever(pipeline=_MockPipeline())
        lg_agent = LangGraphSalesAgent(
            llm=_make_mock_llm(),
            retriever=retriever,
            use_unified_extraction=True,
        )
        init_state = SessionState(session_id="lg-ret-1", stage=Stage.NEEDS_ANALYSIS)
        res = lg_agent.invoke_turn("lg-ret-1", "我想看比亚迪纯电车", session_state=init_state)
        assert len(res.session_state.matched_cars) == 1
        assert res.session_state.matched_cars[0]["car_model"] == "比亚迪海豹"

    @pytest.mark.asyncio
    async def test_graph_astream_turn(self):
        lg_agent = LangGraphSalesAgent(llm=_make_mock_llm(), use_unified_extraction=True)
        events = []
        async for ev_type, payload in lg_agent.astream_turn("lg-stream-1", "你好，推荐一款车"):
            events.append((ev_type, payload))

        types = [t for t, _ in events]
        assert types[0] == "metadata"
        assert "delta" in types
        assert types[-1] == "done"


class TestLangGraphFastAPIEndpoints:
    @pytest.mark.asyncio
    async def test_graph_checkpoint_and_stream_endpoints(self, tmp_path, monkeypatch):
        from backend.app.main import _startup_status, app
        from backend.app.routes.chat import _sessions, set_agent

        monkeypatch.setattr("backend.app.models.storage.SESSIONS_DIR", tmp_path / "sessions")
        (tmp_path / "sessions").mkdir()
        _sessions.clear()

        agent = SalesAgent(llm=_make_mock_llm(), use_unified_extraction=True)
        set_agent(agent)
        _startup_status["agent_ready"] = True

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            g_resp = await client.get("/api/chat/graph")
            assert g_resp.status_code == 200
            g_data = g_resp.json()
            assert g_data["engine"] == "langgraph"
            assert "guard_and_route" in g_data["nodes"]
            assert "generate_reply" in g_data["nodes"]

            m_resp = await client.post(
                "/api/chat/message",
                json={"session_id": "ep-1", "message": "我叫李明，想看20万比亚迪"},
            )
            assert m_resp.status_code == 200
            assert m_resp.json()["profile"]["name"] == "李明"

            cp_resp = await client.get("/api/chat/session/ep-1/checkpoint")
            assert cp_resp.status_code == 200
            assert cp_resp.json()["message_count"] >= 2

            s_resp = await client.post(
                "/api/chat/stream",
                json={"session_id": "ep-stream-1", "message": "你好"},
            )
            assert s_resp.status_code == 200
            body = s_resp.text
            assert "event: metadata" in body
            assert "event: token" in body
            assert "event: done" in body

            # Streaming turn must also record history in agent.memory
            msgs_resp = await client.get("/api/chat/session/ep-stream-1/messages")
            assert msgs_resp.status_code == 200
            assert len(msgs_resp.json()["messages"]) == 2

            # Ending a session must clear LangGraph's MemorySaver checkpoint too
            del_resp = await client.put("/api/chat/session/ep-1/end")
            assert del_resp.status_code == 200
            cp_after_del = await client.get("/api/chat/session/ep-1/checkpoint")
            assert cp_after_del.status_code == 404


class TestRefactorRegressionFixes:
    def test_hybrid_pipeline_real_search_response_shape(self):
        from types import SimpleNamespace

        from src.retrieval.hybrid_pipeline import HybridPipelineResult

        vehicle = SimpleNamespace(
            car_model="小鹏G6",
            precise_labels=SimpleNamespace(
                brand="小鹏",
                price="20万~25万",
                vehicle_category_bottom="SUV",
                powertrain_type="纯电",
            ),
            ambiguous_labels=SimpleNamespace(
                size="中型",
                family_friendliness="高",
                comfort_level="高",
            ),
            key_details=SimpleNamespace(key_details="800V高压快充，智能辅助驾驶"),
        )
        sr = SimpleNamespace(vehicle=vehicle, score=SimpleNamespace(overall_score=0.91))
        hpr = HybridPipelineResult()
        hpr.search_response = SimpleNamespace(results=[sr])

        pipeline = MagicMock()
        pipeline.search.return_value = hpr

        retriever = LlamaIndexHybridRetriever(pipeline=pipeline, top_k=5)
        docs = retriever.invoke("20万纯电SUV")
        assert len(docs) == 1
        assert docs[0].metadata["car_model"] == "小鹏G6"
        assert docs[0].metadata["brand"] == "小鹏"
        assert docs[0].metadata["score"] == pytest.approx(0.91)
        assert "800V" in docs[0].page_content

    @pytest.mark.asyncio
    async def test_stream_scrubs_think_blocks_across_chunks(self):
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.messages import AIMessageChunk
        from langchain_core.outputs import ChatGenerationChunk

        from src.agent.langchain_chains import generate_reply_stream_with_langchain
        from src.agent.schemas import ReservationInfo, UserProfile, VehicleNeeds

        class _ThinkLLM(BaseChatModel):
            @property
            def _llm_type(self):
                return "think-test"

            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                raise NotImplementedError

            async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
                for tok in ["<thi", "nk>内部推理", "</thi", "nk>\n您好，为您推荐比亚迪汉EV。"]:
                    yield ChatGenerationChunk(message=AIMessageChunk(content=tok))

        chunks = []
        async for ch in generate_reply_stream_with_langchain(
            chat_model=_ThinkLLM(),
            stage=Stage.WELCOME,
            conversation_history="user: 你好",
            profile=UserProfile(),
            needs=VehicleNeeds(),
            matched_cars=[],
            reservation=ReservationInfo(),
        ):
            chunks.append(ch)
        out = "".join(chunks)
        assert "<think>" not in out
        assert "内部推理" not in out
        assert "您好，为您推荐比亚迪汉EV。" in out

    def test_langgraph_retrieves_with_extracted_needs(self):
        seen_queries: List[str] = []

        class _CaptureRetriever:
            def invoke(self, query: str):
                seen_queries.append(query)
                return [
                    Document(
                        page_content="比亚迪唐EV 25万 7座纯电SUV",
                        metadata={"car_model": "比亚迪唐EV", "score": 0.9},
                    )
                ]

        lg_agent = LangGraphSalesAgent(
            llm=_make_mock_llm(),
            retriever=_CaptureRetriever(),
            use_unified_extraction=True,
        )
        sess = SessionState(session_id="needs-q-1", stage=Stage.NEEDS_ANALYSIS)
        sess.needs.explicit.brand = "比亚迪"
        sess.needs.explicit.vehicle_category_bottom = "SUV"
        res = lg_agent.invoke_turn("needs-q-1", "预算20到30万", session_state=sess)
        assert res.session_state.matched_cars and res.session_state.matched_cars[0]["car_model"] == "比亚迪唐EV"
        assert seen_queries
        assert "比亚迪" in seen_queries[0]
        assert "SUV" in seen_queries[0]


class TestArchitectureRefactorFeatures:
    def test_stage_routing_skips_retrieval_in_non_selection_stages(self):
        called = []

        class _SpyRetriever:
            def invoke(self, query: str):
                called.append(query)
                return []

        lg_agent = LangGraphSalesAgent(
            llm=_make_mock_llm(),
            retriever=_SpyRetriever(),
            use_unified_extraction=True,
        )
        # WELCOME stage with no vehicle needs should skip retrieve_vehicles
        welcome_state = SessionState(session_id="route-skip-1", stage=Stage.WELCOME)
        lg_agent.invoke_turn("route-skip-1", "你好", session_state=welcome_state, skip_extraction=True)
        assert called == []

        # Graph mermaid must contain the tools node and conditional routing
        mermaid = lg_agent.get_graph_mermaid()
        assert "tools" in mermaid

    def test_tool_node_loop_executes_tools_and_returns_final_reply(self):
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.outputs import ChatGeneration, ChatResult

        class _ToolLoopLLM(BaseChatModel):
            call_count: int = 0

            @property
            def _llm_type(self):
                return "tool-loop-test"

            def bind_tools(self, tools, **kwargs):
                return self

            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                self.call_count += 1
                if self.call_count == 1:
                    return ChatResult(
                        generations=[
                            ChatGeneration(
                                message=AIMessage(
                                    content="",
                                    tool_calls=[
                                        {
                                            "name": "validate_test_drive_slot",
                                            "args": {"reservation_date": "2026-12-01"},
                                            "id": "tc_1",
                                            "type": "tool_call",
                                        }
                                    ],
                                )
                            )
                        ]
                    )
                # Second call should see the ToolMessage output
                assert any(getattr(m, "type", "") == "tool" for m in messages)
                return ChatResult(
                    generations=[
                        ChatGeneration(
                            message=AIMessage(content="预约还需要补充时间、门店、试驾人和联系电话。")
                        )
                    ]
                )

        tool_llm = _ToolLoopLLM()
        lg_agent = LangGraphSalesAgent(
            llm=_make_mock_llm(),
            generation_llm=tool_llm,
            use_unified_extraction=True,
        )
        res = lg_agent.invoke_turn(
            "tool-loop-1",
            "帮我检查一下2026-12-01的预约信息",
            session_state=SessionState(session_id="tool-loop-1", stage=Stage.RESERVATION_4S),
            skip_extraction=True,
        )
        assert tool_llm.call_count == 2
        assert "预约还需要补充" in res.response_text

    def test_structured_slot_passthrough_bypasses_nl_reparsing(self):
        from unittest.mock import MagicMock

        from src.retrieval.hybrid_pipeline import HybridPipeline

        mock_db = MagicMock()
        mock_db.count.return_value = 1
        mock_filter = MagicMock()
        mock_filter.filter.return_value = MagicMock(
            car_models=["比亚迪汉EV"],
            applied_query={"brand": "比亚迪"},
            degrade_level=0,
            total_candidates=1,
        )
        mock_parser = MagicMock()
        pipeline = HybridPipeline(
            db=mock_db,
            filter_engine=mock_filter,
            query_parser=mock_parser,
        )
        res = pipeline.search(
            "比亚迪 20-30万",
            top_k=5,
            explicit_conditions={"brand": "比亚迪", "budget_min": 20.0, "budget_max": 30.0},
        )
        assert res.parse_method == "structured_slots"
        assert res.parsed_conditions["brand"] == "比亚迪"
        assert res.parsed_conditions["price"] == {"op": "between", "min": 20.0, "max": 30.0}
        mock_parser.parse.assert_not_called()

    def test_structured_chat_prompt_uses_system_and_history_messages(self):
        from langchain_core.messages import SystemMessage

        from src.agent.langchain_chains import build_reply_messages
        from src.agent.schemas import ReservationInfo, UserProfile, VehicleNeeds

        msgs = build_reply_messages(
            stage=Stage.NEEDS_ANALYSIS,
            conversation_history="user: 你好\nassistant: 您好\nuser: 预算25万",
            profile=UserProfile(name="张三"),
            needs=VehicleNeeds(),
            matched_cars=[],
            reservation=ReservationInfo(),
            messages=[
                HumanMessage(content="你好"),
                AIMessage(content="您好"),
                HumanMessage(content="预算25万"),
            ],
        )
        assert isinstance(msgs[0], SystemMessage)
        assert isinstance(msgs[1], HumanMessage)
        assert isinstance(msgs[2], AIMessage)
        assert isinstance(msgs[3], HumanMessage)
        assert msgs[3].content.endswith("预算25万")
        assert "张三" not in msgs[0].content

    @pytest.mark.asyncio
    async def test_routed_chat_model_uses_native_async_backend(self):
        class _AsyncBackend:
            model = "async-model"

            def is_available(self):
                return True

            async def achat(self, messages, max_tokens=512, **kwargs):
                return f"NATIVE_ASYNC:{messages[-1]['content']}"

            async def astream_chat(self, messages, max_tokens=512, **kwargs):
                yield "NATIVE_"
                yield "STREAM"

        router = HybridRouter(cloud=_AsyncBackend())
        _, gen_model = build_langchain_llms(router)
        res = await gen_model.ainvoke([HumanMessage(content="ping")])
        assert res.content == "NATIVE_ASYNC:ping"

        chunks = [c.content async for c in gen_model.astream([HumanMessage(content="ping")])]
        assert "".join(chunks) == "NATIVE_STREAM"

    def test_create_checkpointer_fallback_and_fail_fast(self):
        from langgraph.checkpoint.memory import MemorySaver

        from src.core.checkpointer import create_checkpointer

        saver = create_checkpointer(
            dsn="postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
            allow_memory_fallback=True,
        )
        assert isinstance(saver, MemorySaver)

        with pytest.raises(Exception):
            create_checkpointer(
                dsn="postgresql://invalid:invalid@127.0.0.1:1/nonexistent",
                allow_memory_fallback=False,
            )

    @pytest.mark.asyncio
    async def test_astream_turn_emits_stage_changed_true_in_metadata(self):
        ext_llm = MagicMock()
        ext_llm.complete.return_value = MagicMock(
            text=json.dumps({"customer_name": "李四", "city": "上海"})
        )
        gen_llm = MagicMock()
        gen_llm.complete.return_value = MagicMock(text="李四您好，请问您的购车预算是多少？")

        agent = LangGraphSalesAgent(llm=ext_llm, generation_llm=gen_llm)
        events = []
        async for kind, payload in agent.astream_turn("sess-stage-chg", "我叫李四，在上海"):
            events.append((kind, payload))

        meta_events = [p for k, p in events if k == "metadata"]
        assert len(meta_events) == 1
        assert meta_events[0]["stage_changed"] is True
        assert meta_events[0]["session_state"].stage == Stage.PROFILE_ANALYSIS
        assert meta_events[0]["session_state"].profile.name == "李四"

    @pytest.mark.asyncio
    async def test_routed_chat_model_bind_tools_and_tool_message_roundtrip(self):
        from langchain_core.messages import ToolMessage

        from src.agent.langchain_tools import get_autovend_tools

        seen_calls = []

        class _ToolCapableBackend:
            model = "tool-model"

            def is_available(self):
                return True

            async def achat_message(self, messages, max_tokens=512, **kwargs):
                seen_calls.append({"messages": messages, "tools": kwargs.get("tools")})
                if len(seen_calls) == 1:
                    return {
                        "content": "",
                        "tool_calls": [
                            {"name": "validate_test_drive_slot", "args": {}, "id": "call_1"}
                        ],
                    }
                return {"content": "请提供预约日期和电话。", "tool_calls": []}

        router = HybridRouter(cloud=_ToolCapableBackend())
        _, gen_model = build_langchain_llms(router)
        bound = gen_model.bind_tools(get_autovend_tools())

        first = await bound.ainvoke([HumanMessage(content="我要预约试驾")])
        assert len(first.tool_calls) == 1
        assert first.tool_calls[0]["name"] == "validate_test_drive_slot"

        second = await bound.ainvoke(
            [
                HumanMessage(content="我要预约试驾"),
                first,
                ToolMessage(content='{"valid": false}', tool_call_id="call_1"),
            ]
        )
        assert second.content == "请提供预约日期和电话。"
        assert seen_calls[0]["tools"] is not None
        # Verify ToolMessage and AIMessage.tool_calls were serialized in OpenAI format
        sent_msgs = seen_calls[1]["messages"]
        assert sent_msgs[1]["role"] == "assistant"
        assert sent_msgs[1]["tool_calls"][0]["id"] == "call_1"
        assert sent_msgs[2]["role"] == "tool"
        assert sent_msgs[2]["tool_call_id"] == "call_1"

    def test_slots_to_conditions_parses_explicit_price_string_and_power_type(self):
        from src.retrieval.hybrid_pipeline import HybridPipeline

        pipeline = HybridPipeline(db=MagicMock(), filter_engine=MagicMock())
        conds = pipeline._slots_to_conditions(
            {"brand": "比亚迪", "price": "20-30万", "power_type": "纯电"},
            {"comfort_level": "High"},
        )
        assert conds["brand"] == "比亚迪"
        assert conds["powertrain_type"] == "纯电"
        assert isinstance(conds["price"], dict)
        assert conds["price"]["op"] == "between"

