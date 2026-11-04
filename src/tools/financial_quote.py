"""
BYD Financial Calculation Tool — Auto finance loans, down payment, and subsidy estimations.
"""

from typing import Any, Dict

from src.tools.base import BaseTool, ToolExecutionContext, ToolExecutionResult


class FinancialQuoteTool(BaseTool):
    """Tool for calculating BYD automotive finance schemes, down payment, monthly installments, and subsidies."""

    name = "calculate_financial_quote"
    description = (
        "为顾客测算比亚迪官方汽车金融方案。支持测算首付比例（15%/30%/0首付）、贷款期限（24/36/60期）、"
        "免息金融补贴、旧车置换补贴（最高8000元）与国家报废更新补贴（最高20000元）。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "vehicle_price_wan": {
                "type": "number",
                "description": "车辆指导价或预售价（单位：万元），例如 20.98",
            },
            "down_payment_ratio": {
                "type": "number",
                "description": "首付比例（0.0 ~ 0.8），默认 0.15 即 15%",
                "default": 0.15,
            },
            "tenure_months": {
                "type": "integer",
                "description": "贷款期数（24, 36, 48, 60），默认 36 期",
                "default": 36,
            },
            "has_trade_in": {
                "type": "boolean",
                "description": "是否有旧车参与置换（享受比亚迪官方置换补贴）",
                "default": False,
            },
            "has_scrappage": {
                "type": "boolean",
                "description": "是否符合国家报废更新补贴条件（新能源补贴最高2万元）",
                "default": False,
            },
        },
        "required": ["vehicle_price_wan"],
    }

    def execute(self, args: Dict[str, Any], context: ToolExecutionContext) -> ToolExecutionResult:
        price_wan = float(args.get("vehicle_price_wan", 20.0))
        down_ratio = float(args.get("down_payment_ratio", 0.15))
        tenure = int(args.get("tenure_months", 36))
        has_trade_in = bool(args.get("has_trade_in", False))
        has_scrappage = bool(args.get("has_scrappage", False))

        # Financial calculation
        price_yuan = price_wan * 10000.0
        down_payment_yuan = price_yuan * down_ratio
        loan_principal = price_yuan - down_payment_yuan

        # Subsidies
        trade_in_subsidy = 8000.0 if has_trade_in else 0.0
        scrappage_subsidy = 20000.0 if has_scrappage else 0.0
        total_subsidies = trade_in_subsidy + scrappage_subsidy

        # BYD 24-month zero interest promotion policy
        if tenure == 24:
            annual_rate = 0.0  # 24期 0 息
            monthly_rate = 0.0
            monthly_payment = loan_principal / 24.0
            interest_desc = "享受比亚迪官方 24 期 0 息免息金融政策"
        else:
            annual_rate = 0.038  # 3.8% 年化微利金融
            monthly_rate = annual_rate / 12.0
            # 等额本息
            monthly_payment = (
                loan_principal
                * (monthly_rate * ((1 + monthly_rate) ** tenure))
                / (((1 + monthly_rate) ** tenure) - 1)
            )
            interest_desc = f"{tenure} 期低息金融（年化利率约 {annual_rate * 100:.1f}%）"

        effective_down_payment = max(0.0, down_payment_yuan - total_subsidies)

        calc_result = {
            "vehicle_price_yuan": round(price_yuan, 2),
            "down_payment_ratio_pct": f"{down_ratio * 100:.0f}%",
            "down_payment_yuan": round(down_payment_yuan, 2),
            "effective_down_payment_after_subsidies": round(effective_down_payment, 2),
            "loan_principal_yuan": round(loan_principal, 2),
            "tenure_months": tenure,
            "monthly_payment_yuan": round(monthly_payment, 2),
            "subsidies": {
                "byd_trade_in": trade_in_subsidy,
                "national_scrappage": scrappage_subsidy,
                "total_subsidies": total_subsidies,
            },
            "policy_note": interest_desc,
        }

        msg = (
            f"车辆总价 {price_wan:.2f} 万元：首付 {down_ratio * 100:.0f}% 约 {down_payment_yuan / 10000:.2f} 万元；"
            f"分期 {tenure} 个月，月供约 {monthly_payment:.2f} 元/月（{interest_desc}）。"
        )
        if total_subsidies > 0:
            msg += f" 扣除补贴 {total_subsidies:.0f} 元后，实际首付仅需约 {effective_down_payment / 10000:.2f} 万元！"

        return ToolExecutionResult(
            ok=True,
            tool_name=self.name,
            output=calc_result,
            message=msg,
            can_rollback=False,
            metadata={"financial_calculation": True},
        )
