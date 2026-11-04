"""
PostGenerate Hook — Commercial compliance verification and PII restitution.
"""

import logging
from typing import Any, Optional

from src.governance.context import GovernanceContext
from src.governance.hooks import BaseGovernanceHook, HookType
from src.privacy.security_logger import security_audit_logger

logger = logging.getLogger(__name__)


def unmask_state_fields(state: Any, session_id: str, pii_interceptor: Any) -> None:
    """Restore placeholders inside user profile and reservation in-place."""
    if pii_interceptor is None or state is None:
        return
    try:
        profile = getattr(state, "profile", None)
        reservation = getattr(state, "reservation", None)
        for model in (profile, reservation):
            if model is None:
                continue
            dump = model.model_dump() if hasattr(model, "model_dump") else model.__dict__
            for field, value in dump.items():
                if isinstance(value, str) and "<" in value:
                    setattr(model, field, pii_interceptor.unmask(value, session_id))
    except Exception as exc:
        logger.error(f"[{session_id}] PII restitution on state failed: {exc}")


class PostGenerateHook(BaseGovernanceHook):
    """
    Hook executed after Agent response generation.
    Enforces commercial compliance (redacting unauthorized claims)
    and unmasks PII back to original real identifiers for end-user presentation.
    """

    def __init__(
        self,
        pii_interceptor: Optional[Any] = None,
        name: str = "PostGenerateHook",
        priority: int = 50,
    ):
        super().__init__(name=name, priority=priority)
        self.pii_interceptor = pii_interceptor

    @property
    def hook_type(self) -> HookType:
        return HookType.POST_GENERATE

    def set_pii_interceptor(self, interceptor: Any) -> None:
        self.pii_interceptor = interceptor

    def execute(self, context: GovernanceContext) -> GovernanceContext:
        session_id = context.session_id
        text = context.raw_generated_text or context.final_response_text or ""

        # 1. Commercial Compliance & Anti-Hallucination
        from src.agent.reflection import check_sales_compliance

        sanitized_text, warnings = check_sales_compliance(text)
        context.compliance_warnings = warnings

        if warnings:
            logger.warning(f"[{session_id}] Compliance warnings detected: {warnings}")
            security_audit_logger.log_event(
                event_type="COMPLIANCE_REDACTION",
                severity="WARNING",
                session_id=session_id,
                trace_id=context.trace_id,
                details={"warnings": warnings},
            )

        # 2. PII Restitution (Unmask placeholders back to real identity)
        if self.pii_interceptor is not None and sanitized_text:
            try:
                final_text = self.pii_interceptor.unmask(sanitized_text, session_id)
            except Exception as exc:
                logger.error(f"[{session_id}] PII unmasking of generated text failed: {exc}")
                final_text = sanitized_text
        else:
            final_text = sanitized_text

        # 3. Restitute state fields if state object is available in metadata
        state = context.metadata.get("state")
        if state is not None and self.pii_interceptor is not None:
            unmask_state_fields(state, session_id, self.pii_interceptor)

        context.final_response_text = final_text
        return context
