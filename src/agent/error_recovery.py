"""
Self-Healing Error Taxonomy & Recovery Loop for AutoVend Agent (src/agent/error_recovery.py).

Inspired by NousResearch Hermes-Agent error_classifier.py and turn_retry_state.py.
Classifies extraction/tool failures and builds actionable correction hints to allow LLM self-recovery.
"""

import enum
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentErrorCategory(str, enum.Enum):
    """Taxonomy of Agent errors determining recovery strategy."""

    SCHEMA_MISMATCH = "schema_mismatch"        # Extracted JSON fails Pydantic schema validation
    MISSING_REQUIRED_SLOT = "missing_slot"      # Essential slot missing (e.g. phone number)
    CONSTRAINT_CONFLICT = "constraint_conflict"  # Incompatible constraints (e.g. 10万 vs Porsche)
    TOOL_EXECUTION_ERROR = "tool_error"          # Runtime error inside tool execution
    TRANSIENT_TIMEOUT = "transient_timeout"      # LLM or network API timeout
    UNKNOWN_ERROR = "unknown_error"


class RecoveryHint(BaseModel):
    """Actionable hint provided to LLM for self-correction."""

    category: AgentErrorCategory
    hint_text: str
    should_retry: bool = True
    max_retries: int = 3


class ErrorClassifier:
    """Classifies runtime errors and generates self-healing hints for Agent."""

    @staticmethod
    def classify(error: Exception, context: Dict[str, Any] = {}) -> RecoveryHint:
        """Classify an exception and return actionable recovery hint."""
        err_msg = str(error)

        if isinstance(error, (TypeError, ValueError)) and "validation" in err_msg.lower():
            return RecoveryHint(
                category=AgentErrorCategory.SCHEMA_MISMATCH,
                hint_text="上次输出格式不符合 JSON 规范或字段类型错误，请严格按 Pydantic 规范输出 JSON 结构。",
                should_retry=True,
            )

        if "missing" in err_msg.lower() or "required" in err_msg.lower():
            return RecoveryHint(
                category=AgentErrorCategory.MISSING_REQUIRED_SLOT,
                hint_text="缺少预约必需字段（手机号/看车时间），请向客户确认该字段。",
                should_retry=True,
            )

        if "timeout" in err_msg.lower() or "connection" in err_msg.lower():
            return RecoveryHint(
                category=AgentErrorCategory.TRANSIENT_TIMEOUT,
                hint_text="网络连接超时，已触发底层服务退化与备用路由重试。",
                should_retry=True,
            )

        return RecoveryHint(
            category=AgentErrorCategory.UNKNOWN_ERROR,
            hint_text=f"系统捕获非预期的运行异常 ({err_msg[:100]})，请重试或保持当前上下文。",
            should_retry=False,
        )


class AgentSelfHealingLoop:
    """Manages self-healing retries for Agent execution turns."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.attempts: Dict[str, int] = {}

    def execute_with_self_healing(self, session_id: str, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute a function with automatic classification and hint-guided retries."""
        current_attempt = self.attempts.get(session_id, 0)

        while current_attempt < self.max_retries:
            try:
                res = fn(*args, **kwargs)
                self.attempts[session_id] = 0  # Reset on success
                return res
            except Exception as e:
                current_attempt += 1
                self.attempts[session_id] = current_attempt
                hint = ErrorClassifier.classify(e)
                logger.warning(f"Self-healing attempt {current_attempt}/{self.max_retries} for session {session_id}: {hint.hint_text}")

                if not hint.should_retry or current_attempt >= self.max_retries:
                    raise e
