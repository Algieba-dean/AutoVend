"""
LangGraph state schema and projection helpers (`src/agent/graph/state.py`).
"""

import re
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langgraph.graph.message import add_messages

from src.agent.events import (
    AnyDialogueEvent,
    _append_events,
    project_state_incremental,
)
from src.agent.schemas import SessionState, Stage

PROMPT_PATCH_WINDOW = 6
MAX_TOOL_ITERATIONS = 3
MAX_CRAG_RETRIES = 2
MAX_AUDIT_RETRIES = 1
OPEN_THINK_RE = re.compile(r"<(think|thought|reasoning)>", re.IGNORECASE)


class AgentGraphState(TypedDict, total=False):
    """LangGraph state schema for a single AutoVend conversation thread."""

    messages: Annotated[List[AnyMessage], add_messages]
    events: Annotated[List[AnyDialogueEvent], _append_events]
    base_session_state: Optional[SessionState]
    session_id: str
    user_message: str
    safe_message: str
    skip_extraction: bool
    session_state: SessionState
    retrieved_cars: Optional[List[Dict[str, Any]]]
    stage_changed: bool
    notes: List[str]
    plugin_context: Dict[str, Any]
    conversation_text: str
    propose_with_llm: bool
    response_text: str
    tool_iterations: int
    # CRAG retrieval loop & Evidence Ledger & Anti-hallucination audit
    topic_intent: str
    retrieval_retries: int
    retrieval_query_override: Optional[str]
    retrieval_relaxed_constraints: Optional[Dict[str, Any]]
    retrieval_grade_passed: bool
    retrieval_grade_reason: str
    evidence_anchors: List[Dict[str, Any]]
    audit_retries: int
    audit_passed: bool
    critic_feedback: Optional[str]
    artifact_bundle_version: str
    # Budget guard, NBA, HITL, trajectory trace, policy arbitration
    step_count: int
    budget_exhausted: bool
    degrade_reason: str
    next_best_action: str
    hitl_triggered: bool
    hitl_decision: Optional[Dict[str, Any]]
    injection_detected: bool
    policy_veto_log: List[str]
    last_extraction_confidence: Optional[float]
    last_ambiguous_fields: List[str]
    execution_trace: List[str]
    proposed_stage: Optional[Stage]
    proposed_stage_reason: str
    _state_snapshot_index: int
    # Voice-First low-latency fields
    voice_mode: bool
    active_skill: str
    active_skill_prompt: str
    active_skill_tools: List[str]
    skill_needs_retrieval: bool
    direct_response_text: Optional[str]
    async_extraction_scheduled: bool
    llm_call_count: int


def format_messages_as_text(messages: List[AnyMessage], max_turns: int = 20) -> str:
    """Render LangChain message history as a plain transcript for prompts/extractors."""
    recent = messages[-max_turns:] if len(messages) > max_turns else messages
    lines: List[str] = []
    for msg in recent:
        if isinstance(msg, ToolMessage):
            continue
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None) and not msg.content:
            continue
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def project_current_state(state: AgentGraphState) -> SessionState:
    """Project current SessionState from event log or snapshot fallback."""
    events = state.get("events") or []
    base_sess = state.get("base_session_state")
    if events:
        snap_sess = state.get("session_state")
        snap_idx = int(state.get("_state_snapshot_index", 0) or 0)
        projected, _ = project_state_incremental(
            events,
            snapshot_state=snap_sess,
            snapshot_index=snap_idx,
            base_state=base_sess,
        )
        return projected
    sess = state.get("session_state")
    if sess is not None:
        return sess.model_copy(deep=True)
    return SessionState(session_id=state.get("session_id") or "default")
