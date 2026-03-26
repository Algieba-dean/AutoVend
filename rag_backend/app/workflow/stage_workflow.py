"""
Core conversation workflow engine.

Orchestrates the full conversation flow:
1. Receive user message
2. Extract information (profile, needs, reservation) based on current stage
3. Determine stage transition
4. Retrieve vehicles if in needs/selection stage
5. Generate response
6. Update memory and session state
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from llama_index.core.llms import LLM

from app.extractors.implicit_deductor import deduce_implicit_needs
from app.extractors.needs_extractor import extract_explicit_needs
from app.extractors.profile_extractor import extract_profile
from app.extractors.reservation_extractor import extract_reservation
from app.memory.chat_memory import ChatMemoryManager
from app.models.schemas import (
    ChatMessage,
    ChatResponse,
    ReservationInfo,
    Stage,
    StageInfo,
    UserProfile,
    VehicleNeeds,
)
from app.rag.query_engine import format_retrieval_results, retrieve_vehicles
from app.workflow.response_generator import generate_response
from app.workflow.stages import determine_next_stage

logger = logging.getLogger(__name__)


class SessionState:
    """Holds all mutable state for a single conversation session."""

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
        self.matched_cars: List[Dict[str, Any]] = []
        self.reservation = ReservationInfo()
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session state for API response / persistence."""
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


class StageWorkflow:
    """
    Main conversation workflow engine.

    Manages session states, drives extraction/retrieval/generation
    pipeline per message, and handles stage transitions.
    """

    def __init__(
        self,
        llm: LLM,
        vehicle_index=None,
    ):
        """
        Args:
            llm: LLM instance for extraction and generation.
            vehicle_index: VectorStoreIndex for vehicle retrieval.
                          Can be None if not yet built (retrieval will be skipped).
        """
        self.llm = llm
        self.vehicle_index = vehicle_index
        self.memory = ChatMemoryManager()
        self._sessions: Dict[str, SessionState] = {}

    def create_session(
        self,
        session_id: str,
        profile: Optional[UserProfile] = None,
    ) -> SessionState:
        """Create a new conversation session."""
        state = SessionState(session_id, profile)
        self._sessions[session_id] = state
        logger.info(f"Session created: {session_id}")
        return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get an existing session state."""
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> None:
        """End and clean up a session."""
        self._sessions.pop(session_id, None)
        self.memory.clear_session(session_id)
        logger.info(f"Session ended: {session_id}")

    def process_message(
        self,
        session_id: str,
        user_message: str,
    ) -> ChatResponse:
        """
        Process a user message through the full workflow pipeline.

        Pipeline:
        1. Get/create session state
        2. Add user message to memory
        3. Extract information based on current stage
        4. Determine stage transition
        5. Retrieve vehicles if applicable
        6. Generate response
        7. Add response to memory
        8. Return structured ChatResponse

        Args:
            session_id: The session identifier.
            user_message: The user's message text.

        Returns:
            ChatResponse with message, response, stage, profile, needs, etc.
        """
        # 1. Get or create session
        state = self._sessions.get(session_id)
        if state is None:
            state = self.create_session(session_id)

        # 2. Add user message to memory
        self.memory.add_user_message(session_id, user_message)
        conversation_text = self.memory.get_history_as_text(session_id)

        # 3. Extract information based on current stage
        state = self._extract_information(state, conversation_text)

        # 4. Determine stage transition
        old_stage = state.stage
        state.previous_stage = old_stage.value
        state.stage = determine_next_stage(
            state.stage,
            state.profile,
            state.needs,
            state.matched_cars,
            state.reservation,
        )

        if state.stage != old_stage:
            logger.info(
                f"[{session_id}] Stage transition: "
                f"{old_stage.value} → {state.stage.value}"
            )

        # 5. Retrieve vehicles if in needs/selection stage
        if state.stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
            state = self._retrieve_vehicles(state)

        # 6. Generate response
        response_text = generate_response(
            self.llm,
            state.stage,
            conversation_text,
            state.profile,
            state.needs,
            state.matched_cars,
            state.reservation,
        )

        # 7. Add response to memory
        self.memory.add_assistant_message(session_id, response_text)

        # 8. Build and return ChatResponse
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
            content=response_text,
            timestamp=now,
            status="delivered",
        )

        return ChatResponse(
            message=user_msg,
            response=assistant_msg,
            stage=StageInfo(
                previous_stage=state.previous_stage,
                current_stage=state.stage.value,
            ),
            profile=state.profile,
            needs=state.needs,
            matched_car_models=state.matched_cars,
            reservation_info=state.reservation,
        )

    def _extract_information(
        self, state: SessionState, conversation_text: str
    ) -> SessionState:
        """Run extractors relevant to the current stage."""
        stage = state.stage

        # Profile extraction: active during welcome and profile_analysis
        if stage in (Stage.WELCOME, Stage.PROFILE_ANALYSIS):
            state.profile = extract_profile(
                self.llm, conversation_text, state.profile
            )

        # Needs extraction: active during needs_analysis and car_selection
        if stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
            state.needs.explicit = extract_explicit_needs(
                self.llm, conversation_text, state.needs.explicit
            )
            state.needs.implicit = deduce_implicit_needs(
                self.llm, state.profile, state.needs.explicit, state.needs.implicit
            )

        # Reservation extraction: active during reservation stages
        if stage in (Stage.RESERVATION_4S, Stage.RESERVATION_CONFIRMATION):
            state.reservation = extract_reservation(
                self.llm, conversation_text, state.reservation
            )

        return state

    def _retrieve_vehicles(self, state: SessionState) -> SessionState:
        """Retrieve matching vehicles from the RAG index."""
        if self.vehicle_index is None:
            logger.warning("Vehicle index not available, skipping retrieval.")
            return state

        # Build query from explicit needs
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

        # Add implicit needs for semantic richness
        implicit = state.needs.implicit
        if implicit.comfort_level:
            query_parts.append(f"{implicit.comfort_level} comfort")
        if implicit.family_friendliness:
            query_parts.append(f"{implicit.family_friendliness} family friendliness")

        if not query_parts:
            query_parts.append("recommend a good vehicle")

        query = " ".join(query_parts)

        # Build metadata filters from exact-match fields
        filters = {}
        if explicit.brand:
            filters["brand"] = explicit.brand
        if explicit.prize:
            filters["prize"] = explicit.prize
        if explicit.powertrain_type:
            filters["powertrain_type"] = explicit.powertrain_type

        try:
            results = retrieve_vehicles(
                self.vehicle_index,
                query=query,
                metadata_filters=filters if filters else None,
                top_k=5,
            )
            state.matched_cars = format_retrieval_results(results)
            logger.info(f"Retrieved {len(state.matched_cars)} matching vehicles.")
        except Exception as e:
            logger.error(f"Vehicle retrieval failed: {e}")

        return state
