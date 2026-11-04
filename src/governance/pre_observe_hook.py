"""
PreObserve Hook — PII desensitization, prompt injection inspection, and intent short-circuiting.
"""

import logging
from typing import Any, Optional, Set

from src.governance.context import GovernanceContext
from src.governance.hooks import BaseGovernanceHook, HookType
from src.privacy.prompt_sanitizer import PromptSanitizer
from src.privacy.security_logger import security_audit_logger

logger = logging.getLogger(__name__)

DEFAULT_EXTRACTION_SKIP_INTENTS = frozenset({"affirm", "reject", "defer", "smalltalk"})
DEFAULT_INTERRUPT_INTENT = "update_constraint"


class PreObserveHook(BaseGovernanceHook):
    """
    Hook executed prior to Agent observation.
    Performs prompt injection inspection, semantic classification,
    PII masking, and short-circuit routing.
    """

    def __init__(
        self,
        pii_interceptor: Optional[Any] = None,
        semantic_router: Optional[Any] = None,
        skip_intents: Optional[Set[str]] = None,
        interrupt_intent: str = DEFAULT_INTERRUPT_INTENT,
        name: str = "PreObserveHook",
        priority: int = 10,
    ):
        super().__init__(name=name, priority=priority)
        self.pii_interceptor = pii_interceptor
        self.semantic_router = semantic_router
        self.skip_intents = skip_intents or DEFAULT_EXTRACTION_SKIP_INTENTS
        self.interrupt_intent = interrupt_intent

    @property
    def hook_type(self) -> HookType:
        return HookType.PRE_OBSERVE

    def set_pii_interceptor(self, interceptor: Any) -> None:
        self.pii_interceptor = interceptor

    def set_semantic_router(self, router: Any) -> None:
        self.semantic_router = router

    def execute(self, context: GovernanceContext) -> GovernanceContext:
        user_message = context.user_message
        session_id = context.session_id
        trace_id = context.trace_id

        # 1. Prompt Injection Sanitization
        sanitization = PromptSanitizer.inspect_and_sanitize(user_message)
        effective_message = user_message
        if sanitization.is_suspicious:
            security_audit_logger.log_event(
                event_type="PROMPT_INJECTION",
                severity="CRITICAL",
                session_id=session_id,
                trace_id=trace_id,
                details={
                    "raw_input": user_message[:200],
                    "detected_patterns": sanitization.detected_patterns,
                },
            )
            effective_message = sanitization.sanitized_text

        # 2. Semantic Intent Classification (runs on unmasked text so anchor vectors retain full meaning)
        decision = None
        if self.semantic_router is not None:
            try:
                dec = self.semantic_router.classify(effective_message)
                if getattr(dec, "matched", False):
                    decision = dec
            except Exception as exc:
                logger.error(f"[{session_id}] Semantic routing failed in PreObserveHook: {exc}")

        context.decision = decision

        # 3. PII Masking
        safe_message = effective_message
        pii_found = False
        if self.pii_interceptor is not None:
            try:
                safe_message, matches = self.pii_interceptor.mask(effective_message, session_id)
                pii_found = bool(matches)
            except Exception as exc:
                logger.error(f"[{session_id}] PII masking failed in PreObserveHook: {exc}")

        context.safe_message = safe_message
        context.pii_found = pii_found

        # 4. Short-Circuit & Intent Routing
        if decision is not None and getattr(decision, "intent", None) in self.skip_intents and not pii_found:
            context.skip_extraction = True
            logger.info(
                f"[{session_id}] Governance short-circuit: intent '{decision.intent}' skips extraction."
            )

        if decision is not None and getattr(decision, "intent", None) == self.interrupt_intent:
            context.interrupt_detected = True
            logger.info(f"[{session_id}] Governance: interrupt intent '{self.interrupt_intent}' detected.")

        return context
