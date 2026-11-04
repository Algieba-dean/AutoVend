"""
PreToolUse Hook — Risk control, parameter sanitization, and RBAC permissions check.
"""

import logging
import re
from typing import Any, Dict, Optional, Set, Tuple

from src.governance.context import GovernanceContext
from src.governance.hooks import BaseGovernanceHook, HookType
from src.privacy.security_logger import security_audit_logger

logger = logging.getLogger(__name__)

# Standard role-based access control table
DEFAULT_ROLE_ALLOWED_TOOLS: Dict[str, Set[str]] = {
    "customer": {
        "record_profile",
        "record_need",
        "record_reservation",
        "request_clarification",
        "transition_to",
        "select_vehicle",
        "request_more_options",
        "query_store_inventory",
        "book_test_drive",
        "cockpit_hardware_demo",
        "calculate_financial_quote",
    },
    "salesperson": {
        "record_profile",
        "record_need",
        "record_reservation",
        "request_clarification",
        "transition_to",
        "select_vehicle",
        "confirm_reservation",
        "apply_discount",
        "override_stage",
        "query_store_inventory",
        "book_test_drive",
        "cancel_test_drive",
        "cockpit_hardware_demo",
        "calculate_financial_quote",
    },
    "admin": {
        "record_profile",
        "record_need",
        "record_reservation",
        "request_clarification",
        "transition_to",
        "select_vehicle",
        "confirm_reservation",
        "apply_discount",
        "override_stage",
        "query_store_inventory",
        "book_test_drive",
        "cancel_test_drive",
        "cockpit_hardware_demo",
        "calculate_financial_quote",
        "rollback_tool_transaction",
    },
}


def sanitize_arguments(args: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Sanitize tool arguments:
    - Truncate strings longer than 500 characters
    - Strip HTML / script injection tags
    - Strip dangerous SQL injection keywords
    """
    sanitized: Dict[str, Any] = {}
    was_sanitized = False

    for k, v in args.items():
        if isinstance(v, str):
            orig = v
            if len(v) > 500:
                v = v[:500]
                was_sanitized = True

            v_clean = re.sub(
                r"<(script|iframe|object|embed)[^>]*>.*?</\1>", "", v, flags=re.IGNORECASE
            )
            v_clean = re.sub(r"javascript:", "", v_clean, flags=re.IGNORECASE)
            v_clean = re.sub(
                r"(\b(SELECT|INSERT|DELETE|UPDATE|DROP|UNION)\b)", "", v_clean, flags=re.IGNORECASE
            )

            if v_clean != orig:
                was_sanitized = True
                v = v_clean
            sanitized[k] = v
        elif isinstance(v, dict):
            sub_san, sub_flag = sanitize_arguments(v)
            sanitized[k] = sub_san
            if sub_flag:
                was_sanitized = True
        else:
            sanitized[k] = v

    return sanitized, was_sanitized


class PreToolUseHook(BaseGovernanceHook):
    """Governs tool invocation with role permission validation and input parameter sanitization."""

    def __init__(
        self,
        role_allowed_tools: Optional[Dict[str, Set[str]]] = None,
        name: str = "PreToolUseHook",
        priority: int = 20,
    ):
        super().__init__(name=name, priority=priority)
        self.role_allowed_tools = role_allowed_tools or DEFAULT_ROLE_ALLOWED_TOOLS

    @property
    def hook_type(self) -> HookType:
        return HookType.PRE_TOOL_USE

    def execute(self, context: GovernanceContext) -> GovernanceContext:
        tool_name = context.tool_name
        if not tool_name:
            return context

        role = context.user_role.lower()
        allowed_tools = self.role_allowed_tools.get(role, set())

        # 1. RBAC Verification
        if tool_name not in allowed_tools:
            context.tool_allowed = False
            security_audit_logger.log_event(
                event_type="UNAUTHORIZED_TOOL_CALL",
                severity="WARNING",
                session_id=context.session_id,
                trace_id=context.trace_id,
                details={"tool": tool_name, "role": role},
            )
            logger.warning(
                f"[{context.session_id}] Tool execution blocked: '{tool_name}' forbidden for role '{role}'."
            )
            return context

        # 2. Input Sanitization
        sanitized_args, was_sanitized = sanitize_arguments(context.tool_args)
        context.tool_args = sanitized_args
        context.tool_sanitized = was_sanitized

        if was_sanitized:
            security_audit_logger.log_event(
                event_type="ARGS_SANITIZED",
                severity="WARNING",
                session_id=context.session_id,
                trace_id=context.trace_id,
                details={"tool": tool_name},
            )

        context.tool_allowed = True
        return context
