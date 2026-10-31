"""
Abstract Base Interface for Market Search Providers (src/search/providers/base.py).
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.search.models import MarketSearchResult, SearchType


class BaseSearchProvider(ABC):
    """Abstract interface for all live or mock automotive search providers."""

    @abstractmethod
    def search(
        self,
        query: str,
        search_type: SearchType = SearchType.ALL,
        car_model: Optional[str] = None,
    ) -> MarketSearchResult:
        """
        Execute automotive market search.

        Args:
            query: Sanitized user query text.
            search_type: Desired category of information.
            car_model: Optional detected vehicle model name.

        Returns:
            MarketSearchResult with structured intelligence.
        """
        pass
