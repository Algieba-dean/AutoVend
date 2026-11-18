"""
Per-node Token & Cost Ledger for AutoVend (src/llm/cost_ledger.py).

Tracks token usage and USD cost broken down by agent node role
(Extractor / Grader / Generator / Auditor) and enforces per-session budgets
with circuit-breaking / graceful degradation signals.
"""

import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from src.llm.telemetry import PRICING_USD_PER_MTOK, Route


class AgentNodeRole(str, Enum):
    """Logical agent node roles for cost attribution."""

    EXTRACTOR = "Extractor"
    GRADER = "Grader"
    GENERATOR = "Generator"
    AUDITOR = "Auditor"
    OTHER = "Other"


class BudgetExceededError(RuntimeError):
    """Raised when a session exceeds its configured token or USD budget."""

    def __init__(self, session_id: str, spent_usd: float, budget_usd: float, spent_tokens: int, max_tokens: int):
        self.session_id = session_id
        self.spent_usd = spent_usd
        self.budget_usd = budget_usd
        self.spent_tokens = spent_tokens
        self.max_tokens = max_tokens
        super().__init__(
            f"Session '{session_id}' exceeded budget: "
            f"${spent_usd:.4f}/${budget_usd:.4f}, {spent_tokens}/{max_tokens} tokens"
        )


@dataclass
class NodeCostEntry:
    """Aggregated usage for a single node role."""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
        }


@dataclass
class SessionBudgetState:
    """Per-session cost ledger and budget limits."""

    session_id: str
    budget_usd: float = 0.50
    max_tokens: int = 200_000
    by_node: Dict[str, NodeCostEntry] = field(default_factory=dict)
    degraded: bool = False

    @property
    def total_cost_usd(self) -> float:
        return sum(e.cost_usd for e in self.by_node.values())

    @property
    def total_tokens(self) -> int:
        return sum(e.total_tokens for e in self.by_node.values())

    @property
    def is_over_budget(self) -> bool:
        return (self.budget_usd > 0 and self.total_cost_usd >= self.budget_usd) or (
            self.max_tokens > 0 and self.total_tokens >= self.max_tokens
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "budget_usd": self.budget_usd,
            "max_tokens": self.max_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_tokens": self.total_tokens,
            "is_over_budget": self.is_over_budget,
            "degraded": self.degraded,
            "by_node": {k: v.to_dict() for k, v in self.by_node.items()},
        }


_CURRENT_SESSION_ID: ContextVar[str] = ContextVar("autovend_cost_session_id", default="global")
_CURRENT_NODE_ROLE: ContextVar[AgentNodeRole] = ContextVar("autovend_cost_node_role", default=AgentNodeRole.OTHER)


@contextmanager
def node_cost_context(session_id: str, node_role: AgentNodeRole):
    """Bind `(session_id, node_role)` to the current execution context for automatic cost attribution."""
    tok_sid = _CURRENT_SESSION_ID.set(session_id or "global")
    tok_role = _CURRENT_NODE_ROLE.set(node_role)
    try:
        yield
    finally:
        _CURRENT_SESSION_ID.reset(tok_sid)
        _CURRENT_NODE_ROLE.reset(tok_role)


class CostLedger:
    """Thread-safe per-session, per-node token & USD cost ledger."""

    def __init__(self, default_budget_usd: float = 0.50, default_max_tokens: int = 200_000):
        self._lock = threading.Lock()
        self._sessions: Dict[str, SessionBudgetState] = {}
        self.default_budget_usd = default_budget_usd
        self.default_max_tokens = default_max_tokens

    def _get_or_create(self, session_id: str) -> SessionBudgetState:
        sid = session_id or "global"
        if sid not in self._sessions:
            self._sessions[sid] = SessionBudgetState(
                session_id=sid,
                budget_usd=self.default_budget_usd,
                max_tokens=self.default_max_tokens,
            )
        return self._sessions[sid]

    def set_budget(
        self,
        session_id: str,
        budget_usd: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        with self._lock:
            st = self._get_or_create(session_id)
            if budget_usd is not None:
                st.budget_usd = budget_usd
            if max_tokens is not None:
                st.max_tokens = max_tokens

    def record_usage(
        self,
        session_id: Optional[str] = None,
        node_role: Optional[AgentNodeRole] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        route: Route = Route.CLOUD,
        model: str = "unknown",
    ) -> SessionBudgetState:
        sid = session_id or _CURRENT_SESSION_ID.get()
        role = node_role or _CURRENT_NODE_ROLE.get()
        role_key = role.value if isinstance(role, AgentNodeRole) else str(role)

        price = PRICING_USD_PER_MTOK.get(
            route.value if isinstance(route, Route) else str(route),
            PRICING_USD_PER_MTOK["cloud"],
        )
        cost = (max(0, prompt_tokens) * price["input"] + max(0, completion_tokens) * price["output"]) / 1_000_000

        with self._lock:
            st = self._get_or_create(sid)
            entry = st.by_node.setdefault(role_key, NodeCostEntry())
            entry.calls += 1
            entry.prompt_tokens += max(0, int(prompt_tokens))
            entry.completion_tokens += max(0, int(completion_tokens))
            entry.cost_usd += cost
            if st.is_over_budget:
                st.degraded = True
            return st

    def check_budget(self, session_id: Optional[str] = None, raise_on_exceeded: bool = False) -> bool:
        """Return True if within budget; False (or raise BudgetExceededError) if exceeded."""
        sid = session_id or _CURRENT_SESSION_ID.get()
        with self._lock:
            st = self._sessions.get(sid)
            if st is None:
                return True
            if st.is_over_budget:
                st.degraded = True
                if raise_on_exceeded:
                    raise BudgetExceededError(
                        sid, st.total_cost_usd, st.budget_usd, st.total_tokens, st.max_tokens
                    )
                return False
            return True

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            st = self._sessions.get(session_id)
            if st is None:
                return SessionBudgetState(
                    session_id=session_id,
                    budget_usd=self.default_budget_usd,
                    max_tokens=self.default_max_tokens,
                ).to_dict()
            return st.to_dict()

    def reset(self, session_id: Optional[str] = None) -> None:
        with self._lock:
            if session_id is None:
                self._sessions.clear()
            else:
                self._sessions.pop(session_id, None)


cost_ledger = CostLedger()
