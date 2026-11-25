"""
LangGraph-powered Stateful Sales Agent (`src/agent/langgraph_agent.py`).

Thin orchestrator compiling AutoVend's multi-stage automotive sales `StateGraph`
from modular node packages under `src/agent/graph/`:
- `src/agent/graph/state.py` — `AgentGraphState` & event projection
- `src/agent/graph/routing_nodes.py` — Guard, slot extraction, policy arbitration, HITL
- `src/agent/graph/retrieval_nodes.py` — Parallel comparison, Tier-0, hybrid RAG & CRAG loop
- `src/agent/graph/generation_nodes.py` — Plugins/SubDAG, generation, ToolNode, hallucination audit
- `src/agent/graph/streaming.py` — Native `astream(..., stream_mode=["messages", "updates"])`
"""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.agent.callbacks import AutoVendOtelCallbackHandler
from src.agent.circuit_breaker import AgentCircuitBreaker
from src.agent.execution_guard import TurnBudgetConfig, build_safe_degradation_response
from src.agent.graph.generation_nodes import (
    node_audit_hallucination,
    node_generate_reply_async,
    node_generate_reply_sync,
    node_run_plugins_and_subdag,
    node_safe_degrade,
    node_tools_with_contract,
    route_after_audit,
    route_after_generate,
)
from src.agent.graph.retrieval_nodes import (
    car_matches_powertrain,
    extract_budget_bounds,
    extract_comparison_models,
    node_grade_retrieval,
    node_retrieve_vehicles,
    node_rewrite_query,
    route_after_grade,
)
from src.agent.graph.routing_nodes import (
    node_arbitrate_stage,
    node_extract_slots,
    node_guard_and_route,
    node_hitl_handoff,
    route_after_arbitrate,
    route_after_guard,
    route_after_hitl,
)
from src.agent.graph.state import (
    MAX_AUDIT_RETRIES,
    MAX_CRAG_RETRIES,
    MAX_TOOL_ITERATIONS,
    PROMPT_PATCH_WINDOW,
    AgentGraphState,
    format_messages_as_text,
    project_current_state,
)
from src.agent.graph.streaming import sanitize_stream_segment, stream_graph_turn
from src.agent.hooks import LifecycleHookManager
from src.agent.langchain_tools import get_autovend_tools
from src.agent.plugins.pipeline import AgentPluginPipeline
from src.agent.schemas import AgentResult, SessionState
from src.core.agentops import get_current_artifact_bundle_version
from src.core.checkpointer import create_checkpointer
from src.llm.langchain_adapter import ensure_chat_model

logger = logging.getLogger(__name__)

_format_messages_as_text = format_messages_as_text


