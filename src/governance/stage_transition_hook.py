"""
StageTransition Hook — Sales funnel FSM governance and transition arbitration.
"""

import logging

from src.governance.context import GovernanceContext
from src.governance.hooks import BaseGovernanceHook, HookType
from src.privacy.security_logger import security_audit_logger

logger = logging.getLogger(__name__)


class StageTransitionHook(BaseGovernanceHook):
    """Governs sales funnel stage transitions, enforcing forward guards and rollback constraints."""

    def __init__(self, name: str = "StageTransitionHook", priority: int = 40):
        super().__init__(name=name, priority=priority)

    @property
    def hook_type(self) -> HookType:
        return HookType.STAGE_TRANSITION

    def execute(self, context: GovernanceContext) -> GovernanceContext:
        verdict = context.stage_verdict
        if verdict is None:
            return context

        stage_name = getattr(verdict, "stage", None)
        rejection = getattr(verdict, "rejection", None)

        if rejection:
            logger.info(
                f"[{context.session_id}] Stage transition guarded: {rejection}"
            )
            security_audit_logger.log_event(
                event_type="STAGE_TRANSITION_REJECTED",
                severity="INFO",
                session_id=context.session_id,
                trace_id=context.trace_id,
                details={"reason": rejection, "target_stage": str(stage_name)},
            )
        else:
            logger.info(
                f"[{context.session_id}] Stage transition validated -> {stage_name}"
            )
            security_audit_logger.log_event(
                event_type="STAGE_TRANSITION_ACCEPTED",
                severity="INFO",
                session_id=context.session_id,
                trace_id=context.trace_id,
                details={"target_stage": str(stage_name)},
            )

        return context
