"""
Constraint Reconciliation Engine for AutoVend Agent (src/agent/reconciliation.py).

Inspects extracted UserProfile and VehicleNeeds for incompatible constraints:
1. Hard Conflicts: physically or economically impossible constraints (e.g. 15万买保时捷, 5座坐7人).
2. Soft Conflicts: experience compromises or usage friction (e.g. 极寒无桩开纯电, 紧凑SUV装全家大件行李).
3. Generates targeted trade-off matrices and proactive guidance instructions for the Agent.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.agent.schemas import SessionState

logger = logging.getLogger(__name__)


class ConstraintConflict(BaseModel):
    """Represents a conflict detected between user constraints."""

    conflict_type: str  # e.g., "BUDGET_VS_BRAND", "SEATS_VS_FAMILY", "SIZE_VS_PARKING", "POWERTRAIN_VS_USAGE", "BUDGET_VS_TECH"
    conflicting_fields: List[str]
    description: str
    suggested_options: List[str]
    severity: str = "HARD"  # "HARD" (physical/budget impossible) or "SOFT" (experience/trade-off compromise)
    trade_off_options: List[Dict[str, str]] = Field(default_factory=list)

    def to_system_note(self) -> str:
        """Format conflict into a system note for response generator."""
        opts = " 或 ".join([f"({i + 1}) {opt}" for i, opt in enumerate(self.suggested_options)])
        trade_offs = ""
        if self.trade_off_options:
            to_lines = [
                f"方案{i+1}: {t.get('description', '')} (建议行动: {t.get('action', '')})"
                for i, t in enumerate(self.trade_off_options)
            ]
            trade_offs = "；" + "；".join(to_lines)
        return (
            f"[系统约束提示 - 需求冲突通知] ({self.severity}级别): {self.description}。"
            f"请在回复中礼貌向客户说明此矛盾，并给出折中选择方案：{opts}{trade_offs}。"
        )


def _parse_budget_max_k_yuan(price_str: str) -> Optional[float]:
    """
    Parse budget string into upper bound value in 10k RMB (万元).
    Examples: '20万以内' -> 20.0, '15-20万' -> 20.0, '30万左右' -> 35.0
    Returns None if budget cannot be parsed as a numeric bound.
    """
    if not price_str:
        return None

    # Check numbers followed by 万
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*万", price_str)
    if matches:
        nums = [float(m) for m in matches]
        return max(nums)

    # Check raw numbers
    matches_raw = re.findall(r"(\d+)", price_str)
    if matches_raw:
        nums = [float(m) for m in matches_raw]
        val = max(nums)
        if val > 1000:
            return val / 10000.0
        return val

    return None


# Luxury brands and their typical entry-level minimum price in 10k RMB
LUXURY_BRANDS_MIN_PRICE: Dict[str, float] = {
    "保时捷": 55.0,
    "porsche": 55.0,
    "奔驰": 25.0,
    "mercedes": 25.0,
    "宝马": 24.0,
    "bmw": 24.0,
    "奥迪": 20.0,
    "audi": 20.0,
    "路虎": 38.0,
    "land rover": 38.0,
    "沃尔沃": 22.0,
    "volvo": 22.0,
    "雷克萨斯": 23.0,
    "lexus": 23.0,
    "仰望": 100.0,
    "迈巴赫": 150.0,
}

# Large vehicle categories minimum price estimate
LARGE_VEHICLE_MIN_PRICE: Dict[str, float] = {
    "大型suv": 40.0,
    "全尺寸suv": 50.0,
    "大型mpv": 30.0,
    "跑车": 30.0,
}


def check_budget_vs_brand_or_class(state: SessionState) -> Optional[ConstraintConflict]:
    """Check if budget ceiling conflicts with requested luxury brand or high-tier category (HARD)."""
    explicit = state.needs.explicit
    budget_k = _parse_budget_max_k_yuan(explicit.price)
    if budget_k is None:
        return None

    brand_raw = (explicit.brand or "").strip().lower()
    category_raw = (explicit.vehicle_category_bottom or "").strip().lower()

    # Check luxury brand match
    for lux_brand, min_price in LUXURY_BRANDS_MIN_PRICE.items():
        if lux_brand in brand_raw and budget_k < min_price:
            return ConstraintConflict(
                conflict_type="BUDGET_VS_BRAND",
                severity="HARD",
                conflicting_fields=["explicit.price", "explicit.brand"],
                description=f"客户预算上限为 {budget_k:.0f} 万元，但想要看 {explicit.brand} 品牌（起售价通常在 {min_price:.0f} 万以上）",
                suggested_options=[
                    f"适当提升预算至 {min_price:.0f} 万元以上以支持 {explicit.brand}",
                    f"在 {budget_k:.0f} 万预算范围内考虑同级别的优质自主/新势力品牌",
                ],
                trade_off_options=[
                    {
                        "description": f"上调预算至 {min_price:.0f} 万区间",
                        "action": f"解锁 {explicit.brand} 入门级车型配置",
                    },
                    {
                        "description": f"保持 {budget_k:.0f} 万上限并切换主流高性价比品牌",
                        "action": "获得更高阶智驾与豪华舒适满配",
                    },
                ],
            )

    # Check large vehicle category match
    for cat_name, min_price in LARGE_VEHICLE_MIN_PRICE.items():
        if cat_name in category_raw and budget_k < min_price:
            return ConstraintConflict(
                conflict_type="BUDGET_VS_CATEGORY",
                severity="HARD",
                conflicting_fields=["explicit.price", "explicit.vehicle_category_bottom"],
                description=f"客户预算上限为 {budget_k:.0f} 万元，但希望选购 {explicit.vehicle_category_bottom}（市场均价通常在 {min_price:.0f} 万以上）",
                suggested_options=[
                    "调整至中型/紧凑型车型（如中型SUV/MPV）",
                    f"适当提高预算至 {min_price:.0f} 万元左右",
                ],
                trade_off_options=[
                    {
                        "description": "车身级别降一级选购中型SUV",
                        "action": f"在 {budget_k:.0f} 万内获得宽裕乘坐空间",
                    },
                    {
                        "description": f"追加预算至 {min_price:.0f} 万左右",
                        "action": f"支持正规大厂 {explicit.vehicle_category_bottom} 车型",
                    },
                ],
            )

    return None


def check_seat_layout_vs_family(state: SessionState) -> Optional[ConstraintConflict]:
    """Check if requested seating layout is insufficient for user's family size (HARD)."""
    family = (state.profile.family_size or "").strip()
    seat_req = (state.needs.explicit.seat_layout or "").strip()

    if not family or not seat_req:
        return None

    # Parse family size
    fam_count = 0
    fam_match = re.search(r"(\d+)", family)
    if fam_match:
        fam_count = int(fam_match.group(1))
    elif any(k in family for k in ["三代", "大家庭", "6人", "7人"]):
        fam_count = 6

    # Parse requested seats
    seat_count = 0
    seat_match = re.search(r"(\d+)", seat_req)
    if seat_match:
        seat_count = int(seat_match.group(1))
    elif "2座" in seat_req or "两座" in seat_req:
        seat_count = 2
    elif "5座" in seat_req or "五座" in seat_req:
        seat_count = 5

    if fam_count >= 6 and 0 < seat_count <= 5:
        return ConstraintConflict(
            conflict_type="SEATS_VS_FAMILY",
            severity="HARD",
            conflicting_fields=["profile.family_size", "explicit.seat_layout"],
            description=f"客户家庭人数较多（{family}），但目前选定的座椅布局为 {seat_req}，无法满足全家同时出行需求",
            suggested_options=[
                "推荐大6座/7座 SUV 或 MPV 车型，保障全家出行舒适度",
                "确认是否主要为日常单人/双人通勤使用（非全家出行）",
            ],
            trade_off_options=[
                {
                    "description": "升级为 2+2+2 大六座独立座椅布局",
                    "action": "二排进出便捷，全家老少皆能舒适乘坐",
                },
                {
                    "description": "保持五座车型但增加第二辆小车考虑",
                    "action": "日常通勤灵活，长途由两车结伴出行",
                },
            ],
        )

    return None


