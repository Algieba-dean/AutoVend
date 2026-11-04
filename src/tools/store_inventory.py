"""
BYD Store Inventory Query Tool — Real-time DMS inventory check for Dynasty and Ocean series.
"""

from typing import Any, Dict, Optional

from src.tools.base import BaseTool, ToolExecutionContext, ToolExecutionResult
from src.tools.mcp_client import BaseMCPClient, MockBYDMCPServer


class StoreInventoryTool(BaseTool):
    """Tool for querying live vehicle inventory across BYD 4S dealerships."""

    name = "query_store_inventory"
    description = (
        "查询比亚迪4S店内实时现车库存情况（支持王朝系列汉/唐/宋/秦/元与海洋系列海豹/海豚等，返回现车颜色、配置、是否有展车等）。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "car_model": {
                "type": "string",
                "description": "车型名称，例如 '汉 EV'、'海豹'、'唐 DM-i'、'元 PLUS'",
            },
            "series": {
                "type": "string",
                "enum": ["Dynasty", "Ocean", "王朝", "海洋"],
                "description": "比亚迪车系（王朝系列或海洋系列）",
            },
            "store_id": {
                "type": "string",
                "description": "4S门店内码，默认当前旗舰店",
                "default": "BYD_FLAGSHIP_001",
            },
        },
        "required": [],
    }

    def __init__(self, mcp_client: Optional[BaseMCPClient] = None):
        self.client = mcp_client or MockBYDMCPServer()

    def execute(self, args: Dict[str, Any], context: ToolExecutionContext) -> ToolExecutionResult:
        car_model = args.get("car_model")
        series = args.get("series")
        if series in ("王朝", "王朝系列"):
            series = "Dynasty"
        elif series in ("海洋", "海洋系列"):
            series = "Ocean"

        store_id = args.get("store_id", "BYD_FLAGSHIP_001")
        items = self.client.query_inventory(model_name=car_model, series=series, store_id=store_id)

        count = len(items)
        msg = f"已为您查询到 {count} 笔比亚迪现车及展车库存配置信息。"
        return ToolExecutionResult(
            ok=True,
            tool_name=self.name,
            output={"inventory": items, "total": count},
            message=msg,
            can_rollback=False,
        )
