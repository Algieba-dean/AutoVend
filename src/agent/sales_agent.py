"""
SalesAgent — the single entry point for the Agent package.

Processes one conversation turn:
    AgentResult = SalesAgent.process(AgentInput)

Has NO backend dependencies (no FastAPI, no storage, no ChromaDB).
Vehicle retrieval results are passed IN via AgentInput.retrieved_cars.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from llama_index.core.llms import LLM, ChatMessage, MessageRole

from src.agent.circuit_breaker import AgentCircuitBreaker, default_circuit_breaker
from src.agent.extractors.combined_needs_extractor import extract_combined_needs
from src.agent.extractors.profile_extractor import extract_profile
from src.agent.extractors.reservation_extractor import extract_reservation
from src.agent.memory import ChatMemoryManager
from src.agent.patches import StatePatch, diff, format_for_prompt, snapshot
from src.agent.plugins.pipeline import AgentPluginPipeline
from src.agent.reconciliation import reconcile_constraints
from src.agent.reflection import reflect_and_guard
from src.agent.response_generator import (
    _build_stage_prompt,
    generate_response,
    generate_response_stream,
)
from src.agent.schemas import (
    AgentInput,
    AgentResult,
    SessionState,
    Stage,
)
from src.agent.stages import (
    ProposalSource,
    TransitionProposal,
    TransitionVerdict,
    advance,
    advance_adaptive,
    propose_forward,
    should_advance_to_car_selection,
    should_advance_to_confirmation,
)
from src.agent.subdag import run_stage_subdag
from src.agent.tool_planner import plan_tools
from src.agent.tools import ToolResult, dispatch_all
from src.agent.topic_manager import TopicManager, UserDialogueIntent
from src.agent.transition_proposer import propose_by_llm
from src.core.tiered_engine import TieredRetrievalEngine
from src.privacy.prompt_sanitizer import PromptSanitizer
from src.privacy.security_logger import security_audit_logger

logger = logging.getLogger(__name__)

#: How many recent patches ride along in the generation prompt. Enough to carry
#: "what just changed" without re-serialising the whole state every turn.
PROMPT_PATCH_WINDOW = 6


@dataclass
class ToolOutcome:
    """Result of running a batch of tool calls."""

    state: SessionState
    results: List[ToolResult]
    #: Intents the agent cannot fulfil itself — retrieval, stage changes.
    requests: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)


def _record_patches(state: SessionState, before: Dict[str, Any], source: str) -> None:
    """Diff against `before`, append to the patch log, and set `last_patch`."""
    patches = diff(before, snapshot(state), source=source)
    if not patches:
        state.last_patch = {}
        return
    state.patch_log = [*state.patch_log, *(p.to_dict() for p in patches)]
    state.last_patch = {p.path: p.value for p in patches}
    logger.info(f"[{state.session_id}] {len(patches)} patch(es): {state.last_patch}")


class SalesAgent:
    """
    Pure AI conversation agent for automotive sales.

    Stateless per-call: all session state is passed in and returned out.
    Memory buffers are managed internally per session_id for token-limited history.
    """

    def __init__(
        self,
        llm: LLM,
        generation_llm: Optional[LLM] = None,
        enable_tool_planning: bool = False,
        circuit_breaker: Optional[AgentCircuitBreaker] = None,
        plugin_pipeline: Optional[AgentPluginPipeline] = None,
        use_unified_extraction: bool = False,
    ):
        """
        Args:
            llm: LLM used for extraction — filling Pydantic schemas from the
                transcript. Called on every turn with short, constrained
                prompts.
            generation_llm: LLM used to write the customer-facing reply. Defaults
                to `llm`.
            enable_tool_planning: Whether to enable separate tool planning pass.
            circuit_breaker: Anti-loop circuit breaker.
            plugin_pipeline: Middleware plugin pipeline.
            use_unified_extraction: Whether to fold multi-intent extractions into
                a single unified tool/schema call (Battle 3).

        Two slots rather than one because the two jobs have different
        requirements: extraction is high-frequency and schema-bounded, while
        generation is open-ended and is what the customer actually reads.
        Whoever constructs the agent decides whether they are the same model —
        the agent itself holds no opinion, and deliberately knows nothing about
        routing (see tests/test_agent_isolation.py).
        """
        self.llm = llm
        self.generation_llm = generation_llm or llm
        self.enable_tool_planning = enable_tool_planning
        self.circuit_breaker = circuit_breaker or AgentCircuitBreaker()
        self.plugin_pipeline = plugin_pipeline or AgentPluginPipeline()
        self.use_unified_extraction = use_unified_extraction
        self.memory = ChatMemoryManager()

    def remember(self, state: SessionState, user_message: str) -> SessionState:
        """
        Record the user's message without running any extractor.

        For turns a caller has already determined carry no extractable content —
        an acknowledgement, a deferral, small talk. The message still belongs in
        the transcript the response generator reads; it just has nothing for the
        extractors to find, and running them anyway costs a model round trip to
        confirm that.

        The agent does not decide which turns qualify. That judgement lives with
        the caller (see the semantic router), keeping this package free of any
        classification machinery.
        """
        updated = state.model_copy(deep=True)
        self.memory.add_user_message(updated.session_id, user_message)
        return updated

    def observe(
        self,
        state: SessionState,
        user_message: str,
        use_tools: Optional[bool] = None,
    ) -> SessionState:
        """
        Record the user's message and extract what it reveals — no generation.
        """
        import uuid

        updated = state.model_copy(deep=True)
        if not updated.trace_id:
            updated.trace_id = uuid.uuid4().hex[:16]

        # Inspect user_message for Prompt Injection
        sanitization = PromptSanitizer.inspect_and_sanitize(user_message)
        effective_message = user_message
        if sanitization.is_suspicious:
            security_audit_logger.log_event(
                event_type="PROMPT_INJECTION",
                severity="CRITICAL",
                session_id=updated.session_id,
                trace_id=updated.trace_id,
                details={
                    "raw_input": user_message[:200],
                    "detected_patterns": sanitization.detected_patterns,
                },
            )
            effective_message = sanitization.sanitized_text

        self.memory.add_user_message(updated.session_id, effective_message)
        conversation_text = self.memory.get_history_as_text(updated.session_id)

        before = snapshot(updated)
        updated = self._extract_information(
            updated, conversation_text, latest_user_message=effective_message
        )
        _record_patches(updated, before, source="extractor")

        should_use_tools = self.enable_tool_planning if use_tools is None else use_tools
        if should_use_tools:
            calls = plan_tools(self.llm, updated, conversation_text)
            if calls:
                outcome = self.use_tools(updated, calls)
                updated = outcome.state
                updated.pending_requests = outcome.requests

        return updated

    def use_tools(
        self, state: SessionState, calls: List[Dict[str, Any]], atomic: bool = False
    ) -> ToolOutcome:
        """
        Run a batch of tool calls against the state.

        The dispatcher refuses tools outside the current stage's candidate set,
        so a booking cannot be recorded while the conversation is still learning
        who the customer is. Returns the results plus any requests the caller
        must act on — retrieval and stage changes are expressed as intents here
        and carried out by whoever owns those (see `stages.arbitrate`).
        """
        updated = state.model_copy(deep=True)
        before = snapshot(updated)
        results = dispatch_all(updated, calls, atomic=atomic)
        _record_patches(updated, before, source="tool")

        for result in results:
            if not result.ok:
                logger.info(f"[{updated.session_id}] tool refused: {result.message}")

        return ToolOutcome(
            state=updated,
            results=results,
            requests=[r.request for r in results if r.ok and r.request],
        )

    def _prepare_turn_context(
        self,
        state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        propose_with_llm: bool = False,
    ) -> tuple[SessionState, str, bool, List[str], Dict[str, Any]]:
        """
        Shared pre-response pipeline for both synchronous `respond` and streaming `respond_stream`:
        1. Topic hopping & interruptibility analysis + Tier-0 fast spec grounding
        2. Stage FSM arbitration (linear, adaptive multi-hop, or rollback hold)
        3. Anti-loop circuit breaker recording
        4. Pre-response middleware plugin pipeline (Reconciliation, Battlecards, Terminology, Truth)
        5. Stage Sub-DAG execution & prompt patch summary assembly
        """
        updated = state.model_copy(deep=True)
        session_id = updated.session_id
        conversation_text = self.memory.get_history_as_text(session_id)

        if retrieved_cars:
            updated.matched_cars = retrieved_cars

        old_stage = updated.stage
        updated.previous_stage = old_stage.value

        history = self.memory.get_history(session_id)
        last_user_msg = next(
            (msg.content for msg in reversed(history) if msg.role == MessageRole.USER), ""
        )

        # Dynamic Intent Interruptibility & Topic Hopping Analysis
        topic_res = TopicManager.analyze_user_turn(last_user_msg, old_stage, updated)
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
                TopicManager.push_goal(updated, old_stage, topic_res.topic_label)
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
                from src.agent.stages import handle_constraint_change

                outcome = handle_constraint_change(updated, reason="topic_manager_constraint_update")
                if outcome and outcome.rolled_back:
                    old_stage = updated.stage

            if (
                topic_res.suggested_directive
                and topic_res.suggested_directive not in updated.system_notes
            ):
                updated.system_notes.append(topic_res.suggested_directive)
            try:
                car_hint = (
                    updated.matched_cars[0].get("car_model")
                    if updated.matched_cars and isinstance(updated.matched_cars[0], dict)
                    else None
                )
                t0_hit = TieredRetrievalEngine.get_instance().search_tier0(
                    last_user_msg, car_model_hint=car_hint
                )
                if t0_hit is not None and t0_hit.results:
                    fact_note = f"[技术与规格事实依据] {t0_hit.facts_summary}"
                    if fact_note not in updated.system_notes:
                        updated.system_notes.append(fact_note)
            except Exception as te:
                logger.debug(f"Tier 0 lookup failed in _prepare_turn_context: {te}")
        else:
            if (
                topic_res.suggested_directive
                and topic_res.suggested_directive not in updated.system_notes
            ):
                updated.system_notes.append(topic_res.suggested_directive)

        if updated.stage_hold:
            logger.info(f"[{session_id}] Stage held at {old_stage.value}: rollback in progress")
            updated.stage_hold = False
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
            for request in updated.pending_requests:
                if request.get("type") != "transition":
                    continue
                try:
                    target = Stage(request["stage"])
                except (KeyError, ValueError):
                    continue
                proposals.append(
                    TransitionProposal(
                        target=target,
                        source=ProposalSource.LLM,
                        reason=str(request.get("reason", "")),
                    )
                )
            updated.pending_requests = []
            if propose_with_llm:
                llm_proposal = propose_by_llm(self.llm, updated, conversation_text)
                if llm_proposal is not None:
                    proposals.append(llm_proposal)
            forward = propose_forward(updated)
            if forward is not None:
                proposals.append(forward)

            has_multi_slots = (
                topic_res.is_multi_intent
                or len(topic_res.extracted_slots_hint) >= 2
                or (len(updated.last_patch) >= 2 and any("needs" in k for k in updated.last_patch))
                or (
                    updated.stage in (Stage.WELCOME, Stage.PROFILE_ANALYSIS)
                    and bool(updated.needs.explicit.price)
                    and should_advance_to_car_selection(updated.needs)
                )
                or (
                    updated.stage in (Stage.CAR_SELECTION, Stage.RESERVATION_4S)
                    and should_advance_to_confirmation(updated.reservation)
                )
            )
            if has_multi_slots:
                verdict = advance_adaptive(updated, proposals)
            else:
                verdict = advance(updated, proposals)
            updated.stage = verdict.stage

            if verdict.system_note:
                updated.system_notes = [*updated.system_notes, verdict.system_note]

            stage_changed = updated.stage != old_stage
            if stage_changed:
                logger.info(
                    f"[{session_id}] Stage transition: {old_stage.value} → {updated.stage.value} "
                    f"(proposed by {verdict.proposal.source.value})"
                )
            elif verdict.rejection:
                logger.info(f"[{session_id}] Stage held at {old_stage.value}: {verdict.rejection}")

        # Check Anti-Loop Circuit Breaker with Topic Hopping Awareness
        rej_reason = verdict.rejection if (not verdict.accepted) else None
        trip = self.circuit_breaker.record_turn(
            session_id=session_id,
            current_stage=updated.stage,
            rejection_reason=rej_reason,
            is_topic_hopping=is_topic_hopping,
        )
        if trip:
            updated.system_notes = [*updated.system_notes, trip.intervention_note]

        # Run AgentPluginPipeline (ConstraintReconciler, Battlecards, Terminology, TruthDebiaser)
        plugin_context: Dict[str, Any] = {
            "user_input": last_user_msg or conversation_text,
            "conversation_text": conversation_text,
            "matched_cars": updated.matched_cars,
        }
        self.plugin_pipeline.run_before_response(updated, plugin_context)

        # Execute Sub-DAG workflow for current stage
        updated = run_stage_subdag(updated)

        # Assemble notes including recent state patch summary
        notes = list(updated.system_notes)
        patch_summary = format_for_prompt(
            [StatePatch.from_dict(p) for p in updated.patch_log[-PROMPT_PATCH_WINDOW:]]
        )
        if patch_summary:
            notes.append(patch_summary)

        return updated, conversation_text, stage_changed, notes, plugin_context

    def respond(
        self,
        state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        propose_with_llm: bool = False,
    ) -> AgentResult:
        """
        Arbitrate the stage machine and generate the reply for an observed turn.

        Expects `state` to already carry this turn's extractions — i.e. the
        output of `observe`.
        """
        updated, conversation_text, stage_changed, notes, plugin_context = (
            self._prepare_turn_context(
                state=state,
                retrieved_cars=retrieved_cars,
                propose_with_llm=propose_with_llm,
            )
        )
        session_id = updated.session_id

        response_text = generate_response(
            self.generation_llm,
            updated.stage,
            conversation_text,
            updated.profile,
            updated.needs,
            updated.matched_cars,
            updated.reservation,
            system_notes=notes,
        )

        # Run post-response plugins (Reflection & Compliance Guard)
        response_text = self.plugin_pipeline.run_after_response(response_text, plugin_context)

        # Notes are per-turn instructions.
        updated.system_notes = []

        self.memory.add_assistant_message(session_id, response_text)

        return AgentResult(
            session_state=updated,
            response_text=response_text,
            stage_changed=stage_changed,
        )

    def _build_chat_messages(
        self,
        state: SessionState,
        conversation_text: str,
        notes: List[str],
    ) -> List[ChatMessage]:
        """Build ChatML messages for the generation model preserving role isolation."""
        prompt = _build_stage_prompt(
            stage=state.stage,
            conversation_history=conversation_text,
            profile=state.profile,
            needs=state.needs,
            matched_cars=state.matched_cars,
            reservation=state.reservation,
            system_notes=notes,
        )
        return [ChatMessage(role=MessageRole.USER, content=prompt)]

    async def _prepare_turn_context_async(
        self,
        state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        propose_with_llm: bool = False,
    ) -> tuple[SessionState, str, bool, List[str], Dict[str, Any]]:
        """Pure asynchronous pre-processing without blocking thread pool."""
        return self._prepare_turn_context(
            state=state,
            retrieved_cars=retrieved_cars,
            propose_with_llm=propose_with_llm,
        )

    async def _stream_generation_llm(self, messages: List[ChatMessage], prompt: str):
        """
        Natively stream generation tokens using async generator.
        Supports astream_chat, astream_complete, and unit-test mock fallbacks.
        """
        # 1. Native astream_chat
        if hasattr(self.generation_llm, "astream_chat"):
            try:
                res = self.generation_llm.astream_chat(messages)
                if (
                    hasattr(res, "__anext__") or hasattr(res, "__aiter__")
                ) and res.__class__.__name__ not in ("MagicMock", "AsyncMock"):
                    async for chunk in res:
                        yield chunk
                    return
            except Exception as e:
                logger.debug(f"astream_chat failed or unsupported: {e}")

        # 2. Native astream_complete
        if hasattr(self.generation_llm, "astream_complete"):
            try:
                res = self.generation_llm.astream_complete(prompt)
                if (
                    hasattr(res, "__anext__") or hasattr(res, "__aiter__")
                ) and res.__class__.__name__ not in ("MagicMock", "AsyncMock"):
                    async for chunk in res:
                        yield chunk
                    return
            except Exception as e:
                logger.debug(f"astream_complete failed or unsupported: {e}")

        # 3. Synchronous stream_complete fallback
        if hasattr(self.generation_llm, "stream_complete"):
            try:
                res = self.generation_llm.stream_complete(prompt)
                if hasattr(res, "__iter__") and not isinstance(res, (str, bytes, dict)):
                    for chunk in res:
                        yield chunk
                    return
            except Exception:
                pass

        # 4. Synchronous complete fallback (e.g. for mock LLMs in unit tests)
        if hasattr(self.generation_llm, "complete"):
            res = self.generation_llm.complete(prompt)
            text = getattr(res, "text", str(res))
            yield text

    async def respond_stream(
        self,
        state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        propose_with_llm: bool = False,
    ) -> AsyncGenerator[Tuple[str, Any], None]:
        """
        Pure asynchronous streaming response generator (Battle 1).
        Runs entirely in the event loop with zero thread-pool overhead and
        supports cancellation propagation when the client disconnects.

        Yields tuples:
        - ("metadata", {"session_state": updated, "stage_changed": stage_changed})
        - ("delta", token_chunk)
        - ("done", full_response_text)
        """
        # 1. 预处理阶段（纯异步，无阻塞）
        updated, conversation_text, stage_changed, notes, plugin_context = (
            await self._prepare_turn_context_async(
                state, retrieved_cars, propose_with_llm=propose_with_llm
            )
        )
        session_id = updated.session_id

        # 立即下发元数据帧，前端直接驱动 UI 状态机
        yield ("metadata", {"session_state": updated, "stage_changed": stage_changed})

        # 2. 原生异步调用底层模型流
        messages = self._build_chat_messages(updated, conversation_text, notes)
        prompt = messages[0].content if messages else ""

        full_response: List[str] = []
        stream_buffer = ""
        sentence_delims = ("。", "！", "？", "；", "\n")

        try:
            # 真正的原生异步流，无系统线程参与
            async for chunk in self._stream_generation_llm(messages, prompt):
                delta = getattr(chunk, "delta", None)
                if delta is None and hasattr(chunk, "message") and chunk.message:
                    delta = chunk.message.content
                elif delta is None and isinstance(chunk, str):
                    delta = chunk
                elif delta is None and hasattr(chunk, "text"):
                    delta = chunk.text
                delta = delta or ""
                if not delta:
                    continue

                full_response.append(delta)
                stream_buffer += delta

                last_delim = max(stream_buffer.rfind(d) for d in sentence_delims)
                if last_delim != -1:
                    to_guard = stream_buffer[: last_delim + 1]
                    stream_buffer = stream_buffer[last_delim + 1 :]
                    guarded_chunk, _ = reflect_and_guard(to_guard, updated.matched_cars)
                    yield ("delta", guarded_chunk)
                elif len(stream_buffer) >= 48:
                    guarded_chunk, _ = reflect_and_guard(stream_buffer, updated.matched_cars)
                    stream_buffer = ""
                    yield ("delta", guarded_chunk)

            if stream_buffer:
                guarded_chunk, _ = reflect_and_guard(stream_buffer, updated.matched_cars)
                yield ("delta", guarded_chunk)

        except asyncio.CancelledError:
            logger.info(f"[{session_id}] Client aborted request, stopping generation.")
            raise  # 务必向上 re-raise，让上层清理资源

        # 3. 后置处理与持久化落盘
        complete_text = "".join(full_response)
        complete_text = self.plugin_pipeline.run_after_response(
            complete_text, plugin_context
        )

        updated.system_notes = []
        await self.memory.aadd_assistant_message(session_id, complete_text)
        yield ("done", complete_text)

    def process(self, agent_input: AgentInput) -> AgentResult:
        """
        Process one conversation turn: observe, then respond.

        Convenience wrapper for callers that retrieve up front (or not at all).
        Callers that want retrieval to see this turn's needs should drive
        `observe` -> retrieve -> `respond` themselves.

        Args:
            agent_input: Contains session_state, user_message, retrieved_cars.

        Returns:
            AgentResult with updated session_state, response_text, stage_changed.
        """
        state = self.observe(agent_input.session_state, agent_input.user_message)
        return self.respond(state, agent_input.retrieved_cars)

    def clear_session(self, session_id: str) -> None:
        """Clear memory and circuit breaker state for a session."""
        self.memory.clear_session(session_id)
        self.circuit_breaker.reset_session(session_id)
        default_circuit_breaker.reset_session(session_id)

    def get_history_text(self, session_id: str) -> str:
        """Get formatted conversation history for a session."""
        return self.memory.get_history_as_text(session_id)

    def _extract_information(
        self,
        state: SessionState,
        conversation_text: str,
        latest_user_message: str = "",
    ) -> SessionState:
        """
        Run extractors relevant to the current stage or detected user multi-intent
        in the latest user turn (instead of re-scanning the entire conversation history).
        """
        import re

        stage = state.stage
        signal_text = latest_user_message if latest_user_message else conversation_text

        # Multi-Intent signal detection on the current turn:
        has_profile_signal = stage in (Stage.WELCOME, Stage.PROFILE_ANALYSIS) or bool(
            re.search(
                r"我叫|我是|姓|先生|女士|本人|自己开|家人|老婆|老公|太太|爱人|小孩|孩子|老人|口之|代步|通勤|岁|居住|住在|工程师|<CN_PERSON",
                signal_text,
            )
        )

        has_needs_signal = stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION) or bool(
            re.search(
                r"\d+万|预算|价格|纯电|插混|增程|油车|混动|ev|suv|轿车|mpv|猎装|轿跑|续航|加速|马力|空间|座椅|\d座",
                signal_text,
                re.IGNORECASE,
            )
        )

        has_reservation_signal = (
            stage in (Stage.RESERVATION_4S, Stage.RESERVATION_CONFIRMATION)
            or bool(
                re.search(
                    r"试驾|预约|门店|4s店|体验店|体验中心|明天|后天|周末|周[一二三四五六日天]|\d{1,2}\s*[点:：]|上午|下午|1[3-9]\d{9}|<CN_PHONE",
                    signal_text,
                )
            )
        )

        # Multi-intent extraction: when use_unified_extraction is enabled and multiple
        # intent signals are detected, fold 3-4 serial round trips into a single unified call (Battle 3)
        signal_count = sum([bool(has_profile_signal), bool(has_needs_signal), bool(has_reservation_signal)])
        if self.use_unified_extraction and signal_count >= 1:
            from src.agent.extractors.unified_extractor import extract_unified_slots

            state, _ = extract_unified_slots(self.llm, conversation_text, state)
        else:
            # Profile extraction: active during profile stages or when profile info provided in this turn
            if has_profile_signal:
                state.profile = extract_profile(self.llm, conversation_text, state.profile)

            # Combined needs extraction: explicit + implicit in one LLM call
            if has_needs_signal:
                state.needs = extract_combined_needs(
                    self.llm, conversation_text, state.profile, state.needs
                )

            # Reservation extraction: active during reservation stages or when booking info provided
            if has_reservation_signal:
                state.reservation = extract_reservation(self.llm, conversation_text, state.reservation)

        # Run constraint reconciliation engine to detect hard/soft conflicts
        conflicts = reconcile_constraints(state)
        for conflict in conflicts:
            note = conflict.to_system_note()
            if note not in state.system_notes:
                state.system_notes.append(note)

        return state