def check_size_vs_parking(state: SessionState) -> Optional[ConstraintConflict]:
    """Check if requested vehicle size/category conflicts with novice driver or narrow parking (SOFT)."""
    parking = (state.profile.parking_conditions or "").strip()
    driver = (state.profile.target_driver or "").strip()
    category = (state.needs.explicit.vehicle_category_bottom or "").strip()
    implicit_space = (state.needs.implicit.size or "").strip()

    is_narrow = any(k in parking for k in ["窄车位", "立体车库", "老旧小区", "难停车"])
    is_novice = any(k in driver for k in ["新手", "刚拿驾照", "女新手"])
    is_huge = any(
        k in category or k in implicit_space for k in ["大型", "全尺寸", "5米以上", "大型MPV"]
    )

    if (is_narrow or is_novice) and is_huge:
        return ConstraintConflict(
            conflict_type="SIZE_VS_PARKING",
            severity="SOFT",
            conflicting_fields=["profile.parking_conditions", "explicit.vehicle_category_bottom"],
            description=f"客户停车条件或驾驶经验为'{parking or driver}'，但关注大型/全尺寸车型，日常停放及驾驶难度较大",
            suggested_options=[
                "推介配备自动泊车/360全景影像的高配置中型车",
                "建议考虑车身更为灵活的中紧凑型车型",
            ],
            trade_off_options=[
                {
                    "description": "选配高阶高精度自动泊车及循迹倒车功能",
                    "action": "化解老旧窄车位及狭窄胡同挪车困扰",
                },
                {
                    "description": "选择中型车（车长4.7-4.8米）",
                    "action": "兼顾车内空间与日常狭小车位停放容错率",
                },
            ],
        )

    return None


