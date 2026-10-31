"""
Domain schemas for Consumer Truth & Anti-Marketing Fluff Engine.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FluffCategory(str, Enum):
    """Categories of marketing fluff and misleading claims."""

    STANDARD_TECH_AS_BREAKTHROUGH = "standard_tech_as_breakthrough"  # 行业通用技术包装为独家突破 (如支持加92号油)
    NOMINAL_VS_REAL_GAP = "nominal_vs_real_gap"  # 标称参数与实际工况严重脱节 (CLTC续航、峰值充电功率)
    THERMAL_THROTTLE_OMISSION = "thermal_throttle_omission"  # 隐瞒热衰减与极限工况性能限制 (超跑级加速热衰减)
    TIER1_AS_SELF_DEVELOPED = "tier1_as_self_developed"  # 采购Tier-1方案包装为全栈自研 (博世IPB/宁德时代电芯/高通8295)
    FINE_PRINT_RESTRICTION = "fine_print_restriction"  # 苛刻免责条款/文字游戏 (终身质保限制、终身免流限制)
    SAFETY_AND_CHASSIS_MYTH = "safety_and_chassis_myth"  # 机械结构与安全误读/偷换概念 (踩断踏板误解、假防撞梁)
    ADAS_OVERPROMISE = "adas_overpromise"  # 智驾夸大宣传与免责转移 (L3级宣传/L2级免责)


class FluffSeverity(str, Enum):
    """Severity level of the marketing fluff."""

    HIGH = "high"  # 严重误导用户预期/涉及安全责任或重大开销
    MEDIUM = "medium"  # 显著夸大宣传/通用技术虚高溢价
    LOW = "low"  # 常规行业修辞/需提示客观认知


class MarketingFluffItem(BaseModel):
    """A detected marketing fluff pattern with consumer deconstruction."""

    category: FluffCategory
    severity: FluffSeverity = FluffSeverity.MEDIUM
    claim: str  # OEM宣传话术
    reality: str  # 客观工程与行业真相
    debiasing_explanation: str  # 拆解与避坑建议
    industry_benchmark: str = ""  # 行业通用基准水平


class RealWorldRangeGap(BaseModel):
    """Nominal range vs real-world range gap analysis."""

    car_model: str
    powertrain_type: str = "BEV"
    cltc_range_km: float
    wltc_range_km: Optional[float] = None
    winter_low_temp_range_km: float  # 冬季低温(-10°C~0°C)实测续航
    winter_achievement_rate: float  # 冬季达成率 (通常50%~65%)
    highway_120_range_km: float  # 高速120km/h实测续航
    highway_achievement_rate: float  # 高速达成率 (通常60%~70%)
    reasons: List[str] = Field(default_factory=list)


class ChargingCurveReality(BaseModel):
    """Peak charging claims vs real-world power curve."""

    car_model: str
    nominal_peak_power_kw: float  # 标称峰值充电功率 (如 300kW)
    sustained_soc_range: str = "10%-25%"  # 峰值维持区间
    average_power_10_to_80_kw: float  # 10%-80% 平均充电功率
    real_time_10_to_80_min: float  # 实际10%-80% 充电耗时 (分钟)
    winter_cold_charge_penalty_min: float = 15.0  # 冬季未预热额外耗时
    reality_analysis: str = ""


class InfotainmentReliability(BaseModel):
    """In-cabin infotainment software stability cases."""

    car_model: str
    soc_chip: str  # 高通8155 / 高通8295 / 自研芯片
    screen_blackout_rate_per_year: float  # 预估年黑屏/白屏次数
    reboot_frequency: str  # 重启频率 (如 "偶尔卡顿/月均一次")
    ota_negative_regressions: List[str] = Field(default_factory=list)  # OTA负优化案例 (锁电/削减功率/音响变差)


class BatterySafetyRecord(BaseModel):
    """Battery thermal safety history & national standards compliance."""

    car_model: str
    battery_chemistry: str  # 磷酸铁锂 (LFP) / 三元锂 (NCM/NCA)
    pack_supplier: str  # 宁德时代 / 弗迪电池 / 中创新航等
    gb_38031_compliance: str = "符合强标要求 (热失控报警后5分钟内不起火不爆炸)"
    bottom_protection_structure: str = ""  # 底部防托底装甲结构
    historical_fire_incidents: int = 0  # 公开报道热失控起火案例数
    puncture_and_impact_reality: str = ""  # 真实高速托底穿刺表现客观分析


class BrakeChassisControversy(BaseModel):
    """Chassis & brake engineering truth (pedal myths, One-Box redundancy)."""

    topic: str  # 如 "刹车踏板踩断争议" / "One-Box 线控刹车失灵备用"
    myth_or_claim: str  # 坊间传言或用户疑虑
    engineering_fact: str  # 工程力学与汽车被动安全真相
    material_and_standards: str  # 材质(如 PA66-GF30)与法规(GB 7258)
    redundancy_mechanism: str  # 冗余设计 (机械液压备份回路)


class CrashTestSummary(BaseModel):
    """Crash test ratings from C-IASI (中保研) or C-NCAP."""

    car_model: str
    evaluator: str = "C-IASI (中保研)"
    test_year: str = ""
    occupant_safety: str = "G (优秀)"
    small_overlap_25_result: str = "G (良好/优秀，A柱无严重弯折，气囊准确承托)"
    side_impact_b_pillar_result: str = "B柱距座椅中线距离充足，侵入量合规"
    pedestrian_safety: str = "G"
    active_safety: str = "G"
    structural_defect_notes: List[str] = Field(default_factory=list)


class DepreciationValuation(BaseModel):
    """Residual value and secondary market valuation."""

    car_model: str
    one_year_residual_rate: float  # 1年保值率 (如 0.72)
    three_year_residual_rate: float  # 3年保值率 (如 0.52)
    current_wholesale_price_range_wan: str  # 近期二手车批发价区间 (万元)
    current_retail_price_range_wan: str  # 近期二手车零售价区间 (万元)
    market_liquidity_rating: str = "中等"  # 高/中/低


class DriveAwayPriceCalculation(BaseModel):
    """Transparent real drive-away price calculation."""

    car_model: str
    msrp_wan: float  # 官方指导价
    official_cash_discount_wan: float = 0.0  # 官方限时现金立减
    official_perks_discount_wan: float = 0.0  # 选装基金/权益折算
    trade_in_subsidy_wan: float = 0.0  # 地方/国家置换补贴
    net_car_price_wan: float  # 裸车成交价 = MSRP - 折扣 - 权益 - 补贴
    purchase_tax_wan: float = 0.0  # 购置税
    commercial_and_compulsory_insurance_wan: float = 0.65  # 商业险+交强险
    registration_and_misc_wan: float = 0.08  # 上牌费及杂费
    total_drive_away_price_wan: float  # 实际落地价
    hidden_fee_warnings: List[str] = Field(default_factory=list)  # 避坑提示 (金融服务费/出库费等)


class MIITVehicleDeclaration(BaseModel):
    """Public regulatory declaration parameters from MIIT (工信部)."""

    car_model: str
    product_model_code: str = ""  # 工信部产品申报型号 (如 BJ7000MBEVA1)
    manufacturer: str = ""  # 生产企业
    curb_weight_kg: float  # 整备质量 (kg)
    gross_weight_kg: float  # 总质量 (kg)
    battery_net_weight_kg: float  # 动力蓄电池组总质量 (kg)
    battery_mass_ratio: float  # 电池重量占比 (电池质量 / 整备质量)
    battery_chemistry: str  # 磷酸铁锂 / 三元锂
    battery_system_energy_density_wh_kg: float = 0.0  # 电池系统能量密度
    motor_type: str = "交流异步 / 永磁同步"
    motor_peak_power_kw: float  # 驱动电机峰值功率 (kW)
    motor_rated_power_kw: float  # 驱动电机额定(持续)功率 (kW)
    rated_to_peak_power_ratio: float  # 持续功率与峰值功率比值 (说明高速持续动力储备)
    cltc_energy_consumption_kwh_per_100km: float  # 百公里耗电量 (kWh/100km)
    top_speed_kmh: float  # 最高车速 (km/h)
    relevant_national_standards: List[str] = Field(default_factory=list)  # 对应国家标准代号


class VehicleTruthReport(BaseModel):
    """Comprehensive Consumer Truth & Anti-Marketing Fluff Report for a model."""

    car_model: str
    miit_specs: Optional[MIITVehicleDeclaration] = None
    fluff_exposures: List[MarketingFluffItem] = Field(default_factory=list)
    range_gap: Optional[RealWorldRangeGap] = None
    charging_reality: Optional[ChargingCurveReality] = None
    infotainment_cases: Optional[InfotainmentReliability] = None
    battery_safety: Optional[BatterySafetyRecord] = None
    brake_and_chassis: List[BrakeChassisControversy] = Field(default_factory=list)
    crash_test: Optional[CrashTestSummary] = None
    depreciation: Optional[DepreciationValuation] = None
    drive_away_price: Optional[DriveAwayPriceCalculation] = None
    summary_verdict: str = ""  # 最终用户立场总结

    def format_markdown(self) -> str:
        """Format the entire comprehensive truth report in structured Markdown."""
        lines = [f"# 🛡️ 【用户立场·全维度真实拆解报告】: {self.car_model}", ""]

        if self.summary_verdict:
            lines.extend([f"> **核心结论**: {self.summary_verdict}", ""])

        # 1. MIIT specs
        if self.miit_specs:
            spec = self.miit_specs
            lines.extend([
                f"## 📋 工信部申报真实参数 ({spec.product_model_code})",
                f"- **整备质量 / 电池总质量**: {spec.curb_weight_kg} kg / {spec.battery_net_weight_kg} kg (电池占比: **{spec.battery_mass_ratio*100:.1f}%**)",
                f"- **电池类型与能量密度**: {spec.battery_chemistry} ({spec.battery_system_energy_density_wh_kg} Wh/kg)",
                f"- **电机峰值 / 持续额定功率**: {spec.motor_peak_power_kw} kW / **{spec.motor_rated_power_kw} kW** (持续率: **{spec.rated_to_peak_power_ratio*100:.1f}%**)",
                f"- **百公里申报能耗**: {spec.cltc_energy_consumption_kwh_per_100km} kWh/100km | **最高车速**: {spec.top_speed_kmh} km/h",
                "",
            ])

        # 2. Fluff exposures
        if self.fluff_exposures:
            lines.extend(["## 🚫 营销去魅与硬宣传拆解", ""])
            for fluff in self.fluff_exposures:
                lines.extend([
                    f"### 话术: {fluff.claim}",
                    f"- **工程真相**: {fluff.reality}",
                    f"- **行业基准**: {fluff.industry_benchmark}",
                    f"- **避坑建议**: {fluff.debiasing_explanation}",
                    "",
                ])

        # 3. Real range & charging
        if self.range_gap:
            rg = self.range_gap
            lines.extend([
                "## ⚡ 续航真实达成率",
                f"- **CLTC标称续航**: {rg.cltc_range_km:.0f} km",
                f"- **北方冬季实测 (-10℃~0℃)**: {rg.winter_low_temp_range_km:.0f} km (达成率 **{rg.winter_achievement_rate*100:.0f}%**)",
                f"- **高速 120km/h 巡航实测**: {rg.highway_120_range_km:.0f} km (达成率 **{rg.highway_achievement_rate*100:.0f}%**)",
                f"- **衰减主因**: {'；'.join(rg.reasons)}",
                "",
            ])

        if self.charging_reality:
            ch = self.charging_reality
            lines.extend([
                "## 🔋 真实充电功率曲线",
                f"- **标称最高功率**: {ch.nominal_peak_power_kw:.0f} kW (仅在 {ch.sustained_soc_range} 短暂维持)",
                f"- **10%~80% 全程平均功率**: **{ch.average_power_10_to_80_kw:.0f} kW**",
                f"- **10%~80% 实际耗时**: 常温约 **{ch.real_time_10_to_80_min:.0f} 分钟** (冷车未预热增加约 {ch.winter_cold_charge_penalty_min:.0f} 分钟)",
                f"- **曲线解析**: {ch.reality_analysis}",
                "",
            ])

        # 4. Reliability & Safety
        if self.infotainment_cases:
            info = self.infotainment_cases
            lines.extend([
                "## 🖥️ 车机稳定性实测",
                f"- **芯片方案**: {info.soc_chip}",
                f"- **年均黑屏频次**: 约 {info.screen_blackout_rate_per_year} 次 | **卡顿重启**: {info.reboot_frequency}",
                "- **OTA历史负优化**:",
            ])
            for reg in info.ota_negative_regressions:
                lines.append(f"  • {reg}")
            lines.append("")

        if self.battery_safety:
            bs = self.battery_safety
            lines.extend([
                "## 🛡️ 电池安全与托底防护",
                f"- **电芯与封装**: {bs.battery_chemistry} ({bs.pack_supplier})",
                f"- **国标符合度**: {bs.gb_38031_compliance}",
                f"- **底部装甲结构**: {bs.bottom_protection_structure}",
                f"- **穿刺与托底真相**: {bs.puncture_and_impact_reality}",
                "",
            ])

        if self.brake_and_chassis:
            lines.extend(["## ⚙️ 底盘与机械争议真相", ""])
            for c in self.brake_and_chassis:
                lines.extend([
                    f"### {c.topic}",
                    f"- **传言**: {c.myth_or_claim}",
                    f"- **工程事实**: {c.engineering_fact}",
                    f"- **标准与冗余**: {c.material_and_standards}；{c.redundancy_mechanism}",
                    "",
                ])

        if self.crash_test:
            ct = self.crash_test
            lines.extend([
                f"## 💥 碰撞测试表现 ({ct.evaluator})",
                f"- **车内乘员安全**: **{ct.occupant_safety}** (25%偏置碰撞: {ct.small_overlap_25_result})",
                f"- **侧碰B柱侵入**: {ct.side_impact_b_pillar_result}",
                f"- **行人与主动安全**: 行人 {ct.pedestrian_safety} | 主动安全 {ct.active_safety}",
                "",
            ])

        # 5. Price & Depreciation
        if self.depreciation:
            dep = self.depreciation
            lines.extend([
                "## 📉 二手车保值率",
                f"- **1年保值率**: **{dep.one_year_residual_rate*100:.1f}%** | **3年保值率**: **{dep.three_year_residual_rate*100:.1f}%**",
                f"- **二手批发区间**: {dep.current_wholesale_price_range_wan} 万元 | **零售区间**: {dep.current_retail_price_range_wan} 万元",
                f"- **流动性评级**: {dep.market_liquidity_rating}",
                "",
            ])

        if self.drive_away_price:
            p = self.drive_away_price
            lines.extend([
                "## 💰 真实终端落地价明细",
                f"- **官方指导价**: {p.msrp_wan:.2f} 万 | **净裸车价**: **{p.net_car_price_wan:.2f} 万**",
                f"- **购置税**: {p.purchase_tax_wan:.2f} 万 | **保费**: {p.commercial_and_compulsory_insurance_wan:.2f} 万 | **上牌**: {p.registration_and_misc_wan:.2f} 万",
                f"- ➡️ **真实全包落地价**: **{p.total_drive_away_price_wan:.2f} 万元**",
                "",
            ])

        return "\n".join(lines)
