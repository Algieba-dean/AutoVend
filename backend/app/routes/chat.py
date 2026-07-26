"""
Chat API routes — thin orchestration layer.

Owns session lifecycle and API response formatting.
Delegates all AI logic to agent.SalesAgent via AgentInput/AgentResult protocol.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    StageInfo,
)
from src.agent.sales_agent import SalesAgent
from src.agent.schemas import SessionState, Stage, UserProfile
from src.retrieval.adapters import hybrid_result_to_cars, needs_to_query_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Number of candidate vehicles handed to the agent per turn.
RETRIEVAL_TOP_K = 5

# Injected at startup
_agent: Optional[SalesAgent] = None
_pipeline = None

# In-memory session state store (session_id → SessionState)
_sessions: Dict[str, SessionState] = {}

# Cache of previous explicit needs per session (for change detection)
_prev_explicit: Dict[str, dict] = {}


def set_agent(agent: SalesAgent) -> None:
    """Inject the SalesAgent instance (called from main.py on startup)."""
    global _agent
    _agent = agent


def set_pipeline(pipeline) -> None:
    """Inject the hybrid retrieval pipeline (called from main.py on startup)."""
    global _pipeline
    _pipeline = pipeline


def _get_agent() -> SalesAgent:
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized.")
    return _agent


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

    query_text = needs_to_query_text(state.needs.explicit)

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
async def create_session(request: SessionCreateRequest):
    """Create a new chat session."""
    _get_agent()
    session_id = str(uuid.uuid4())
    profile = request.profile or UserProfile(phone_number=request.phone_number)
    state = SessionState(session_id=session_id, profile=profile)
    _sessions[session_id] = state

    return SessionCreateResponse(
        session_id=session_id,
        message="Session created successfully.",
        stage=StageInfo(current_stage=state.stage.value),
        profile=state.profile,
    )


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message and receive AI response."""
    agent = _get_agent()

    # Get or auto-create session
    state = _sessions.get(request.session_id)
    if state is None:
        profile = request.profile or UserProfile()
        state = SessionState(session_id=request.session_id, profile=profile)
        _sessions[request.session_id] = state

    # Observe first, retrieve second: retrieval must see the needs stated in
    # *this* message. Querying before extraction lags a turn behind the user —
    # ask for a mid-size electric SUV and you get last turn's recommendations.
    state = agent.observe(state, request.message)

    # Vehicle retrieval (backend concern — results passed back to the agent)
    retrieved_cars = _retrieve_cars(state)

    result = agent.respond(state, retrieved_cars)

    # Update stored session state
    _sessions[request.session_id] = result.session_state

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


@router.get("/session/{session_id}/messages")
async def get_messages(session_id: str):
    """Get message history for a session."""
    agent = _get_agent()

    state = _sessions.get(session_id)
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

    state = _sessions.pop(session_id, None)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    _prev_explicit.pop(session_id, None)
    agent.clear_session(session_id)
    return {"message": "Session ended successfully.", "session_id": session_id}
