"""
Unified Truth Engine Service (src/truth_engine/service.py).
Single entry-point for marketing debiasing, MIIT specs deconstruction,
reliability defect cases, and transparent price calculations.
"""

import logging
from typing import Any, Dict, List, Optional

from src.truth_engine.debiaser import MarketingDebiaser
from src.truth_engine.miit_platform import MIITSpecsPlatform
from src.truth_engine.models import VehicleTruthReport
from src.truth_engine.price_valuation import PriceValuationEngine
from src.truth_engine.reliability_cases import ReliabilityCaseRepository

logger = logging.getLogger(__name__)


class TruthEngineService:
    """Unified service orchestrating consumer truth, de-biasing, and engineering transparency."""

    _instance: Optional["TruthEngineService"] = None

    def __init__(self):
        self.debiaser = MarketingDebiaser.get_instance()
        self.miit_platform = MIITSpecsPlatform.get_instance()
        self.reliability_repo = ReliabilityCaseRepository.get_instance()
        self.price_engine = PriceValuationEngine.get_instance()

    @classmethod
    def get_instance(cls) -> "TruthEngineService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def deconstruct_vehicle_specs(self, car_model: str) -> Dict[str, Any]:
        """
        Deconstruct vehicle specifications against MIIT declaration & national standards.
        """
        spec = self.miit_platform.find_specs(car_model)
        markdown = self.miit_platform.format_deconstruction_markdown(car_model)
        details = self.miit_platform.deconstruct_parameters(spec) if spec else {}
        return {
            "car_model": car_model,
            "found_in_miit": spec is not None,
            "details": details,
            "summary_markdown": markdown,
        }

    def uncover_marketing_fluff(
        self, claim_or_text: str, car_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect and strip marketing fluff, expose invalid claims, and calculate real-world physical gaps.
        """
        fluff_items = self.debiaser.inspect_text_for_fluff(claim_or_text)
        detected_model = self.miit_platform.extract_model_name_from_text(f"{car_model or ''} {claim_or_text}")
        effective_model = detected_model or (car_model if car_model and car_model not in ("当前车型", "目标车型") else None)
        markdown = self.debiaser.generate_debiasing_summary(claim_or_text, car_model=effective_model)
        range_gap = self.debiaser.get_range_gap(effective_model) if effective_model else None
        charging = self.debiaser.get_charging_curve_reality(effective_model) if effective_model else None

        return {
            "detected_fluff_count": len(fluff_items),
            "fluff_items": [item.model_dump() for item in fluff_items],
            "range_gap": range_gap.model_dump() if range_gap else None,
            "charging_reality": charging.model_dump() if charging else None,
            "summary_markdown": markdown,
        }

    def get_real_owner_feedback_and_safety_cases(
        self, car_model: str, query_filter: str = ""
    ) -> Dict[str, Any]:
        """
        Retrieve real owner software/hardware defects, battery thermal cases,
        chassis/brake engineering truths, C-IASI crash results, and transparent pricing.
        """
        detected_in_filter = self.miit_platform.extract_model_name_from_text(query_filter)
        if detected_in_filter:
            target_model = detected_in_filter
        elif car_model and car_model not in ("当前车型", "目标车型"):
            target_model = car_model
        else:
            target_model = self.miit_platform.extract_model_name_from_text(car_model) or car_model

        markdown = self.reliability_repo.format_reliability_report_markdown(
            car_model=target_model, query_filter=query_filter
        )
        info = self.reliability_repo.find_infotainment_record(target_model)
        batt = self.reliability_repo.find_battery_safety(target_model)
        crash = self.reliability_repo.find_crash_test(target_model)
        controversies = self.reliability_repo.get_chassis_brake_controversies(query_filter)
        dep = self.price_engine.get_depreciation_data(target_model)
        calc = self.price_engine.calculate_drive_away_price(target_model)

        return {
            "car_model": target_model,
            "infotainment": info.model_dump() if info else None,
            "battery_safety": batt.model_dump() if batt else None,
            "crash_test": crash.model_dump() if crash else None,
            "controversies": [c.model_dump() for c in controversies],
            "depreciation": dep.model_dump() if dep else None,
            "drive_away_price": calc.model_dump() if calc else None,
            "summary_markdown": markdown,
        }

    def calculate_drive_away_price(
        self,
        car_model: str,
        msrp_wan: Optional[float] = None,
        cash_discount: float = 0.0,
        perks_discount: float = 0.0,
        trade_in_subsidy: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Calculate transparent drive-away price with zero hidden dealer markups.
        """
        calc = self.price_engine.calculate_drive_away_price(
            car_model=car_model,
            msrp_wan=msrp_wan,
            cash_discount_wan=cash_discount,
            perks_discount_wan=perks_discount,
            trade_in_subsidy_wan=trade_in_subsidy,
        )
        dep = self.price_engine.get_depreciation_data(car_model)
        markdown = self.price_engine.format_price_and_depreciation_markdown(
            car_model=car_model,
            msrp_wan=msrp_wan,
            cash_discount=cash_discount,
            perks_discount=perks_discount,
            trade_in_subsidy=trade_in_subsidy,
        )
        return {
            "calculation": calc.model_dump(),
            "depreciation": dep.model_dump() if dep else None,
            "summary_markdown": markdown,
        }

    def build_full_truth_report(self, car_model: str) -> VehicleTruthReport:
        """Build an end-to-end comprehensive Truth Report."""
        miit = self.miit_platform.find_specs(car_model)
        rg = self.debiaser.get_range_gap(car_model)
        ch = self.debiaser.get_charging_curve_reality(car_model)
        info = self.reliability_repo.find_infotainment_record(car_model)
        batt = self.reliability_repo.find_battery_safety(car_model)
        controversies = self.reliability_repo.get_chassis_brake_controversies()
        crash = self.reliability_repo.find_crash_test(car_model)
        dep = self.price_engine.get_depreciation_data(car_model)
        calc = self.price_engine.calculate_drive_away_price(car_model)

        # Detect any standard fluff for this model
        fluff_list = self.debiaser.inspect_text_for_fluff(f"{car_model} 92号油 全栈自研 超跑级加速 终身质保 800V 零自燃")

        return VehicleTruthReport(
            car_model=car_model,
            miit_specs=miit,
            fluff_exposures=fluff_list,
            range_gap=rg,
            charging_reality=ch,
            infotainment_cases=info,
            battery_safety=batt,
            brake_and_chassis=controversies,
            crash_test=crash,
            depreciation=dep,
            drive_away_price=calc,
            summary_verdict=f"【{car_model} 真实拆解结论】：回归工信部申报客观参数与物理常识，杜绝营销神话，理性购车。",
        )

    def format_full_truth_report_markdown(self, car_model: str) -> str:
        """Format an end-to-end comprehensive truth report in Markdown."""
        report = self.build_full_truth_report(car_model)
        return report.format_markdown()

    def get_national_standards(self) -> Dict[str, Dict[str, Any]]:
        """Retrieve statutory national standards reference database."""
        return self.miit_platform.get_national_standards()

    def get_known_models(self) -> List[str]:
        """Retrieve list of all benchmark models in the truth engine."""
        return self.miit_platform.get_all_models()

    def generate_truth_sales_note(
        self, query_text: str, car_model: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate proactive system prompt note for the Agent when consumer truth,
        marketing fluff, safety controversies, or price calculations are touched.
        """
        triggers = [
            "92号油", "92号汽油", "吃粗粮", "全栈自研", "超跑级加速", "秒杀超跑",
            "800v", "伪800v", "闪充", "零自燃", "千公里", "大压铸",
            "踩断", "踏板", "刹车踩断", "塑料刹车", "线控刹车", "刹车失灵", "断轴",
            "黑屏", "死机", "OTA负优化", "锁电", "电池自燃", "起火", "热失控", "穿刺", "托底",
            "工信部", "申报参数", "整备质量", "额定功率", "国标", "GB 38031", "GB 7258", "CLTC",
            "虚标", "冬季续航", "打折", "高速续航", "充电慢", "峰值功率",
            "中保研", "C-IASI", "碰撞测试", "A柱", "侵入",
            "保值率", "二手车", "落地价", "金融服务费", "出库费", "套路"
        ]
        text_to_check = f"{query_text} {car_model or ''}"
        matched = any(t in text_to_check.lower() for t in triggers)
        fluff_detected = bool(self.debiaser.inspect_text_for_fluff(query_text))

        if not matched and not fluff_detected:
            return None

        # Resolve vehicle model: query explicit mention takes priority
        detected_in_query = self.miit_platform.extract_model_name_from_text(query_text)
        target_model = detected_in_query or (car_model if car_model and car_model not in ("当前车型", "目标车型") else None)

        # Build combined note
        notes = []

        # 1. Debiaser & nominal vs real
        debias_md = self.debiaser.generate_debiasing_summary(query_text, car_model=target_model)
        if debias_md:
            notes.append(debias_md)

        # 2. Safety controversy or reliability if asked
        if any(k in query_text for k in ("刹车", "踩断", "塑料", "断轴", "电池", "自燃", "起火", "黑屏", "死机", "OTA", "中保研", "碰撞")):
            model_for_rel = target_model or "当前关注车型"
            rel_md = self.reliability_repo.format_reliability_report_markdown(
                model_for_rel, query_filter=query_text
            )
            notes.append(rel_md)

        # 3. MIIT parameters if queried
        if any(k in query_text for k in ("工信部", "申报", "整备质量", "电池重量", "额定功率", "国标", "真实参数")):
            if target_model:
                miit_md = self.miit_platform.format_deconstruction_markdown(target_model)
                notes.append(miit_md)
            else:
                notes.append("💡 提示：请说明具体意向车型（如小米SU7、特斯拉Model 3/Y、问界M9、极氪001等），以调取工信部真实申报参数与国标拆解。")

        # 4. Price & depreciation if queried
        if any(k in query_text for k in ("落地价", "多少钱落地", "落地", "保值率", "二手车", "优惠", "补贴", "金融服务费")):
            if target_model:
                price_md = self.price_engine.format_price_and_depreciation_markdown(target_model)
                notes.append(price_md)
            else:
                notes.append("💡 提示：请说明目标车型以计算透明落地全包价（已自动剔除4S店金融服务费与出库费套路）及二手保值率。")

        if not notes:
            return None

        directive = (
            "【AUTO-VEND CONSUMER TRUTH DIRECTIVE (用户立场·营销去魅拆解准则)】:\n"
            "用户正在关切车辆的真实体验、宣传真实性、被动安全、电池隐患、故障率或终端落地底价。\n"
            "你必须坚持【绝对客观、中立、站在用户真实利益视角】的拆解原则：\n"
            "1. 坚决剥离无意义的硬宣传与虚假噱头（例如讲清加92号油是混动常识并非独创；讲清全栈自研与Tier-1供应链硬件关系）；\n"
            "2. 客观呈现物理差距（明示CLTC续航在冬季和120km/h高速下的客观折扣与电池热力学限制）；\n"
            "3. 运用严密的结构力学与国家标准解答安全焦虑（如说明玻纤工程塑料刹车踏板的碰撞溃缩解耦防断腿原理，以及线控刹车机械液压备份冗余）；\n"
            "4. 曝光4S店金融服务费、出库费等隐形乱收费套路，给出清晰透明的落地价算法。\n\n"
        )
        return directive + "\n\n".join(notes)
