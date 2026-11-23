"""
Trajectory-Level Evaluation for AutoVend LangGraph Agent (src/eval/trajectory_eval.py).

Evaluates not just final reply text, but the exact LangGraph decision trajectory:
- Chitchat/greeting turns MUST NOT trigger `retrieve_vehicles`
- Constraint-change turns MUST trigger rollback / re-retrieval
- Price/monthly-payment queries MUST invoke `calculate_drive_away_price` instead of mental math
- Negative exclusions MUST purge rejected models/powertrains from `matched_cars`
- Policy-as-Code violations MUST block unauthorized tool calls
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, ToolMessage

from src.agent.schemas import SessionState


@dataclass
class TrajectoryScenario:
    name: str
    user_message: str
    initial_state: Optional[SessionState] = None
    retrieved_cars: Optional[List[Dict[str, Any]]] = None
    skip_extraction: bool = False
    required_nodes: List[str] = field(default_factory=list)
    forbidden_nodes: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    forbidden_powertrains: List[str] = field(default_factory=list)
    forbidden_models: List[str] = field(default_factory=list)
    expect_interrupted: Optional[bool] = None
    expect_policy_blocked: bool = False


@dataclass
class TrajectoryEvalResult:
    scenario_name: str
    passed: bool
    executed_nodes: List[str] = field(default_factory=list)
    called_tools: List[str] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    final_state: Optional[SessionState] = None
    response_text: str = ""


def evaluate_trajectory(
    agent: Any,
    scenario: TrajectoryScenario,
    session_id: Optional[str] = None,
) -> TrajectoryEvalResult:
    """Execute `scenario` through `agent.graph.stream(..., stream_mode='updates')` and assert trajectory invariants."""
    sid = session_id or f"traj_{scenario.name}"
    config = agent._build_run_config(sid, scenario.initial_state)
    graph_input: Dict[str, Any] = {
        "session_id": sid,
        "user_message": scenario.user_message,
        "skip_extraction": scenario.skip_extraction,
        "retrieved_cars": scenario.retrieved_cars,
    }
    if scenario.initial_state is not None:
        graph_input["session_state"] = scenario.initial_state

    executed_nodes: List[str] = []
    called_tools: List[str] = []
    blocked_tools: List[str] = []
    interrupted = False
    latest_state: Optional[SessionState] = scenario.initial_state
    response_text = ""

    for update in agent.graph.stream(graph_input, config=config, stream_mode="updates"):
        if not isinstance(update, dict):
            continue
        if "__interrupt__" in update:
            interrupted = True
            continue
        for node_name, payload in update.items():
            executed_nodes.append(node_name)
            if not isinstance(payload, dict):
                continue
            if "session_state" in payload and payload["session_state"] is not None:
                latest_state = payload["session_state"]
            if "response_text" in payload and payload["response_text"]:
                response_text = payload["response_text"]
            for msg in payload.get("messages") or []:
                if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                    for tc in msg.tool_calls:
                        t_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                        if t_name:
                            called_tools.append(t_name)
                elif isinstance(msg, ToolMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    if "POLICY_VIOLATION" in content:
                        t_name = getattr(msg, "name", "") or "unknown"
                        blocked_tools.append(t_name)

    failures: List[str] = []
    for req_node in scenario.required_nodes:
        if req_node not in executed_nodes:
            failures.append(f"missing required node '{req_node}' (executed={executed_nodes})")

    for forb_node in scenario.forbidden_nodes:
        if forb_node in executed_nodes:
            failures.append(f"executed forbidden node '{forb_node}' (executed={executed_nodes})")

    for req_tool in scenario.required_tools:
        if req_tool not in called_tools:
            failures.append(f"missing required tool call '{req_tool}' (called={called_tools})")

    if scenario.expect_interrupted is not None and interrupted != scenario.expect_interrupted:
        failures.append(f"expected interrupted={scenario.expect_interrupted}, got {interrupted}")

    if scenario.expect_policy_blocked and not blocked_tools:
        failures.append("expected at least one tool call blocked by Policy-as-Code, got none")

    if latest_state is not None and latest_state.matched_cars:
        for car in latest_state.matched_cars:
            cm = str(car.get("car_model") or "").lower()
            cp = str(car.get("powertrain_type") or car.get("power_type") or "").lower()
            for fp in scenario.forbidden_powertrains:
                if fp.lower() in cp:
                    failures.append(f"excluded powertrain '{fp}' leaked into matched_cars: {car.get('car_model')}")
            for fm in scenario.forbidden_models:
                if fm.lower() in cm:
                    failures.append(f"excluded model '{fm}' leaked into matched_cars: {car.get('car_model')}")

    return TrajectoryEvalResult(
        scenario_name=scenario.name,
        passed=len(failures) == 0,
        executed_nodes=executed_nodes,
        called_tools=called_tools,
        blocked_tools=blocked_tools,
        failures=failures,
        final_state=latest_state,
        response_text=response_text,
    )
