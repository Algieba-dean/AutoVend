"""
Standardized Lifecycle Hooks for AutoVend Agent (src/agent/hooks.py).

Consolidates cross-cutting safety and formatting concerns into explicit
PreTurn / PreTool / PostResponse hooks:
- PreTurn: Prompt injection inspection & sanitization, optional PII masking
- PreTool: Tool contract validation (needsApproval / isReadOnly / arg checks)
- PostResponse: `<think>` block scrubbing, compliance/prompt-leak sanitization, optional PII unmasking
"""

import logging
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.agent.guardrail.compliance import DualStreamComplianceGuard
from src.agent.langchain_tools import get_tool_contract
from src.agent.policy_engine import ToolPolicyEngine
from src.agent.reflection import check_sales_compliance, sanitize_prompt_leakage
from src.agent.think_scrubber import scrub_think_blocks
from src.privacy.prompt_sanitizer import PromptSanitizer
from src.privacy.security_logger import security_audit_logger

logger = logging.getLogger(__name__)


@dataclass
class TurnHookContext:
    session_id: str
    trace_id: str = ""
    raw_message: str = ""
    safe_message: str = ""
    pii_masked: bool = False
    injection_detected: bool = False
    detected_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolHookContext:
    session_id: str
    tool_name: str
    tool_args: Dict[str, Any] = field(default_factory=dict)
    approved: bool = True
    rejection_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponseHookContext:
    session_id: str
    raw_response: str
    sanitized_response: str = ""
    had_think_blocks: bool = False
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LifecycleHook(ABC):
    """Base interface for standardized agent lifecycle hooks."""

    name: str = "base_hook"

    def pre_turn(self, ctx: TurnHookContext) -> TurnHookContext:
        return ctx

    def pre_tool(self, ctx: ToolHookContext) -> ToolHookContext:
        return ctx

    def post_response(self, ctx: ResponseHookContext) -> ResponseHookContext:
        return ctx


class PromptSecurityPreTurnHook(LifecycleHook):
    """PreTurn hook: prompt injection detection/sanitization + optional PII masking."""

    name = "prompt_security_pre_turn"

    def __init__(self, pii_mask_fn: Optional[Callable[[str, str], tuple[str, bool]]] = None):
        self._pii_mask_fn = pii_mask_fn

    def pre_turn(self, ctx: TurnHookContext) -> TurnHookContext:
        text = ctx.safe_message or ctx.raw_message
        sanitization = PromptSanitizer.inspect_and_sanitize(text)
        if sanitization.is_suspicious:
            ctx.injection_detected = True
            ctx.detected_patterns = list(sanitization.detected_patterns)
            security_audit_logger.log_event(
                event_type="PROMPT_INJECTION",
                severity="CRITICAL",
                session_id=ctx.session_id,
                trace_id=ctx.trace_id,
                details={
                    "raw_input": text[:200],
                    "detected_patterns": sanitization.detected_patterns,
                },
            )
            text = sanitization.sanitized_text

        if self._pii_mask_fn is not None and text:
            try:
                masked_text, found = self._pii_mask_fn(text, ctx.session_id)
                text = masked_text
                ctx.pii_masked = bool(found)
            except Exception as exc:
                logger.warning(f"PII mask hook failed: {exc}")

        ctx.safe_message = text
        return ctx


class ToolContractPreToolHook(LifecycleHook):
    """PreTool hook: validates tool execution against its declared ToolContract."""

    name = "tool_contract_pre_tool"

    def __init__(self, auto_approve_tools: bool = True):
        self.auto_approve_tools = auto_approve_tools

    def pre_tool(self, ctx: ToolHookContext) -> ToolHookContext:
        contract = get_tool_contract(ctx.tool_name)
        ctx.metadata["contract"] = contract.to_dict()
        if contract.needsApproval and not self.auto_approve_tools:
            if not ctx.metadata.get("explicit_approval", False):
                ctx.approved = False
                ctx.rejection_reason = f"Tool '{ctx.tool_name}' requires explicit approval before execution."
        return ctx


