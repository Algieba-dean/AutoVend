"""Privacy layer: rule-based PII detection and reversible masking."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.privacy.interceptor import PIIInterceptor, PIIMatch, get_interceptor

__all__ = ["PIIInterceptor", "PIIMatch", "get_interceptor"]


def __getattr__(name: str) -> Any:
    if name in ("PIIInterceptor", "PIIMatch", "get_interceptor"):
        from src.privacy import interceptor

        return getattr(interceptor, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
