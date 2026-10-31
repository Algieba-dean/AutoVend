"""
OEM Automotive Proprietary Terminology Plugin (src/agent/plugins/terminology_plugin.py).

Detects OEM proprietary technologies (e.g. BYD DiSus/云辇, Xiaomi V800/800V, Huawei Tuling/途灵,
Tesla 4680, Li Auto Magic Carpet/魔毯) in customer input and injects objective technical definitions,
differentiation points, and tactical sales guidance into agent system notes.
"""

from typing import Any, Dict

from src.agent.plugins.base import BaseAgentPlugin
from src.core.terminology import AutomotiveKnowledgeGraph


class TerminologyPlugin(BaseAgentPlugin):
    """Middleware plugin resolving proprietary terminology and enriching conversational advice."""

    @property
    def name(self) -> str:
        return "TerminologyPlugin"

    def process_before_response(self, state: Any, context: Dict[str, Any]) -> None:
        """Check customer input for OEM proprietary terms and inject resolution notes."""
        user_input = context.get("user_input", "")
        conv_text = context.get("conversation_text", "")
        if not user_input and not conv_text:
            return

        kg = AutomotiveKnowledgeGraph.get_instance()
        query_text = user_input or conv_text
        matched = kg.extract_terms(query_text)
        sales_note = kg.generate_system_sales_note(query_text, context=conv_text)
        if sales_note:
            if not hasattr(state, "system_notes") or state.system_notes is None:
                state.system_notes = []
            if sales_note not in state.system_notes:
                state.system_notes.append(sales_note)
        if matched:
            context["terminology_matched"] = len(matched)
            context["matched_technologies"] = [m.entity.name for m in matched]

    def process_after_response(self, response_text: str, context: Dict[str, Any]) -> str:
        return response_text
