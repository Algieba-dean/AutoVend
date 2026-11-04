#!/usr/bin/env python3
"""
BYD 4S Showroom In-Cabin Sales & Tour Assistant — Interactive CLI / REPL Demo.

Showcases the multi-layer decoupled architecture:
- Layer 1/2: Presentation / Gateway (CLI Interface)
- Layer 3: Hook & Governance Layer (src/governance/ - AOP 防线: PII masking, RBAC, Compliance, Restitution)
- Layer 4: Agent Core Engine (src/agent/orchestrator.py - SalesOrchestrator with Anchor Vehicle Context & Subagents)
- Layer 5: Tool Execution Layer (src/tools/ - DMS Inventory, Test Drive Booking, Cockpit Hardware Demo, Reversible Rollback)
"""

import os
import sys
from types import SimpleNamespace

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent.orchestrator import SalesOrchestrator
from src.agent.schemas import AnchorVehicleContext, SessionState
from src.governance import get_governance_engine
from src.tools.base import ToolExecutionContext
from src.tools.registry import get_tool_registry

BANNER = """
================================================================================
          比亚迪 (BYD) 4S 旗舰店 · 展车座舱专属 AI 销售与智能导览顾问
================================================================================
"""


def render_anchor_card(anchor: AnchorVehicleContext) -> str:
    return f"""
+-------------------------------------------------------------------------------+
|  当前座舱展车主锚点 (Anchor Vehicle)                                          |
|  - 车型: {anchor.model_name:<18} 车系: {anchor.series} ({anchor.trim})
|  - 动力: {anchor.powertrain:<50}|
|  - 车机: {anchor.cockpit_system:<50}|
|  - 底盘: {anchor.chassis:<50}|
|  - 智驾: {anchor.adas:<50}|
|  - 指导价: {anchor.price_guidance:<48}|
+-------------------------------------------------------------------------------+
"""


class CLICockpitMockLLM:
    """Mock LLM matching LlamaIndex LLM interface for the CLI demo."""

    def complete(self, prompt: str, **kwargs):
        # If extraction prompt
        if "Extract" in prompt or "Pydantic" in prompt or "extract" in prompt.lower():
            return SimpleNamespace(text="{}")

        # If generation prompt has subagent conclusions in system_notes (check latest paragraph first)
        for block in reversed(prompt.split("\n\n")):
            block_str = block.strip()
            if any(k in block_str for k in ("【汽车金融专家", "【试驾排期专家", "【专家对比建议", "【专家分析", "对比建议", "专家对比")):
                return SimpleNamespace(
                    text=f"为您整理了比亚迪专家的深度建议：\n{block_str}\n欢迎体验当前展车座舱功能或随时预约实车试驾！"
                )

        return SimpleNamespace(
            text="您好！欢迎莅临比亚迪4S旗舰店。您当前正坐在我们的旗舰展车【比亚迪汉EV】座舱内。本车搭载了行业领先的刀片电池、DiLink 100智能座舱与云辇-C阻尼系统，请问有什么可以为您介绍的吗？"
        )


