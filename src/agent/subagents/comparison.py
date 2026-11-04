"""
Model Comparison Subagent — Expert in-depth analysis of BYD Dynasty & Ocean series and rival vehicles.
"""

from typing import Any, Dict

from src.agent.subagents.base import BaseSubagent, SubagentResult


class ModelComparisonSubagent(BaseSubagent):
    """
    Expert subagent for comparative vehicle analysis.
    Specializes in BYD Dynasty series (Han, Tang, Song, Qin, Yuan) vs Ocean series (Seal, Dolphin, Seagull)
    and comparisons against external EV rivals (e.g., Tesla Model 3/Y, Xiaopeng, Geely).
    """

    name = "model_comparison_subagent"
    description = "比亚迪车型深度对比专家（王朝系列、海洋系列、竞品全方位技术对比）"

    def run(self, task: str, context: Dict[str, Any]) -> SubagentResult:
        anchor = context.get("anchor_vehicle", {})
        anchor_model = anchor.get("model_name", "BYD-Han EV")
        user_message = task or context.get("user_message", "")

        msg_lower = user_message.lower()
        sections = []
        targets = []

        # 1. Ocean series: Seal / Dolphin / Seagull
        if "海豹" in user_message or "seal" in msg_lower:
            sections.append(
                f"【{anchor_model} vs 比亚迪海豹EV】\n"
                f"• 定位差异：当前展车【汉EV】定位于豪华行政C级旗舰，轴距2920mm，强调行政商务气场与云辇-C高品质奢华滤震；"
                f"海豹EV则是e平台3.0原生后驱/四驱运动轿跑，搭载CTB电池车身一体化，操控极限更高、更具驾驶乐趣。\n"
                f"• 适用人群：追求越级后排空间与商务家庭兼顾首选汉EV；追求灵动运动操控首选海豹。"
            )
            targets.append("BYD-SEAL EV")
        elif "海豚" in user_message or "海鸥" in user_message or "dolphin" in msg_lower:
            sections.append(
                f"【{anchor_model} vs 海洋网纯电精品（海豚/海鸥）】\n"
                f"• 海豚/海鸥专为都市年轻通勤与灵活代步打造，车身小巧停车便捷、电耗极低；"
                f"而当前展车【汉EV】为中大型旗舰豪华轿车，在高速稳定性、隔音静谧性、续航里程及豪华配置上属于跨级别体验。"
            )
            targets.append("BYD-Dolphin/Seagull")

        # 2. Competitors: Tesla Model 3 / Model Y
        if "特斯拉" in user_message or "model 3" in msg_lower or "model y" in msg_lower:
            sections.append(
                f"【{anchor_model} vs 特斯拉 Model 3/Y】\n"
                f"• 电池安全：比亚迪自研刀片电池通过严苛针刺不起火测试，热失控风险远低于传统三元锂电池；\n"
                f"• 座舱奢享：{anchor_model}标配Nappa真皮、多模式座椅通风/加热/按摩、丹拿音响与31色氛围灯，座舱用料与隔音NVH显著优于特斯拉极简毛坯设计；\n"
                f"• 本地智能：DiLink系统深度兼容国内App生态，支持15.6英寸自适应旋转，车机本土化与语音体验更贴合国内使用习惯。"
            )
            targets.append("Tesla")

        # 3. Dynasty SUV & other models: Tang / Song / Qin / Yuan
        if "唐" in user_message or "tang" in msg_lower:
            sections.append(
                "【比亚迪王朝唐系列（旗舰SUV）】\n"
                "• 唐系列主打豪华大7座空间与越野通过性，DM-i混动综合续航超1000公里，支持云辇-C与智能电四驱，兼顾全家出行与自驾长途。"
            )
            targets.append("BYD-Tang DM-i")
        elif "宋" in user_message or "song" in msg_lower or "秦" in user_message or "qin" in msg_lower or "元" in user_message:
            sections.append(
                "【比亚迪国民爆款（宋/秦/元系列）】\n"
                "• 秦/宋/元主打极致质价比与超低用车成本，百公里亏电油耗低至3L级别；而当前展车【汉EV】则是旗舰级科技与豪华标杆。"
            )
            targets.append("BYD-Dynasty-Family")

        if not sections:
            conclusion = (
                f"【专家分析：当前展车 {anchor_model} 核心技术亮点】\n"
                f"当前展车搭载比亚迪自研超级刀片电池、e平台3.0高阶架构与DiLink 100智能座舱，"
                f"兼具极致结构安全、高能量密度以及超长电驱动续航，在同级别车型中具备极强的质价比与保值实力。"
            )
            data = {"comparison_type": "anchor_highlight", "target": anchor_model}
        else:
            conclusion = f"【专家对比建议：{anchor_model} 全方位技术解析】\n" + "\n\n".join(sections)
            data = {"comparison_type": "multi_target_comparison", "targets": targets}

        return SubagentResult(
            success=True,
            subagent_name=self.name,
            conclusion=conclusion,
            structured_data=data,
        )
