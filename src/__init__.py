"""
AutoVend RAG Agent System

智能汽车销售助手，基于RAG和LLM技术。
"""

__version__ = "1.0.0"
__author__ = "AutoVend Team"

import sys
if not hasattr(sys, "get_int_max_str_digits"):
    def _get_int_max_str_digits() -> int:
        return 4300

    def _set_int_max_str_digits(maxdigits: int) -> None:
        pass

    sys.get_int_max_str_digits = _get_int_max_str_digits  # type: ignore[attr-defined]
    sys.set_int_max_str_digits = _set_int_max_str_digits  # type: ignore[attr-defined]

