"""
Execution Context for Sub-DAG Workflow Engine.

Carries session state, user input, node outputs, and helper methods for variable resolution.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.agent.schemas import SessionState


class SubDAGContext:
    """Context object passed through Sub-DAG node execution."""

    def __init__(
        self,
        session_state: SessionState,
        user_message: str = "",
        node_outputs: Optional[Dict[str, Dict[str, Any]]] = None,
        variables: Optional[Dict[str, Any]] = None,
    ):
        self.session_state = session_state
        self.user_message = user_message
        self.node_outputs = node_outputs or {}
        self.variables = variables or {}
        self.system_notes: List[str] = []

    def set_node_output(self, node_id: str, output: Dict[str, Any]) -> None:
        """Record output from a node execution."""
        self.node_outputs[node_id] = output

    def get_variable(self, path: str, default: Any = None) -> Any:
        """
        Get a variable value by dot-notation path or expression.
        Examples: 'profile.name', 'matched_cars[0].brand', 'node_outputs.fetch_specs.body'
        """
        if not path:
            return default

        # Root search dicts
        root_data = {
            "session_state": self.session_state.model_dump(),
            "profile": self.session_state.profile.model_dump(),
            "needs": self.session_state.needs.model_dump(),
            "matched_cars": self.session_state.matched_cars,
            "reservation": self.session_state.reservation.model_dump(),
            "user_message": self.user_message,
            "node_outputs": self.node_outputs,
            "variables": self.variables,
            "subdag_state": self.session_state.subdag_state,
        }

        # Also add direct node_outputs keys for convenience
        for k, v in self.node_outputs.items():
            root_data[k] = v

        try:
            curr: Any = root_data
            tokens = re.split(r'\.|\[|\]', path)
            tokens = [t for t in tokens if t != '']

            for token in tokens:
                if isinstance(curr, dict):
                    if token in curr:
                        curr = curr[token]
                    else:
                        return default
                elif isinstance(curr, list):
                    try:
                        idx = int(token)
                        if 0 <= idx < len(curr):
                            curr = curr[idx]
                        else:
                            return default
                    except ValueError:
                        return default
                elif hasattr(curr, token):
                    curr = getattr(curr, token)
                else:
                    return default

            return curr
        except Exception:
            return default

    def resolve_template(self, template: str) -> str:
        """
        Resolve {{var.path}} template tags in string.
        """
        if not isinstance(template, str) or "{{" not in template:
            return template

        def _replacer(match: re.Match) -> str:
            var_path = match.group(1).strip()
            val = self.get_variable(var_path, default="")
            return str(val) if val is not None else ""

        return re.sub(r"\{\{(.*?)\}\}", _replacer, template)
