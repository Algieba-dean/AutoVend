"""
Subagent Sandbox Dispatcher — Routes domain tasks to expert subagents and collects conclusions.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agent.subagents.base import BaseSubagent, SubagentResult
from src.agent.subagents.comparison import ModelComparisonSubagent
from src.agent.subagents.finance import FinancialCalculatorSubagent
from src.agent.subagents.test_drive import TestDriveSchedulerSubagent

logger = logging.getLogger(__name__)


class SubagentDispatcher:
    """Dispatches specialized sub-tasks into domain expert subagent sandboxes."""

    def __init__(self):
        self._subagents: Dict[str, BaseSubagent] = {}
        self._init_subagents()

    def _init_subagents(self) -> None:
        self.register(ModelComparisonSubagent())
        self.register(FinancialCalculatorSubagent())
        self.register(TestDriveSchedulerSubagent())

    def register(self, subagent: BaseSubagent) -> None:
        self._subagents[subagent.name] = subagent

    def dispatch(
        self, subagent_name: str, task: str, context: Dict[str, Any]
    ) -> Optional[SubagentResult]:
        subagent = self._subagents.get(subagent_name)
        if not subagent:
            logger.warning(f"Subagent '{subagent_name}' not found.")
            return None
        try:
            return subagent.run(task, context)
        except Exception as exc:
            logger.error(f"Error running subagent '{subagent_name}': {exc}")
            return None

    def auto_dispatch(self, user_message: str, context: Dict[str, Any]) -> List[SubagentResult]:
        """Automatically dispatch relevant expert subagents based on conversation context."""
        results: List[SubagentResult] = []
        msg = user_message.lower()

        # 1. Comparison subagent triggers
        comparison_keywords = [
            "对比", "比一比", "区别", "哪个好", "特斯拉", "海豹", "海豚", "海鸥",
            "唐", "汉", "宋", "秦", "元", "model", "suv"
        ]
        if any(kw in user_message or kw in msg for kw in comparison_keywords):
            res = self.dispatch("model_comparison_subagent", user_message, context)
            if res and res.success:
                results.append(res)

        # 2. Finance subagent triggers
        finance_keywords = ["首付", "月供", "分期", "贷款", "金融", "利息", "免息", "多少钱", "预算", "置换"]
        if any(kw in user_message for kw in finance_keywords):
            res = self.dispatch("financial_calculator_subagent", user_message, context)
            if res and res.success:
                results.append(res)

        # 3. Test drive scheduler triggers
        test_drive_keywords = ["试驾", "体验", "开一下", "排期", "预约", "试乘"]
        if any(kw in user_message for kw in test_drive_keywords):
            res = self.dispatch("test_drive_scheduler_subagent", user_message, context)
            if res and res.success:
                results.append(res)

        return results
