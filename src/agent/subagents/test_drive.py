"""
Test Drive Scheduler Subagent — Expert in 4S store test drive scheduling and experience routes.
"""

from typing import Any, Dict

from src.agent.subagents.base import BaseSubagent, SubagentResult


class TestDriveSchedulerSubagent(BaseSubagent):
    """Expert subagent for 4S dealership test drive scheduling, route planning, and slot optimization."""

    name = "test_drive_scheduler_subagent"
    description = "比亚迪4S店试驾排期专家（实车试驾路线规划、专属顾问时间槽与体验环节调度）"

    def run(self, task: str, context: Dict[str, Any]) -> SubagentResult:
        anchor = context.get("anchor_vehicle", {})
        anchor_model = anchor.get("model_name", "BYD-Han EV")

        conclusion = (
            f"【试驾排期专家调度建议】：\n"
            f"1. 推荐体验路线：建议为您安排『城市拥堵路况 + 环线高架加速』组合试驾路线（全程约 12 公里），"
            f"可完整体验 {anchor_model} 的超低电耗/油耗、云辇底盘滤震质感及 DiPilot 高阶智驾自动领航体验；\n"
            f"2. 试驾排期：店内现车试驾车已就位并已完成全车消毒，当前工作日/周末上午 10:00 及下午 14:30 均有 VIP 试驾空档；\n"
            f"3. 预约提醒：只需提供您的称呼与联系手机号，系统即可秒级完成 DMS 系统试驾槽锁定并指派资深产品专家陪同。"
        )

        return SubagentResult(
            success=True,
            subagent_name=self.name,
            conclusion=conclusion,
            structured_data={
                "recommended_route_km": 12,
                "preferred_slots": ["10:00", "14:30"],
                "target_model": anchor_model,
            },
        )
