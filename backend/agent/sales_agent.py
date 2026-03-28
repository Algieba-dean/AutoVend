"""
SalesAgent — the single entry point for the Agent package.

Processes one conversation turn:
    AgentResult = SalesAgent.process(AgentInput)

Has NO backend dependencies (no FastAPI, no storage, no ChromaDB).
Vehicle retrieval results are passed IN via AgentInput.retrieved_cars.
"""

import logging

from llama_index.core.llms import LLM

from agent.extractors.combined_needs_extractor import extract_combined_needs
from agent.extractors.profile_extractor import extract_profile
from agent.extractors.reservation_extractor import extract_reservation
from agent.memory import ChatMemoryManager
from agent.response_generator import generate_response
from agent.schemas import (
    AgentInput,
    AgentResult,
    SessionState,
    Stage,
)
from agent.stages import determine_next_stage

logger = logging.getLogger(__name__)


class SalesAgent:
    """
    Pure AI conversation agent for automotive sales.

    Stateless per-call: all session state is passed in and returned out.
    Memory buffers are managed internally per session_id for token-limited history.
    """

    def __init__(self, llm: LLM):
        """
        Args:
            llm: LLM instance for extraction and generation.
        """
        self.llm = llm
        self.memory = ChatMemoryManager()

    def process(self, agent_input: AgentInput) -> AgentResult:
        """
        Process one conversation turn.

        Pipeline:
        1. Add user message to memory
        2. Extract information based on current stage
        3. Inject retrieved cars into state
        4. Determine stage transition
        5. Generate response
        6. Add response to memory
        7. Return AgentResult

        Args:
            agent_input: Contains session_state, user_message, retrieved_cars.

        Returns:
            AgentResult with updated session_state, response_text, stage_changed.
        """
        state = agent_input.session_state.model_copy(deep=True)
        session_id = state.session_id
        user_message = agent_input.user_message

        # 1. Add user message to memory
        self.memory.add_user_message(session_id, user_message)
        conversation_text = self.memory.get_history_as_text(session_id)

        # 2. Extract information based on current stage
        state = self._extract_information(state, conversation_text)

        # 3. Inject retrieved cars from backend
        if agent_input.retrieved_cars:
            state.matched_cars = agent_input.retrieved_cars

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

        stage_changed = state.stage != old_stage
        if stage_changed:
            logger.info(f"[{session_id}] Stage transition: {old_stage.value} → {state.stage.value}")

        # 5. Generate response
        response_text = generate_response(
            self.llm,
            state.stage,
            conversation_text,
            state.profile,
            state.needs,
            state.matched_cars,
            state.reservation,
        )

        # 6. Add response to memory
        self.memory.add_assistant_message(session_id, response_text)

        # 7. Return result
        return AgentResult(
            session_state=state,
            response_text=response_text,
            stage_changed=stage_changed,
        )

    def clear_session(self, session_id: str) -> None:
        """Clear memory for a session."""
        self.memory.clear_session(session_id)

    def get_history_text(self, session_id: str) -> str:
        """Get formatted conversation history for a session."""
        return self.memory.get_history_as_text(session_id)

    def _extract_information(self, state: SessionState, conversation_text: str) -> SessionState:
        """Run extractors relevant to the current stage."""
        stage = state.stage

        # Profile extraction: active during welcome and profile_analysis
        if stage in (Stage.WELCOME, Stage.PROFILE_ANALYSIS):
            state.profile = extract_profile(self.llm, conversation_text, state.profile)

        # Combined needs extraction: explicit + implicit in one LLM call
        if stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
            state.needs = extract_combined_needs(
                self.llm, conversation_text, state.profile, state.needs
            )

        # Reservation extraction: active during reservation stages
        if stage in (Stage.RESERVATION_4S, Stage.RESERVATION_CONFIRMATION):
            state.reservation = extract_reservation(self.llm, conversation_text, state.reservation)

        return state
