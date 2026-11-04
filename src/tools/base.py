"""
Base abstractions and types for the decoupled Tool Execution Layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolExecutionContext:
    """Contextual metadata passed into tool executions."""

    session_id: str = ""
    trace_id: str = ""
    user_role: str = "customer"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionResult:
    """Standardized result returned by tool executions."""

    ok: bool
    tool_name: str
    output: Any = None
    message: str = ""
    transaction_id: Optional[str] = None
    can_rollback: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "tool_name": self.tool_name,
            "output": self.output,
            "message": self.message,
            "transaction_id": self.transaction_id,
            "can_rollback": self.can_rollback,
            "metadata": self.metadata,
        }


class BaseTool(ABC):
    """Abstract base class for all tools in the execution layer."""

    name: str = ""
    description: str = ""
    parameters_schema: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, args: Dict[str, Any], context: ToolExecutionContext) -> ToolExecutionResult:
        """Execute the tool with given arguments and context."""
        raise NotImplementedError

    def rollback(self, transaction_id: str, context: ToolExecutionContext) -> bool:
        """
        Reverse state modifications made by a previous execution of this tool.
        Returns True if rollback succeeded, False if unsupported or failed.
        """
        return False
