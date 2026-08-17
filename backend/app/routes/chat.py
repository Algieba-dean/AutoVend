"""
Chat API routes — thin orchestration layer.

Owns session lifecycle and API response formatting.
Delegates all AI logic to SalesAgent via the observe/respond protocol.

A turn passes through three gates before any model is consulted:

    1. Semantic router  — anchor-vector classification (microseconds, no model)
       tags the turn. Control-flow turns like "行，听你的" carry no vehicle
       attribute and skip extraction entirely. Runs on raw text: placeholders
       would destroy the meaning it classifies on, and the embedder is local.
    2. PII interceptor  — real identifiers become per-session placeholders, so
       nothing sensitive reaches memory, prompts, or a cloud API. Values
       extracted back out are restored before storage.
    3. Hybrid inference — whatever survives goes to the local 8B model or the
       cloud, per src/llm/router.py.

Each gate is optional and fails open: no anchors built, or Presidio absent,
and the turn simply takes the long path it took before these layers existed.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    StageInfo,
)
from backend.app.models.storage import FileStorage
from src.agent.sales_agent import SalesAgent
from src.agent.schemas import SessionState, Stage, UserProfile
from src.retrieval.adapters import hybrid_result_to_cars, needs_to_query_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Number of candidate vehicles handed to the agent per turn.
RETRIEVAL_TOP_K = 5

#: Control-flow intents that carry no information the extractor could use.
#: A hit here skips extraction: "行，听你的" states no vehicle attribute, and
#: an LLM call to establish that is a round trip spent to learn nothing.
#: `budget_objection` and `request_detail` are deliberately absent — the first
#: revises the budget slot, the second may name a model.
EXTRACTION_SKIP_INTENTS = frozenset({"affirm", "reject", "defer", "smalltalk"})

#: The interrupt intent. A turn that contradicts an agreed constraint rolls the
#: FSM back along a legal backward edge and clears what the abandoned stage
#: produced — otherwise the conversation claims to be re-examining requirements
#: while still holding the recommendations those requirements produced.
INTERRUPT_INTENT = "update_constraint"

# Injected at startup
_agent: Optional[SalesAgent] = None
_pipeline = None
_semantic_router = None
_pii = None

# In-memory session state store (session_id → SessionState)
_sessions: Dict[str, SessionState] = {}

# Cache of previous explicit needs per session (for change detection)
_prev_explicit: Dict[str, dict] = {}


def _session_payload(state: SessionState, agent: SalesAgent) -> dict:
    """Serialize structured state and the bounded conversation transcript."""
    memory = getattr(agent, "memory", None)
    history = memory.get_history(state.session_id) if memory is not None else []
    messages = [
        {"role": message.role.value, "content": message.content or ""} for message in history
    ]
    return {
        "version": 1,
        "state": state.model_dump(mode="json"),
        "messages": messages,
    }


async def _persist_session(session_id: str, payload: dict) -> None:
    """Background-task entry point for durable session persistence."""
    try:
        FileStorage.save_session(session_id, payload)
    except Exception as exc:
        logger.error(f"[{session_id}] session persistence failed: {exc}")


def _restore_session(session_id: str, agent: SalesAgent) -> Optional[SessionState]:
    """Restore state and memory after a worker restart, accepting legacy snapshots."""
    data = FileStorage.load_session(session_id)
    if not data:
        return None
    try:
        state_data = data.get("state", data)
        state = SessionState.model_validate(state_data)
        agent.clear_session(session_id)
        for message in data.get("messages", []):
            role = str(message.get("role", ""))
            content = str(message.get("content", ""))
            if role == "user":
                agent.memory.add_user_message(session_id, content)
            elif role == "assistant":
                agent.memory.add_assistant_message(session_id, content)
        logger.info(f"[{session_id}] restored persisted session at {state.stage.value}")
        return state
    except Exception as exc:
        logger.warning(f"[{session_id}] persisted session is invalid: {exc}")
        return None


def set_agent(agent: SalesAgent) -> None:
    """Inject the SalesAgent instance (called from main.py on startup)."""
    global _agent
    _agent = agent


def set_pipeline(pipeline) -> None:
    """Inject the hybrid retrieval pipeline (called from main.py on startup)."""
    global _pipeline
    _pipeline = pipeline


def set_semantic_router(semantic_router) -> None:
    """Inject the anchor-vector router. None disables the fast path."""
    global _semantic_router
    _semantic_router = semantic_router


def set_pii_interceptor(interceptor) -> None:
    """Inject the PII interceptor. None disables masking."""
    global _pii
    _pii = interceptor


def _get_agent() -> SalesAgent:
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized.")
    return _agent


# ── privacy and semantic gates ────────────────────────────────────────


def _mask(text: str, session_id: str) -> tuple:
    """
    Replace PII with per-session placeholders.

    Returns (masked_text, found_any). The flag feeds the fast-path guard: a
    turn containing PII must never skip extraction.

    Fails open — a recognizer bug should not take the conversation down — but
    logs at error level, because an unmasked turn is a real privacy event.
    """
    if _pii is None:
        return text, False
    try:
        masked, matches = _pii.mask(text, session_id)
        return masked, bool(matches)
    except Exception as exc:
        logger.error(f"[{session_id}] PII masking failed, message sent unmasked: {exc}")
        return text, False


def _unmask(text: str, session_id: str) -> str:
    if _pii is None or not text:
        return text
    try:
        return _pii.unmask(text, session_id)
    except Exception as exc:
        logger.error(f"[{session_id}] PII unmasking failed: {exc}")
        return text


def _unmask_state(state: SessionState, session_id: str) -> None:
    """
    Restore placeholders inside the extracted profile and reservation, in place.

    Without this the session would store `<CN_PERSON_1>` as the customer's name
    and put it on the test-drive booking.
    """
    if _pii is None:
        return
    try:
        for model in (state.profile, state.reservation):
            for field, value in model.model_dump().items():
                if isinstance(value, str) and "<" in value:
                    setattr(model, field, _pii.unmask(value, session_id))
    except Exception as exc:
        logger.error(f"[{session_id}] PII unmasking of session state failed: {exc}")


def _classify(text: str, session_id: str):
    """Route the turn against anchor vectors, or None when unavailable."""
    if _semantic_router is None:
        return None
    try:
        decision = _semantic_router.classify(text)
    except Exception as exc:
        logger.error(f"[{session_id}] semantic routing failed: {exc}")
        return None
    if not decision.matched:
        logger.debug(
            f"[{session_id}] no semantic match "
            f"(best={decision.score:.3f}, margin={decision.margin:.3f})"
        )
        return None
    return decision


def _rollback_on_constraint_change(state: SessionState, decision) -> SessionState:
    """
    Walk the FSM back after a constraint change, and say so in the next reply.

    Returns the state unchanged when the current stage has no rollback target —
    revising requirements while still gathering them needs no stage change, only
    the extraction that already happened.
    """
    from src.agent.stages import handle_constraint_change

    updated = state.model_copy(deep=True)
    outcome = handle_constraint_change(
        updated, reason=f"semantic intent {decision.intent} (score={decision.score:.3f})"
    )
    if outcome is None:
        logger.info(
            f"[{state.session_id}] constraint change at {state.stage.value}: no rollback needed"
        )
        return state
    if not outcome.rolled_back:
        logger.warning(f"[{state.session_id}] rollback refused: {outcome.verdict.rejection}")
        return state

    if outcome.verdict.system_note:
        updated.system_notes = [*updated.system_notes, outcome.verdict.system_note]
    # The needs cache is keyed on explicit needs; a rollback that clears
    # matched_cars must also drop the cache, or the next turn sees unchanged
    # needs and skips retrieval, leaving the customer with no recommendations.
    _prev_explicit.pop(state.session_id, None)

    logger.info(
        f"[{state.session_id}] constraint change → rolled back to "
        f"{updated.stage.value}, cleared {outcome.cleared_fields or 'nothing'}"
    )
    return updated


def _retrieve_cars(state: SessionState) -> list:
    """
    Retrieve candidate vehicles via the hybrid pipeline.

    Pipeline: rule/LLM intent parsing → SQLite structured pre-filter →
    dense + sparse recall over the reduced candidate set → RRF fusion.
    Pre-filtering before the vector search is what keeps latency flat as the
    catalogue grows, since only the surviving candidates get scored.
    """
    if _pipeline is None:
        return []
    if state.stage not in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
        return state.matched_cars

    # Skip retrieval if explicit needs haven't changed (performance optimization)
    sid = state.session_id
    current_explicit = state.needs.explicit.model_dump()
    if sid in _prev_explicit and _prev_explicit[sid] == current_explicit:
        if state.matched_cars:
            logger.debug(f"[{sid}] Skipping retrieval: explicit needs unchanged.")
            return state.matched_cars
    _prev_explicit[sid] = current_explicit

    query_text = needs_to_query_text(state.needs.explicit, state.needs.implicit)

    try:
        result = _pipeline.search(query_text, top_k=RETRIEVAL_TOP_K)
        cars = hybrid_result_to_cars(result, limit=RETRIEVAL_TOP_K)
        logger.info(
            f"[{sid}] Retrieval '{query_text}': {result.candidate_count} candidates "
            f"(degrade={result.degrade_level}) → {len(cars)} cars in {result.total_time:.3f}s"
        )
        # An empty result is worse than a stale one: keep the previous cars so the
        # agent still has something concrete to talk about.
        return cars or state.matched_cars
    except Exception as e:
        logger.error(f"Vehicle retrieval failed: {e}")
        return state.matched_cars


@router.post("/session", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest, background_tasks: BackgroundTasks):
    """Create a new chat session."""
    _get_agent()
    session_id = str(uuid.uuid4())
    profile = request.profile or UserProfile(phone_number=request.phone_number)
    state = SessionState(session_id=session_id, profile=profile)
    _sessions[session_id] = state
    background_tasks.add_task(_persist_session, session_id, _session_payload(state, _get_agent()))

    return SessionCreateResponse(
        session_id=session_id,
        message="Session created successfully.",
        stage=StageInfo(current_stage=state.stage.value),
        profile=state.profile,
    )


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest, background_tasks: BackgroundTasks):
    """Send a message and receive AI response."""
    agent = _get_agent()

    # Get or auto-create session
    state = _sessions.get(request.session_id) or _restore_session(request.session_id, agent)
    if state is None:
        profile = request.profile or UserProfile()
        state = SessionState(session_id=request.session_id, profile=profile)
        _sessions[request.session_id] = state

    # Gate 1 — classify with anchor vectors. Microseconds, no model.
    #
    # Runs on the *raw* text, before masking. Masking first would hand the
    # embedder "我叫<CN_PERSON_1>，手机<CN_PHONE_NUMBER_1>" — placeholders carry
    # no meaning, and an introduction reliably mis-classified as small talk,
    # which then skipped the very extraction that should have captured the name.
    # The embedding model is local and in-process; the threat this layer defends
    # against is PII reaching a third-party API, which happens further down.
    decision = _classify(request.message, request.session_id)

    # Gate 2 — mask PII before the text reaches memory, prompts or a cloud API.
    safe_message, pii_found = _mask(request.message, request.session_id)

    # Observe first, retrieve second: retrieval must see the needs stated in
    # *this* message. Querying before extraction lags a turn behind the user —
    # ask for a mid-size electric SUV and you get last turn's recommendations.
    #
    # A control-flow turn skips extraction but still enters memory: "我再想想吧"
    # is part of the conversation the generator has to read, it just has nothing
    # for the extractor to pull out.
    # A turn carrying PII always goes through extraction, whatever the router
    # thinks. Someone giving their name or number has stated something the
    # profile needs; a classifier confident enough to skip that would be wrong
    # in the one direction the product cannot absorb.
    skip_extraction = (
        decision is not None and decision.intent in EXTRACTION_SKIP_INTENTS and not pii_found
    )

    if skip_extraction:
        state = agent.remember(state, safe_message)
        logger.info(
            f"[{request.session_id}] semantic fast-path: {decision.intent} "
            f"(score={decision.score:.3f}) — extraction skipped"
        )
    else:
        state = agent.observe(state, safe_message)

    # Interrupt: the customer contradicted a constraint they had already given.
    # Roll back along a legal backward edge before retrieval runs, so the query
    # is built from the revised needs rather than the superseded ones.
    if decision is not None and decision.intent == INTERRUPT_INTENT:
        state = _rollback_on_constraint_change(state, decision)

    # Vehicle retrieval (backend concern — results passed back to the agent)
    retrieved_cars = _retrieve_cars(state)

    result = agent.respond(state, retrieved_cars)

    # Restore real values before anything is stored or shown. The models only
    # ever saw placeholders; the session state holds the truth.
    _unmask_state(result.session_state, request.session_id)
    result = result.model_copy(
        update={"response_text": _unmask(result.response_text, request.session_id)}
    )

    # Update stored session state
    _sessions[request.session_id] = result.session_state
    background_tasks.add_task(
        _persist_session,
        request.session_id,
        _session_payload(result.session_state, agent),
    )

    # Build API response
    now = datetime.now(timezone.utc).isoformat()
    user_msg = ChatMessage(
        message_id=f"msg_{datetime.now().timestamp()}",
        sender_type="user",
        sender_id=request.session_id,
        content=request.message,
        timestamp=now,
        status="delivered",
    )
    assistant_msg = ChatMessage(
        message_id=f"msg_{datetime.now().timestamp()}",
        sender_type="system",
        sender_id="AutoVend",
        content=result.response_text,
        timestamp=now,
        status="delivered",
    )

    return ChatResponse(
        message=user_msg,
        response=assistant_msg,
        stage=StageInfo(
            previous_stage=result.session_state.previous_stage,
            current_stage=result.session_state.stage.value,
        ),
        profile=result.session_state.profile,
        needs=result.session_state.needs,
        matched_car_models=result.session_state.matched_cars,
        reservation_info=result.session_state.reservation,
    )


@router.post("/stream")
async def send_message_stream(request: ChatRequest):
    """
    Send a message and stream SSE events (metadata, token deltas, done).
    """
    agent = _get_agent()
    state = _sessions.get(request.session_id) or _restore_session(request.session_id, agent)
    if state is None:
        profile = request.profile or UserProfile()
        state = SessionState(session_id=request.session_id, profile=profile)
        _sessions[request.session_id] = state

    decision = _classify(request.message, request.session_id)
    safe_message, pii_found = _mask(request.message, request.session_id)

    skip_extraction = (
        decision is not None and decision.intent in EXTRACTION_SKIP_INTENTS and not pii_found
    )

    if skip_extraction:
        state = agent.remember(state, safe_message)
    else:
        state = agent.observe(state, safe_message)

    if decision is not None and decision.intent == INTERRUPT_INTENT:
        state = _rollback_on_constraint_change(state, decision)

    retrieved_cars = _retrieve_cars(state)

    async def sse_event_generator():
        import json
        stream_gen = agent.respond_stream(state, retrieved_cars)
        for event_type, data in stream_gen:
            if event_type == "metadata":
                updated_state = data["session_state"]
                stage_changed = data["stage_changed"]
                _unmask_state(updated_state, request.session_id)
                _sessions[request.session_id] = updated_state

                meta_payload = {
                    "stage": {
                        "previous_stage": updated_state.previous_stage,
                        "current_stage": updated_state.stage.value,
                        "stage_changed": stage_changed,
                    },
                    "profile": updated_state.profile.model_dump(),
                    "needs": updated_state.needs.model_dump(),
                    "matched_car_models": updated_state.matched_cars,
                    "reservation_info": updated_state.reservation.model_dump(),
                }
                yield f"event: metadata\ndata: {json.dumps(meta_payload, ensure_ascii=False)}\n\n"
            elif event_type == "delta":
                unmasked_delta = _unmask(data, request.session_id)
                token_payload = {"delta": unmasked_delta}
                yield f"event: token\ndata: {json.dumps(token_payload, ensure_ascii=False)}\n\n"
            elif event_type == "done":
                unmasked_text = _unmask(data, request.session_id)
                done_payload = {"response_text": unmasked_text}
                yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@router.get("/session/{session_id}/messages")
async def get_messages(session_id: str):
    """Get message history for a session."""
    agent = _get_agent()

    state = _sessions.get(session_id) or _restore_session(session_id, agent)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    _sessions[session_id] = state

    history = agent.memory.get_history(session_id)
    messages = []
    for msg in history:
        messages.append(
            {
                "message_id": f"msg_{id(msg)}",
                "sender_type": "user" if msg.role.value == "user" else "system",
                "content": msg.content,
            }
        )

    return {
        "session_id": session_id,
        "messages": messages,
        "stage": StageInfo(
            previous_stage=state.previous_stage,
            current_stage=state.stage.value,
        ),
        "profile": state.profile,
        "needs": state.needs,
        "matched_car_models": state.matched_cars,
        "reservation_info": state.reservation,
    }


@router.put("/session/{session_id}/end")
async def end_session(session_id: str):
    """End a chat session."""
    agent = _get_agent()

    state = _sessions.pop(session_id, None) or _restore_session(session_id, agent)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    _prev_explicit.pop(session_id, None)
    agent.clear_session(session_id)
    FileStorage.delete_session(session_id)
    return {"message": "Session ended successfully.", "session_id": session_id}
