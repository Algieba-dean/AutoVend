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
from concurrent.futures import ThreadPoolExecutor
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

from src.agent.callbacks import AutoVendOtelCallbackHandler
from src.agent.circuit_breaker import AgentCircuitBreaker
from src.agent.evidence_ledger import VerificationEvidenceLedger
from src.agent.extractors.combined_needs_extractor import extract_combined_needs
from src.agent.extractors.profile_extractor import extract_profile
from src.agent.extractors.reservation_extractor import extract_reservation
from src.agent.hooks import LifecycleHookManager
from src.agent.langchain_chains import _fallback_response, build_reply_messages
from src.agent.langchain_tools import enforce_tool_result_limit, get_autovend_tools
from src.agent.patches import StatePatch, diff, format_for_prompt, snapshot
from src.agent.plugins.pipeline import AgentPluginPipeline
from src.agent.reflection import audit_response_against_evidence
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
from src.agent.topic_manager import TopicManager, UserDialogueIntent
from src.core.agentops import (
    agent_slo_monitor,
    enqueue_agent_dlq,
    get_current_artifact_bundle_version,
    record_compliance_audit,
)
from src.core.checkpointer import create_checkpointer
from src.core.container import ServiceContainer
from src.core.interfaces import RAGQueryRequest
from src.core.long_term_memory import LongTermMemoryStore
from src.core.tiered_engine import TieredRetrievalEngine
from src.core.truth_engine import TruthEngineFacade
from src.llm.cost_ledger import AgentNodeRole, cost_ledger, node_cost_context
from src.llm.langchain_adapter import ensure_chat_model

logger = logging.getLogger(__name__)

