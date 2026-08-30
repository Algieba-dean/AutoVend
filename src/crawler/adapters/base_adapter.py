"""
Abstract Base Class for Automotive Site Adapters.
Defines unified interface for dynamic brand discovery, serial tree resolution, and spec extraction.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.crawler.schemas import BrandMeta, RawSerialSpecSheet, SerialMeta


class BaseSiteAdapter(ABC):
    """Unified crawler adapter specification for automotive platforms."""

    @abstractmethod
    async def initialize(self) -> None:
        """Start underlying browser or HTTP session and perform session priming."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    async def discover_all_brands(self) -> List[BrandMeta]:
        """Dynamically discover all automotive brands indexed on the platform."""
        pass

    @abstractmethod
    async def discover_serials_by_brand(self, brand: BrandMeta) -> List[SerialMeta]:
        """Dynamically fetch all vehicle series (serials) under a given brand."""
        pass

    @abstractmethod
    async def extract_serial_full_specs(
        self,
        serial: SerialMeta,
        include_discontinued: bool = False,
    ) -> Optional[RawSerialSpecSheet]:
        """Extract full multi-tiered specification comparison sheet for a car series."""
        pass