class LangGraphSalesAgent:
    """
    LangGraph + LangChain Stateful Sales Agent.

    Single compiled `StateGraph` with checkpointer (`PostgresSaver` or `MemorySaver`)
    managing multi-turn automotive sales conversations, conditional CRAG retrieval
    routing, contract-aware `ToolNode` loops, and anti-hallucination auditing.
    """

    def __init__(
        self,
        llm: Any,
        generation_llm: Optional[Any] = None,
        auditor_llm: Optional[Any] = None,
        retriever: Optional[Any] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        circuit_breaker: Optional[AgentCircuitBreaker] = None,
        plugin_pipeline: Optional[AgentPluginPipeline] = None,
        hook_manager: Optional[LifecycleHookManager] = None,
        use_unified_extraction: bool = True,
        budget_config: Optional[TurnBudgetConfig] = None,
        voice_mode: bool = False,
    ):
        self.extraction_chat_model: BaseChatModel = ensure_chat_model(llm)
        self.generation_chat_model: BaseChatModel = ensure_chat_model(generation_llm or llm)
        self.auditor_chat_model: Optional[BaseChatModel] = (
            ensure_chat_model(auditor_llm) if auditor_llm is not None else None
        )
        self.tools = get_autovend_tools()
        self.retriever = retriever
        self.checkpointer = checkpointer or create_checkpointer()
        self.circuit_breaker = circuit_breaker or AgentCircuitBreaker()
        self.plugin_pipeline = plugin_pipeline or AgentPluginPipeline()
        self.hook_manager = hook_manager or LifecycleHookManager()
        self.use_unified_extraction = use_unified_extraction
        self.budget_config = budget_config or TurnBudgetConfig()
        self.voice_mode = voice_mode
        self._artifact_bundle_version: str = get_current_artifact_bundle_version()
        self._sync_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="lg_sync_gen")

        self.graph = self._build_graph()

    def _get_generation_runnable(self, tool_names: Optional[List[str]] = None) -> Any:
        if tool_names is not None:
            if not tool_names:
                return self.generation_chat_model
            allowed = set(tool_names)
            selected_tools = [t for t in self.tools if t.name in allowed]
        else:
            selected_tools = self.tools
        if hasattr(self.generation_chat_model, "bind_tools") and selected_tools:
            try:
                return self.generation_chat_model.bind_tools(selected_tools)
            except NotImplementedError:
                pass
        return self.generation_chat_model

    @staticmethod
    def _project_current_state(state: AgentGraphState) -> SessionState:
        return project_current_state(state)

    @staticmethod
    def _extract_comparison_models(query: str, sess: SessionState) -> List[str]:
        return extract_comparison_models(query, sess)

    @staticmethod
    def _extract_budget_bounds(sess: SessionState) -> Tuple[Optional[float], Optional[float]]:
        return extract_budget_bounds(sess)

    @staticmethod
    def _car_matches_powertrain(car: Dict[str, Any], target_power: str) -> bool:
        return car_matches_powertrain(car, target_power)

    # ── Thin Node/Route Delegations (for direct unit-testability) ─────

    def _node_guard_and_route(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_guard_and_route(self, state)

    def _route_after_guard(self, state: AgentGraphState):
        return route_after_guard(state)

    def _node_extract_slots(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_extract_slots(self, state)

    def _node_arbitrate_stage(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_arbitrate_stage(self, state)

    def _route_after_arbitrate(self, state: AgentGraphState):
        return route_after_arbitrate(state)

    def _node_hitl_handoff(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_hitl_handoff(state)

    def _route_after_hitl(self, state: AgentGraphState):
        return route_after_hitl(state)

    def _node_retrieve_vehicles(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_retrieve_vehicles(self, state)

    def _node_grade_retrieval(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_grade_retrieval(self, state)

    def _route_after_grade(self, state: AgentGraphState):
        return route_after_grade(self, state)

    def _node_rewrite_query(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_rewrite_query(state)

    def _node_run_plugins_and_subdag(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_run_plugins_and_subdag(self, state)

    def _node_generate_reply_sync(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_generate_reply_sync(self, state)

    async def _node_generate_reply_async(self, state: AgentGraphState) -> Dict[str, Any]:
        return await node_generate_reply_async(self, state)

    def _route_after_generate(self, state: AgentGraphState):
        return route_after_generate(self, state)

    def _node_tools_with_contract(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_tools_with_contract(self, state)

    def _node_audit_hallucination(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_audit_hallucination(self, state)

    def _route_after_audit(self, state: AgentGraphState):
        return route_after_audit(self, state)

    def _node_safe_degrade(self, state: AgentGraphState) -> Dict[str, Any]:
        return node_safe_degrade(state)

    # ── Graph Builder ─────────────────────────────────────────────────

    def _build_graph(self):
        builder = StateGraph(AgentGraphState)
        builder.add_node("guard_and_route", self._node_guard_and_route)
        builder.add_node("extract_slots", self._node_extract_slots)
        builder.add_node("arbitrate_stage", self._node_arbitrate_stage)
        builder.add_node("hitl_handoff", self._node_hitl_handoff)
        builder.add_node("retrieve_vehicles", self._node_retrieve_vehicles)
        builder.add_node("grade_retrieval", self._node_grade_retrieval)
        builder.add_node("rewrite_query", self._node_rewrite_query)
        builder.add_node("run_plugins_and_subdag", self._node_run_plugins_and_subdag)
        builder.add_node(
            "generate_reply",
            RunnableLambda(self._node_generate_reply_sync, afunc=self._node_generate_reply_async),
        )
        builder.add_node("tools", self._node_tools_with_contract)
        builder.add_node("audit_hallucination", self._node_audit_hallucination)
        builder.add_node("safe_degrade", self._node_safe_degrade)

        builder.add_edge(START, "guard_and_route")
        builder.add_conditional_edges(
            "guard_and_route",
            self._route_after_guard,
            {
                "extract_slots": "extract_slots",
                "arbitrate_stage": "arbitrate_stage",
            },
        )
        builder.add_edge("extract_slots", "arbitrate_stage")
        builder.add_conditional_edges(
            "arbitrate_stage",
            self._route_after_arbitrate,
            {
                "hitl_handoff": "hitl_handoff",
                "retrieve_vehicles": "retrieve_vehicles",
                "run_plugins_and_subdag": "run_plugins_and_subdag",
            },
        )
        builder.add_conditional_edges(
            "hitl_handoff",
            self._route_after_hitl,
            {
                "retrieve_vehicles": "retrieve_vehicles",
                "run_plugins_and_subdag": "run_plugins_and_subdag",
            },
        )
        builder.add_edge("retrieve_vehicles", "grade_retrieval")
        builder.add_conditional_edges(
            "grade_retrieval",
            self._route_after_grade,
            {
                "rewrite_query": "rewrite_query",
                "run_plugins_and_subdag": "run_plugins_and_subdag",
                "safe_degrade": "safe_degrade",
            },
        )
        builder.add_edge("rewrite_query", "retrieve_vehicles")
        builder.add_edge("run_plugins_and_subdag", "generate_reply")
        builder.add_conditional_edges(
            "generate_reply",
            self._route_after_generate,
            {
                "tools": "tools",
                "audit_hallucination": "audit_hallucination",
                "safe_degrade": "safe_degrade",
            },
        )
        builder.add_edge("tools", "generate_reply")
        builder.add_conditional_edges(
            "audit_hallucination",
            self._route_after_audit,
            {
                "generate_reply": "generate_reply",
                "safe_degrade": "safe_degrade",
                "__end__": END,
            },
        )
        builder.add_edge("safe_degrade", END)

        return builder.compile(checkpointer=self.checkpointer)

    # ── Public Execution API ──────────────────────────────────────────

    def _build_run_config(
        self, session_id: str, session_state: Optional[SessionState] = None
    ) -> Dict[str, Any]:
        trace_id = (
            session_state.trace_id if session_state and session_state.trace_id else ""
        ) or uuid.uuid4().hex[:16]
        bundle_ver = self._artifact_bundle_version or get_current_artifact_bundle_version()
        cb = AutoVendOtelCallbackHandler(
            session_id=session_id,
            trace_id=trace_id,
            artifact_bundle_version=bundle_ver,
        )
        return {
            "configurable": {"thread_id": session_id},
            "recursion_limit": self.budget_config.recursion_limit,
            "metadata": {
                "artifact_bundle_version": bundle_ver,
                "trace_id": trace_id,
            },
            "callbacks": [cb],
        }

    @staticmethod
    def _to_agent_result(
        out: Dict[str, Any], fallback_session: Optional[SessionState] = None
    ) -> AgentResult:
        final_sess = out.get("session_state") or fallback_session or SessionState()
        interrupts = out.get("__interrupt__")
        if interrupts:
            first_int = interrupts[0]
            handoff_val = getattr(first_int, "value", first_int)
            handoff_dict = handoff_val if isinstance(handoff_val, dict) else {"payload": handoff_val}
            if isinstance(handoff_dict, dict):
                final_sess.handoff_context = handoff_dict
            handoff_msg = (
                "您好，当前您的购车需求已进入专属顾问人工服务通道，我已将您的偏好与候选车型摘要同步给门店专家，请稍候。"
            )
            return AgentResult(
                response_text=out.get("response_text") or handoff_msg,
                session_state=final_sess,
                stage_changed=bool(out.get("stage_changed", False)),
                matched_cars=final_sess.matched_cars,
                interrupted=True,
                handoff_context=handoff_dict,
                next_best_action=str(out.get("next_best_action") or "handoff_to_human"),
            )
        return AgentResult(
            response_text=out.get("response_text", ""),
            session_state=final_sess,
            stage_changed=bool(out.get("stage_changed", False)),
            matched_cars=final_sess.matched_cars,
            interrupted=False,
            handoff_context=final_sess.handoff_context,
            next_best_action=str(out.get("next_best_action") or final_sess.last_nba_action or ""),
        )

    def invoke_turn(
        self,
        session_id: str,
        user_message: str,
        session_state: Optional[SessionState] = None,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_extraction: bool = False,
        propose_with_llm: bool = False,
        voice_mode: Optional[bool] = None,
    ) -> AgentResult:
        """Execute one full conversation turn synchronously through the LangGraph StateGraph."""
        config = self._build_run_config(session_id, session_state)
        graph_input: AgentGraphState = {
            "session_id": session_id,
            "user_message": user_message,
            "skip_extraction": skip_extraction,
            "retrieved_cars": retrieved_cars,
            "propose_with_llm": propose_with_llm,
            "voice_mode": self.voice_mode if voice_mode is None else bool(voice_mode),
        }
        if session_state is not None:
            graph_input["session_state"] = session_state

        try:
            out = self.graph.invoke(graph_input, config=config)
            return self._to_agent_result(out, fallback_session=session_state)
        except GraphRecursionError as exc:
            logger.warning(
                f"[{session_id}] GraphRecursionError caught, routing to safe degradation: {exc}"
            )
            sess = session_state or SessionState(session_id=session_id)
            return AgentResult(
                response_text=build_safe_degradation_response(sess, reason="recursion_limit_reached"),
                session_state=sess,
                stage_changed=False,
                matched_cars=sess.matched_cars,
            )

    async def ainvoke_turn(
        self,
        session_id: str,
        user_message: str,
        session_state: Optional[SessionState] = None,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_extraction: bool = False,
        propose_with_llm: bool = False,
        voice_mode: Optional[bool] = None,
    ) -> AgentResult:
        """Execute one full conversation turn asynchronously through the LangGraph StateGraph."""
        config = self._build_run_config(session_id, session_state)
        graph_input: AgentGraphState = {
            "session_id": session_id,
            "user_message": user_message,
            "skip_extraction": skip_extraction,
            "retrieved_cars": retrieved_cars,
            "propose_with_llm": propose_with_llm,
            "voice_mode": self.voice_mode if voice_mode is None else bool(voice_mode),
        }
        if session_state is not None:
            graph_input["session_state"] = session_state

        try:
            out = await self.graph.ainvoke(graph_input, config=config)
            return self._to_agent_result(out, fallback_session=session_state)
        except GraphRecursionError as exc:
            logger.warning(
                f"[{session_id}] Async GraphRecursionError caught, routing to safe degradation: {exc}"
            )
            sess = session_state or SessionState(session_id=session_id)
            return AgentResult(
                response_text=build_safe_degradation_response(sess, reason="recursion_limit_reached"),
                session_state=sess,
                stage_changed=False,
                matched_cars=sess.matched_cars,
            )

    def resume_turn(self, session_id: str, resume_payload: Any) -> AgentResult:
        """Resume an interrupted LangGraph thread via `Command(resume=...)`."""
        config = self._build_run_config(session_id)
        out = self.graph.invoke(Command(resume=resume_payload), config=config)
        return self._to_agent_result(out)

    async def aresume_turn(self, session_id: str, resume_payload: Any) -> AgentResult:
        """Asynchronously resume an interrupted LangGraph thread via `Command(resume=...)`."""
        config = self._build_run_config(session_id)
        out = await self.graph.ainvoke(Command(resume=resume_payload), config=config)
        return self._to_agent_result(out)

    def _sanitize_stream_segment(self, session_id: str, segment: str) -> str:
        return sanitize_stream_segment(self, session_id, segment)

    async def astream_turn(
        self,
        session_id: str,
        user_message: str,
        session_state: Optional[SessionState] = None,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_extraction: bool = False,
        propose_with_llm: bool = False,
        voice_mode: Optional[bool] = None,
    ) -> AsyncGenerator[Tuple[str, Any], None]:
        async for ev in stream_graph_turn(
            self,
            session_id=session_id,
            user_message=user_message,
            session_state=session_state,
            retrieved_cars=retrieved_cars,
            skip_extraction=skip_extraction,
            propose_with_llm=propose_with_llm,
            voice_mode=voice_mode,
        ):
            yield ev

    def commit_spoken_text(
        self,
        session_id: str,
        turn_id: Optional[int] = None,
        spoken_text: str = "",
        interrupted: bool = True,
    ) -> Dict[str, Any]:
        """
        Barge-in writeback protocol: update the last AIMessage in the Checkpointer
        to the exact truncated text the user actually heard, marked with `[interrupted]`.
        """
        try:
            snap = self.get_graph_state(session_id)
        except Exception as exc:
            logger.warning(f"[{session_id}] commit_spoken_text get_graph_state failed: {exc}")
            return {"updated": False, "error": str(exc)}

        values = getattr(snap, "values", None) or {}
        messages = list(values.get("messages") or [])
        last_ai_idx = None
        for idx in range(len(messages) - 1, -1, -1):
            msg = messages[idx]
            if isinstance(msg, AIMessage):
                has_tool_calls = bool(getattr(msg, "tool_calls", None))
                text_content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content or "")
                ).strip()
                if has_tool_calls and not text_content:
                    continue
                last_ai_idx = idx
                break

        if last_ai_idx is None:
            return {"updated": False, "reason": "no_ai_message_found"}

        last_ai = messages[last_ai_idx]
        clean_spoken = (spoken_text or "").strip()
        if interrupted and not clean_spoken.endswith("[interrupted]"):
            new_content = f"{clean_spoken} [interrupted]".strip()
        else:
            new_content = clean_spoken

        updated_kwargs = {
            **dict(getattr(last_ai, "additional_kwargs", None) or {}),
            "interrupted": interrupted,
            "turn_id": turn_id,
            "spoken_text": clean_spoken,
        }
        updated_ai = AIMessage(
            content=new_content,
            id=getattr(last_ai, "id", None),
            additional_kwargs=updated_kwargs,
        )
        update_payload: Dict[str, Any] = {"messages": [updated_ai], "response_text": new_content}
        sess = values.get("session_state")
        interrupted_during_confirmation = False
        if interrupted and isinstance(sess, SessionState) and sess.pending_action:
            from src.agent.events import SlotUpdated

            sess_copy = sess.model_copy(deep=True)
            pa_copy = dict(sess_copy.pending_action or {})
            pa_copy["interrupted_during_confirmation"] = True
            sess_copy.pending_action = pa_copy
            interrupted_during_confirmation = True
            eff_turn = int(turn_id if turn_id is not None else getattr(sess_copy, "turn_count", 0))
            update_payload["session_state"] = sess_copy
            update_payload["events"] = [
                SlotUpdated(
                    turn_id=eff_turn,
                    source="barge_in_commit",
                    field_path="pending_action",
                    value=pa_copy,
                )
            ]

        try:
            self.graph.update_state(
                {"configurable": {"thread_id": session_id}},
                update_payload,
            )
            return {
                "updated": True,
                "session_id": session_id,
                "turn_id": turn_id,
                "content": new_content,
                "interrupted": interrupted,
                "interrupted_during_confirmation": interrupted_during_confirmation,
            }
        except Exception as exc:
            logger.warning(f"[{session_id}] commit_spoken_text update_state failed: {exc}")
            return {"updated": False, "error": str(exc)}

    def get_graph_state(self, session_id: str) -> Any:
        """Return the LangGraph checkpointer StateSnapshot for `session_id`."""
        return self.graph.get_state({"configurable": {"thread_id": session_id}})

    def clear_session(self, session_id: str) -> None:
        """Delete the LangGraph checkpointer thread for `session_id`."""
        if hasattr(self.checkpointer, "delete_thread"):
            try:
                self.checkpointer.delete_thread(session_id)
            except Exception as exc:
                logger.debug(f"[{session_id}] checkpointer delete_thread failed: {exc}")

    def hydrate_history(
        self,
        session_id: str,
        messages: List[Tuple[str, str]],
        session_state: Optional[SessionState] = None,
    ) -> None:
        """Restore persisted conversation messages and state into the LangGraph checkpointer."""
        lc_msgs: List[AnyMessage] = []
        for role, content in messages:
            if role == "user":
                lc_msgs.append(HumanMessage(content=content))
            else:
                lc_msgs.append(AIMessage(content=content))
        values: Dict[str, Any] = {"messages": lc_msgs}
        if session_state is not None:
            values["session_state"] = session_state
        try:
            self.graph.update_state({"configurable": {"thread_id": session_id}}, values)
        except Exception as exc:
            logger.debug(f"[{session_id}] checkpointer hydrate_history failed: {exc}")

    def get_graph_mermaid(self) -> str:
        """Return a Mermaid diagram of the compiled LangGraph StateGraph."""
        return self.graph.get_graph().draw_mermaid()


__all__ = [
    "LangGraphSalesAgent",
    "AgentGraphState",
    "PROMPT_PATCH_WINDOW",
    "MAX_TOOL_ITERATIONS",
    "MAX_CRAG_RETRIES",
    "MAX_AUDIT_RETRIES",
    "_format_messages_as_text",
]
