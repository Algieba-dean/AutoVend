"""
Tool Registry and Dispatcher — Central registry managing tools and transaction lifecycle.
"""

import logging
from typing import Any, Dict, List, Optional

from src.governance.engine import get_governance_engine
from src.tools.base import BaseTool, ToolExecutionContext, ToolExecutionResult
from src.tools.cockpit_demo import CockpitHardwareDemoTool
from src.tools.financial_quote import FinancialQuoteTool
from src.tools.mcp_client import BaseMCPClient, MockBYDMCPServer
from src.tools.store_inventory import StoreInventoryTool
from src.tools.test_drive import TestDriveBookingTool
from src.tools.transaction_manager import TransactionManager, TransactionRecord

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Manages available tools, executes invocations, and handles transaction reversibility."""

    def __init__(self, mcp_client: Optional[BaseMCPClient] = None):
        self.mcp_client = mcp_client or MockBYDMCPServer()
        self.transaction_manager = TransactionManager()
        self._tools: Dict[str, BaseTool] = {}
        self._init_default_tools()

    def _init_default_tools(self) -> None:
        """Register default tools for the BYD sales & in-cabin tour assistant."""
        self.register_tool(StoreInventoryTool(self.mcp_client))
        self.register_tool(TestDriveBookingTool(self.mcp_client))
        self.register_tool(CockpitHardwareDemoTool())
        self.register_tool(FinancialQuoteTool())

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.debug(f"Tool registered: '{tool.name}'")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_tools_catalog(self) -> List[Dict[str, Any]]:
        """Return catalog schemas for LLM function calling / tool planning."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema,
            }
            for t in self._tools.values()
        ]

    def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None,
        state_snapshot: Optional[Dict[str, Any]] = None,
    ) -> ToolExecutionResult:
        """
        Execute a tool by name, governed by AOP Hook Layer (RBAC, sanitization, audit).
        """
        tool = self.get_tool(tool_name)
        ctx = context or ToolExecutionContext()

        if tool is None:
            return ToolExecutionResult(
                ok=False,
                tool_name=tool_name,
                message=f"Tool '{tool_name}' not found in registry.",
            )

        # 1. Governance AOP: PreToolUse (RBAC check + argument sanitization)
        gov = get_governance_engine()
        sanitized_args, allowed = gov.pre_tool_use(
            tool_name=tool_name,
            tool_args=args,
            session_id=ctx.session_id,
            trace_id=ctx.trace_id,
            user_role=ctx.user_role,
        )
        if not allowed:
            return ToolExecutionResult(
                ok=False,
                tool_name=tool_name,
                message=f"Tool '{tool_name}' execution denied for role '{ctx.user_role}'.",
            )

        try:
            result = tool.execute(sanitized_args, ctx)
            if result.ok and result.transaction_id:
                self.transaction_manager.record(
                    tool_name=tool_name,
                    session_id=ctx.session_id,
                    args=sanitized_args,
                    output=result.output,
                    snapshot=state_snapshot,
                    transaction_id=result.transaction_id,
                )

            # 2. Governance AOP: PostToolUse (audit trail & transaction recording)
            gov.post_tool_use(
                tool_name=tool_name,
                tool_result=result,
                transaction_id=result.transaction_id,
                session_id=ctx.session_id,
                trace_id=ctx.trace_id,
                user_role=ctx.user_role,
            )
            return result
        except Exception as exc:
            logger.error(f"Execution error in tool '{tool_name}': {exc}")
            err_result = ToolExecutionResult(
                ok=False,
                tool_name=tool_name,
                message=f"Tool '{tool_name}' execution failed: {str(exc)}",
            )
            gov.post_tool_use(
                tool_name=tool_name,
                tool_result=err_result,
                session_id=ctx.session_id,
                trace_id=ctx.trace_id,
                user_role=ctx.user_role,
            )
            return err_result

    def rollback_transaction(
        self,
        transaction_id: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> bool:
        """Roll back a specific transaction by ID with RBAC governance."""
        rec = self.transaction_manager.get_transaction(transaction_id)
        if not rec:
            return False
        tool = self.get_tool(rec.tool_name)
        ctx = context or ToolExecutionContext(session_id=rec.session_id, user_role="admin")

        # Governance RBAC check for rollback
        gov = get_governance_engine()
        _, allowed = gov.pre_tool_use(
            tool_name="rollback_tool_transaction",
            tool_args={"transaction_id": transaction_id},
            session_id=ctx.session_id,
            trace_id=ctx.trace_id,
            user_role=ctx.user_role,
        )
        if not allowed:
            logger.warning(
                f"[{ctx.session_id}] Rollback denied: user_role '{ctx.user_role}' lacks rollback privilege."
            )
            return False

        success = self.transaction_manager.rollback(transaction_id, tool, ctx)
        gov.post_tool_use(
            tool_name="rollback_tool_transaction",
            tool_result={"ok": success, "rolled_back": True, "message": f"Rollback {transaction_id}"},
            transaction_id=transaction_id,
            session_id=ctx.session_id,
            trace_id=ctx.trace_id,
            user_role=ctx.user_role,
        )
        return success

    def rollback_latest(
        self,
        session_id: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> Optional[TransactionRecord]:
        """Roll back the most recent reversible tool transaction for a session."""
        ctx = context or ToolExecutionContext(session_id=session_id, user_role="admin")
        txs = self.transaction_manager.get_session_transactions(session_id)
        for rec in reversed(txs):
            if rec.status == "COMMITTED":
                if self.rollback_transaction(rec.transaction_id, context=ctx):
                    return rec
        return None


# Global Tool Registry
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def set_tool_registry(registry: ToolRegistry) -> None:
    global _registry
    _registry = registry
