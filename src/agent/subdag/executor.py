"""
Executor for Sub-DAG Workflow Engine.

Executes sub-DAG nodes, handles conditional branching, collects API & decision results,
and updates SessionState.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agent.schemas import SessionState, Stage
from src.agent.subdag.context import SubDAGContext
from src.agent.subdag.graph import SubDAGGraph
from src.agent.subdag.nodes import (
    APINode,
    BaseSubDAGNode,
    ConditionNode,
    DecisionNode,
    EndNode,
    LLMNode,
    StartNode,
)

logger = logging.getLogger(__name__)


@dataclass
class SubDAGResult:
    """Execution result from running a Sub-DAG."""

    stage: Stage
    completed: bool
    executed_nodes: List[str]
    node_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    system_notes: List[str] = field(default_factory=list)


class SubDAGExecutor:
    """Executes a Sub-DAG workflow graph for a given stage."""

    def __init__(self, stage: Stage, definition: Dict[str, Any]):
        self.stage = stage
        self.definition = definition
        self.graph = SubDAGGraph(
            nodes=definition.get("nodes", []),
            edges=definition.get("edges", []),
        )

    def _create_node_executor(self, node_def: Dict[str, Any]) -> BaseSubDAGNode:
        """Instantiate node executor instance from definition."""
        node_id = node_def["id"]
        node_type = node_def.get("type", "start")
        config = node_def.get("data", {})

        if node_type == "start":
            return StartNode(node_id, node_type, config)
        elif node_type == "end":
            return EndNode(node_id, node_type, config)
        elif node_type == "condition":
            return ConditionNode(node_id, node_type, config)
        elif node_type == "api":
            return APINode(node_id, node_type, config)
        elif node_type == "llm":
            return LLMNode(node_id, node_type, config)
        elif node_type == "decision":
            return DecisionNode(node_id, node_type, config)
        else:
            # Fallback
            return StartNode(node_id, node_type, config)

    def run(self, context: SubDAGContext) -> SubDAGResult:
        """Run the Sub-DAG from entry node to completion."""
        # Find trigger/start node
        start_nodes = [n for n in self.graph.nodes.values() if n.get("type") == "start"]
        if not start_nodes:
            start_node_id = self.graph.get_topo_sort()[0] if self.graph.nodes else None
        else:
            start_node_id = start_nodes[0]["id"]

        if not start_node_id:
            return SubDAGResult(
                stage=self.stage,
                completed=True,
                executed_nodes=[],
            )

        executed_node_ids: List[str] = []
        curr_node_ids = [start_node_id]
        completed = False

        while curr_node_ids:
            next_node_ids = []
            for node_id in curr_node_ids:
                if node_id in executed_node_ids:
                    continue

                node_def = self.graph.get_node(node_id)
                if not node_def:
                    continue

                executor = self._create_node_executor(node_def)
                outputs, handle_id = executor.execute(context)
                context.set_node_output(node_id, outputs)
                executed_node_ids.append(node_id)

                if node_def.get("type") == "end":
                    completed = True

                # Determine next targets based on edge handle
                targets = self.graph.get_next_nodes(node_id, handle_id)
                next_node_ids.extend(targets)

            curr_node_ids = list(dict.fromkeys(next_node_ids))  # preserve order & deduplicate

        # Store subdag execution summary into session_state.subdag_state
        context.session_state.subdag_state[self.stage.value] = {
            "completed": completed,
            "executed_nodes": executed_node_ids,
            "outputs": context.node_outputs,
        }

        # Inject system notes gathered during sub-dag execution
        for note in context.system_notes:
            if note not in context.session_state.system_notes:
                context.session_state.system_notes.append(note)

        return SubDAGResult(
            stage=self.stage,
            completed=completed,
            executed_nodes=executed_node_ids,
            node_outputs=context.node_outputs,
            system_notes=context.system_notes,
        )


def run_stage_subdag(
    state: SessionState,
    user_message: str = "",
) -> SessionState:
    """
    Run sub-DAG workflow for the active stage if one is registered.
    Returns the updated SessionState.
    """
    from src.agent.subdag.stage_dags import get_stage_subdag

    executor = get_stage_subdag(state.stage)
    if not executor:
        return state

    context = SubDAGContext(session_state=state, user_message=user_message)
    executor.run(context)
    return state
