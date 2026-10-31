"""
OEM Proprietary Automotive Technology Registry (src/terminology/registry.py).

Comprehensive structured taxonomy database covering leading Chinese and global automakers:
BYD, Xiaomi, HIMA (Huawei/AITO/Luxeed/Stelato/Maextro), Tesla, Li Auto, Zeekr/Geely, NIO, XPENG,
and other OEMs, aggregated from modular brand registries.
"""

from typing import Dict, List

from src.terminology.brands import (
    BYD_TECHNOLOGIES,
    HIMA_TECHNOLOGIES,
    LI_AUTO_TECHNOLOGIES,
    NIO_TECHNOLOGIES,
    OTHER_OEM_TECHNOLOGIES,
    TESLA_TECHNOLOGIES,
    XIAOMI_TECHNOLOGIES,
    XPENG_TECHNOLOGIES,
    ZEEKR_TECHNOLOGIES,
)
from src.terminology.generic_registry import (
    GENERIC_AUTOMOTIVE_TECHNOLOGIES,
    GENERIC_TECHNOLOGY_REGISTRY,
)
from src.terminology.schemas import TechnologyEntity

# Comprehensive catalog of OEM proprietary technologies
OEM_TECHNOLOGIES: List[TechnologyEntity] = (
    BYD_TECHNOLOGIES
    + XIAOMI_TECHNOLOGIES
    + HIMA_TECHNOLOGIES
    + TESLA_TECHNOLOGIES
    + LI_AUTO_TECHNOLOGIES
    + ZEEKR_TECHNOLOGIES
    + NIO_TECHNOLOGIES
    + XPENG_TECHNOLOGIES
    + OTHER_OEM_TECHNOLOGIES
)

# Complete unified catalog of OEM proprietary and generic automotive technologies
ALL_AUTOMOTIVE_TECHNOLOGIES: List[TechnologyEntity] = (
    OEM_TECHNOLOGIES + GENERIC_AUTOMOTIVE_TECHNOLOGIES
)

# Quick access mapping index by canonical ID (covers both OEM proprietary and generic technologies)
OEM_TECHNOLOGY_REGISTRY: Dict[str, TechnologyEntity] = {
    entity.id: entity for entity in ALL_AUTOMOTIVE_TECHNOLOGIES
}

__all__ = [
    "OEM_TECHNOLOGIES",
    "ALL_AUTOMOTIVE_TECHNOLOGIES",
    "OEM_TECHNOLOGY_REGISTRY",
    "GENERIC_AUTOMOTIVE_TECHNOLOGIES",
    "GENERIC_TECHNOLOGY_REGISTRY",
]
