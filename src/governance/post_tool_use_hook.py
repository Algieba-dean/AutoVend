"""
PostToolUse Hook — Transaction snapshotting, rollback tracking, and audit logging.
"""

import logging

from src.governance.context import GovernanceContext
from src.governance.hooks import BaseGovernanceHook, HookType
from src.privacy.security_logger import security_audit_logger

logger = logging.getLogger(__name__)


class PostToolUseHook(BaseGovernanceHook):
    """Governs tool execution outcomes: captures transaction snapshots and registers audit trails."""

    def __init__(self, name: str = "PostToolUseHook", priority: int = 30):
        super().__init__(name=name, priority=priority)

    @property
    def hook_type(self) -> HookType:
        return HookType.POST_TOOL_USE

    def execute(self, context: GovernanceContext) -> GovernanceContext:
        tool_name = context.tool_name
        result = context.tool_result

        if not tool_name:
            return context

        is_ok = True
        rolled_back = False
        message = ""

        if isinstance(result, dict):
            is_ok = result.get("ok", True)
            rolled_back = result.get("rolled_back", False)
            message = result.get("message", "")
        elif hasattr(result, "ok"):
            is_ok = getattr(result, "ok", True)
            rolled_back = getattr(result, "rolled_back", False)
            message = getattr(result, "message", "")

        # Audit event
        security_audit_logger.log_event(
            event_type="TOOL_EXECUTION",
            severity="INFO" if is_ok else "WARNING",
            session_id=context.session_id,
            trace_id=context.trace_id,
            details={
                "tool": tool_name,
                "ok": is_ok,
                "rolled_back": rolled_back,
                "transaction_id": context.transaction_id,
                "message": message[:200] if message else "",
            },
        )

        logger.info(
            f"[{context.session_id}] PostToolUse: tool '{tool_name}' ok={is_ok}, rolled_back={rolled_back}"
        )
        return context
