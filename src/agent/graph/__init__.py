"""
Modular LangGraph Sales Agent subpackage (`src/agent/graph`).

Splits the compiled StateGraph into single-responsibility modules:
- `state.py`: AgentGraphState TypedDict, constants, and state projection helpers
- `routing_nodes.py`: guard_and_route, extract_slots, arbitrate_stage, hitl_handoff
- `retrieval_nodes.py`: retrieve_vehicles, grade_retrieval, rewrite_query
- `generation_nodes.py`: run_plugins_and_subdag, generate_reply, tools, audit_hallucination, safe_degrade
- `streaming.py`: native LangGraph stream_mode=["messages", "updates"] handler
"""

from src.agent.graph.state import (
    MAX_AUDIT_RETRIES,
    MAX_CRAG_RETRIES,
    MAX_TOOL_ITERATIONS,
    PROMPT_PATCH_WINDOW,
    AgentGraphState,
    format_messages_as_text,
    project_current_state,
)

__all__ = [
    "AgentGraphState",
    "PROMPT_PATCH_WINDOW",
    "MAX_TOOL_ITERATIONS",
    "MAX_CRAG_RETRIES",
    "MAX_AUDIT_RETRIES",
    "format_messages_as_text",
    "project_current_state",
]
