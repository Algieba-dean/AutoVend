"""
Generic Automotive Technical Terminology Registry (src/terminology/generic_registry.py).

Comprehensive structured encyclopedia of standard automotive engineering concepts covering 6 core categories:
1. 悬架形式 (麦弗逊 / 双叉臂 / 五连杆 / CDC连续阻尼减振 / 单双腔空气悬架 / 后轮主动转向 等)
2. 电池形态 (三元锂 / 磷酸铁锂 / 半固态与固态电池 / CTB / CTC / 4680大圆柱电芯 等)
3. 补能与电气 (增程EREV / 插电混动PHEV / 单双三四电机分布式驱动 / 800V高压碳化硅 / 4C-5C超充 / 全自动换电 等)
4. 智驾与算法 (端到端E2E大模型 / Occupancy占用网络 / BEV+Transformer / 激光雷达 / 无图城市NOA 等)
5. 智能座舱 (AR-HUD / 高通8295 / 语音大模型 / OLED-MiniLED / 杜比全景声 / 手车互联 / 零重力座椅 等)
6. 车身安全 (一体化大压铸 / 热成型硼钢 / 钢铝混合车身 / 硬件双冗余 / 超长保压气帘 / AEB / 电池装甲 等)
"""

from typing import Dict, List

from src.terminology.generic import (
    GENERIC_ALL_TECHNOLOGIES,
    GENERIC_AUTONOMOUS_TECHNOLOGIES,
    GENERIC_BATTERY_TECHNOLOGIES,
    GENERIC_BODY_SAFETY_TECHNOLOGIES,
    GENERIC_CHASSIS_TECHNOLOGIES,
    GENERIC_COCKPIT_TECHNOLOGIES,
    GENERIC_POWERTRAIN_TECHNOLOGIES,
)
from src.terminology.schemas import TechnologyEntity

GENERIC_AUTOMOTIVE_TECHNOLOGIES: List[TechnologyEntity] = GENERIC_ALL_TECHNOLOGIES

# Quick access mapping index for generic technologies
GENERIC_TECHNOLOGY_REGISTRY: Dict[str, TechnologyEntity] = {
    entity.id: entity for entity in GENERIC_AUTOMOTIVE_TECHNOLOGIES
}

__all__ = [
    "GENERIC_AUTOMOTIVE_TECHNOLOGIES",
    "GENERIC_TECHNOLOGY_REGISTRY",
    "GENERIC_CHASSIS_TECHNOLOGIES",
    "GENERIC_BATTERY_TECHNOLOGIES",
    "GENERIC_POWERTRAIN_TECHNOLOGIES",
    "GENERIC_AUTONOMOUS_TECHNOLOGIES",
    "GENERIC_COCKPIT_TECHNOLOGIES",
    "GENERIC_BODY_SAFETY_TECHNOLOGIES",
]
