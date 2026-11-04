"""
Unit tests for Tool Execution Layer and Reversible Rollback (src/tools/).
"""

from src.tools.base import ToolExecutionContext
from src.tools.cockpit_demo import CockpitHardwareDemoTool
from src.tools.financial_quote import FinancialQuoteTool
from src.tools.mcp_client import MockBYDMCPServer
from src.tools.registry import ToolRegistry
from src.tools.store_inventory import StoreInventoryTool
from src.tools.test_drive import TestDriveBookingTool


def test_byd_store_inventory_tool():
    tool = StoreInventoryTool()
    ctx = ToolExecutionContext(session_id="sess_inv_1")

    # Dynasty query
    res_dynasty = tool.execute({"series": "Dynasty"}, ctx)
    assert res_dynasty.ok is True
    assert res_dynasty.output["total"] > 0
    assert any("Han" in item["car_model"] for item in res_dynasty.output["inventory"])

    # Model specific query
    res_seal = tool.execute({"car_model": "海豹"}, ctx)
    assert res_seal.ok is True
    assert any("SEAL" in item["car_model"] for item in res_seal.output["inventory"])


def test_test_drive_booking_and_rollback():
    mcp_server = MockBYDMCPServer()
    tool = TestDriveBookingTool(mcp_client=mcp_server)
    ctx = ToolExecutionContext(session_id="sess_td_1")

    # 1. Book test drive
    book_args = {
        "customer_name": "李女士",
        "phone_number": "13800138000",
        "car_model": "BYD-Han EV",
        "date_time": "本周六下午 15:00",
        "route_preference": "comfort_experience",
    }
    result = tool.execute(book_args, ctx)
    assert result.ok is True
    assert result.can_rollback is True
    tx_id = result.transaction_id
    booking_id = result.metadata["booking_id"]
    assert mcp_server._reservations[booking_id]["status"] == "CONFIRMED"

    # 2. Rollback test drive booking
    rollback_ok = tool.rollback(tx_id, ctx)
    assert rollback_ok is True
    assert mcp_server._reservations[booking_id]["status"] == "CANCELLED"


def test_cockpit_hardware_demo_and_rollback():
    tool = CockpitHardwareDemoTool()
    ctx = ToolExecutionContext(session_id="sess_demo_1")

    # Rotate DiLink screen to portrait
    res1 = tool.execute({"feature": "rotate_screen", "parameter": "portrait"}, ctx)
    assert res1.ok is True
    assert tool._feature_states["rotate_screen"] == "portrait"
    assert "竖屏" in res1.message

    # Rollback to original landscape
    tx_id = res1.transaction_id
    rb_ok = tool.rollback(tx_id, ctx)
    assert rb_ok is True
    assert tool._feature_states["rotate_screen"] == "landscape"


def test_financial_quote_tool():
    tool = FinancialQuoteTool()
    ctx = ToolExecutionContext(session_id="sess_fin_1")

    # 24-month zero interest
    res_24 = tool.execute(
        {"vehicle_price_wan": 20.0, "down_payment_ratio": 0.15, "tenure_months": 24}, ctx
    )
    assert res_24.ok is True
    out_24 = res_24.output
    assert "0 息" in out_24["policy_note"]
    assert out_24["tenure_months"] == 24

    # With trade-in and scrappage subsidies
    res_subsidy = tool.execute(
        {
            "vehicle_price_wan": 20.0,
            "has_trade_in": True,
            "has_scrappage": True,
        },
        ctx,
    )
    assert res_subsidy.ok is True
    out_sub = res_subsidy.output
    assert out_sub["subsidies"]["total_subsidies"] == 28000.0


def test_tool_registry_transaction_integration():
    registry = ToolRegistry()
    ctx = ToolExecutionContext(session_id="sess_reg_1")

    # Execute tool via registry
    res = registry.execute(
        tool_name="book_test_drive",
        args={
            "customer_name": "张先生",
            "phone_number": "13900000000",
            "car_model": "BYD-Tang DM-i",
            "date_time": "明天上午 10:00",
        },
        context=ctx,
    )
    assert res.ok is True
    tx_id = res.transaction_id

    # Verify transaction record exists
    rec = registry.transaction_manager.get_transaction(tx_id)
    assert rec is not None
    assert rec.status == "COMMITTED"

    # Verify RBAC: customer is rejected from rolling back transactions
    customer_rb = registry.rollback_latest(session_id="sess_reg_1", context=ctx)
    assert customer_rb is None

    # Roll back latest with admin privilege
    admin_ctx = ToolExecutionContext(session_id="sess_reg_1", user_role="admin")
    rolled_rec = registry.rollback_latest(session_id="sess_reg_1", context=admin_ctx)
    assert rolled_rec is not None
    assert rolled_rec.status == "ROLLED_BACK"
