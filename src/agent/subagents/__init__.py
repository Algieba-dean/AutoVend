"""
Domain Expert Subagents Package (src/agent/subagents/).

Specialized domain subagents running in sandboxes:
- ModelComparisonSubagent (BYD Dynasty vs Ocean and competitor benchmark)
- FinancialCalculatorSubagent (Auto loan, down payment, installment, subsidies)
- TestDriveSchedulerSubagent (Showroom in-store test drive scheduling and routes)
- SubagentDispatcher (Routes and aggregates expert conclusions)
"""

from src.agent.subagents.base import BaseSubagent, SubagentResult
from src.agent.subagents.comparison import ModelComparisonSubagent
from src.agent.subagents.dispatcher import SubagentDispatcher
from src.agent.subagents.finance import FinancialCalculatorSubagent
from src.agent.subagents.test_drive import TestDriveSchedulerSubagent

__all__ = [
    "BaseSubagent",
    "SubagentResult",
    "ModelComparisonSubagent",
    "FinancialCalculatorSubagent",
    "TestDriveSchedulerSubagent",
    "SubagentDispatcher",
]
