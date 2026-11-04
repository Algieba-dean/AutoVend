"""
Governance Hooks definition and base interfaces.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from src.governance.context import GovernanceContext


class HookType(str, Enum):
    """Lifecycle hook points across the governance pipeline."""

    SESSION_START = "session_start"
    PRE_OBSERVE = "pre_observe"
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    STAGE_TRANSITION = "stage_transition"
    POST_GENERATE = "post_generate"
    SESSION_END = "session_end"


class BaseGovernanceHook(ABC):
    """Base class for all governance aspect hooks."""

    def __init__(self, name: Optional[str] = None, priority: int = 100):
        self.name = name or self.__class__.__name__
        self.priority = priority

    @property
    @abstractmethod
    def hook_type(self) -> HookType:
        """The lifecycle point at which this hook attaches."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, context: GovernanceContext) -> GovernanceContext:
        """Execute the governance hook logic and return the updated context."""
        raise NotImplementedError
