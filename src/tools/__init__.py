"""
Tool Execution & External Ecosystem Layer (src/tools/).

Decouples external tool executions from in-memory agent state.
Provides MCP Client integration, DMS store inventory queries, test drive scheduling,
in-cabin hardware demo, and state change transaction rollback.
"""

from src.tools.base import BaseTool, ToolExecutionContext, ToolExecutionResult
from src.tools.cockpit_demo import CockpitHardwareDemoTool
from src.tools.financial_quote import FinancialQuoteTool
from src.tools.mcp_client import BaseMCPClient, MockBYDMCPServer
from src.tools.registry import (
    ToolRegistry,
    get_tool_registry,
    set_tool_registry,
)
from src.tools.store_inventory import StoreInventoryTool
from src.tools.test_drive import TestDriveBookingTool
from src.tools.transaction_manager import TransactionManager, TransactionRecord

__all__ = [
    "BaseTool",
    "ToolExecutionContext",
    "ToolExecutionResult",
    "ToolRegistry",
    "get_tool_registry",
    "set_tool_registry",
    "TransactionManager",
    "TransactionRecord",
    "BaseMCPClient",
    "MockBYDMCPServer",
    "StoreInventoryTool",
    "TestDriveBookingTool",
    "CockpitHardwareDemoTool",
    "FinancialQuoteTool",
]
