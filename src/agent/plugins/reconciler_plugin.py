"""
Constraint Reconciler Plugin (src/agent/plugins/reconciler_plugin.py).
"""

from typing import Any, Dict
from src.agent.plugins.base import BaseAgentPlugin
from src.agent.reconciliation import reconcile_constraints


class ConstraintReconcilerPlugin(BaseAgentPlugin):
    """Middleware plugin for detecting and resolving user constraint conflicts."""

    @property
    def name(self) -> str:
        return "ConstraintReconcilerPlugin"

    def process_before_response(self, state: Any, context: Dict[str, Any]) -> None:
        """Detect conflicts between explicit profile/needs and inject system note."""
        conflicts, note = reconcile_constraints(state)
        if note:
            state.system_notes.append(note)
            context["conflicts_detected"] = len(conflicts)

    def process_after_response(self, response_text: str, context: Dict[str, Any]) -> str:
        return response_text
