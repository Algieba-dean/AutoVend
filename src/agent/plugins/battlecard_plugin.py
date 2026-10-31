"""
Competitor Battlecard Plugin (src/agent/plugins/battlecard_plugin.py).
"""

from typing import Any, Dict

from src.agent.battlecards import match_battlecards
from src.agent.plugins.base import BaseAgentPlugin


class BattlecardPlugin(BaseAgentPlugin):
    """Middleware plugin matching competitor mentions to inject selling cards."""

    @property
    def name(self) -> str:
        return "BattlecardPlugin"

    def process_before_response(self, state: Any, context: Dict[str, Any]) -> None:
        """Check conversation for competitor mentions and inject battlecard notes."""
        user_input = context.get("user_input", "") or context.get("conversation_text", "")
        matched_cards = match_battlecards(user_input)
        if matched_cards:
            if not hasattr(state, "system_notes") or state.system_notes is None:
                state.system_notes = []
            notes = [
                b.to_system_note() if hasattr(b, "to_system_note") else str(b)
                for b in matched_cards
            ]
            for note in notes:
                if note not in state.system_notes:
                    state.system_notes.append(note)
            context["battlecards_matched"] = len(matched_cards)

    def process_after_response(self, response_text: str, context: Dict[str, Any]) -> str:
        return response_text
