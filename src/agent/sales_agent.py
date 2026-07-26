"""
SalesAgent — the single entry point for the Agent package.

Processes one conversation turn:
    AgentResult = SalesAgent.process(AgentInput)

Has NO backend dependencies (no FastAPI, no storage, no ChromaDB).
Vehicle retrieval results are passed IN via AgentInput.retrieved_cars.
"""

import logging
from typing import Any, Dict, List, Optional

from llama_index.core.llms import LLM

from src.agent.extractors.combined_needs_extractor import extract_combined_needs
from src.agent.extractors.profile_extractor import extract_profile
from src.agent.extractors.reservation_extractor import extract_reservation
from src.agent.memory import ChatMemoryManager
from src.agent.response_generator import generate_response
from src.agent.schemas import (
    AgentInput,
    AgentResult,
    SessionState,
    Stage,
)
from src.agent.stages import determine_next_stage

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

    def observe(self, state: SessionState, user_message: str) -> SessionState:
        """
        Record the user's message and extract what it reveals — no generation.

        Split out of `process` so a caller can retrieve vehicles using the needs
        stated in *this* turn. Retrieving before observing means the index is
        queried with the previous turn's needs, so a user who says "mid-size
        electric SUV" gets recommendations for whatever they asked for one turn
        earlier.

        Args:
            state: Session state at the start of the turn.
            user_message: What the user just said.

        Returns:
            An updated copy of the state. The input is not mutated.
        """
        updated = state.model_copy(deep=True)
        self.memory.add_user_message(updated.session_id, user_message)
        conversation_text = self.memory.get_history_as_text(updated.session_id)
        return self._extract_information(updated, conversation_text)

    def respond(
        self,
        state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentResult:
        """
        Advance the stage machine and generate the reply for an observed turn.

        Expects `state` to already carry this turn's extractions — i.e. the
        output of `observe`.
        """
        updated = state.model_copy(deep=True)
        session_id = updated.session_id
        conversation_text = self.memory.get_history_as_text(session_id)

        if retrieved_cars:
            updated.matched_cars = retrieved_cars

        old_stage = updated.stage
        updated.previous_stage = old_stage.value
        updated.stage = determine_next_stage(
            updated.stage,
            updated.profile,
            updated.needs,
            updated.matched_cars,
            updated.reservation,
        )

        stage_changed = updated.stage != old_stage
        if stage_changed:
            logger.info(
                f"[{session_id}] Stage transition: {old_stage.value} → {updated.stage.value}"
            )

        response_text = generate_response(
            self.llm,
            updated.stage,
            conversation_text,
            updated.profile,
            updated.needs,
            updated.matched_cars,
            updated.reservation,
        )

        self.memory.add_assistant_message(session_id, response_text)

        return AgentResult(
            session_state=updated,
            response_text=response_text,
            stage_changed=stage_changed,
        )

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
