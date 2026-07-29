"""
Tool Call Loop Circuit-Breaker Guardrails for AutoVend Agent (src/agent/tool_guardrails.py).

Inspired by NousResearch Hermes-Agent tool_guardrails.py.
Prevents Agent from getting stuck in infinite tool-calling loops with identical parameters
or repeating failing search queries without making progress.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ToolCallObservation:
    """Record of a tool call attempt and result hash."""

    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    result_hash: str


class ToolLoopGuardrail:
    """
    Circuit-breaker that tracks per-turn tool invocations and detects repetitive loops.
    """

    def __init__(
        self,
        exact_repeat_limit: int = 2,
        same_tool_failure_limit: int = 3,
    ):
        self.exact_repeat_limit = exact_repeat_limit
        self.same_tool_failure_limit = same_tool_failure_limit
        self.observations: List[ToolCallObservation] = []

    def _hash_args(self, args: Dict[str, Any]) -> str:
        """Create deterministic hash for tool arguments."""
        try:
            raw = json.dumps(args, sort_keys=True, ensure_ascii=False)
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        except Exception:
            return str(hash(str(args)))

    def record_and_evaluate(
        self, tool_name: str, args: Dict[str, Any], success: bool, result_payload: Any = None
    ) -> Optional[str]:
        """
        Record a tool execution and evaluate if a loop is detected.
        Returns a warning/circuit-breaker instruction if a loop is detected, else None.
        """
        arg_hash = self._hash_args(args)
        res_str = str(result_payload)[:200] if result_payload else ""
        res_hash = hashlib.sha256(res_str.encode("utf-8")).hexdigest()[:12]

        obs = ToolCallObservation(
            tool_name=tool_name,
            arguments=args,
            success=success,
            result_hash=res_hash,
        )
        self.observations.append(obs)

        # 1. Check exact repeat (same tool + same args)
        matching_exact = [
            o for o in self.observations if o.tool_name == tool_name and self._hash_args(o.arguments) == arg_hash
        ]
        if len(matching_exact) >= self.exact_repeat_limit:
            msg = f"检测到重复调用工具 [{tool_name}] 且参数完全一致 ({self.exact_repeat_limit} 次)。已熔断重复检索，请更换查询关键词或直接基于现有结果回答。"
            logger.warning(msg)
            return msg

        # 2. Check same tool repeated failures
        matching_failures = [
            o for o in self.observations if o.tool_name == tool_name and not o.success
        ]
        if len(matching_failures) >= self.same_tool_failure_limit:
            msg = f"工具 [{tool_name}] 已连续失败 {self.same_tool_failure_limit} 次。请勿继续尝试该工具，切至备用逻辑。"
            logger.warning(msg)
            return msg

        return None

    def reset(self) -> None:
        """Reset observations for a new turn."""
        self.observations.clear()
