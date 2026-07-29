"""
Agent Plugin Pipeline Manager (src/agent/plugins/pipeline.py).

Orchestrates execution of pre-response and post-response agent plugins in a clean pipeline.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agent.plugins.base import BaseAgentPlugin
from src.agent.plugins.battlecard_plugin import BattlecardPlugin
from src.agent.plugins.reconciler_plugin import ConstraintReconcilerPlugin
from src.agent.plugins.reflection_plugin import ReflectionGuardPlugin

logger = logging.getLogger(__name__)


class AgentPluginPipeline:
    """Manager executing ordered agent middleware plugins."""

    def __init__(self, plugins: Optional[List[BaseAgentPlugin]] = None):
        if plugins is None:
            self.plugins: List[BaseAgentPlugin] = [
                ConstraintReconcilerPlugin(),
                BattlecardPlugin(),
                ReflectionGuardPlugin(),
            ]
        else:
            self.plugins = plugins

    def run_before_response(self, state: Any, context: Dict[str, Any]) -> None:
        """Run all pre-response plugins."""
        for plugin in self.plugins:
            try:
                plugin.process_before_response(state, context)
            except Exception as e:
                logger.warning(f"Plugin {plugin.name} pre-processing warning: {e}")

    def run_after_response(self, response_text: str, context: Dict[str, Any]) -> str:
        """Run all post-response plugins sequentially."""
        current_text = response_text
        for plugin in self.plugins:
            try:
                current_text = plugin.process_after_response(current_text, context)
            except Exception as e:
                logger.warning(f"Plugin {plugin.name} post-processing warning: {e}")
        return current_text