class ToolPolicyPreToolHook(LifecycleHook):
    """PreTool hook: deterministic Policy-as-Code argument boundary validation."""

    name = "tool_policy_pre_tool"

    def __init__(self, policy_engine: Optional[ToolPolicyEngine] = None):
        self.policy_engine = policy_engine or ToolPolicyEngine()

    def pre_tool(self, ctx: ToolHookContext) -> ToolHookContext:
        res = self.policy_engine.validate(ctx.tool_name, ctx.tool_args)
        if not res.allowed:
            ctx.approved = False
            ctx.rejection_reason = f"[POLICY_VIOLATION] {res.reason}"
            ctx.metadata["policy_violations"] = res.violations
        return ctx


class ResponseSanitizePostHook(LifecycleHook):
    """PostResponse hook: strips `<think>` blocks, compliance risks, prompt leaks, and restores PII."""

    name = "response_sanitize_post"

    def __init__(self, pii_unmask_fn: Optional[Callable[[str, str], str]] = None):
        self._pii_unmask_fn = pii_unmask_fn

    def post_response(self, ctx: ResponseHookContext) -> ResponseHookContext:
        text = ctx.sanitized_response or ctx.raw_response
        cleaned, had_think = scrub_think_blocks(text)
        ctx.had_think_blocks = had_think

        guard_res = DualStreamComplianceGuard.inspect(cleaned)
        if not guard_res.is_compliant:
            ctx.warnings.extend([f"出站合规拦截: {v}" for v in guard_res.violations])
            compliant = guard_res.guarded_text
        else:
            compliant, comp_warnings = check_sales_compliance(cleaned)
            ctx.warnings.extend(comp_warnings)
        safe, leak_warnings = sanitize_prompt_leakage(compliant)
        ctx.warnings.extend(leak_warnings)

        if self._pii_unmask_fn is not None and safe:
            try:
                safe = self._pii_unmask_fn(safe, ctx.session_id)
            except Exception as exc:
                logger.warning(f"PII unmask hook failed: {exc}")

        ctx.sanitized_response = safe.strip()
        return ctx


class LifecycleHookManager:
    """Executes ordered PreTurn, PreTool, and PostResponse hooks."""

    def __init__(self, hooks: Optional[List[LifecycleHook]] = None):
        if hooks is None:
            self.hooks: List[LifecycleHook] = [
                PromptSecurityPreTurnHook(),
                ToolContractPreToolHook(auto_approve_tools=True),
                ToolPolicyPreToolHook(),
                ResponseSanitizePostHook(),
            ]
        else:
            self.hooks = list(hooks)

    def run_pre_turn(self, session_id: str, raw_message: str, trace_id: str = "") -> TurnHookContext:
        ctx = TurnHookContext(
            session_id=session_id,
            trace_id=trace_id,
            raw_message=raw_message,
            safe_message=raw_message,
        )
        for hook in self.hooks:
            try:
                ctx = hook.pre_turn(ctx)
            except Exception as exc:
                logger.warning(f"PreTurn hook '{hook.name}' error: {exc}")
        return ctx

    def run_pre_tool(
        self,
        session_id: str,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolHookContext:
        ctx = ToolHookContext(
            session_id=session_id,
            tool_name=tool_name,
            tool_args=dict(tool_args or {}),
            metadata=dict(metadata or {}),
        )
        for hook in self.hooks:
            try:
                ctx = hook.pre_tool(ctx)
                if not ctx.approved:
                    break
            except Exception as exc:
                logger.warning(f"PreTool hook '{hook.name}' error (fail-closed): {exc}")
                ctx.approved = False
                ctx.rejection_reason = f"[POLICY_ERROR] PreTool hook '{hook.name}' failed: {exc}"
                break
        return ctx

    def run_post_response(self, session_id: str, raw_response: str) -> ResponseHookContext:
        ctx = ResponseHookContext(
            session_id=session_id,
            raw_response=raw_response,
            sanitized_response=raw_response,
        )
        for hook in self.hooks:
            try:
                ctx = hook.post_response(ctx)
            except Exception as exc:
                logger.warning(f"PostResponse hook '{hook.name}' error: {exc}")
        return ctx
