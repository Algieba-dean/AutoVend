"""
Financial Calculator Subagent — Domain expert for BYD auto loans, installment plans, and subsidies.
"""

from typing import Any, Dict

from src.agent.subagents.base import BaseSubagent, SubagentResult


class FinancialCalculatorSubagent(BaseSubagent):
    """Expert subagent for BYD auto loan calculations, financial schemes, and purchase policy guidance."""

    name = "financial_calculator_subagent"
    description = "比亚迪汽车金融测算专家（首付比、月供分期、官方免息期与双重置换补贴精准测算）"

    def run(self, task: str, context: Dict[str, Any]) -> SubagentResult:
        user_message = task or context.get("user_message", "")
        anchor = context.get("anchor_vehicle", {})
        price_str = anchor.get("price_guidance", "20.98万元")
        try:
            price_wan = float(price_str.replace("万元", "").replace("万", "").strip())
        except ValueError:
            price_wan = 20.98

        price_yuan = price_wan * 10000.0
        # Default 15% down payment, 36 months tenure
        down_ratio = 0.15
        if "0首付" in user_message or "零首付" in user_message:
            down_ratio = 0.0
        elif "30%" in user_message or "三成" in user_message:
            down_ratio = 0.3

        down_payment_yuan = price_yuan * down_ratio
        loan_principal = price_yuan - down_payment_yuan

        # 24-month zero interest
        monthly_24 = loan_principal / 24.0
        # 36-month low interest (3.8%)
        monthly_36 = (loan_principal * 1.038) / 36.0

        conclusion = (
            f"【汽车金融专家测算方案（基于当前车型预售价约 {price_wan:.2f} 万元）】：\n"
            f"1. 官方免息方案：首付 {down_ratio * 100:.0f}% 约 {down_payment_yuan / 10000:.2f} 万元，"
            f"选择比亚迪官方 24 期 0 息免息金融政策，月供仅需约 {monthly_24:.0f} 元/月（0 利息、0 手续费）；\n"
            f"2. 轻松长贷方案：36 期超低微利金融，月供约 {monthly_36:.0f} 元/月；\n"
            f"3. 专属补贴权益：若有旧车置换可享受比亚迪厂家最高 8,000 元置换补贴；若符合国家新能源报废更新补贴标准，更可享最高 20,000 元现金补贴！"
        )

        return SubagentResult(
            success=True,
            subagent_name=self.name,
            conclusion=conclusion,
            structured_data={
                "price_wan": price_wan,
                "down_payment_yuan": down_payment_yuan,
                "monthly_24_zero_interest": monthly_24,
                "monthly_36": monthly_36,
            },
        )
