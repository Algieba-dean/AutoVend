"""
SalesAgent — Unified public facade over `LangGraphSalesAgent`.

Processes conversation turns via the compiled LangGraph `StateGraph`:
    AgentResult = SalesAgent.process(AgentInput)
    AgentResult = SalesAgent.run_graph_turn(state, user_message, ...)
    AgentResult = await SalesAgent.arun_graph_turn(state, user_message, ...)

Has NO backend dependencies (no FastAPI, no storage, no ChromaDB, no LlamaIndex).
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from src.agent.circuit_breaker import AgentCircuitBreaker, default_circuit_breaker
from src.agent.graph.state import format_messages_as_text
from src.agent.langgraph_agent import LangGraphSalesAgent
from src.agent.plugins.pipeline import AgentPluginPipeline
from src.agent.schemas import AgentInput, AgentResult, SessionState

logger = logging.getLogger(__name__)


class SalesAgent:
    """
    Stateful automotive sales agent backed by `LangGraphSalesAgent`.

    Preserves the `SalesAgent` public API (`process`, `run_graph_turn`,
    `arun_graph_turn`, `astream_graph_turn`, `clear_session`, `get_history_text`)
    with a single LangGraph + LangChain execution path and checkpointer.
    """

    def __init__(
        self,
        llm: Any,
        generation_llm: Optional[Any] = None,
        auditor_llm: Optional[Any] = None,
        retriever: Optional[Any] = None,
        checkpointer: Optional[Any] = None,
        circuit_breaker: Optional[AgentCircuitBreaker] = None,
        plugin_pipeline: Optional[AgentPluginPipeline] = None,
        use_unified_extraction: bool = True,
    ):
        self.llm = llm
        self.generation_llm = generation_llm or llm
        self.auditor_llm = auditor_llm
        self.retriever = retriever
        self.checkpointer = checkpointer
        self.circuit_breaker = circuit_breaker or AgentCircuitBreaker()
        self.plugin_pipeline = plugin_pipeline or AgentPluginPipeline()
        self.use_unified_extraction = use_unified_extraction
        self._langgraph_agent: Optional[LangGraphSalesAgent] = None

    @property
    def langgraph(self) -> LangGraphSalesAgent:
        """Lazily constructed `LangGraphSalesAgent` backed by LangGraph + LangChain."""
        if self._langgraph_agent is None:
            self._langgraph_agent = LangGraphSalesAgent(
                llm=self.llm,
                generation_llm=self.generation_llm,
                auditor_llm=self.auditor_llm,
                retriever=self.retriever,
                checkpointer=self.checkpointer,
                circuit_breaker=self.circuit_breaker,
                plugin_pipeline=self.plugin_pipeline,
                use_unified_extraction=self.use_unified_extraction,
            )
        return self._langgraph_agent

    def run_graph_turn(
        self,
        state: SessionState,
        user_message: str,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_extraction: bool = False,
        propose_with_llm: bool = False,
    ) -> AgentResult:
        """Execute a full conversation turn synchronously via the LangGraph StateGraph."""
        return self.langgraph.invoke_turn(
            session_id=state.session_id,
            user_message=user_message,
            session_state=state,
            retrieved_cars=retrieved_cars,
            skip_extraction=skip_extraction,
            propose_with_llm=propose_with_llm,
        )

    async def arun_graph_turn(
        self,
        state: SessionState,
        user_message: str,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_extraction: bool = False,
        propose_with_llm: bool = False,
    ) -> AgentResult:
        """Execute a full conversation turn asynchronously via the LangGraph StateGraph."""
        return await self.langgraph.ainvoke_turn(
            session_id=state.session_id,
            user_message=user_message,
            session_state=state,
            retrieved_cars=retrieved_cars,
            skip_extraction=skip_extraction,
            propose_with_llm=propose_with_llm,
        )

    async def astream_graph_turn(
        self,
        state: SessionState,
        user_message: str,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_extraction: bool = False,
        propose_with_llm: bool = False,
    ) -> AsyncGenerator[Tuple[str, Any], None]:
        """Stream a conversation turn via LangGraph + LangChain `.astream()`."""
        async for ev in self.langgraph.astream_turn(
            session_id=state.session_id,
            user_message=user_message,
            session_state=state,
            retrieved_cars=retrieved_cars,
            skip_extraction=skip_extraction,
            propose_with_llm=propose_with_llm,
        ):
            yield ev

    def process(self, agent_input: AgentInput) -> AgentResult:
        """Process one conversation turn synchronously through the LangGraph StateGraph."""
        return self.run_graph_turn(
            state=agent_input.session_state,
            user_message=agent_input.user_message,
            retrieved_cars=agent_input.retrieved_cars or None,
        )

    def clear_session(self, session_id: str) -> None:
        """Clear circuit breaker state and LangGraph checkpointer thread for a session."""
        self.circuit_breaker.reset_session(session_id)
        default_circuit_breaker.reset_session(session_id)
        if self._langgraph_agent is not None:
            self._langgraph_agent.clear_session(session_id)

    def get_history_text(self, session_id: str) -> str:
        """Get formatted conversation history directly from the LangGraph checkpointer."""
        try:
            snap = self.langgraph.get_graph_state(session_id)
            if snap is not None and getattr(snap, "values", None):
                return format_messages_as_text(snap.values.get("messages") or [])
        except Exception as exc:
            logger.debug(f"[{session_id}] get_history_text failed: {exc}")
        return ""
