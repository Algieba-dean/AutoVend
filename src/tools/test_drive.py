"""
BYD Test Drive Booking Tool — Appointment scheduling and reversible transaction rollback.
"""

import uuid
from typing import Any, Dict, Optional

from src.tools.base import BaseTool, ToolExecutionContext, ToolExecutionResult
from src.tools.mcp_client import BaseMCPClient, MockBYDMCPServer


class TestDriveBookingTool(BaseTool):
    """Tool for scheduling test drives at the BYD 4S store with transaction rollback support."""

    __test__ = False

    name = "book_test_drive"
    description = (
        "为顾客预约比亚迪线下4S店实车试驾。支持预约指定车型、时段、试驾路线，并支持可逆撤回/取消。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "customer_name": {"type": "string", "description": "试驾人姓名"},
            "phone_number": {"type": "string", "description": "联系手机号"},
            "car_model": {"type": "string", "description": "预约试驾车型，例如 '汉 EV' 或 '唐 DM-i'"},
            "date_time": {"type": "string", "description": "预约试驾日期与时间段，如 '本周六上午 10:00'"},
            "route_preference": {
                "type": "string",
                "enum": ["city_eco", "highway_speed", "comfort_experience"],
                "description": "试驾偏好路线：城市道路体验DM-i超低油耗 / 环线高速体验百公里加速 / 舒适底盘云辇滤震体验",
                "default": "city_eco",
            },
        },
        "required": ["customer_name", "phone_number", "car_model", "date_time"],
    }

    def __init__(self, mcp_client: Optional[BaseMCPClient] = None):
        self.client = mcp_client or MockBYDMCPServer()
        self._tx_to_booking: Dict[str, str] = {}

    def execute(self, args: Dict[str, Any], context: ToolExecutionContext) -> ToolExecutionResult:
        customer_name = args.get("customer_name", "贵宾客户")
        phone_number = args.get("phone_number", "")
        car_model = args.get("car_model", "比亚迪展车")
        date_time = args.get("date_time", "即刻")

        res = self.client.create_reservation(
            customer_name=customer_name,
            phone_number=phone_number,
            car_model=car_model,
            date_time=date_time,
        )

        booking_id = res.get("booking_id", "")
        tx_id = f"tx_td_{uuid.uuid4().hex[:8]}"
        self._tx_to_booking[tx_id] = booking_id

        msg = f"已成功为 {customer_name} 预约 {car_model} 试驾，预约单号: {booking_id}，时间: {date_time}。"
        return ToolExecutionResult(
            ok=True,
            tool_name=self.name,
            output=res,
            message=msg,
            transaction_id=tx_id,
            can_rollback=True,
            metadata={"booking_id": booking_id},
        )

    def rollback(self, transaction_id: str, context: ToolExecutionContext) -> bool:
        booking_id = self._tx_to_booking.get(transaction_id)
        if not booking_id:
            return False
        ok = self.client.cancel_reservation(booking_id)
        if ok:
            self._tx_to_booking.pop(transaction_id, None)
        return ok
