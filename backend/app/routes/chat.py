"""
Chat API routes — thin orchestration layer.

Owns session lifecycle and API response formatting.
Delegates all AI logic to agent.SalesAgent via AgentInput/AgentResult protocol.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from agent.sales_agent import SalesAgent
from agent.schemas import AgentInput, SessionState, Stage, UserProfile
from app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    StageInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Injected at startup
_agent: Optional[SalesAgent] = None
_vehicle_index = None

# In-memory session state store (session_id → SessionState)
_sessions: Dict[str, SessionState] = {}

# Cache of previous explicit needs per session (for change detection)
_prev_explicit: Dict[str, dict] = {}


def set_agent(agent: SalesAgent) -> None:
    """Inject the SalesAgent instance (called from main.py on startup)."""
    global _agent
    _agent = agent


def set_vehicle_index(index) -> None:
    """Inject vehicle index for RAG retrieval (called from main.py on startup)."""
    global _vehicle_index
    _vehicle_index = index


def _get_agent() -> SalesAgent:
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized.")
    return _agent


def _retrieve_cars(state: SessionState) -> list:
    """Run RAG retrieval if vehicle index is available and stage is appropriate."""
    if _vehicle_index is None:
        return []
    if state.stage not in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
        return state.matched_cars

    # Skip retrieval if explicit needs haven't changed (performance optimization)
    sid = state.session_id
    current_explicit = state.needs.explicit.model_dump()
    if sid in _prev_explicit and _prev_explicit[sid] == current_explicit:
        if state.matched_cars:
            logger.debug(f"[{sid}] Skipping RAG: explicit needs unchanged.")
            return state.matched_cars
    _prev_explicit[sid] = current_explicit

    from app.rag.query_engine import format_retrieval_results, retrieve_vehicles

    explicit = state.needs.explicit
    query_parts = []
    if explicit.vehicle_category_bottom:
        query_parts.append(explicit.vehicle_category_bottom)
    if explicit.powertrain_type:
        query_parts.append(explicit.powertrain_type)
    if explicit.design_style:
        query_parts.append(explicit.design_style)
    if explicit.brand:
        query_parts.append(f"{explicit.brand} brand")
    if explicit.prize:
        query_parts.append(f"price range {explicit.prize}")
    if explicit.seat_layout:
        query_parts.append(explicit.seat_layout)
    if not query_parts:
        query_parts.append("recommend a good vehicle")

    filters: Dict[str, Any] = {}
    if explicit.brand:
        filters["brand"] = explicit.brand
    if explicit.powertrain_type:
        filters["powertrain_type"] = explicit.powertrain_type

    try:
        results = retrieve_vehicles(
            _vehicle_index,
            " ".join(query_parts),
            metadata_filters=filters if filters else None,
            top_k=5,
        )
        return format_retrieval_results(results)
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

    # RAG retrieval (backend concern — results passed to agent)
    retrieved_cars = _retrieve_cars(state)

    # Delegate to agent
    agent_input = AgentInput(
        session_state=state,
        user_message=request.message,
        retrieved_cars=retrieved_cars,
    )
    result = agent.process(agent_input)

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
