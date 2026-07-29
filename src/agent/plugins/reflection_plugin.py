"""
Reflection & Guardrail Plugin (src/agent/plugins/reflection_plugin.py).
"""

from typing import Any, Dict

from src.agent.plugins.base import BaseAgentPlugin
from src.agent.reflection import reflect_and_guard


class ReflectionGuardPlugin(BaseAgentPlugin):
    """Middleware plugin validating generated response against hallucination & compliance rules."""

    @property
    def name(self) -> str:
        return "ReflectionGuardPlugin"

    def process_before_response(self, state: Any, context: Dict[str, Any]) -> None:
        pass

    def process_after_response(self, response_text: str, context: Dict[str, Any]) -> str:
        """Reflect and guard response text against ground truth matched cars."""
        matched_cars = context.get("matched_cars", [])
        guarded_text, issues = reflect_and_guard(response_text, matched_cars=matched_cars)
        if issues:
            context["reflection_issues"] = issues
        return guarded_text
