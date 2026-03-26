"""
Chat API routes — session management and message processing.
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    StageInfo,
    UserProfile,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Workflow instance is injected at app startup via set_workflow()
_workflow = None


def set_workflow(workflow) -> None:
    """Inject the StageWorkflow instance (called from main.py on startup)."""
    global _workflow
    _workflow = workflow


def _get_workflow():
    if _workflow is None:
        raise HTTPException(
            status_code=503, detail="Workflow engine not initialized."
        )
    return _workflow


@router.post("/session", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest):
    """Create a new chat session."""
    wf = _get_workflow()
    session_id = str(uuid.uuid4())
    profile = request.profile or UserProfile(phone_number=request.phone_number)
    state = wf.create_session(session_id, profile)

    return SessionCreateResponse(
        session_id=session_id,
        message="Session created successfully.",
        stage=StageInfo(current_stage=state.stage.value),
        profile=state.profile,
    )


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message and receive AI response."""
    wf = _get_workflow()

    # Update profile if provided in request
    session = wf.get_session(request.session_id)
    if session is None and request.profile:
        wf.create_session(request.session_id, request.profile)

    response = wf.process_message(request.session_id, request.message)
    return response


@router.get("/session/{session_id}/messages")
async def get_messages(session_id: str):
    """Get message history for a session."""
    wf = _get_workflow()

    history_text = wf.memory.get_history_as_text(session_id)
    session = wf.get_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    return {
        "session_id": session_id,
        "history": history_text,
        "stage": session.stage.value,
    }


@router.put("/session/{session_id}/end")
async def end_session(session_id: str):
    """End a chat session."""
    wf = _get_workflow()

    session = wf.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    wf.end_session(session_id)
    return {"message": "Session ended successfully.", "session_id": session_id}
