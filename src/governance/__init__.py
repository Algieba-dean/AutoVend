"""
Hook & Governance Layer (AOP 防线).

Provides decoupled lifecycle hooks for Session, PreObserve, Tool Use, Stage Transition,
Compliance, and PII Restitution.
"""

from src.governance.context import GovernanceContext
from src.governance.engine import (
    GovernanceEngine,
    get_governance_engine,
    set_governance_engine,
)
from src.governance.hooks import BaseGovernanceHook, HookType
from src.governance.post_generate_hook import PostGenerateHook
from src.governance.post_tool_use_hook import PostToolUseHook
from src.governance.pre_observe_hook import PreObserveHook
from src.governance.pre_tool_use_hook import PreToolUseHook
from src.governance.session_hooks import SessionEndHook, SessionStartHook
from src.governance.stage_transition_hook import StageTransitionHook

__all__ = [
    "GovernanceContext",
    "GovernanceEngine",
    "get_governance_engine",
    "set_governance_engine",
    "HookType",
    "BaseGovernanceHook",
    "SessionStartHook",
    "PreObserveHook",
    "PreToolUseHook",
    "PostToolUseHook",
    "StageTransitionHook",
    "PostGenerateHook",
    "SessionEndHook",
]