PROMPT_PATCH_WINDOW = 6
MAX_TOOL_ITERATIONS = 3
MAX_CRAG_RETRIES = 2
MAX_AUDIT_RETRIES = 1
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
    # P1: CRAG retrieval loop & Evidence Ledger & Anti-hallucination audit
    topic_intent: str
    retrieval_retries: int
    retrieval_query_override: Optional[str]
    retrieval_relaxed_constraints: Optional[Dict[str, Any]]
    retrieval_grade_passed: bool
    retrieval_grade_reason: str
    evidence_anchors: List[Dict[str, Any]]
    audit_retries: int
    audit_passed: bool
    critic_feedback: Optional[str]
    artifact_bundle_version: str


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
        hook_manager: Optional[LifecycleHookManager] = None,
        use_unified_extraction: bool = True,
    ):
        self.extraction_chat_model: BaseChatModel = ensure_chat_model(llm)
        self.generation_chat_model: BaseChatModel = ensure_chat_model(generation_llm or llm)
        self.tools = get_autovend_tools()
        self.retriever = retriever
        self.checkpointer = checkpointer or create_checkpointer()
        self.circuit_breaker = circuit_breaker or AgentCircuitBreaker()
        self.plugin_pipeline = plugin_pipeline or AgentPluginPipeline()
        self.hook_manager = hook_manager or LifecycleHookManager()
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

        # Standardized PreTurn Hook (prompt injection + optional PII masking)
        turn_hook_ctx = self.hook_manager.run_pre_turn(
            session_id=sess.session_id,
            raw_message=user_message,
            trace_id=sess.trace_id,
        )
        effective_message = turn_hook_ctx.safe_message
        bundle_ver = get_current_artifact_bundle_version()
        if turn_hook_ctx.injection_detected:
            record_compliance_audit(
                event_type="PROMPT_SANITIZER_INTERCEPT",
                session_id=sess.session_id,
                trace_id=sess.trace_id,
                checkpoint_id=sess.session_id,
                severity="CRITICAL",
                details={
                    "detected_patterns": turn_hook_ctx.detected_patterns,
                    "artifact_bundle_version": bundle_ver,
                },
            )

        # Cross-session Long-Term Memory recall (by phone_number or session_id)
        user_key = sess.profile.phone_number or sess.session_id
        if user_key:
            recalled = LongTermMemoryStore.get_instance().recall(user_key)
            if recalled is not None:
                if recalled.parking_conditions and not sess.profile.parking_conditions:
                    sess.profile.parking_conditions = recalled.parking_conditions
                if recalled.family_size and not sess.profile.family_size:
                    sess.profile.family_size = recalled.family_size
                if recalled.residence and not sess.profile.residence:
                    sess.profile.residence = recalled.residence
                mem_note = LongTermMemoryStore.format_for_prompt(recalled)
                if mem_note and mem_note not in sess.system_notes:
                    sess.system_notes.append(mem_note)

        existing_msgs = list(state.get("messages") or [])
        new_msg = HumanMessage(content=effective_message)
        conversation_text = _format_messages_as_text([*existing_msgs, new_msg])

        return {
            "messages": [new_msg],
            "safe_message": effective_message,
            "session_state": sess,
            "conversation_text": conversation_text,
            "tool_iterations": 0,
            "retrieval_retries": 0,
            "retrieval_query_override": None,
            "retrieval_relaxed_constraints": None,
            "retrieval_grade_passed": True,
            "retrieval_grade_reason": "",
            "evidence_anchors": [],
            "audit_retries": 0,
            "audit_passed": True,
            "critic_feedback": None,
            "artifact_bundle_version": bundle_ver,
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

        with node_cost_context(sess.session_id, AgentNodeRole.EXTRACTOR):
            try:
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
            except Exception as exc:
                logger.warning(f"[{sess.session_id}] Schema extraction failed, capturing to DLQ: {exc}")
                enqueue_agent_dlq(
                    task_type="extractor",
                    session_id=sess.session_id,
                    checkpoint_id=sess.session_id,
                    trace_id=sess.trace_id,
                    user_message=state.get("safe_message") or state.get("user_message", ""),
                    stage=sess.stage.value,
                    error_message=str(exc),
                    error_category="schema_extraction_failure",
                    context_snapshot={"conversation_tail": conversation_text[-400:]},
                )

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
            enqueue_agent_dlq(
                task_type="circuit_breaker",
                session_id=session_id,
                checkpoint_id=session_id,
                trace_id=sess.trace_id,
                user_message=last_user_msg,
                stage=sess.stage.value,
                error_message=trip.intervention_note,
                error_category="circuit_breaker_trip",
                context_snapshot={"reason": str(getattr(trip, "reason", ""))},
            )
            agent_slo_monitor.record_turn(circuit_breaker_tripped=True)

        return {
            "session_state": sess,
            "stage_changed": stage_changed,
            "topic_intent": topic_res.intent.value,
        }

    def _route_after_arbitrate(
        self, state: AgentGraphState
    ) -> Literal["retrieve_vehicles", "run_plugins_and_subdag"]:
        """Skip vehicle retrieval in non-selection stages unless cars were pre-supplied or comparing models."""
        if state.get("retrieved_cars"):
            return "retrieve_vehicles"
        if state.get("topic_intent") == UserDialogueIntent.SPEC_COMPARISON.value:
            return "retrieve_vehicles"
        sess = state.get("session_state")
        if sess is not None and sess.stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
            return "retrieve_vehicles"
        return "run_plugins_and_subdag"

    # ── Retrieval Helpers (Multi-car Parallel + CRAG) ─────────────────

    @staticmethod
    def _extract_comparison_models(query: str, sess: SessionState) -> List[str]:
        """Extract >= 2 distinct vehicle models for parallel comparison retrieval."""
        if not query:
            return []
        found: List[str] = []
        try:
            known_models = TruthEngineFacade.get_instance().get_known_models()
        except Exception:
            known_models = []

        q_lower = query.lower()
        for model in sorted(known_models, key=len, reverse=True):
            if model.lower() in q_lower and model not in found:
                found.append(model)

        # Also check any matched_cars already in session
        for car in sess.matched_cars or []:
            cm = str(car.get("car_model") or "").strip()
            if cm and cm.lower() in q_lower and cm not in found:
                found.append(cm)

        if len(found) >= 2:
            return found[:4]

        # Heuristic split on comparison connectors ("对比", "vs", "和", "还是", "跟")
        parts = [
            p.strip()
            for p in re.split(r"(?:\bvs\.?\b|对比|还是|以及|和|跟|与)", query, flags=re.IGNORECASE)
            if p and len(p.strip()) >= 2
        ]
        if len(parts) >= 2 and any(k in query for k in ("对比", "vs", "VS", "区别", "哪个好", "选谁")):
            return parts[:3]
        return []

    def _retrieve_single_query(
        self,
        retrieval_query: str,
        explicit_dict: Dict[str, Any],
        implicit_dict: Dict[str, Any],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Execute one retrieval call against `self.retriever` or `ServiceContainer.get_rag_service()`."""
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
                cars = documents_to_car_dicts(docs, limit=top_k)
                if cars:
                    try:
                        from src.retrieval.compression import ContextCompressor

                        cars = ContextCompressor.compress_matched_cars(
                            cars,
                            query_text=retrieval_query,
                            active_constraints=explicit_dict,
                        )
                    except Exception:
                        pass
                return cars
            except Exception as exc:
                logger.warning(f"LangChain retriever failed for '{retrieval_query}': {exc}")

        rag_service = ServiceContainer.get_rag_service()
        if rag_service is not None:
            try:
                resp = rag_service.search_vehicles(
                    RAGQueryRequest(
                        query_text=retrieval_query,
                        explicit_conditions=explicit_dict,
                        implicit_needs=implicit_dict,
                        top_k=top_k,
                    )
                )
                return list(resp.results or [])
            except Exception as exc:
                logger.warning(f"RAGService retrieval failed for '{retrieval_query}': {exc}")
        return []

    def _node_retrieve_vehicles(self, state: AgentGraphState) -> Dict[str, Any]:
        sess = state["session_state"].model_copy(deep=True)
        ledger = VerificationEvidenceLedger()

        pre_retrieved = state.get("retrieved_cars")
        if pre_retrieved:
            enriched = ledger.record_retrieved_vehicles(pre_retrieved, source="pre_retrieved")
            sess.matched_cars = enriched
            return {"session_state": sess, "evidence_anchors": ledger.get_anchors_summary()}

        query = state.get("safe_message") or state.get("user_message", "")
        retries = int(state.get("retrieval_retries", 0))
        override_query = state.get("retrieval_query_override")
        relaxed_explicit = state.get("retrieval_relaxed_constraints")

        # Multi-car comparison parallel retrieval (avoid Top-K domination by a single model)
        is_compare = state.get("topic_intent") == UserDialogueIntent.SPEC_COMPARISON.value
        compare_models = self._extract_comparison_models(query, sess) if (is_compare or query) else []
        if (is_compare or len(compare_models) >= 2) and len(compare_models) >= 2 and retries == 0:
            explicit_dict = sess.needs.explicit.model_dump(exclude_none=True)
            implicit_dict = sess.needs.implicit.model_dump(exclude_none=True)

            def _fetch_model(model_name: str) -> List[Dict[str, Any]]:
                # Try Tier 0 first for sub-ms exact spec hit, then vector/hybrid retriever
                t0_cars: List[Dict[str, Any]] = []
                try:
                    t0 = TieredRetrievalEngine.get_instance().search_tier0(model_name, car_model_hint=model_name)
                    if t0 is not None and t0.results:
                        for r in t0.results[:2]:
                            meta = dict(r.metadata) if r.metadata else {}
                            cm = r.car_model or meta.get("car_model", "")
                            if cm:
                                t0_cars.append({
                                    **meta,
                                    "car_model": cm,
                                    "score": getattr(r, "score", 1.0),
                                    "metadata": meta,
                                    "text_snippet": r.text_snippet or t0.facts_summary or "",
                                })
                except Exception:
                    pass
                rag_cars = self._retrieve_single_query(
                    model_name,
                    {k: v for k, v in explicit_dict.items() if k != "brand"},
                    implicit_dict,
                    top_k=3,
                ) if (self.retriever is not None or ServiceContainer.get_rag_service() is not None) else []
                return t0_cars + rag_cars

            per_model_results: List[List[Dict[str, Any]]] = []
            with ThreadPoolExecutor(max_workers=min(4, len(compare_models))) as pool:
                per_model_results = list(pool.map(_fetch_model, compare_models))

            # Round-robin interleave & deduplicate by car_model
            merged: List[Dict[str, Any]] = []
            seen_models: set[str] = set()
            max_len = max((len(lst) for lst in per_model_results), default=0)
            for idx in range(max_len):
                for lst in per_model_results:
                    if idx < len(lst):
                        car = lst[idx]
                        cm = str(car.get("car_model") or "").strip()
                        if cm and cm not in seen_models:
                            seen_models.add(cm)
                            merged.append(car)
            if merged:
                enriched = ledger.record_retrieved_vehicles(merged[:6], source="parallel_comparison")
                sess.matched_cars = enriched
                return {"session_state": sess, "evidence_anchors": ledger.get_anchors_summary()}

        # Tier 0 fast-path spec lookup (<1-2ms) on initial attempt when user asks about a specific model/spec
        if query and retries == 0:
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
                        enriched = ledger.record_retrieved_vehicles(fast_cars, source="tier0_fastpath")
                        sess.matched_cars = enriched
                        return {"session_state": sess, "evidence_anchors": ledger.get_anchors_summary()}
            except Exception as te:
                logger.debug(f"[{sess.session_id}] Tier 0 lookup skipped: {te}")

        if sess.stage not in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
            return {"session_state": sess}

        from src.retrieval.adapters import needs_to_query_text

        explicit_dict = (
            dict(relaxed_explicit)
            if relaxed_explicit is not None
            else sess.needs.explicit.model_dump(exclude_none=True)
        )
        implicit_dict = sess.needs.implicit.model_dump(exclude_none=True)

        if override_query:
            retrieval_query = override_query
        else:
            needs_query = needs_to_query_text(sess.needs.explicit, sess.needs.implicit)
            if needs_query and needs_query != "recommend a good vehicle":
                retrieval_query = needs_query
            else:
                retrieval_query = query or needs_query or "recommend a vehicle"

        cars = self._retrieve_single_query(retrieval_query, explicit_dict, implicit_dict, top_k=5)
        if cars:
            enriched = ledger.record_retrieved_vehicles(cars, source="hybrid_rag")
            sess.matched_cars = enriched
            return {"session_state": sess, "evidence_anchors": ledger.get_anchors_summary()}
        sess.matched_cars = []

        return {"session_state": sess, "evidence_anchors": ledger.get_anchors_summary()}

    # ── CRAG Grade & Query Rewrite Nodes ──────────────────────────────

    @staticmethod
    def _extract_budget_bounds(sess: SessionState) -> Tuple[Optional[float], Optional[float]]:
        b_min = sess.needs.explicit.budget_min
        b_max = sess.needs.explicit.budget_max
        if b_max is None and sess.needs.explicit.price:
            nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", sess.needs.explicit.price)]
            if len(nums) >= 2:
                b_min = b_min if b_min is not None else min(nums[0], nums[1])
                b_max = max(nums[0], nums[1])
            elif len(nums) == 1:
                b_max = nums[0]
        return b_min, b_max

    @staticmethod
    def _car_matches_powertrain(car: Dict[str, Any], target_power: str) -> bool:
        meta = car.get("metadata") if isinstance(car.get("metadata"), dict) else {}
        car_power = str(
            car.get("powertrain_type") or car.get("power_type") or meta.get("powertrain_type") or ""
        ).lower()
        if not car_power:
            return True  # metadata absent -> do not falsely reject
        t = target_power.lower()
        if any(k in t for k in ("纯电", "bev", "ev")):
            return any(k in car_power for k in ("纯电", "bev", "ev"))
        if any(k in t for k in ("增程", "reev")):
            return any(k in car_power for k in ("增程", "reev"))
        if any(k in t for k in ("插混", "phev", "混动")):
            return any(k in car_power for k in ("插混", "phev", "混动", "dm-i"))
        if any(k in t for k in ("燃油", "汽油", "ice")):
            return any(k in car_power for k in ("燃油", "汽油", "ice"))
        return t in car_power

    def _node_grade_retrieval(self, state: AgentGraphState) -> Dict[str, Any]:
        """CRAG Grader: verify retrieved cars are non-empty and respect hard budget/powertrain/brand constraints."""
        sess = state["session_state"].model_copy(deep=True)
        retries = int(state.get("retrieval_retries", 0))

        with node_cost_context(sess.session_id, AgentNodeRole.GRADER):
            # Pre-retrieved or non-selection stages pass immediately
            if state.get("retrieved_cars"):
                return {"retrieval_grade_passed": True, "retrieval_grade_reason": "pre_retrieved"}
            if sess.stage not in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
                return {"retrieval_grade_passed": True, "retrieval_grade_reason": "non_selection_stage"}

            backend_available = (self.retriever is not None) or (ServiceContainer.get_rag_service() is not None)
            cars = sess.matched_cars or []

            if not cars:
                if not backend_available:
                    return {"retrieval_grade_passed": True, "retrieval_grade_reason": "no_backend_configured"}
                if retries < MAX_CRAG_RETRIES:
                    return {"retrieval_grade_passed": False, "retrieval_grade_reason": "召回结果为空"}
                note = "[CRAG检索提示] 放宽次要条件后仍未命中精确车型，请礼貌引导客户适当放宽预算或车型条件。"
                if note not in sess.system_notes:
                    sess.system_notes.append(note)
                enqueue_agent_dlq(
                    task_type="zero_hit",
                    session_id=sess.session_id,
                    checkpoint_id=sess.session_id,
                    trace_id=sess.trace_id,
                    user_message=state.get("safe_message") or state.get("user_message", ""),
                    stage=sess.stage.value,
                    error_message="CRAG retrieval exhausted with 0 matched vehicles",
                    error_category="rag_zero_hit",
                    context_snapshot={"explicit_needs": sess.needs.explicit.model_dump(exclude_none=True)},
                )
                return {"session_state": sess, "retrieval_grade_passed": True, "retrieval_grade_reason": "exhausted_empty"}

            # Hard constraint checks against matched_cars
            b_min, b_max = self._extract_budget_bounds(sess)
            target_power = (sess.needs.explicit.powertrain_type or "").strip()
            target_brand = (sess.needs.explicit.brand or "").strip()

            reasons: List[str] = []
            if b_max is not None:
                budget_ok = False
                has_any_price = False
                for car in cars:
                    meta = car.get("metadata") if isinstance(car.get("metadata"), dict) else {}
                    p_raw = car.get("price_wan") or car.get("msrp_wan") or car.get("price") or meta.get("price")
                    if p_raw is not None:
                        m = re.search(r"(\d+(?:\.\d+)?)", str(p_raw))
                        if m:
                            has_any_price = True
                            p_val = float(m.group(1))
                            if p_val > 1000:
                                p_val /= 10000.0
                            low_ok = (b_min is None) or (p_val >= b_min * 0.8)
                            high_ok = p_val <= b_max * 1.2
                            if low_ok and high_ok:
                                budget_ok = True
                                break
                if has_any_price and not budget_ok:
                    reasons.append(f"召回车型价格均超出预算约束 ({b_max}万)")

            if target_power and not any(self._car_matches_powertrain(c, target_power) for c in cars):
                reasons.append(f"召回车型动力类型均不符合 '{target_power}'")

            if target_brand and state.get("topic_intent") != UserDialogueIntent.SPEC_COMPARISON.value:
                brand_ok = any(
                    target_brand.lower() in str(c.get("brand") or c.get("car_model") or "").lower()
                    for c in cars
                )
                if not brand_ok:
                    reasons.append(f"召回车型品牌均不符合 '{target_brand}'")

            if reasons and retries < MAX_CRAG_RETRIES and backend_available:
                return {
                    "retrieval_grade_passed": False,
                    "retrieval_grade_reason": "; ".join(reasons),
                }

            if reasons and retries >= MAX_CRAG_RETRIES:
                note = f"[CRAG检索提示] 已尝试放宽次要条件重搜，但仍存在约束偏差（{'; '.join(reasons)}），请如实向客户说明并给出最接近的备选。"
                if note not in sess.system_notes:
                    sess.system_notes.append(note)

            return {
                "session_state": sess,
                "retrieval_grade_passed": True,
                "retrieval_grade_reason": "passed" if not reasons else "exhausted_with_partial_match",
            }

    def _route_after_grade(
        self, state: AgentGraphState
    ) -> Literal["rewrite_query", "run_plugins_and_subdag"]:
        if not state.get("retrieval_grade_passed", True) and int(state.get("retrieval_retries", 0)) < MAX_CRAG_RETRIES:
            return "rewrite_query"
        return "run_plugins_and_subdag"

    def _node_rewrite_query(self, state: AgentGraphState) -> Dict[str, Any]:
        """Relax secondary constraints and rewrite retrieval query for CRAG retry."""
        sess = state["session_state"]
        retries = int(state.get("retrieval_retries", 0)) + 1
        explicit_dict = sess.needs.explicit.model_dump(exclude_none=True)

        # Retry 1: drop secondary attributes (design_style, seat_layout, autonomous_driving_level, brand)
        relaxed = {
            k: v
            for k, v in explicit_dict.items()
            if v and k not in ("design_style", "seat_layout", "autonomous_driving_level", "drive_type")
        }
        if retries == 1:
            relaxed.pop("brand", None)
            parts = [str(relaxed.get(k)) for k in ("price", "powertrain_type", "vehicle_category_bottom") if relaxed.get(k)]
            new_query = " ".join(parts) or state.get("safe_message") or "推荐新能源或家用车型"
        else:
            # Retry 2: further relax powertrain and expand budget by 20%
            relaxed.pop("brand", None)
            relaxed.pop("powertrain_type", None)
            if "budget_max" in relaxed and isinstance(relaxed["budget_max"], (int, float)):
                relaxed["budget_max"] = round(float(relaxed["budget_max"]) * 1.2, 1)
            new_query = (
                f"{relaxed.get('vehicle_category_bottom', '')} {relaxed.get('price', '')}".strip()
                or "高性价比热门车型推荐"
            )

        logger.info(
            f"[{sess.session_id}] CRAG rewrite #{retries} (reason: {state.get('retrieval_grade_reason')}) -> '{new_query}'"
        )
        return {
            "retrieval_retries": retries,
            "retrieval_query_override": new_query,
            "retrieval_relaxed_constraints": relaxed,
        }

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
        post_ctx = self.hook_manager.run_post_response(sess.session_id, raw_text)
        reply = post_ctx.sanitized_response or _fallback_response(sess.stage, sess.profile)
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
        if not cost_ledger.check_budget(sess.session_id):
            logger.warning(f"[{sess.session_id}] CostLedger budget exceeded; degrading generation.")
            ai_msg = AIMessage(content=_fallback_response(sess.stage, sess.profile))
            return self._finalize_generation_output(state, sess, ai_msg)
        with node_cost_context(sess.session_id, AgentNodeRole.GENERATOR):
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
        if not cost_ledger.check_budget(sess.session_id):
            logger.warning(f"[{sess.session_id}] CostLedger budget exceeded; degrading async generation.")
            ai_msg = AIMessage(content=_fallback_response(sess.stage, sess.profile))
            return self._finalize_generation_output(state, sess, ai_msg)
        with node_cost_context(sess.session_id, AgentNodeRole.GENERATOR):
            try:
                ai_msg = await self._get_generation_runnable().ainvoke(prompt_msgs)
                if not isinstance(ai_msg, AIMessage):
                    ai_msg = AIMessage(content=getattr(ai_msg, "content", str(ai_msg)))
            except Exception as exc:
                logger.error(f"LangGraph async reply generation failed at stage {sess.stage.value}: {exc}")
                ai_msg = AIMessage(content=_fallback_response(sess.stage, sess.profile))
        return self._finalize_generation_output(state, sess, ai_msg)

    def _route_after_generate(self, state: AgentGraphState) -> Literal["tools", "audit_hallucination"]:
        messages = state.get("messages") or []
        if messages:
            last = messages[-1]
            if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
                if int(state.get("tool_iterations", 0)) <= MAX_TOOL_ITERATIONS:
                    return "tools"
        return "audit_hallucination"

    def _node_tools_with_contract(self, state: AgentGraphState) -> Dict[str, Any]:
        """Contract-aware ToolNode: runs PreToolHook and enforces `maxResultSizeChars`."""
        sess = state.get("session_state")
        session_id = sess.session_id if sess is not None else (state.get("session_id") or "default")
        messages = list(state.get("messages") or [])
        last_msg = messages[-1] if messages else None
        tool_calls = getattr(last_msg, "tool_calls", None) or []

        blocked_msgs: List[ToolMessage] = []
        allowed_calls = []
        for tc in tool_calls:
            t_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
            t_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            t_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
            hook_ctx = self.hook_manager.run_pre_tool(session_id, t_name, t_args)
            if not hook_ctx.approved:
                blocked_msgs.append(
                    ToolMessage(
                        content=hook_ctx.rejection_reason,
                        tool_call_id=t_id,
                        name=t_name,
                    )
                )
            else:
                allowed_calls.append(tc)

        if blocked_msgs and not allowed_calls:
            return {"messages": blocked_msgs}

        call_args_by_id: Dict[str, Any] = {}
        for tc in allowed_calls:
            tc_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
            tc_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            if tc_id:
                call_args_by_id[tc_id] = tc_args

        invoke_state = state
        if blocked_msgs and last_msg is not None and isinstance(last_msg, AIMessage):
            filtered_ai = last_msg.model_copy(update={"tool_calls": allowed_calls})
            invoke_state = {**state, "messages": [*messages[:-1], filtered_ai]}

        base_tool_node = ToolNode(self.tools)
        try:
            out = base_tool_node.invoke(invoke_state)
        except Exception as exc:
            enqueue_agent_dlq(
                task_type="tool_execution",
                session_id=session_id,
                checkpoint_id=session_id,
                trace_id=sess.trace_id if sess else "",
                error_message=str(exc),
                error_category="tool_exception",
                context_snapshot={"tool_calls": [str(tc)[:200] for tc in tool_calls]},
            )
            raise
        out_msgs = list(out.get("messages") or [])
        bounded_msgs: List[AnyMessage] = []
        audit_tools = {"calculate_drive_away_price", "submit_test_drive_reservation", "validate_test_drive_slot"}
        for msg in out_msgs:
            if isinstance(msg, ToolMessage):
                t_name = getattr(msg, "name", None) or ""
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                bounded_content = enforce_tool_result_limit(t_name, content)
                if t_name in audit_tools:
                    record_compliance_audit(
                        event_type="TOOL_COMPLIANCE_AUDIT",
                        session_id=session_id,
                        trace_id=sess.trace_id if sess else "",
                        checkpoint_id=session_id,
                        details={
                            "tool_name": t_name,
                            "input_args": call_args_by_id.get(msg.tool_call_id, {}),
                            "output_preview": bounded_content[:300],
                        },
                    )
                bounded_msgs.append(
                    ToolMessage(
                        content=bounded_content,
                        tool_call_id=msg.tool_call_id,
                        name=getattr(msg, "name", None),
                    )
                )
            else:
                bounded_msgs.append(msg)
        return {"messages": [*blocked_msgs, *bounded_msgs]}

    def _node_audit_hallucination(self, state: AgentGraphState) -> Dict[str, Any]:
        """
        Anti-hallucination audit node (reusing `reflection.py` + `evidence_ledger.py`):
        Verifies price, range, and compliance consistency against retrieved evidence.
        Triggers up to 1 Critic-guided rewrite; degrades safely if retries exhausted.
        """
        sess = state["session_state"].model_copy(deep=True)
        reply = state.get("response_text", "")
        retries = int(state.get("audit_retries", 0))
        anchors = state.get("evidence_anchors") or []

        with node_cost_context(sess.session_id, AgentNodeRole.AUDITOR):
            report = audit_response_against_evidence(
                reply,
                matched_cars=sess.matched_cars,
                evidence_anchors=anchors,
            )

        if anchors:
            record_compliance_audit(
                event_type="EVIDENCE_LEDGER_SNAPSHOT",
                session_id=sess.session_id,
                trace_id=sess.trace_id,
                checkpoint_id=sess.session_id,
                details={"anchors": anchors[:10]},
            )

        is_zero_hit = sess.stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION) and not sess.matched_cars
        crag_rewritten = int(state.get("retrieval_retries", 0)) > 0

        if report.is_clean:
            agent_slo_monitor.record_turn(
                crag_rewritten=crag_rewritten,
                auditor_rejected=False,
                zero_hit=is_zero_hit,
            )
            return {"audit_passed": True, "critic_feedback": None}

        critic_msg = "; ".join(report.warnings)
        enqueue_agent_dlq(
            task_type="auditor_rejection",
            session_id=sess.session_id,
            checkpoint_id=sess.session_id,
            trace_id=sess.trace_id,
            user_message=state.get("safe_message") or state.get("user_message", ""),
            stage=sess.stage.value,
            error_message=critic_msg,
            error_category="hallucination_or_compliance_violation",
            context_snapshot={"draft_reply": reply[:400], "anchors": anchors[:5]},
        )

        if retries < MAX_AUDIT_RETRIES and report.hallucination_detected:
            logger.warning(f"[{sess.session_id}] Audit flagged hallucination (retry #{retries + 1}): {critic_msg}")
            critic_note = f"[反幻觉审计 Critic 意见] 上一版草稿存在事实/参数偏差：{critic_msg}。请严格依据匹配车型与证据账本重写回复。"
            notes = list(state.get("notes") or [])
            if critic_note not in notes:
                notes.append(critic_note)
            return {
                "audit_passed": False,
                "audit_retries": retries + 1,
                "critic_feedback": critic_msg,
                "notes": notes,
            }

        # Retries exhausted or non-hallucination compliance sanitization -> safe degradation
        agent_slo_monitor.record_turn(
            crag_rewritten=crag_rewritten,
            auditor_rejected=True,
            zero_hit=is_zero_hit,
        )
        safe_reply = report.sanitized_text.strip() or _fallback_response(sess.stage, sess.profile)
        return {
            "audit_passed": True,
            "response_text": safe_reply,
            "critic_feedback": critic_msg,
        }

    def _route_after_audit(self, state: AgentGraphState) -> Literal["generate_reply", "__end__"]:
        if not state.get("audit_passed", True):
            return "generate_reply"
        return "__end__"

    # ── Graph Builder ─────────────────────────────────────────────────

    def _build_graph(self):
        builder = StateGraph(AgentGraphState)
        builder.add_node("guard_and_route", self._node_guard_and_route)
        builder.add_node("extract_slots", self._node_extract_slots)
        builder.add_node("arbitrate_stage", self._node_arbitrate_stage)
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
        builder.add_edge("retrieve_vehicles", "grade_retrieval")
        builder.add_conditional_edges(
            "grade_retrieval",
            self._route_after_grade,
            {
                "rewrite_query": "rewrite_query",
                "run_plugins_and_subdag": "run_plugins_and_subdag",
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
            },
        )
        builder.add_edge("tools", "generate_reply")
        builder.add_conditional_edges(
            "audit_hallucination",
            self._route_after_audit,
            {
                "generate_reply": "generate_reply",
                "__end__": END,
            },
        )

        return builder.compile(checkpointer=self.checkpointer)

    # ── Public Execution API ──────────────────────────────────────────

    def _build_run_config(
        self, session_id: str, session_state: Optional[SessionState] = None
    ) -> Dict[str, Any]:
        trace_id = (session_state.trace_id if session_state and session_state.trace_id else "") or uuid.uuid4().hex[:16]
        bundle_ver = get_current_artifact_bundle_version()
        cb = AutoVendOtelCallbackHandler(
            session_id=session_id,
            trace_id=trace_id,
            artifact_bundle_version=bundle_ver,
        )
        return {
            "configurable": {"thread_id": session_id},
            "metadata": {
                "artifact_bundle_version": bundle_ver,
                "trace_id": trace_id,
            },
            "callbacks": [cb],
        }

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
        config = self._build_run_config(session_id, session_state)
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
        config = self._build_run_config(session_id, session_state)
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
        config = self._build_run_config(session_id, session_state)
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
                if "audit_hallucination" in payload:
                    audit_upd = payload["audit_hallucination"]
                    if "response_text" in audit_upd:
                        final_text = audit_upd["response_text"]
                    if not audit_upd.get("audit_passed", True):
                        buf = ""
                        in_think = False
                        think_tag = ""
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
