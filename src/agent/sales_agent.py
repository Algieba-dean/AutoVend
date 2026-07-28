"""
SalesAgent — the single entry point for the Agent package.

Processes one conversation turn:
    AgentResult = SalesAgent.process(AgentInput)

Has NO backend dependencies (no FastAPI, no storage, no ChromaDB).
Vehicle retrieval results are passed IN via AgentInput.retrieved_cars.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from llama_index.core.llms import LLM

from src.agent.extractors.combined_needs_extractor import extract_combined_needs
from src.agent.extractors.profile_extractor import extract_profile
from src.agent.extractors.reservation_extractor import extract_reservation
from src.agent.memory import ChatMemoryManager
from src.agent.patches import StatePatch, diff, format_for_prompt, snapshot
from src.agent.response_generator import generate_response
from src.agent.schemas import (
    AgentInput,
    AgentResult,
    SessionState,
    Stage,
)
from src.agent.stages import ProposalSource, TransitionProposal, advance, propose_forward
from src.agent.tool_planner import plan_tools
from src.agent.tools import ToolResult, dispatch_all
from src.agent.transition_proposer import propose_by_llm

logger = logging.getLogger(__name__)

#: How many recent patches ride along in the generation prompt. Enough to carry
#: "what just changed" without re-serialising the whole state every turn.
PROMPT_PATCH_WINDOW = 6


@dataclass
class ToolOutcome:
    """Result of running a batch of tool calls."""

    state: SessionState
    results: List[ToolResult]
    #: Intents the agent cannot fulfil itself — retrieval, stage changes.
    requests: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)


def _record_patches(state: SessionState, before: Dict[str, Any], source: str) -> None:
    """Diff against `before`, append to the patch log, and set `last_patch`."""
    patches = diff(before, snapshot(state), source=source)
    if not patches:
        state.last_patch = {}
        return
    state.patch_log = [*state.patch_log, *(p.to_dict() for p in patches)]
    state.last_patch = {p.path: p.value for p in patches}
    logger.info(f"[{state.session_id}] {len(patches)} patch(es): {state.last_patch}")


class SalesAgent:
    """
    Pure AI conversation agent for automotive sales.

    Stateless per-call: all session state is passed in and returned out.
    Memory buffers are managed internally per session_id for token-limited history.
    """

    def __init__(
        self,
        llm: LLM,
        generation_llm: Optional[LLM] = None,
        enable_tool_planning: bool = False,
    ):
        """
        Args:
            llm: LLM used for extraction — filling Pydantic schemas from the
                transcript. Called on every turn with short, constrained
                prompts.
            generation_llm: LLM used to write the customer-facing reply. Defaults
                to `llm`.

        Two slots rather than one because the two jobs have different
        requirements: extraction is high-frequency and schema-bounded, while
        generation is open-ended and is what the customer actually reads.
        Whoever constructs the agent decides whether they are the same model —
        the agent itself holds no opinion, and deliberately knows nothing about
        routing (see tests/test_agent_isolation.py).
        """
        self.llm = llm
        self.generation_llm = generation_llm or llm
        self.enable_tool_planning = enable_tool_planning
        self.memory = ChatMemoryManager()

    def remember(self, state: SessionState, user_message: str) -> SessionState:
        """
        Record the user's message without running any extractor.

        For turns a caller has already determined carry no extractable content —
        an acknowledgement, a deferral, small talk. The message still belongs in
        the transcript the response generator reads; it just has nothing for the
        extractors to find, and running them anyway costs a model round trip to
        confirm that.

        The agent does not decide which turns qualify. That judgement lives with
        the caller (see the semantic router), keeping this package free of any
        classification machinery.
        """
        updated = state.model_copy(deep=True)
        self.memory.add_user_message(updated.session_id, user_message)
        return updated

    def observe(
        self,
        state: SessionState,
        user_message: str,
        use_tools: Optional[bool] = None,
    ) -> SessionState:
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
            use_tools: Also let the model plan tool calls for this stage. Costs
                an extra LLM call; the extractors already cover writing fields,
                so this earns its keep when the turn calls for an action —
                selecting a vehicle, asking for one specific missing field.

        Returns:
            An updated copy of the state. The input is not mutated.
        """
        updated = state.model_copy(deep=True)
        self.memory.add_user_message(updated.session_id, user_message)
        conversation_text = self.memory.get_history_as_text(updated.session_id)

        before = snapshot(updated)
        updated = self._extract_information(updated, conversation_text)
        _record_patches(updated, before, source="extractor")

        should_use_tools = self.enable_tool_planning if use_tools is None else use_tools
        if should_use_tools:
            calls = plan_tools(self.llm, updated, conversation_text)
            if calls:
                outcome = self.use_tools(updated, calls)
                updated = outcome.state
                updated.pending_requests = outcome.requests

        return updated

    def use_tools(self, state: SessionState, calls: List[Dict[str, Any]]) -> ToolOutcome:
        """
        Run a batch of tool calls against the state.

        The dispatcher refuses tools outside the current stage's candidate set,
        so a booking cannot be recorded while the conversation is still learning
        who the customer is. Returns the results plus any requests the caller
        must act on — retrieval and stage changes are expressed as intents here
        and carried out by whoever owns those (see `stages.arbitrate`).
        """
        updated = state.model_copy(deep=True)
        before = snapshot(updated)
        results = dispatch_all(updated, calls)
        _record_patches(updated, before, source="tool")

        for result in results:
            if not result.ok:
                logger.info(f"[{updated.session_id}] tool refused: {result.message}")

        return ToolOutcome(
            state=updated,
            results=results,
            requests=[r.request for r in results if r.ok and r.request],
        )

    def respond(
        self,
        state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        propose_with_llm: bool = False,
    ) -> AgentResult:
        """
        Arbitrate the stage machine and generate the reply for an observed turn.

        Expects `state` to already carry this turn's extractions — i.e. the
        output of `observe`.

        Args:
            retrieved_cars: Candidates from the backend, if any.
            propose_with_llm: Also ask the model whether the stage is complete.
                Its answer is a *proposal*; `stages.arbitrate` still decides.
                Off by default because it costs an extra call per turn and the
                rule-based proposer covers the linear path.
        """
        updated = state.model_copy(deep=True)
        session_id = updated.session_id
        conversation_text = self.memory.get_history_as_text(session_id)

        if retrieved_cars:
            updated.matched_cars = retrieved_cars

        old_stage = updated.stage
        updated.previous_stage = old_stage.value

        if updated.stage_hold:
            # A rollback happened this turn. Advancing now would undo it
            # immediately: the constraint the customer disowned is still in
            # state, so the forward guard still passes. Hold for one turn and
            # let them state the revised value first.
            logger.info(f"[{session_id}] Stage held at {old_stage.value}: rollback in progress")
            updated.stage_hold = False
            stage_changed = False
        else:
            proposals = []
            for request in updated.pending_requests:
                if request.get("type") != "transition":
                    continue
                try:
                    target = Stage(request["stage"])
                except (KeyError, ValueError):
                    continue
                proposals.append(
                    TransitionProposal(
                        target=target,
                        source=ProposalSource.LLM,
                        reason=str(request.get("reason", "")),
                    )
                )
            updated.pending_requests = []
            if propose_with_llm:
                llm_proposal = propose_by_llm(self.llm, updated, conversation_text)
                if llm_proposal is not None:
                    proposals.append(llm_proposal)
            forward = propose_forward(updated)
            if forward is not None:
                proposals.append(forward)

            verdict = advance(updated, proposals)
            updated.stage = verdict.stage

            # A refused transition must not stall silently: the guard's reason
            # is handed to the generator so the reply asks for what is missing.
            if verdict.system_note:
                updated.system_notes = [*updated.system_notes, verdict.system_note]

            stage_changed = updated.stage != old_stage
            if stage_changed:
                logger.info(
                    f"[{session_id}] Stage transition: {old_stage.value} → {updated.stage.value} "
                    f"(proposed by {verdict.proposal.source.value})"
                )
            elif verdict.rejection:
                logger.info(f"[{session_id}] Stage held at {old_stage.value}: {verdict.rejection}")

        # Recent patches ride at the end of the prompt. The transcript window is short; this keeps
        # "the customer just changed their budget" visible even when the turn
        # that said so has scrolled out without invalidating the stable prompt prefix.
        notes = list(updated.system_notes)
        patch_summary = format_for_prompt(
            [StatePatch.from_dict(p) for p in updated.patch_log[-PROMPT_PATCH_WINDOW:]]
        )
        if patch_summary:
            notes.append(patch_summary)

        response_text = generate_response(
            self.generation_llm,
            updated.stage,
            conversation_text,
            updated.profile,
            updated.needs,
            updated.matched_cars,
            updated.reservation,
            system_notes=notes,
        )

        # Run Self-Reflection & Compliance Guard
        from src.agent.reflection import reflect_and_guard

        response_text, reflection_warnings = reflect_and_guard(
            response_text, updated.matched_cars
        )

        # Notes are per-turn instructions. Carrying them forward would keep
        # telling the model about a constraint change several turns after the
        # customer moved on.
        updated.system_notes = []

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

        # Run constraint reconciliation engine to detect hard/soft conflicts
        from src.agent.reconciliation import reconcile_constraints

        conflicts = reconcile_constraints(state)
        for conflict in conflicts:
            note = conflict.to_system_note()
            if note not in state.system_notes:
                state.system_notes.append(note)

        return state