class BYDCockpitCLI:
    """Terminal REPL interface for the in-cabin assistant."""

    def __init__(self):
        self.registry = get_tool_registry()
        self.governance = get_governance_engine()
        self.anchor = AnchorVehicleContext(
            brand="BYD",
            series="Dynasty",
            model_name="BYD-Han EV",
            trim="715KM 旗舰型",
            powertrain="纯电 (刀片电池 + e平台3.0)",
            cockpit_system="DiLink 100 高阶智能座舱 (15.6英寸自适应旋转Pad)",
            chassis="云辇-C 智能阻尼车身控制系统",
            adas="DiPilot 智能驾驶辅助系统",
            price_guidance="24.98万元",
        )
        self.orchestrator = SalesOrchestrator(
            llm=CLICockpitMockLLM(),
            default_anchor_vehicle=self.anchor,
        )
        self.session_id = "byd_cockpit_demo_01"
        self.state = SessionState(session_id=self.session_id, anchor_vehicle=self.anchor)

        # Execute SessionStart Hook
        self.governance.on_session_start(self.session_id)

    def print_welcome(self):
        print(BANNER)
        print(render_anchor_card(self.anchor))
        print("💡 快捷指令:")
        print("  /demo <feature>   : 模拟座舱硬件交互 (rotate_screen, ambient_light, seat_massage, yunnian_suspension)")
        print("  /compare <model>  : 触发专家子智能体进行车型对比 (例如: /compare 海豹 或 /compare 特斯拉)")
        print("  /finance          : 触发汽车金融测算专家 (测算 24期免息与首付)")
        print("  /testdrive        : 体验试驾排期调度并预约")
        print("  /inventory        : 查询店内现车库存")
        print("  /rollback         : 事务可逆回滚测试")
        print("  /exit             : 结束会话")
        print("-" * 80)

    def handle_message(self, user_text: str) -> str:
        """Process user utterance through the full multi-layer decoupled pipeline."""
        # 1. Governance Layer: PreObserve (PII desensitization + intent routing)
        ctx = self.governance.pre_observe(
            user_message=user_text,
            session_id=self.session_id,
            trace_id=self.state.trace_id,
        )

        # 2. Agent Core Engine: Observe & Respond
        if ctx.skip_extraction:
            self.state = self.orchestrator.remember(self.state, ctx.safe_message)
        else:
            self.state = self.orchestrator.observe(self.state, ctx.safe_message)

        result = self.orchestrator.respond(self.state)
        self.state = result.session_state

        # 3. Governance Layer: PostGenerate (Compliance check & PII restitution)
        final_text, warnings = self.governance.post_generate(
            response_text=result.response_text,
            state=self.state,
            session_id=self.session_id,
        )

        output_lines = [f"[比亚迪销售顾问]: {final_text}"]
        if warnings:
            output_lines.append(f"  (合规护栏拦截提示: {', '.join(warnings)})")

        return "\n".join(output_lines)

    def handle_command(self, cmd: str) -> str:
        parts = cmd.strip().split()
        verb = parts[0].lower()
        t_ctx = ToolExecutionContext(session_id=self.session_id, user_role="customer")

        if verb == "/demo":
            feature = parts[1] if len(parts) > 1 else "rotate_screen"
            param = parts[2] if len(parts) > 2 else "portrait"
            res = self.registry.execute("cockpit_hardware_demo", {"feature": feature, "parameter": param}, t_ctx)
            if res.ok:
                return f"🚗 [座舱硬件联动演示]: {res.message} (Transaction ID: {res.transaction_id})"
            return f"❌ [座舱硬件指令失败]: {res.message}"

        elif verb == "/compare":
            model = " ".join(parts[1:]) if len(parts) > 1 else "海豹"
            return self.handle_message(f"请问当前展车和{model}有什么不同，深度对比一下")

        elif verb == "/finance":
            if len(parts) > 1:
                detail = " ".join(parts[1:])
                return self.handle_message(f"我想了解汽车金融分期方案：{detail}，请专家测算")
            return self.handle_message("如果我买这台汉EV，首付一成大概要多少？有免息政策吗？")

        elif verb == "/testdrive":
            name = parts[1] if len(parts) > 1 else "张先生"
            phone = parts[2] if len(parts) > 2 else "13800001234"
            date_time = parts[3] if len(parts) > 3 else "本周六上午 10:30"
            model = parts[4] if len(parts) > 4 else self.anchor.model_name
            res = self.registry.execute(
                "book_test_drive",
                {
                    "customer_name": name,
                    "phone_number": phone,
                    "car_model": model,
                    "date_time": date_time,
                    "route_preference": "comfort_experience",
                },
                t_ctx,
            )
            if res.ok:
                return f"📅 [DMS 试驾排期预约]: {res.message} (事务单号: {res.transaction_id})"
            return f"❌ [试驾预约失败]: {res.message}"

        elif verb == "/inventory":
            query_arg = parts[1] if len(parts) > 1 else self.anchor.series
            if query_arg in ("王朝", "Dynasty", "海洋", "Ocean"):
                query_payload = {"series": query_arg}
            else:
                query_payload = {"car_model": query_arg}
            res = self.registry.execute("query_store_inventory", query_payload, t_ctx)
            items = res.output.get("inventory", []) if res.ok and res.output else []
            lines = [f"📦 [4S 店现车库存]: 查询到 {len(items)} 台在店现车/展车:"]
            for it in items[:4]:
                lines.append(f"  • {it['car_model']} ({it['trim']}) - {it['color']} [现车: {it['stock_count']}台]")
            return "\n".join(lines)

        elif verb == "/rollback":
            admin_ctx = ToolExecutionContext(session_id=self.session_id, user_role="admin")
            rec = self.registry.rollback_latest(self.session_id, admin_ctx)
            if rec:
                return f"⏪ [事务可逆回滚]: 成功撤销最新交易 {rec.transaction_id} (工具: {rec.tool_name})"
            return "⏪ [事务可逆回滚]: 当前会话无待撤销事务。"

        elif verb == "/anchor":
            return render_anchor_card(self.anchor)

        elif verb in ("/help", "/?"):
            return """💡 快捷指令:
  /anchor           : 重新查看当前展车主锚点核心配置卡片
  /demo <feature>   : 模拟座舱硬件交互 (rotate_screen, ambient_light, seat_massage, yunnian_suspension)
  /compare <model>  : 触发专家子智能体进行车型对比 (例如: /compare 海豹 或 /compare 特斯拉)
  /finance          : 触发汽车金融测算专家 (测算 24期免息与首付)
  /testdrive        : 体验试驾排期调度并预约
  /inventory        : 查询店内现车库存
  /rollback         : 事务可逆回滚测试
  /help             : 查看指令帮助
  /exit             : 结束会话"""

        return f"未知指令: {cmd}"

    def run_repl(self):
        self.print_welcome()
        while True:
            try:
                user_input = input("\n[顾客]: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("/exit", "exit", "quit"):
                    self.governance.on_session_end(self.session_id)
                    print("\n[销售顾问]: 感谢您体验比亚迪座舱智能导览助手，祝您生活愉快，一路向前！")
                    break
                if user_input.startswith("/"):
                    print(self.handle_command(user_input))
                else:
                    print(self.handle_message(user_input))
            except (KeyboardInterrupt, EOFError):
                break


if __name__ == "__main__":
    cli = BYDCockpitCLI()
    cli.run_repl()
