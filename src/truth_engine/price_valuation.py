"""
Depreciation Valuation & Real Drive-Away Price Calculator.
(src/truth_engine/price_valuation.py)

Calculates:
- 1-year and 3-year residual value rates (保值率)
- Recent used car wholesale and retail transaction price ranges
- Real transparent drive-away price (裸车价 - 优惠 - 权益 - 置换补贴 + 购置税 + 商业险 + 杂费)
- Exposure of 4S dealership hidden fees (金融服务费, 出库费, 强制装潢)
"""

from typing import Dict, Optional

from src.truth_engine.master_data import SEED_VEHICLE_PRICING, TruthMasterDataStore
from src.truth_engine.models import DepreciationValuation, DriveAwayPriceCalculation

# Legacy module-level aliases derived from seed data for backward-compatible imports only.
# Runtime calculations always query TruthMasterDataStore (PostgreSQL).
DEPRECIATION_DATABASE: Dict[str, DepreciationValuation] = {
    k: DepreciationValuation(
        car_model=k,
        one_year_residual_rate=float(v["one_year_residual_rate"]),
        three_year_residual_rate=float(v["three_year_residual_rate"]),
        current_wholesale_price_range_wan=str(v["wholesale_price_range_wan"]),
        current_retail_price_range_wan=str(v["retail_price_range_wan"]),
        market_liquidity_rating=str(v["market_liquidity_rating"]),
    )
    for k, v in SEED_VEHICLE_PRICING.items()
    if v.get("one_year_residual_rate") is not None
}

DEFAULT_MSRP_MAP: Dict[str, float] = {
    k: float(v["msrp_wan"])
    for k, v in SEED_VEHICLE_PRICING.items()
    if v.get("msrp_wan") is not None
}


