"""
Core conversation workflow engine backed by LangGraph + LangChain + LlamaIndex.

Orchestrates the full conversation flow via `LangGraphSalesAgent` (`StateGraph` +
`MemorySaver` checkpointer) and `LlamaIndexHybridRetriever` (LangChain `BaseRetriever`
wrapping LlamaIndex / HybridPipeline).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.app.models.schemas import (
    ChatMessage,
    ChatResponse,
    ReservationInfo,
    Stage,
    StageInfo,
    UserProfile,
    VehicleNeeds,
)
from src.agent.langgraph_agent import LangGraphSalesAgent
from src.agent.schemas import SessionState as AgentSessionState
from src.retrieval.langchain_retriever import LlamaIndexHybridRetriever

logger = logging.getLogger(__name__)


class SessionState:
    """Backward-compatible mutable session state wrapper for StageWorkflow."""

    def __init__(
        self,
        session_id: str,
        profile: Optional[UserProfile] = None,
    ):
        self.session_id = session_id
        self.stage = Stage.WELCOME
        self.previous_stage = ""
        self.profile = profile or UserProfile()
        self.needs = VehicleNeeds()
        self.matched_cars: list[Dict[str, Any]] = []
        self.reservation = ReservationInfo()
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "stage": self.stage.value,
            "previous_stage": self.previous_stage,
            "profile": self.profile.model_dump(),
            "needs": self.needs.model_dump(),
            "matched_cars": self.matched_cars,
            "reservation": self.reservation.model_dump(),
            "created_at": self.created_at,
        }

    def to_agent_state(self) -> AgentSessionState:
        return AgentSessionState(
            session_id=self.session_id,
            stage=self.stage,
            previous_stage=self.previous_stage,
            profile=self.profile,
            needs=self.needs,
            matched_cars=self.matched_cars,
            reservation=self.reservation,
            created_at=self.created_at,
        )

    def sync_from_agent_state(self, agent_state: AgentSessionState) -> None:
        self.stage = agent_state.stage
        self.previous_stage = agent_state.previous_stage
        self.profile = agent_state.profile
        self.needs = agent_state.needs
        self.matched_cars = agent_state.matched_cars
        self.reservation = agent_state.reservation


class StageWorkflow:
    """
    Main conversation workflow engine powered by LangGraph StateGraph.

    Preserves the synchronous session API while delegating state transitions,
    slot extraction, LlamaIndex retrieval, plugin execution, and LangChain
    response generation to `LangGraphSalesAgent`.
    """

    def __init__(
        self,
        llm: Any,
        vehicle_index=None,
        use_unified_extraction: bool = False,
    ):
        self.llm = llm
        self.vehicle_index = vehicle_index
        retriever = (
            LlamaIndexHybridRetriever(llama_index=vehicle_index)
            if vehicle_index is not None
            else None
        )
        self.graph_agent = LangGraphSalesAgent(
            llm=llm,
            retriever=retriever,
            use_unified_extraction=use_unified_extraction,
        )

    def create_session(
        self,
        session_id: str,
        profile: Optional[UserProfile] = None,
    ) -> SessionState:
        """Create a new conversation session in the LangGraph checkpointer."""
        state = SessionState(session_id=session_id, profile=profile or UserProfile())
        self.graph_agent.hydrate_history(session_id, [], session_state=state.to_agent_state())
        logger.info(f"Session created: {session_id}")
        return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get an existing session state from the LangGraph checkpointer."""
        snap = self.graph_agent.get_graph_state(session_id)
        if snap is None or not getattr(snap, "values", None):
            return None
        agent_state = snap.values.get("session_state")
        if agent_state is None:
            return None
        wrapper = SessionState(session_id=session_id)
        wrapper.sync_from_agent_state(agent_state)
        return wrapper

    def end_session(self, session_id: str) -> None:
        """End and clean up a session."""
        self.graph_agent.clear_session(session_id)
        logger.info(f"Session ended: {session_id}")

    def process_message(
        self,
        session_id: str,
        user_message: str,
    ) -> ChatResponse:
        """Process a user message through the LangGraph StateGraph pipeline."""
        existing = self.get_session(session_id)
        result = self.graph_agent.invoke_turn(
            session_id=session_id,
            user_message=user_message,
            session_state=existing.to_agent_state() if existing is not None else None,
        )
        updated_state = result.session_state

        now = datetime.now(timezone.utc).isoformat()
        user_msg = ChatMessage(
            message_id=f"msg_{datetime.now().timestamp()}",
            sender_type="user",
            sender_id=session_id,
            content=user_message,
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
                previous_stage=updated_state.previous_stage,
                current_stage=updated_state.stage.value,
            ),
            profile=updated_state.profile,
            needs=updated_state.needs,
            matched_car_models=updated_state.matched_cars,
            reservation_info=updated_state.reservation,
        )
