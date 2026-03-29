"""
SalesAgent — the single entry point for the Agent package.

Processes one conversation turn:
    AgentResult = SalesAgent.process(AgentInput)

Architecture layers (executed per turn):
  1. Local/Edge  — FSM state routing + structured extraction + query rewrite
  2. RAG Engine  — dual-path retrieval + reranker (handled by backend)
  3. Cloud Brain — implicit-need inference + parameter comparison + response gen
  4. Guardrails  — fact-consistency check + circuit-breaker fallback

Has NO backend dependencies (no FastAPI, no storage, no ChromaDB).
Vehicle retrieval results are passed IN via AgentInput.retrieved_cars.
"""

import logging

from llama_index.core.llms import LLM

from agent.extractors.global_extractor import extract_global
from agent.extractors.query_rewriter import rewrite_query
from agent.guardrails import check_response
from agent.memory import ChatMemoryManager
from agent.response_generator import generate_response
from agent.schemas import (
    AgentInput,
    AgentResult,
    SessionState,
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
        Process one conversation turn through four architecture layers.

        Layer 1 — Local/Edge:
          1a. Add user message to memory
          1b. Structured information extraction (global extractor)
          1c. FSM state routing (determine_next_stage)
          1d. Query rewriting (negative needs + colloquial cleanup)
        Layer 2 — RAG Engine (external):
          2a. Inject retrieved cars from backend (dual-path + reranker)
        Layer 3 — Cloud Brain:
          3a. Generate response (implicit need reasoning + sales rhetoric)
        Layer 4 — Guardrails:
          4a. Fact-consistency check against retrieved data
          4b. Circuit breaker if hallucination detected

        Args:
            agent_input: Contains session_state, user_message, retrieved_cars.

        Returns:
            AgentResult with updated session_state, response_text, stage_changed.
        """
        state = agent_input.session_state.model_copy(deep=True)
        session_id = state.session_id
        user_message = agent_input.user_message

        # ── Layer 1: Local/Edge Processing ──────────────────────────
        # 1a. Memory
        self.memory.add_user_message(session_id, user_message)
        conversation_text = self.memory.get_history_as_text(session_id)

        # 1b. Structured extraction (profile + needs + reservation)
        state = self._extract_information(state, conversation_text)

        # 1c. FSM state routing
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
            logger.info(
                f"[{session_id}] Stage: "
                f"{old_stage.value} → {state.stage.value}"
            )

        # 1d. Query rewriting (negative needs + normalization)
        rewrite = rewrite_query(
            user_message, state.profile, state.needs
        )
        state.rewrite_result = rewrite

        # ── Layer 2: RAG Engine (injected from backend) ─────────────
        if agent_input.retrieved_cars:
            state.matched_cars = agent_input.retrieved_cars

        # ── Layer 3: Cloud Brain (response generation) ──────────────
        response_text = generate_response(
            self.llm,
            state.stage,
            conversation_text,
            state.profile,
            state.needs,
            state.matched_cars,
            state.reservation,
        )

        # ── Layer 4: Guardrails (fact check + circuit breaker) ──────
        guardrail = check_response(
            response_text, state.matched_cars
        )
        response_text = guardrail.final_response

        # ── Finalize ────────────────────────────────────────────────
        self.memory.add_assistant_message(session_id, response_text)

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
        """
        Run global extraction on every turn regardless of stage.

        Unlike the previous stage-gated approach, this extracts profile,
        needs, and reservation info simultaneously. This means if a user
        says "I'm Zhang San, 30 years old, want a Tesla SUV under 300K"
        in one message, all fields are captured immediately.
        """
        return extract_global(self.llm, conversation_text, state)
