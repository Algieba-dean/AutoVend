"""
Generic Automotive Technology Terminology Package (src/terminology/generic/__init__.py).
Aggregates and exports standard automotive technical concepts across 6 core domains:
- 悬架形式 (chassis.py, 18 entries)
- 电池形态 (battery.py, 17 entries)
- 补能与电气 (powertrain.py, 17 entries)
- 智驾与算法 (autonomous.py, 17 entries)
- 智能座舱 (cockpit.py, 16 entries)
- 车身安全 (body_safety.py, 17 entries)
Total: 102 generic technical concepts.
"""

from typing import List

from src.terminology.generic.autonomous import GENERIC_AUTONOMOUS_TECHNOLOGIES
from src.terminology.generic.battery import GENERIC_BATTERY_TECHNOLOGIES
from src.terminology.generic.body_safety import GENERIC_BODY_SAFETY_TECHNOLOGIES
from src.terminology.generic.chassis import GENERIC_CHASSIS_TECHNOLOGIES
from src.terminology.generic.cockpit import GENERIC_COCKPIT_TECHNOLOGIES
from src.terminology.generic.powertrain import GENERIC_POWERTRAIN_TECHNOLOGIES
from src.terminology.schemas import TechnologyEntity

GENERIC_ALL_TECHNOLOGIES: List[TechnologyEntity] = (
    GENERIC_CHASSIS_TECHNOLOGIES
    + GENERIC_BATTERY_TECHNOLOGIES
    + GENERIC_POWERTRAIN_TECHNOLOGIES
    + GENERIC_AUTONOMOUS_TECHNOLOGIES
    + GENERIC_COCKPIT_TECHNOLOGIES
    + GENERIC_BODY_SAFETY_TECHNOLOGIES
)

__all__ = [
    "GENERIC_CHASSIS_TECHNOLOGIES",
    "GENERIC_BATTERY_TECHNOLOGIES",
    "GENERIC_POWERTRAIN_TECHNOLOGIES",
    "GENERIC_AUTONOMOUS_TECHNOLOGIES",
    "GENERIC_COCKPIT_TECHNOLOGIES",
    "GENERIC_BODY_SAFETY_TECHNOLOGIES",
    "GENERIC_ALL_TECHNOLOGIES",
]
