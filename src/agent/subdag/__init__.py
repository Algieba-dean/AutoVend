"""
Sub-DAG workflow engine for complex local stage execution within top-level Sales FSM.

Provides DAG graph topology, execution context, API nodes, condition nodes,
and decision nodes inspired by tgo workflow engine architecture.
"""

from src.agent.subdag.context import SubDAGContext
from src.agent.subdag.executor import SubDAGExecutor, SubDAGResult, run_stage_subdag
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
from src.agent.subdag.stage_dags import (
    create_car_selection_dag,
    create_reservation_4s_dag,
    get_stage_subdag,
)

__all__ = [
    "SubDAGContext",
    "SubDAGGraph",
    "SubDAGExecutor",
    "SubDAGResult",
    "run_stage_subdag",
    "BaseSubDAGNode",
    "StartNode",
    "EndNode",
    "ConditionNode",
    "APINode",
    "LLMNode",
    "DecisionNode",
    "create_car_selection_dag",
    "create_reservation_4s_dag",
    "get_stage_subdag",
]