class PriceValuationEngine:
    """Valuation of secondary market depreciation and transparent real drive-away price calculation."""

    _instance: Optional["PriceValuationEngine"] = None

    @classmethod
    def get_instance(cls) -> "PriceValuationEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_depreciation_data(self, car_model: str) -> Optional[DepreciationValuation]:
        """Fetch 1-year, 3-year residual rate and used car transaction price range."""
        if not car_model or not isinstance(car_model, str):
            return None
        clean = car_model.strip()
        if not clean:
            return None

        from src.truth_engine.miit_platform import MIITSpecsPlatform
        platform = MIITSpecsPlatform.get_instance()
        spec = platform.find_specs(clean)
        canonical = spec.car_model if spec else clean

        db_val = TruthMasterDataStore.get_depreciation_valuation(canonical)
        if db_val is not None:
            return db_val

        # Generic estimate for other vehicles
        if len(clean) <= 20:
            return DepreciationValuation(
                car_model=canonical,
                one_year_residual_rate=0.70,
                three_year_residual_rate=0.50,
                current_wholesale_price_range_wan="按官方指导价约 65%~70% 折算",
                current_retail_price_range_wan="按官方指导价约 72%~78% 折算",
                market_liquidity_rating="中等",
            )
        return None

    def calculate_drive_away_price(
        self,
        car_model: str,
        msrp_wan: Optional[float] = None,
        cash_discount_wan: float = 0.0,
        perks_discount_wan: float = 0.0,
        trade_in_subsidy_wan: float = 0.0,
        is_nev: bool = True,
        cash_discount: Optional[float] = None,
        perks_discount: Optional[float] = None,
        trade_in_subsidy: Optional[float] = None,
    ) -> DriveAwayPriceCalculation:
        """
        Calculate precise, transparent drive-away price with zero hidden fluff:
        - Deduct official discounts, perks, and government trade-in subsidies.
        - Calculate NEV purchase tax (2024-2025 max exemption is 30,000 RMB, i.e., tax on price > ~339,000 RMB).
        - Realistic insurance cost and registration fees.
        """
        # Alias support
        effective_cash = cash_discount if cash_discount is not None else cash_discount_wan
        effective_perks = perks_discount if perks_discount is not None else perks_discount_wan
        effective_subsidy = trade_in_subsidy if trade_in_subsidy is not None else trade_in_subsidy_wan

        from src.truth_engine.miit_platform import MIITSpecsPlatform
        platform = MIITSpecsPlatform.get_instance()
        spec = platform.find_specs(car_model)
        canonical_name = spec.car_model if spec else car_model

        if msrp_wan is None:
            msrp_wan = TruthMasterDataStore.get_msrp_wan(canonical_name, fallback_model=car_model) or 25.0

        # Net car invoice price
        net_car = max(0.0, msrp_wan - effective_cash - effective_perks - effective_subsidy)

        # Purchase tax calculation from PostgreSQL active tax policy
        policy = TruthMasterDataStore.get_active_tax_policy()
        vat_divisor = policy["vat_divisor"]
        tax_rate = policy["purchase_tax_rate"]
        nev_cap = policy["nev_exemption_limit_wan"]

        purchase_tax = 0.0
        if is_nev:
            taxable_base = net_car / vat_divisor
            normal_tax = taxable_base * tax_rate
            if normal_tax > nev_cap:
                purchase_tax = round(normal_tax - nev_cap, 2)
            else:
                purchase_tax = 0.0
        else:
            purchase_tax = round((net_car / vat_divisor) * tax_rate, 2)

        # Insurance estimate (compulsory 950 RMB + comprehensive commercial insurance)
        if net_car < 15.0:
            insurance = 0.50  # 5000 RMB
        elif net_car < 25.0:
            insurance = 0.65  # 6500 RMB
        elif net_car < 40.0:
            insurance = 0.85  # 8500 RMB
        else:
            insurance = 1.10  # 11000 RMB

        registration_fee = 0.05  # 500 RMB standard self-registration cost

        total_price = round(net_car + purchase_tax + insurance + registration_fee, 2)

        hidden_fee_warnings = [
            "【金融服务费警告】：若办理分车贷，4S店常私收 3000~5000元'金融服务费'或'资信审查费'。国家发改委明确规定此项收费违规，应坚决拒绝支付！",
            "【出库费与PDI检测费】：新车出库交车检验（PDI）属于主机厂与经销商法定义务，严禁加收1000~2000元所谓的'出库检测费'！",
            "【装潢包捆绑销售】：提防'强加8000元装潢大礼包才给提车'的猫腻，实际几百元的劣质脚垫防爆膜切勿买单，坚持协议写明不强制装潢！",
            "【次年保险押金】：部分4S店要求缴纳 1000~2000元'次年续保押金'，属于霸王条款，提车有权拒绝并在次年自由选择车险机构！",
        ]

        return DriveAwayPriceCalculation(
            car_model=car_model,
            msrp_wan=msrp_wan,
            official_cash_discount_wan=cash_discount_wan,
            official_perks_discount_wan=perks_discount_wan,
            trade_in_subsidy_wan=trade_in_subsidy_wan,
            net_car_price_wan=round(net_car, 2),
            purchase_tax_wan=purchase_tax,
            commercial_and_compulsory_insurance_wan=insurance,
            registration_and_misc_wan=registration_fee,
            total_drive_away_price_wan=total_price,
            hidden_fee_warnings=hidden_fee_warnings,
        )

    def format_price_and_depreciation_markdown(
        self,
        car_model: str,
        msrp_wan: Optional[float] = None,
        cash_discount: float = 0.0,
        perks_discount: float = 0.0,
        trade_in_subsidy: float = 0.0,
    ) -> str:
        """Format depreciation and drive-away price transparent report in Markdown."""
        dep = self.get_depreciation_data(car_model)
        calc = self.calculate_drive_away_price(
            car_model=car_model,
            msrp_wan=msrp_wan,
            cash_discount_wan=cash_discount,
            perks_discount_wan=perks_discount,
            trade_in_subsidy_wan=trade_in_subsidy,
        )

        lines = [
            f"### 💰 【保值率评估与终端真实落地价拆解】: {car_model}",
            "",
            "#### 📉 二手车保值率与近期市场行情:",
            f"- **1年保值率预估**: **{dep.one_year_residual_rate*100:.1f}%** | **3年保值率预估**: **{dep.three_year_residual_rate*100:.1f}%**",
            f"- **近期二手车批发价格区间**: {dep.current_wholesale_price_range_wan if '万元' in dep.current_wholesale_price_range_wan else dep.current_wholesale_price_range_wan + ' 万元'}",
            f"- **近期二手车零售成交区间**: {dep.current_retail_price_range_wan if '万元' in dep.current_retail_price_range_wan else dep.current_retail_price_range_wan + ' 万元'}",
            f"- **二手市场流通周转评价**: {dep.market_liquidity_rating}",
            "",
            "#### 🧾 真实终端落地价阳光明细 (万元):",
            f"- **官方指导价 (MSRP)**: {calc.msrp_wan:.2f} 万",
            f"- **官方终端限时直降**: -{calc.official_cash_discount_wan:.2f} 万",
            f"- **官方选装基金/权益折算**: -{calc.official_perks_discount_wan:.2f} 万",
            f"- **国家/地方以旧换新置换补贴**: -{calc.trade_in_subsidy_wan:.2f} 万",
            f"- **净裸车开票价**: **{calc.net_car_price_wan:.2f} 万**",
            f"- **车辆购置税**: {calc.purchase_tax_wan:.2f} 万 (2024-2025新能源免税上限3万元)",
            f"- **首年商业险 + 交强险预估**: {calc.commercial_and_compulsory_insurance_wan:.2f} 万",
            f"- **车管所正规上牌工本费**: {calc.registration_and_misc_wan:.2f} 万",
            f"- ➡️ **真实到手全包落地价**: **{calc.total_drive_away_price_wan:.2f} 万元**",
            "",
            "#### ⚠️ 4S店套路与隐形乱收费排雷指南:",
        ]
        for w in calc.hidden_fee_warnings:
            lines.append(f"- {w}")

        return "\n".join(lines)
