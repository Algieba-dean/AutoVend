"""
Constraint Reconciliation Engine for AutoVend Agent.

Inspects extracted UserProfile and VehicleNeeds for incompatible constraints
(e.g., budget limits vs luxury brands, seat layout vs family size, etc.)
and generates targeted system instructions for trade-off resolution.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.agent.schemas import SessionState, UserProfile, VehicleNeeds

logger = logging.getLogger(__name__)


class ConstraintConflict(BaseModel):
    """Represents a conflict detected between user constraints."""

    conflict_type: str  # e.g., "BUDGET_VS_BRAND", "SEATS_VS_FAMILY", "SIZE_VS_PARKING"
    conflicting_fields: List[str]
    description: str
    suggested_options: List[str]

    def to_system_note(self) -> str:
        """Format conflict into a system note for response generator."""
        opts = " 或 ".join([f"({i+1}) {opt}" for i, opt in enumerate(self.suggested_options)])
        return (
            f"[系统约束提示 - 需求冲突通知]: {self.description}。"
            f"请在回复中礼貌向客户说明此矛盾，并给出折中选择方案：{opts}。"
        )


def _parse_budget_max_k_yuan(prize_str: str) -> Optional[float]:
    """
    Parse budget string into upper bound value in 10k RMB (万元).
    Examples: '20万以内' -> 20.0, '15-20万' -> 20.0, '30万左右' -> 35.0
    Returns None if budget cannot be parsed as a numeric bound.
    """
    if not prize_str:
        return None
    
    # Check numbers followed by 万
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*万", prize_str)
    if matches:
        nums = [float(m) for m in matches]
        return max(nums)
    
    # Check raw numbers
    matches_raw = re.findall(r"(\d+)", prize_str)
    if matches_raw:
        nums = [float(m) for m in matches_raw]
        val = max(nums)
        # If numbers look like full RMB e.g. 200000 -> 20
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
    """Check if budget ceiling conflicts with requested luxury brand or high-tier category."""
    explicit = state.needs.explicit
    budget_k = _parse_budget_max_k_yuan(explicit.prize)
    if budget_k is None:
        return None

    brand_raw = (explicit.brand or "").strip().lower()
    category_raw = (explicit.vehicle_category_bottom or "").strip().lower()

    # Check luxury brand match
    for lux_brand, min_price in LUXURY_BRANDS_MIN_PRICE.items():
        if lux_brand in brand_raw and budget_k < min_price:
            return ConstraintConflict(
                conflict_type="BUDGET_VS_BRAND",
                conflicting_fields=["explicit.prize", "explicit.brand"],
                description=f"客户预算上限为 {budget_k:.0f} 万元，但想要看 {explicit.brand} 品牌（起售价通常在 {min_price:.0f} 万以上）",
                suggested_options=[
                    f"适当提升预算至 {min_price:.0f} 万元以上以支持 {explicit.brand}",
                    f"在 {budget_k:.0f} 万预算范围内考虑同级别的优质自主/新势力品牌",
                ],
            )

    # Check large vehicle category match
    for cat_name, min_price in LARGE_VEHICLE_MIN_PRICE.items():
        if cat_name in category_raw and budget_k < min_price:
            return ConstraintConflict(
                conflict_type="BUDGET_VS_CATEGORY",
                conflicting_fields=["explicit.prize", "explicit.vehicle_category_bottom"],
                description=f"客户预算上限为 {budget_k:.0f} 万元，但希望选购 {explicit.vehicle_category_bottom}（市场均价通常在 {min_price:.0f} 万以上）",
                suggested_options=[
                    f"调整至中型/紧凑型车型（如中型SUV/MPV）",
                    f"适当提高预算至 {min_price:.0f} 万元左右",
                ],
            )

    return None


def check_seat_layout_vs_family(state: SessionState) -> Optional[ConstraintConflict]:
    """Check if requested seating layout is insufficient for user's family size."""
    family = (state.profile.family_size or "").strip()
    seat_req = (state.needs.explicit.seat_layout or "").strip()

    if not family or not seat_req:
        return None

    # Parse family size
    fam_count = 0
    fam_match = re.search(r"(\d+)", family)
    if fam_match:
        fam_count = int(fam_match.group(1))
    elif "三代" in family or "大家庭" in family or "6人" in family or "7人" in family:
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
            conflicting_fields=["profile.family_size", "explicit.seat_layout"],
            description=f"客户家庭人数较多（{family}），但目前选定的座椅布局为 {seat_req}，无法满足全家同时出行需求",
            suggested_options=[
                "推荐大6座/7座 SUV 或 MPV 车型，保障全家出行舒适度",
                "确认是否主要为日常单人/双人通勤使用（非全家出行）",
            ],
        )

    return None


def check_size_vs_parking(state: SessionState) -> Optional[ConstraintConflict]:
    """Check if requested vehicle size/category conflicts with novice driver or narrow parking."""
    parking = (state.profile.parking_conditions or "").strip()
    driver = (state.profile.target_driver or "").strip()
    category = (state.needs.explicit.vehicle_category_bottom or "").strip()
    implicit_space = (state.needs.implicit.size or "").strip()

    is_narrow = any(k in parking for k in ["窄车位", "立体车库", "老旧小区", "难停车"])
    is_novice = any(k in driver for k in ["新手", "刚拿驾照", "女新手"])
    is_huge = any(k in category or k in implicit_space for k in ["大型", "全尺寸", "5米以上", "大型MPV"])

    if (is_narrow or is_novice) and is_huge:
        return ConstraintConflict(
            conflict_type="SIZE_VS_PARKING",
            conflicting_fields=["profile.parking_conditions", "explicit.vehicle_category_bottom"],
            description=f"客户停车条件或驾驶经验为'{parking or driver}'，但关注大型/全尺寸车型，日常停放及驾驶难度较大",
            suggested_options=[
                "推介配备自动泊车/360全景影像的高配置中型车",
                "建议考虑车身更为灵活的中紧凑型车型",
            ],
        )

    return None


def reconcile_constraints(state: SessionState) -> List[ConstraintConflict]:
    """
    Run all constraint reconciliation checks on SessionState.
    Returns a list of detected ConstraintConflicts.
    """
    conflicts: List[ConstraintConflict] = []

    for check_fn in [
        check_budget_vs_brand_or_class,
        check_seat_layout_vs_family,
        check_size_vs_parking,
    ]:
        try:
            conflict = check_fn(state)
            if conflict:
                conflicts.append(conflict)
        except Exception as e:
            logger.warning(f"Error running constraint check {check_fn.__name__}: {e}")

    return conflicts
