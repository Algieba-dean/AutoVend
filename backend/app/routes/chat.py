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

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
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
from src.agent.storage.distributed_session import get_distributed_session_store
from src.mlops import (
    alert_manager,
    deployment_router,
    dlq_replay_engine,
    otel_tracer,
    prometheus_exporter,
    semantic_drift_detector,
)
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

# Per-session async locks to prevent concurrent turn race conditions
_session_locks: Dict[str, "asyncio.Lock"] = {}

# Cache of previous explicit needs per session (for change detection)
_prev_explicit: Dict[str, dict] = {}


def get_or_restore_session(
    session_id: str,
    agent: SalesAgent,
    profile: Optional[UserProfile] = None,
    auto_create: bool = True,
) -> Optional[SessionState]:
    """Unified session accessor shared across text chat and voice endpoints."""
    state = _sessions.get(session_id) or _restore_session(session_id, agent)
    if state is None and auto_create:
        state = SessionState(session_id=session_id, profile=profile or UserProfile())
        _sessions[session_id] = state
    elif state is not None:
        _sessions[session_id] = state
    return state


def save_session_state(session_id: str, state: SessionState, agent: SalesAgent) -> None:
    """Update in-memory session state and persist to disk."""
    _sessions[session_id] = state
    try:
        FileStorage.save_session(session_id, _session_payload(state, agent))
    except Exception as exc:
        logger.error(f"[{session_id}] session persistence failed: {exc}")


def _get_session_lock(session_id: str):
    import asyncio

    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


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


