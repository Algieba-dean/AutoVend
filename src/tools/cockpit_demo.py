"""
BYD Cockpit Hardware Demo Tool — Interactive in-cabin hardware demonstration for showroom vehicles.
"""

import uuid
from typing import Any, Dict

from src.tools.base import BaseTool, ToolExecutionContext, ToolExecutionResult


class CockpitHardwareDemoTool(BaseTool):
    """
    Tool for controlling in-cabin interactive hardware on the BYD showroom anchor vehicle.
    Demonstrates DiLink rotatable screen, YunNian suspension damping, Dynaudio sound,
    ambient lighting, seat massage, and smart fragrance.
    """

    name = "cockpit_hardware_demo"
    description = (
        "控制当前展车座舱内的实车硬件演示（仅限展车展厅模式）：旋转DiLink悬浮Pad、"
        "调节31色座舱氛围灯、开启座椅按摩通风、切换云辇系统阻尼演示、播放丹拿音响试听等。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "feature": {
                "type": "string",
                "enum": [
                    "rotate_screen",
                    "ambient_light",
                    "seat_massage",
                    "dynaudio_demo",
                    "yunnian_suspension",
                    "smart_fragrance",
                ],
                "description": "需要演示的车机/座舱硬件功能",
            },
            "parameter": {
                "type": "string",
                "description": "演示参数，例如 rotate_screen 的 'portrait' 或 'landscape'；ambient_light 的 'cyan' 或 'gold'；seat_massage 的 'wave' 或 'pulse'",
                "default": "default",
            },
        },
        "required": ["feature"],
    }

    def __init__(self):
        # Current hardware states for rollback
        self._feature_states: Dict[str, str] = {
            "rotate_screen": "landscape",
            "ambient_light": "ice_blue",
            "seat_massage": "off",
            "dynaudio_demo": "off",
            "yunnian_suspension": "comfort",
            "smart_fragrance": "off",
        }
        self._tx_snapshots: Dict[str, Dict[str, str]] = {}

    def execute(self, args: Dict[str, Any], context: ToolExecutionContext) -> ToolExecutionResult:
        feature = args.get("feature", "rotate_screen")
        param = args.get("parameter", "default")

        tx_id = f"tx_hw_{uuid.uuid4().hex[:8]}"
        prev_state = self._feature_states.get(feature, "off")
        self._tx_snapshots[tx_id] = {feature: prev_state}

        # Apply simulated hardware change
        self._feature_states[feature] = param

        feature_descriptions = {
            "rotate_screen": f"已将中控 15.6 英寸自适应旋转悬浮 Pad 旋转至 {'竖屏浏览' if param == 'portrait' else '横屏影音'} 模式！",
            "ambient_light": f"已为您切换 31 色律动音乐氛围灯为『{param}』主题光效！",
            "seat_massage": f"已开启主驾 SPA 级 10 点气动按摩（当前模式: {param}）与座椅吸风式通风！",
            "dynaudio_demo": "正在播放丹拿 HiFi 原厂调音环绕声乐演示段落（原声音乐厅模式）！",
            "yunnian_suspension": f"云辇-C 智能阻尼车身控制系统已切换至『{param}』路况适应演示模式！",
            "smart_fragrance": "已释放比亚迪专属定制车载香氛（前调茶香），负离子空气净化系统已同步开启！",
        }

        feedback = feature_descriptions.get(
            feature, f"展车座舱硬件 {feature} 已响应指令: {param}。"
        )

        return ToolExecutionResult(
            ok=True,
            tool_name=self.name,
            output={"feature": feature, "current_state": param, "previous_state": prev_state},
            message=feedback,
            transaction_id=tx_id,
            can_rollback=True,
            metadata={"anchor_vehicle_demo": True},
        )

    def rollback(self, transaction_id: str, context: ToolExecutionContext) -> bool:
        prev = self._tx_snapshots.get(transaction_id)
        if not prev:
            return False
        for feat, val in prev.items():
            self._feature_states[feat] = val
        self._tx_snapshots.pop(transaction_id, None)
        return True
