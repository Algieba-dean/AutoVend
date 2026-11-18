"""
LangGraph-powered Stateful Sales Agent (`src/agent/langgraph_agent.py`).

Implements AutoVend's multi-stage automotive sales agent as a single compiled
`langgraph.graph.StateGraph` with:
- Typed `AgentGraphState` and `add_messages` reducer
- Conditional routing (`guard_and_route` -> `extract_slots` | `arbitrate_stage`;
  `arbitrate_stage` -> `retrieve_vehicles` | `run_plugins_and_subdag`)
- LangChain `with_structured_output(...)` extractors (zero LlamaIndex shims)
- LangChain `ToolNode` + `bind_tools()` tool-calling loop (`generate_reply` <-> `tools`)
- Native `self.graph.astream(..., stream_mode=["messages", "updates"])` streaming
- Unified persistence via `PostgresSaver` / `MemorySaver` checkpointer
"""

import logging
import re
import uuid
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypedDict,
)

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.agent.circuit_breaker import AgentCircuitBreaker
from src.agent.extractors.combined_needs_extractor import extract_combined_needs
from src.agent.extractors.profile_extractor import extract_profile
from src.agent.extractors.reservation_extractor import extract_reservation
from src.agent.langchain_chains import _fallback_response, build_reply_messages
from src.agent.langchain_tools import get_autovend_tools
from src.agent.patches import StatePatch, diff, format_for_prompt, snapshot
from src.agent.plugins.pipeline import AgentPluginPipeline
from src.agent.schemas import AgentResult, SessionState, Stage
from src.agent.stages import (
    ProposalSource,
    TransitionProposal,
    TransitionVerdict,
    advance,
    advance_adaptive,
    handle_constraint_change,
    propose_forward,
    should_advance_to_car_selection,
    should_advance_to_confirmation,
)
from src.agent.subdag import run_stage_subdag
from src.agent.think_scrubber import scrub_think_blocks
from src.agent.topic_manager import TopicManager, UserDialogueIntent
from src.core.checkpointer import create_checkpointer
from src.core.container import ServiceContainer
from src.core.interfaces import RAGQueryRequest
from src.core.tiered_engine import TieredRetrievalEngine
from src.llm.langchain_adapter import ensure_chat_model
from src.privacy.prompt_sanitizer import PromptSanitizer
from src.privacy.security_logger import security_audit_logger

logger = logging.getLogger(__name__)

PROMPT_PATCH_WINDOW = 6
MAX_TOOL_ITERATIONS = 3
_OPEN_THINK_RE = re.compile(r"<(think|thought|reasoning)>", re.IGNORECASE)


class AgentGraphState(TypedDict, total=False):
    """LangGraph state schema for a single AutoVend conversation thread."""

    messages: Annotated[List[AnyMessage], add_messages]
    session_id: str
    user_message: str
    safe_message: str
    skip_extraction: bool
    session_state: SessionState
    retrieved_cars: Optional[List[Dict[str, Any]]]
    stage_changed: bool
    notes: List[str]
    plugin_context: Dict[str, Any]
    conversation_text: str
    propose_with_llm: bool
    response_text: str
    tool_iterations: int


def _format_messages_as_text(messages: List[AnyMessage], max_turns: int = 20) -> str:
    """Render LangChain message history as a plain transcript for prompts/extractors."""
    recent = messages[-max_turns:] if len(messages) > max_turns else messages
    lines: List[str] = []
    for msg in recent:
        if isinstance(msg, ToolMessage):
            continue
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None) and not msg.content:
            continue
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _record_patches(state: SessionState, before: Dict[str, Any], source: str) -> None:
    patches = diff(before, snapshot(state), source=source)
    if not patches:
        state.last_patch = {}
        return
    state.patch_log = [*state.patch_log, *(p.to_dict() for p in patches)]
    state.last_patch = {p.path: p.value for p in patches}
    logger.info(f"[{state.session_id}] {len(patches)} patch(es): {state.last_patch}")


