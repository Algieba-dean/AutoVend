"""
Truth Debiaser & Anti-Marketing Fluff Plugin (src/agent/plugins/truth_plugin.py).

Detects marketing fluff inquiries, safety controversies (brake/battery), real-world range/charging gaps,
and MIIT specification requests, injecting unvarnished objective consumer guidance into Agent system notes.
"""

from typing import Any, Dict

from src.agent.plugins.base import BaseAgentPlugin
from src.core.truth_engine import TruthEngineFacade


class TruthDebiaserPlugin(BaseAgentPlugin):
    """Middleware plugin injecting marketing debiasing and consumer truth guidance."""

    @property
    def name(self) -> str:
        return "TruthDebiaserPlugin"

    def process_before_response(self, state: Any, context: Dict[str, Any]) -> None:
        """Inspect conversation context and inject truth deconstruction notes."""
        user_input = context.get("user_input", "")
        if not user_input:
            return

        facade = TruthEngineFacade.get_instance()
        detected_model = facade.extract_model_name_from_text(user_input)
        car_model = detected_model
        if not car_model and hasattr(state, "matched_cars") and state.matched_cars:
            first_car = state.matched_cars[0]
            if isinstance(first_car, dict):
                car_model = first_car.get("car_model")

        truth_note = facade.generate_truth_sales_note(user_input, car_model=car_model)
        if truth_note:
            if not hasattr(state, "system_notes") or state.system_notes is None:
                state.system_notes = []
            if truth_note not in state.system_notes:
                state.system_notes.append(truth_note)
            context["truth_debiasing_triggered"] = True

    def process_after_response(self, response_text: str, context: Dict[str, Any]) -> str:
        return response_text
