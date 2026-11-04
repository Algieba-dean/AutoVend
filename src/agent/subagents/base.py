"""
Subagent base interfaces and result schemas.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SubagentResult:
    """Outcome produced by an expert subagent sandbox execution."""

    success: bool
    subagent_name: str
    conclusion: str
    structured_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "subagent_name": self.subagent_name,
            "conclusion": self.conclusion,
            "structured_data": self.structured_data,
        }


class BaseSubagent(ABC):
    """Abstract base class for domain expert subagents."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, task: str, context: Dict[str, Any]) -> SubagentResult:
        """Execute domain expert task in a sandboxed context and return conclusion only."""
        raise NotImplementedError