def check_powertrain_vs_usage(state: SessionState) -> Optional[ConstraintConflict]:
    """Check pure electric (BEV) against extreme cold or frequent long trips without charging pile (SOFT)."""
    p_type = (getattr(state.needs.explicit, "powertrain_type", "") or "").strip().lower()
    residence = (getattr(state.profile, "residence", "") or "").strip()
    usability = (getattr(state.needs.implicit, "vehicle_usability", "") or "").strip()
    driving_range = (getattr(state.needs.implicit, "driving_range", "") or "").strip()

    context_str = f"{residence} {usability} {driving_range}"
    is_bev = any(k in p_type for k in ["纯电", "bev", "电动车"])
    is_cold = any(k in context_str for k in ["东北", "极寒", "北方冬天", "零下", "哈尔滨", "长春", "沈阳"])
    is_long_trip = any(k in context_str for k in ["长途自驾", "跨省跑长途", "无固定车位", "没有充电桩", "长途"])

    if is_bev and (is_cold or is_long_trip):
        scenario_desc = residence or usability or "长途/极寒场景"
        return ConstraintConflict(
            conflict_type="POWERTRAIN_VS_USAGE",
            severity="SOFT",
            conflicting_fields=["needs.explicit.powertrain_type", "profile.residence"],
            description=f"客户关注纯电动车型，但用车环境或场景包含'{scenario_desc}'，可能存在低温里程衰减或长途排队补能焦虑",
            suggested_options=[
                "考虑插电混动 (PHEV) 或可油可电的增程式 (REEV) 车型",
                "若坚持纯电，建议选择配备高效热泵空调与 800V 高压超充平台的大电池版本",
            ],

            trade_off_options=[
                {
                    "description": "转向增程/插混混动架构",
                    "action": "城市纯电通勤低成本，长途极寒燃油直驱零焦虑",
                },
                {
                    "description": "选购 800V 纯电平台并选装冬季电池保温包",
                    "action": "提升低温充电倍率与续航达成率",
                },
            ],
        )

    return None


def check_budget_vs_tech_features(state: SessionState) -> Optional[ConstraintConflict]:
    """Check if budget under 16万 conflicts with demanding high-tier LiDAR / NOA smart driving (HARD)."""
    explicit = state.needs.explicit
    budget_k = _parse_budget_max_k_yuan(explicit.price)
    if budget_k is None:
        return None

    design = (explicit.design_style or "").strip()
    implicit_safety = (state.needs.implicit.safety or "").strip()

    wants_high_noa = any(
        k in (design + implicit_safety)
        for k in ["激光雷达", "城市noa", "高阶智驾", "自动领航", "端到端智驾"]
    )

    if wants_high_noa and budget_k < 16.0:
        return ConstraintConflict(
            conflict_type="BUDGET_VS_TECH",
            severity="HARD",
            conflicting_fields=["needs.explicit.price", "needs.explicit.design_style"],
            description=f"客户预算上限为 {budget_k:.0f} 万元，但明确要求搭载激光雷达或城市高阶NOA系统（当前量产车门槛通常在 18 万以上）",
            suggested_options=[
                "将购车预算微调至 18-20 万元区间，选择搭载高阶激光雷达智驾的成熟新势力车型",
                f"在 {budget_k:.0f} 万元预算内选择配备成熟可靠 L2 级基础辅助驾驶（如自适应巡航+车道居中）的高性价比车型",
            ],
            trade_off_options=[
                {
                    "description": "预算提升 2-3 万元",
                    "action": "直接买到配备双 Orin-X 与激光雷达的高阶智驾标杆车型",
                },
                {
                    "description": "维持现有预算并专注 L2 级实用功能",
                    "action": "满足高速定速巡航与车道保持，兼顾购车经济性",
                },
            ],
        )

    return None


def reconcile_constraints(state: SessionState) -> List[ConstraintConflict]:
    """
    Run all constraint reconciliation checks on SessionState.
    Returns a list of detected ConstraintConflicts (both HARD and SOFT).
    """
    conflicts: List[ConstraintConflict] = []

    for check_fn in [
        check_budget_vs_brand_or_class,
        check_seat_layout_vs_family,
        check_size_vs_parking,
        check_powertrain_vs_usage,
        check_budget_vs_tech_features,
    ]:
        try:
            conflict = check_fn(state)
            if conflict:
                conflicts.append(conflict)
        except Exception as e:
            logger.warning(f"Error running constraint check {check_fn.__name__}: {e}")

    return conflicts
