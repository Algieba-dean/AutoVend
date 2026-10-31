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
        """Detect conflicts between explicit profile/needs and inject system notes."""
        conflicts = reconcile_constraints(state)
        if conflicts:
            if not hasattr(state, "system_notes") or state.system_notes is None:
                state.system_notes = []
            for conflict in conflicts:
                note = (
                    conflict.to_system_note()
                    if hasattr(conflict, "to_system_note")
                    else str(conflict)
                )
                if note and note not in state.system_notes:
                    state.system_notes.append(note)
            context["conflicts_detected"] = len(conflicts)

    def process_after_response(self, response_text: str, context: Dict[str, Any]) -> str:
        return response_text
