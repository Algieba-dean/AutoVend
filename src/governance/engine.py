"""
Governance Engine — Central orchestrator for the Hook & Governance Layer (AOP 防线).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.governance.context import GovernanceContext
from src.governance.hooks import BaseGovernanceHook, HookType
from src.governance.post_generate_hook import PostGenerateHook
from src.governance.post_tool_use_hook import PostToolUseHook
from src.governance.pre_observe_hook import PreObserveHook
from src.governance.pre_tool_use_hook import PreToolUseHook
from src.governance.session_hooks import SessionEndHook, SessionStartHook
from src.governance.stage_transition_hook import StageTransitionHook

logger = logging.getLogger(__name__)


class GovernanceEngine:
    """Manages lifecycle hooks across Presentation, Gateway, Agent, and Tool boundaries."""

    def __init__(
        self,
        pii_interceptor: Optional[Any] = None,
        semantic_router: Optional[Any] = None,
    ):
        self._hooks: Dict[HookType, List[BaseGovernanceHook]] = {
            ht: [] for ht in HookType
        }
        self.pii_interceptor = pii_interceptor
        self.semantic_router = semantic_router
        self._init_default_hooks()

    def _init_default_hooks(self) -> None:
        """Register default out-of-the-box governance hooks."""
        self.register_hook(SessionStartHook())
        self.register_hook(
            PreObserveHook(
                pii_interceptor=self.pii_interceptor,
                semantic_router=self.semantic_router,
            )
        )
        self.register_hook(PreToolUseHook())
        self.register_hook(PostToolUseHook())
        self.register_hook(StageTransitionHook())
        self.register_hook(PostGenerateHook(pii_interceptor=self.pii_interceptor))
        self.register_hook(SessionEndHook())

    def register_hook(self, hook: BaseGovernanceHook) -> None:
        """Add a governance hook, keeping the execution list sorted by ascending priority."""
        ht = hook.hook_type
        self._hooks[ht].append(hook)
        self._hooks[ht].sort(key=lambda h: h.priority)

    def set_pii_interceptor(self, interceptor: Any) -> None:
        """Dynamically configure or update the PII interceptor."""
        self.pii_interceptor = interceptor
        for hook in self._hooks[HookType.PRE_OBSERVE]:
            if isinstance(hook, PreObserveHook):
                hook.set_pii_interceptor(interceptor)
        for hook in self._hooks[HookType.POST_GENERATE]:
            if isinstance(hook, PostGenerateHook):
                hook.set_pii_interceptor(interceptor)

    def set_semantic_router(self, router: Any) -> None:
        """Dynamically configure or update the Semantic Router."""
        self.semantic_router = router
        for hook in self._hooks[HookType.PRE_OBSERVE]:
            if isinstance(hook, PreObserveHook):
                hook.set_semantic_router(router)

    def execute_hook(self, hook_type: HookType, context: GovernanceContext) -> GovernanceContext:
        """Execute all registered hooks for a given lifecycle stage."""
        hooks = self._hooks.get(hook_type, [])
        for hook in hooks:
            try:
                context = hook.execute(context)
            except Exception as exc:
                logger.error(
                    f"[{context.session_id}] Error executing hook {hook.name} at {hook_type.value}: {exc}"
                )
        return context

    # ── High-Level Convenience Methods ─────────────────────────────

    def on_session_start(
        self, session_id: str, trace_id: str = "", user_role: str = "customer"
    ) -> GovernanceContext:
        ctx = GovernanceContext(session_id=session_id, trace_id=trace_id, user_role=user_role)
        return self.execute_hook(HookType.SESSION_START, ctx)

    def pre_observe(
        self, user_message: str, session_id: str, trace_id: str = "", user_role: str = "customer"
    ) -> GovernanceContext:
        ctx = GovernanceContext(
            session_id=session_id,
            trace_id=trace_id,
            user_role=user_role,
            user_message=user_message,
        )
        return self.execute_hook(HookType.PRE_OBSERVE, ctx)

    def pre_tool_use(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        session_id: str,
        trace_id: str = "",
        user_role: str = "customer",
    ) -> Tuple[Dict[str, Any], bool]:
        ctx = GovernanceContext(
            session_id=session_id,
            trace_id=trace_id,
            user_role=user_role,
            tool_name=tool_name,
            tool_args=tool_args,
        )
        ctx = self.execute_hook(HookType.PRE_TOOL_USE, ctx)
        return ctx.tool_args, ctx.tool_allowed

    def post_tool_use(
        self,
        tool_name: str,
        tool_result: Any,
        transaction_id: Optional[str] = None,
        session_id: str = "",
        trace_id: str = "",
        user_role: str = "customer",
    ) -> GovernanceContext:
        ctx = GovernanceContext(
            session_id=session_id,
            trace_id=trace_id,
            user_role=user_role,
            tool_name=tool_name,
            tool_result=tool_result,
            transaction_id=transaction_id,
        )
        return self.execute_hook(HookType.POST_TOOL_USE, ctx)

    def stage_transition(
        self,
        verdict: Any,
        session_id: str,
        trace_id: str = "",
        user_role: str = "customer",
    ) -> GovernanceContext:
        ctx = GovernanceContext(
            session_id=session_id,
            trace_id=trace_id,
            user_role=user_role,
            stage_verdict=verdict,
        )
        return self.execute_hook(HookType.STAGE_TRANSITION, ctx)

    def post_generate(
        self,
        response_text: str,
        state: Optional[Any] = None,
        session_id: str = "",
        trace_id: str = "",
        user_role: str = "customer",
    ) -> Tuple[str, List[str]]:
        ctx = GovernanceContext(
            session_id=session_id,
            trace_id=trace_id,
            user_role=user_role,
            raw_generated_text=response_text,
            metadata={"state": state} if state is not None else {},
        )
        ctx = self.execute_hook(HookType.POST_GENERATE, ctx)
        return ctx.final_response_text, ctx.compliance_warnings

    def on_session_end(
        self, session_id: str, trace_id: str = "", user_role: str = "customer"
    ) -> GovernanceContext:
        ctx = GovernanceContext(session_id=session_id, trace_id=trace_id, user_role=user_role)
        return self.execute_hook(HookType.SESSION_END, ctx)


# Global Engine Instance
_engine: Optional[GovernanceEngine] = None


def get_governance_engine() -> GovernanceEngine:
    global _engine
    if _engine is None:
        _engine = GovernanceEngine()
    return _engine


def set_governance_engine(engine: GovernanceEngine) -> None:
    global _engine
    _engine = engine
