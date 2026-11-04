"""
Session lifecycle governance hooks (SessionStart, SessionEnd).
"""

import logging

from src.governance.context import GovernanceContext
from src.governance.hooks import BaseGovernanceHook, HookType
from src.privacy.security_logger import security_audit_logger

logger = logging.getLogger(__name__)


class SessionStartHook(BaseGovernanceHook):
    """Governs session initialization and environment bootstrap."""

    @property
    def hook_type(self) -> HookType:
        return HookType.SESSION_START

    def execute(self, context: GovernanceContext) -> GovernanceContext:
        logger.info(f"[{context.session_id}] Governance: SessionStart hook executed.")
        security_audit_logger.log_event(
            event_type="SESSION_START",
            severity="INFO",
            session_id=context.session_id,
            trace_id=context.trace_id,
            details={"user_role": context.user_role},
        )
        return context


class SessionEndHook(BaseGovernanceHook):
    """Governs session termination, data flush and audit logging."""

    @property
    def hook_type(self) -> HookType:
        return HookType.SESSION_END

    def execute(self, context: GovernanceContext) -> GovernanceContext:
        logger.info(f"[{context.session_id}] Governance: SessionEnd hook executed.")
        security_audit_logger.log_event(
            event_type="SESSION_END",
            severity="INFO",
            session_id=context.session_id,
            trace_id=context.trace_id,
            details={"terminated": True},
        )
        return context