def _retrieve_cars(state: SessionState, user_query: str = "") -> list:
    """
    Retrieve candidate vehicles via Tiered Retrieval Engine and Hybrid pipeline.

    Supports Tier 0 fast-path spec lookup (<1-2ms) and dynamic topic hopping
    without stage locking.
    """
    if user_query:
        try:
            from src.retrieval.tiered_engine import TieredRetrievalEngine

            t0 = TieredRetrievalEngine.get_instance().search_tier0(user_query)
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
                    return fast_cars
        except Exception as te:
            logger.debug(f"Tier 0 lookup skipped or failed: {te}")

    if _pipeline is None:
        return state.matched_cars
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
        from src.retrieval.compression import ContextCompressor

        cars = ContextCompressor.compress_matched_cars(
            cars, query_text=query_text, active_constraints=state.needs.explicit.model_dump()
        )
        # Filter through Data Freshness and Lifecycle Engine to prevent tombstone recommendations
        try:
            from src.ingestion.freshness import DataFreshnessEngine
            freshness_engine = DataFreshnessEngine()
            cars, upgrade_notes = freshness_engine.filter_recommendable_vehicles(cars)
            for note in upgrade_notes:
                if note not in state.system_notes:
                    state.system_notes.append(note)
        except Exception as fe:
            logger.warning(f"Data freshness filtering warning: {fe}")

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
    turn_start_time = time.time()
    agent = _get_agent()
    session_id = request.session_id
    session_store = get_distributed_session_store()

    try:
        async with session_store.lock_session(session_id):
            # Get or auto-create session from distributed store
            state = await session_store.get(session_id)
            if state is None:
                state = get_or_restore_session(session_id, agent, profile=request.profile)
            if state is None:
                profile = request.profile or UserProfile()
                state = SessionState(session_id=session_id, profile=profile)
                _sessions[session_id] = state
            await session_store.save(session_id, state)

            stage_val = state.stage.value if state else "welcome"
            span = otel_tracer.start_span(
                f"agent.turn.{stage_val}",
                attributes={
                    "session.id": session_id,
                    "agent.stage": stage_val,
                    "message.length": len(request.message),
                },
            )

            try:
                # Gate 1 — classify with anchor vectors. Microseconds, no model.
                decision = _classify(request.message, session_id)

                # Gate 2 — mask PII before the text reaches memory, prompts or a cloud API.
                safe_message, pii_found = _mask(request.message, session_id)

                skip_extraction = (
                    decision is not None and decision.intent in EXTRACTION_SKIP_INTENTS and not pii_found
                )

                if skip_extraction:
                    state = agent.remember(state, safe_message)
                    logger.info(
                        f"[{session_id}] semantic fast-path: {decision.intent} "
                        f"(score={decision.score:.3f}) — extraction skipped"
                    )
                else:
                    state = agent.observe(state, safe_message)

                # Interrupt: the customer contradicted a constraint they had already given.
                # Roll back along a legal backward edge before retrieval runs.
                if decision is not None and decision.intent == INTERRUPT_INTENT:
                    state = _rollback_on_constraint_change(state, decision)

                # Vehicle retrieval (backend concern — results passed back to the agent)
                retrieved_cars = _retrieve_cars(state, user_query=request.message)

                result = agent.respond(state, retrieved_cars)

                # Restore real values before anything is stored or shown.
                _unmask_state(result.session_state, session_id)
                result = result.model_copy(
                    update={"response_text": _unmask(result.response_text, session_id)}
                )

                # Update stored session state with OCC version bump
                _sessions[session_id] = result.session_state
                await session_store.save(session_id, result.session_state)
                background_tasks.add_task(
                    _persist_session,
                    session_id,
                    _session_payload(result.session_state, agent),
                )

                # Record MLOps telemetry & observability
                duration_s = time.time() - turn_start_time
                curr_stage = result.session_state.stage.value
                span.end(status_code="OK")
                prometheus_exporter.inc_counter("autovend_requests_total", labels={"stage": curr_stage})
                prometheus_exporter.observe_histogram(
                    "autovend_latency_seconds", duration_s, labels={"stage": curr_stage}
                )
                deployment_router.record_turn_metric(
                    session_id, variant="baseline", success=True, latency_s=duration_s
                )
                semantic_drift_detector.record_production_query(
                    intent=curr_stage,
                    retrieval_hit=bool(retrieved_cars),
                    retrieval_top1_score=0.85 if retrieved_cars else 0.0,
                )

                # Build API response
                now = datetime.now(timezone.utc).isoformat()
                user_msg = ChatMessage(
                    message_id=f"msg_{datetime.now().timestamp()}",
                    sender_type="user",
                    sender_id=session_id,
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
            except Exception as exc:
                duration_s = time.time() - turn_start_time
                curr_stage = state.stage.value if state else "unknown"
                span.end(status_code="ERROR", status_message=str(exc))
                prometheus_exporter.inc_counter("autovend_errors_total", labels={"stage": curr_stage})
                deployment_router.record_turn_metric(
                    session_id, variant="baseline", success=False, latency_s=duration_s
                )
                dlq_replay_engine.enqueue_failed_task(
                    task_type="agent_turn",
                    payload={
                        "session_id": session_id,
                        "message": request.message,
                        "stage": curr_stage,
                    },
                    error_message=str(exc),
                    error_category="agent_exception",
                )
                alert_manager.evaluate_metrics({"error_rate": 1.0, "p95_latency_s": duration_s})
                raise
    except SessionLockTimeoutError as e:
        raise HTTPException(status_code=429, detail=e.detail)


@router.post("/stream")
async def send_message_stream(request: ChatRequest, raw_request: Request):
    """
    Send a message and stream SSE events (metadata, token deltas, done).
    Battle 1 & 2: Pure asynchronous streaming bridge without threadpool starvation,
    with client disconnect detection, cancellation propagation, distributed lease lock held
    across the entire stream lifetime, and OCC state persistence.
    """
    import json

    turn_start_time = time.time()
    agent = _get_agent()
    session_id = request.session_id
    session_store = get_distributed_session_store()

    # Battle 2: Distributed re-entrant lease lock
    lock_ctx = session_store.lock_session(session_id)
    try:
        await lock_ctx.__aenter__()
    except SessionLockTimeoutError as e:
        raise HTTPException(status_code=429, detail=e.detail)

    lock_released = False

    async def release_lock():
        nonlocal lock_released
        if not lock_released:
            lock_released = True
            await lock_ctx.__aexit__(None, None, None)

    try:
        state = await session_store.get(session_id)
        if state is None:
            state = get_or_restore_session(session_id, agent, profile=request.profile)
        if state is None:
            profile = request.profile or UserProfile()
            state = SessionState(session_id=session_id, profile=profile)
            _sessions[session_id] = state
        await session_store.save(session_id, state)

        stage_val = state.stage.value if state else "welcome"
        span = otel_tracer.start_span(
            f"agent.turn.stream.{stage_val}",
            attributes={
                "session.id": session_id,
                "agent.stage": stage_val,
                "message.length": len(request.message),
            },
        )

        # Gate 1 & 2: Semantic classification and PII masking
        decision = _classify(request.message, session_id)
        safe_message, pii_found = _mask(request.message, session_id)

        skip_extraction = (
            decision is not None
            and decision.intent in EXTRACTION_SKIP_INTENTS
            and not pii_found
        )

        if skip_extraction:
            state = agent.remember(state, safe_message)
        else:
            state = agent.observe(state, safe_message)

        if decision is not None and decision.intent == INTERRUPT_INTENT:
            state = _rollback_on_constraint_change(state, decision)

        retrieved_cars = _retrieve_cars(state, user_query=request.message)

        async def sse_event_publisher():
            pii_chunk_buffer = ""
            last_emitted_state = state
            try:
                # Battle 1: Native async generator streaming with zero threadpool blocking
                async for event_type, data in agent.respond_stream(state, retrieved_cars):
                    # Client disconnect cancellation propagation
                    if raw_request is not None and await raw_request.is_disconnected():
                        logger.warning(
                            f"Client disconnected for session {session_id}, cleanly halting streaming."
                        )
                        break

                    if event_type == "metadata":
                        updated_state = data["session_state"]
                        stage_changed = data.get("stage_changed", False)
                        _unmask_state(updated_state, session_id)
                        _sessions[session_id] = updated_state
                        last_emitted_state = updated_state

                        meta_payload = {
                            "stage": {
                                "previous_stage": updated_state.previous_stage,
                                "current_stage": updated_state.stage.value,
                                "stage_changed": stage_changed,
                            },
                            "profile": updated_state.profile.model_dump(mode="json"),
                            "needs": updated_state.needs.model_dump(mode="json"),
                            "matched_car_models": updated_state.matched_cars,
                            "reservation_info": updated_state.reservation.model_dump(mode="json"),
                        }
                        yield f"event: metadata\ndata: {json.dumps(meta_payload, ensure_ascii=False)}\n\n"

                    elif event_type == "delta":
                        combined = pii_chunk_buffer + data
                        pii_chunk_buffer = ""
                        open_idx = combined.rfind("<")
                        close_idx = combined.rfind(">")
                        if open_idx != -1 and open_idx > close_idx and (len(combined) - open_idx) <= 24:
                            emit_part = combined[:open_idx]
                            pii_chunk_buffer = combined[open_idx:]
                        else:
                            emit_part = combined

                        if emit_part:
                            unmasked_delta = _unmask(emit_part, session_id)
                            token_payload = {"delta": unmasked_delta}
                            yield f"event: token\ndata: {json.dumps(token_payload, ensure_ascii=False)}\n\n"

                    elif event_type == "done":
                        if pii_chunk_buffer:
                            flushed = _unmask(pii_chunk_buffer, session_id)
                            pii_chunk_buffer = ""
                            yield f"event: token\ndata: {json.dumps({'delta': flushed}, ensure_ascii=False)}\n\n"

                        unmasked_text = _unmask(data, session_id)
                        done_payload = {"response_text": unmasked_text}
                        yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

            except asyncio.CancelledError:
                logger.info(f"Streaming task cleanly cancelled for session {session_id}")
            finally:
                # 无论正常结束还是客户端中断断连，统一异步持久化状态到存储层并安全释放租约锁
                try:
                    final_state = _sessions.get(session_id, last_emitted_state)
                    await session_store.save(session_id, final_state)
                    await _persist_session(session_id, _session_payload(final_state, agent))

                    duration_s = time.time() - turn_start_time
                    curr_stage = final_state.stage.value if final_state else "unknown"
                    span.end(status_code="OK")
                    prometheus_exporter.inc_counter(
                        "autovend_requests_total", labels={"stage": curr_stage}
                    )
                    prometheus_exporter.observe_histogram(
                        "autovend_latency_seconds", duration_s, labels={"stage": curr_stage}
                    )
                    deployment_router.record_turn_metric(
                        session_id, variant="baseline", success=True, latency_s=duration_s
                    )
                    semantic_drift_detector.record_production_query(
                        intent=curr_stage,
                        retrieval_hit=bool(retrieved_cars),
                        retrieval_top1_score=0.85 if retrieved_cars else 0.0,
                    )
                except Exception as save_err:
                    logger.error(f"Error persisting session {session_id} on stream completion: {save_err}")
                finally:
                    await release_lock()

        return StreamingResponse(
            sse_event_publisher(),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception:
        await release_lock()
        raise


@router.get("/sessions")
async def list_sessions():
    """List all active chat sessions for Dealer Portal and admin views."""
    sessions_list = []
    for sid, state in _sessions.items():
        sessions_list.append(
            {
                "session_id": sid,
                "stage": state.stage.value,
                "profile": state.profile.model_dump(mode="json"),
                "needs": state.needs.model_dump(mode="json"),
                "matched_cars_count": len(state.matched_cars),
                "reservation": state.reservation.model_dump(mode="json"),
            }
        )
    return {"sessions": sessions_list, "total": len(sessions_list)}


@router.get("/session/{session_id}")
async def get_session_details(session_id: str):
    """Get structured details for a single chat session."""
    agent = _get_agent()
    state = get_or_restore_session(session_id, agent, auto_create=False)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    return {
        "session_id": session_id,
        "stage": StageInfo(
            previous_stage=state.previous_stage,
            current_stage=state.stage.value,
        ),
        "profile": state.profile,
        "needs": state.needs,
        "matched_car_models": state.matched_cars,
        "reservation_info": state.reservation,
    }


@router.get("/session/{session_id}/messages")
async def get_messages(session_id: str):
    """Get message history for a session."""
    agent = _get_agent()

    state = get_or_restore_session(session_id, agent, auto_create=False)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found.")

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