class LangGraphSalesAgent:
    """
    LangGraph + LangChain + LlamaIndex Sales Agent.

    Single compiled `StateGraph` with checkpointer (`PostgresSaver` or `MemorySaver`)
    managing multi-turn automotive sales conversations, conditional retrieval routing,
    and `ToolNode` tool-calling loops.
    """

    def __init__(
        self,
        llm: Any,
        generation_llm: Optional[Any] = None,
        retriever: Optional[Any] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        circuit_breaker: Optional[AgentCircuitBreaker] = None,
        plugin_pipeline: Optional[AgentPluginPipeline] = None,
        use_unified_extraction: bool = True,
    ):
        self.extraction_chat_model: BaseChatModel = ensure_chat_model(llm)
        self.generation_chat_model: BaseChatModel = ensure_chat_model(generation_llm or llm)
        self.tools = get_autovend_tools()
        self.retriever = retriever
        self.checkpointer = checkpointer or create_checkpointer()
        self.circuit_breaker = circuit_breaker or AgentCircuitBreaker()
        self.plugin_pipeline = plugin_pipeline or AgentPluginPipeline()
        self.use_unified_extraction = use_unified_extraction

        self.graph = self._build_graph()

    def _get_generation_runnable(self) -> Any:
        if hasattr(self.generation_chat_model, "bind_tools") and self.tools:
            try:
                return self.generation_chat_model.bind_tools(self.tools)
            except NotImplementedError:
                pass
        return self.generation_chat_model

    # ── Graph Nodes ───────────────────────────────────────────────────

    def _node_guard_and_route(self, state: AgentGraphState) -> Dict[str, Any]:
        session_id = state.get("session_id") or "default"
        user_message = state.get("user_message", "")
        sess = state.get("session_state")
        if sess is None:
            sess = SessionState(session_id=session_id)
        else:
            sess = sess.model_copy(deep=True)

        if not sess.trace_id:
            sess.trace_id = uuid.uuid4().hex[:16]

        sanitization = PromptSanitizer.inspect_and_sanitize(user_message)
        effective_message = user_message
        if sanitization.is_suspicious:
            security_audit_logger.log_event(
                event_type="PROMPT_INJECTION",
                severity="CRITICAL",
                session_id=sess.session_id,
                trace_id=sess.trace_id,
                details={
                    "raw_input": user_message[:200],
                    "detected_patterns": sanitization.detected_patterns,
                },
            )
            effective_message = sanitization.sanitized_text

        existing_msgs = list(state.get("messages") or [])
        new_msg = HumanMessage(content=effective_message)
        conversation_text = _format_messages_as_text([*existing_msgs, new_msg])

        return {
            "messages": [new_msg],
            "safe_message": effective_message,
            "session_state": sess,
            "conversation_text": conversation_text,
            "tool_iterations": 0,
        }

    def _route_after_guard(
        self, state: AgentGraphState
    ) -> Literal["extract_slots", "arbitrate_stage"]:
        if state.get("skip_extraction"):
            return "arbitrate_stage"
        return "extract_slots"

    def _node_extract_slots(self, state: AgentGraphState) -> Dict[str, Any]:
        sess = state["session_state"].model_copy(deep=True)
        conversation_text = state.get("conversation_text", "")
        before = snapshot(sess)

        stage = sess.stage
        ext_model = self.extraction_chat_model

        if self.use_unified_extraction:
            from src.agent.extractors.unified_extractor import extract_unified_slots

            sess, _ = extract_unified_slots(ext_model, conversation_text, sess)
        else:
            if stage in (Stage.WELCOME, Stage.PROFILE_ANALYSIS):
                sess.profile = extract_profile(ext_model, conversation_text, sess.profile)
                sess.needs = extract_combined_needs(
                    ext_model, conversation_text, sess.profile, sess.needs
                )
            elif stage == Stage.NEEDS_ANALYSIS:
                sess.needs = extract_combined_needs(
                    ext_model, conversation_text, sess.profile, sess.needs
                )
            elif stage == Stage.CAR_SELECTION:
                sess.needs = extract_combined_needs(
                    ext_model, conversation_text, sess.profile, sess.needs
                )
                sess.reservation = extract_reservation(ext_model, conversation_text, sess.reservation)
            elif stage in (Stage.RESERVATION_4S, Stage.RESERVATION_CONFIRMATION):
                sess.reservation = extract_reservation(ext_model, conversation_text, sess.reservation)

        from src.agent.reconciliation import reconcile_constraints

        for conflict in reconcile_constraints(sess):
            note = conflict.to_system_note()
            if note not in sess.system_notes:
                sess.system_notes.append(note)

        _record_patches(sess, before, source="extractor")
        return {"session_state": sess, "conversation_text": conversation_text}

    def _node_arbitrate_stage(self, state: AgentGraphState) -> Dict[str, Any]:
        sess = state["session_state"].model_copy(deep=True)
        session_id = sess.session_id
        last_user_msg = state.get("safe_message") or state.get("user_message", "")
        old_stage = sess.stage
        sess.previous_stage = old_stage.value

        topic_res = TopicManager.analyze_user_turn(last_user_msg, old_stage, sess)
        is_topic_hopping = False

        if topic_res.is_interrupt:
            if topic_res.intent in (
                UserDialogueIntent.SIDE_QUESTION,
                UserDialogueIntent.SPEC_COMPARISON,
            ) or (
                topic_res.intent == UserDialogueIntent.MULTI_INTENT
                and topic_res.topic_label
                and topic_res.topic_label != "车辆参数与技术咨询"
                and not any(
                    k in last_user_msg
                    for k in ("改一下", "换成", "预算调整为", "改选", "重新考虑", "重新选车", "重新选")
                )
            ):
                TopicManager.push_goal(sess, old_stage, topic_res.topic_label)
                if not topic_res.is_multi_intent:
                    is_topic_hopping = True
            elif topic_res.intent == UserDialogueIntent.CONSTRAINT_UPDATE or (
                topic_res.intent == UserDialogueIntent.MULTI_INTENT
                and any(
                    k in last_user_msg
                    for k in (
                        "改一下",
                        "换成",
                        "预算调整为",
                        "改选",
                        "重新考虑",
                        "重新选车",
                        "重新选",
                        "不要轿车",
                        "不要SUV",
                        "不要油车",
                        "不要纯电",
                        "先别急着约",
                        "先不约",
                        "先别约",
                        "不急着约",
                    )
                )
            ):
                outcome = handle_constraint_change(sess, reason="topic_manager_constraint_update")
                if outcome and outcome.rolled_back:
                    old_stage = sess.stage

            if topic_res.suggested_directive and topic_res.suggested_directive not in sess.system_notes:
                sess.system_notes.append(topic_res.suggested_directive)
            try:
                car_hint = (
                    sess.matched_cars[0].get("car_model")
                    if sess.matched_cars and isinstance(sess.matched_cars[0], dict)
                    else None
                )
                t0_hit = TieredRetrievalEngine.get_instance().search_tier0(
                    last_user_msg, car_model_hint=car_hint
                )
                if t0_hit is not None and t0_hit.results:
                    fact_note = f"[技术与规格事实依据] {t0_hit.facts_summary}"
                    if fact_note not in sess.system_notes:
                        sess.system_notes.append(fact_note)
            except Exception as te:
                logger.debug(f"Tier 0 lookup failed in arbitrate_stage: {te}")
        else:
            if topic_res.suggested_directive and topic_res.suggested_directive not in sess.system_notes:
                sess.system_notes.append(topic_res.suggested_directive)

        if sess.stage_hold:
            sess.stage_hold = False
            stage_changed = False
            verdict = TransitionVerdict(
                accepted=True,
                stage=old_stage,
                proposal=TransitionProposal(target=old_stage, source=ProposalSource.RULE),
            )
        elif is_topic_hopping:
            stage_changed = False
            verdict = TransitionVerdict(
                accepted=True,
                stage=old_stage,
                proposal=TransitionProposal(
                    target=old_stage,
                    source=ProposalSource.RULE,
                    reason="topic_hopping_side_question",
                ),
            )
        else:
            proposals = []
            forward = propose_forward(sess)
            if forward is not None:
                proposals.append(forward)

            has_multi_slots = (
                topic_res.is_multi_intent
                or len(topic_res.extracted_slots_hint) >= 2
                or (len(sess.last_patch) >= 2 and any("needs" in k for k in sess.last_patch))
                or (
                    sess.stage in (Stage.WELCOME, Stage.PROFILE_ANALYSIS)
                    and bool(sess.needs.explicit.price)
                    and should_advance_to_car_selection(sess.needs)
                )
                or (
                    sess.stage in (Stage.CAR_SELECTION, Stage.RESERVATION_4S)
                    and should_advance_to_confirmation(sess.reservation)
                )
            )
            verdict = advance_adaptive(sess, proposals) if has_multi_slots else advance(sess, proposals)
            sess.stage = verdict.stage
            if verdict.system_note:
                sess.system_notes = [*sess.system_notes, verdict.system_note]
            stage_changed = sess.stage != old_stage

        rej_reason = verdict.rejection if (not verdict.accepted) else None
        trip = self.circuit_breaker.record_turn(
            session_id=session_id,
            current_stage=sess.stage,
            rejection_reason=rej_reason,
            is_topic_hopping=is_topic_hopping,
        )
        if trip:
            sess.system_notes = [*sess.system_notes, trip.intervention_note]

        return {"session_state": sess, "stage_changed": stage_changed}

    def _route_after_arbitrate(
        self, state: AgentGraphState
    ) -> Literal["retrieve_vehicles", "run_plugins_and_subdag"]:
        """Skip vehicle retrieval in non-selection stages unless cars were pre-supplied."""
        if state.get("retrieved_cars"):
            return "retrieve_vehicles"
        sess = state.get("session_state")
        if sess is not None and sess.stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
            return "retrieve_vehicles"
        return "run_plugins_and_subdag"

    def _node_retrieve_vehicles(self, state: AgentGraphState) -> Dict[str, Any]:
        sess = state["session_state"].model_copy(deep=True)
        pre_retrieved = state.get("retrieved_cars")
        if pre_retrieved:
            sess.matched_cars = pre_retrieved
            return {"session_state": sess}

        query = state.get("safe_message") or state.get("user_message", "")

        # Tier 0 fast-path spec lookup (<1-2ms) when user asks about a specific model/spec
        if query:
            try:
                t0 = TieredRetrievalEngine.get_instance().search_tier0(query)
                if t0 is not None and t0.results:
                    fast_cars = []
                    for r in t0.results:
                        meta = dict(r.metadata) if r.metadata else {}
                        car_entry = {
                            **meta,
                            "car_model": r.car_model or meta.get("car_model", ""),
                            "score": getattr(r, "score", 1.0),
                            "metadata": meta,
                            "text_snippet": r.text_snippet or t0.facts_summary or "",
                        }
                        if car_entry["car_model"]:
                            fast_cars.append(car_entry)
                    if fast_cars:
                        sess.matched_cars = fast_cars
                        return {"session_state": sess}
            except Exception as te:
                logger.debug(f"[{sess.session_id}] Tier 0 lookup skipped: {te}")

        if sess.stage not in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
            return {"session_state": sess}

        from src.retrieval.adapters import needs_to_query_text

        explicit_dict = sess.needs.explicit.model_dump(exclude_none=True)
        implicit_dict = sess.needs.implicit.model_dump(exclude_none=True)
        needs_query = needs_to_query_text(sess.needs.explicit, sess.needs.implicit)
        if needs_query and needs_query != "recommend a good vehicle":
            retrieval_query = needs_query
        else:
            retrieval_query = query or needs_query or "recommend a vehicle"

        if self.retriever is not None:
            try:
                from src.retrieval.langchain_retriever import documents_to_car_dicts

                if hasattr(self.retriever, "retrieve_with_slots"):
                    docs = self.retriever.retrieve_with_slots(
                        retrieval_query,
                        explicit_conditions=explicit_dict,
                        implicit_needs=implicit_dict,
                    )
                else:
                    docs = self.retriever.invoke(retrieval_query)
                cars = documents_to_car_dicts(docs, limit=5)
                if cars:
                    try:
                        from src.retrieval.compression import ContextCompressor

                        cars = ContextCompressor.compress_matched_cars(
                            cars,
                            query_text=retrieval_query,
                            active_constraints=sess.needs.explicit.model_dump(),
                        )
                    except Exception:
                        pass
                    sess.matched_cars = cars
                return {"session_state": sess}
            except Exception as exc:
                logger.warning(f"[{sess.session_id}] LangChain retriever failed: {exc}")

        rag_service = ServiceContainer.get_rag_service()
        if rag_service is not None:
            try:
                resp = rag_service.search_vehicles(
                    RAGQueryRequest(
                        query_text=retrieval_query,
                        explicit_conditions=explicit_dict,
                        implicit_needs=implicit_dict,
                        top_k=5,
                    )
                )
                if resp.results:
                    sess.matched_cars = resp.results
            except Exception as exc:
                logger.warning(f"[{sess.session_id}] RAGService retrieval failed: {exc}")

        return {"session_state": sess}

    def _node_run_plugins_and_subdag(self, state: AgentGraphState) -> Dict[str, Any]:
        sess = state["session_state"].model_copy(deep=True)
        last_user_msg = state.get("safe_message") or state.get("user_message", "")
        conversation_text = state.get("conversation_text", "")

        plugin_context: Dict[str, Any] = {
            "user_input": last_user_msg or conversation_text,
            "conversation_text": conversation_text,
            "matched_cars": sess.matched_cars,
        }
        self.plugin_pipeline.run_before_response(sess, plugin_context)
        sess = run_stage_subdag(sess)

        notes = list(sess.system_notes)
        patch_summary = format_for_prompt(
            [StatePatch.from_dict(p) for p in sess.patch_log[-PROMPT_PATCH_WINDOW:]]
        )
        if patch_summary:
            notes.append(patch_summary)

        return {
            "session_state": sess,
            "notes": notes,
            "plugin_context": plugin_context,
        }

    def _build_generation_inputs(self, state: AgentGraphState) -> Tuple[SessionState, List[AnyMessage]]:
        sess = state["session_state"].model_copy(deep=True)
        conversation_text = state.get("conversation_text", "")
        notes = state.get("notes", [])
        all_msgs = list(state.get("messages") or [])

        # Separate dialogue history from any trailing tool-call / ToolMessage loop in this turn
        trailing_tool_msgs: List[AnyMessage] = []
        dialogue_msgs = list(all_msgs)
        while dialogue_msgs and isinstance(dialogue_msgs[-1], (ToolMessage, AIMessage)):
            last = dialogue_msgs[-1]
            if isinstance(last, ToolMessage) or getattr(last, "tool_calls", None):
                trailing_tool_msgs.insert(0, dialogue_msgs.pop())
            else:
                break

        prompt_msgs = build_reply_messages(
            stage=sess.stage,
            conversation_history=conversation_text,
            profile=sess.profile,
            needs=sess.needs,
            matched_cars=sess.matched_cars,
            reservation=sess.reservation,
            system_notes=notes,
            messages=dialogue_msgs,
        )
        prompt_msgs.extend(trailing_tool_msgs)
        return sess, prompt_msgs

    def _finalize_generation_output(
        self, state: AgentGraphState, sess: SessionState, ai_msg: AIMessage
    ) -> Dict[str, Any]:
        tool_calls = getattr(ai_msg, "tool_calls", None) or []
        iters = int(state.get("tool_iterations", 0))
        if tool_calls and iters < MAX_TOOL_ITERATIONS:
            return {
                "messages": [ai_msg],
                "tool_iterations": iters + 1,
            }

        raw_text = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
        cleaned, _ = scrub_think_blocks(raw_text)
        reply = cleaned.strip() or _fallback_response(sess.stage, sess.profile)
        plugin_context = state.get("plugin_context", {})
        reply = self.plugin_pipeline.run_after_response(reply, plugin_context)
        sess.system_notes = []

        return {
            "session_state": sess,
            "response_text": reply,
            "messages": [AIMessage(content=reply)],
        }

    def _node_generate_reply_sync(self, state: AgentGraphState) -> Dict[str, Any]:
        sess, prompt_msgs = self._build_generation_inputs(state)
        try:
            ai_msg = self._get_generation_runnable().invoke(prompt_msgs)
            if not isinstance(ai_msg, AIMessage):
                ai_msg = AIMessage(content=getattr(ai_msg, "content", str(ai_msg)))
        except Exception as exc:
            logger.error(f"LangGraph reply generation failed at stage {sess.stage.value}: {exc}")
            ai_msg = AIMessage(content=_fallback_response(sess.stage, sess.profile))
        return self._finalize_generation_output(state, sess, ai_msg)

    async def _node_generate_reply_async(self, state: AgentGraphState) -> Dict[str, Any]:
        sess, prompt_msgs = self._build_generation_inputs(state)
        try:
            ai_msg = await self._get_generation_runnable().ainvoke(prompt_msgs)
            if not isinstance(ai_msg, AIMessage):
                ai_msg = AIMessage(content=getattr(ai_msg, "content", str(ai_msg)))
        except Exception as exc:
            logger.error(f"LangGraph async reply generation failed at stage {sess.stage.value}: {exc}")
            ai_msg = AIMessage(content=_fallback_response(sess.stage, sess.profile))
        return self._finalize_generation_output(state, sess, ai_msg)

    def _route_after_generate(self, state: AgentGraphState) -> Literal["tools", "__end__"]:
        messages = state.get("messages") or []
        if messages:
            last = messages[-1]
            if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
                if int(state.get("tool_iterations", 0)) <= MAX_TOOL_ITERATIONS:
                    return "tools"
        return "__end__"

    # ── Graph Builder ─────────────────────────────────────────────────

    def _build_graph(self):
        builder = StateGraph(AgentGraphState)
        builder.add_node("guard_and_route", self._node_guard_and_route)
        builder.add_node("extract_slots", self._node_extract_slots)
        builder.add_node("arbitrate_stage", self._node_arbitrate_stage)
        builder.add_node("retrieve_vehicles", self._node_retrieve_vehicles)
        builder.add_node("run_plugins_and_subdag", self._node_run_plugins_and_subdag)
        builder.add_node(
            "generate_reply",
            RunnableLambda(self._node_generate_reply_sync, afunc=self._node_generate_reply_async),
        )
        builder.add_node("tools", ToolNode(self.tools))

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
                "retrieve_vehicles": "retrieve_vehicles",
                "run_plugins_and_subdag": "run_plugins_and_subdag",
            },
        )
        builder.add_edge("retrieve_vehicles", "run_plugins_and_subdag")
        builder.add_edge("run_plugins_and_subdag", "generate_reply")
        builder.add_conditional_edges(
            "generate_reply",
            self._route_after_generate,
            {
                "tools": "tools",
                "__end__": END,
            },
        )
        builder.add_edge("tools", "generate_reply")

        return builder.compile(checkpointer=self.checkpointer)

    # ── Public Execution API ──────────────────────────────────────────

    def invoke_turn(
        self,
        session_id: str,
        user_message: str,
        session_state: Optional[SessionState] = None,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_extraction: bool = False,
        propose_with_llm: bool = False,
    ) -> AgentResult:
        """Execute one full conversation turn synchronously through the LangGraph StateGraph."""
        config = {"configurable": {"thread_id": session_id}}
        graph_input: AgentGraphState = {
            "session_id": session_id,
            "user_message": user_message,
            "skip_extraction": skip_extraction,
            "retrieved_cars": retrieved_cars,
            "propose_with_llm": propose_with_llm,
        }
        if session_state is not None:
            graph_input["session_state"] = session_state

        out = self.graph.invoke(graph_input, config=config)
        final_sess = out["session_state"]
        return AgentResult(
            response_text=out["response_text"],
            session_state=final_sess,
            stage_changed=bool(out.get("stage_changed", False)),
            matched_cars=final_sess.matched_cars,
        )

    async def ainvoke_turn(
        self,
        session_id: str,
        user_message: str,
        session_state: Optional[SessionState] = None,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_extraction: bool = False,
        propose_with_llm: bool = False,
    ) -> AgentResult:
        """Execute one full conversation turn asynchronously through the LangGraph StateGraph."""
        config = {"configurable": {"thread_id": session_id}}
        graph_input: AgentGraphState = {
            "session_id": session_id,
            "user_message": user_message,
            "skip_extraction": skip_extraction,
            "retrieved_cars": retrieved_cars,
            "propose_with_llm": propose_with_llm,
        }
        if session_state is not None:
            graph_input["session_state"] = session_state

        out = await self.graph.ainvoke(graph_input, config=config)
        final_sess = out["session_state"]
        return AgentResult(
            response_text=out["response_text"],
            session_state=final_sess,
            stage_changed=bool(out.get("stage_changed", False)),
            matched_cars=final_sess.matched_cars,
        )

    async def astream_turn(
        self,
        session_id: str,
        user_message: str,
        session_state: Optional[SessionState] = None,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_extraction: bool = False,
        propose_with_llm: bool = False,
    ) -> AsyncGenerator[Tuple[str, Any], None]:
        """
        Stream a turn natively via `self.graph.astream(..., stream_mode=["messages", "updates"])`.

        Emits `("metadata", ...)` after pre-generation nodes, `("delta", token)` for
        each streamed reply token (with `<think>` blocks stripped), and `("done", final_text)`.
        """
        config = {"configurable": {"thread_id": session_id}}
        graph_input: AgentGraphState = {
            "session_id": session_id,
            "user_message": user_message,
            "skip_extraction": skip_extraction,
            "retrieved_cars": retrieved_cars,
            "propose_with_llm": propose_with_llm,
        }
        if session_state is not None:
            graph_input["session_state"] = session_state

        emitted_metadata = False
        emitted_tokens = False
        latest_stage_changed = False
        final_text = ""
        buf = ""
        in_think = False
        think_tag = ""

        async for mode, payload in self.graph.astream(
            graph_input,
            config=config,
            stream_mode=["messages", "updates"],
        ):
            if mode == "updates" and isinstance(payload, dict):
                if "arbitrate_stage" in payload:
                    latest_stage_changed = bool(
                        payload["arbitrate_stage"].get("stage_changed", False)
                    )
                if "run_plugins_and_subdag" in payload and not emitted_metadata:
                    upd = payload["run_plugins_and_subdag"]
                    sess: SessionState = upd["session_state"]
                    emitted_metadata = True
                    yield (
                        "metadata",
                        {
                            "session_state": sess,
                            "stage_changed": latest_stage_changed,
                            "matched_cars": sess.matched_cars,
                        },
                    )
                if "generate_reply" in payload:
                    gen_upd = payload["generate_reply"]
                    if "response_text" in gen_upd:
                        final_text = gen_upd["response_text"]
            elif mode == "messages":
                msg_chunk, meta = payload
                if meta.get("langgraph_node") != "generate_reply":
                    continue
                if getattr(msg_chunk, "tool_call_chunks", None) or getattr(
                    msg_chunk, "tool_calls", None
                ):
                    continue
                token = msg_chunk.content if isinstance(msg_chunk.content, str) else ""
                if not token:
                    continue

                buf += token
                while buf:
                    if in_think:
                        close_re = re.compile(rf"</{re.escape(think_tag)}>", re.IGNORECASE)
                        m_close = close_re.search(buf)
                        if m_close:
                            buf = buf[m_close.end() :].lstrip("\r\n")
                            in_think = False
                            think_tag = ""
                        else:
                            keep = len(think_tag) + 4
                            if len(buf) > keep:
                                buf = buf[-keep:]
                            break
                    else:
                        m_open = _OPEN_THINK_RE.search(buf)
                        if m_open:
                            before = buf[: m_open.start()]
                            if before:
                                emitted_tokens = True
                                yield ("delta", before)
                            in_think = True
                            think_tag = m_open.group(1)
                            buf = buf[m_open.end() :]
                        else:
                            lt_idx = buf.rfind("<")
                            if lt_idx != -1 and (len(buf) - lt_idx) <= 12:
                                safe_part = buf[:lt_idx]
                                if safe_part:
                                    emitted_tokens = True
                                    yield ("delta", safe_part)
                                buf = buf[lt_idx:]
                                break
                            else:
                                emitted_tokens = True
                                yield ("delta", buf)
                                buf = ""
                                break

        if not in_think and buf:
            emitted_tokens = True
            yield ("delta", buf)

        if not emitted_tokens and final_text:
            yield ("delta", final_text)

        yield ("done", final_text)

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
