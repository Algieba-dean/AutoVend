"""
Agent storage facade — delegates to src.core.storage.distributed_session
to preserve strict architectural separation (see tests/test_agent_isolation.py).
"""

from src.core.storage.distributed_session import (
    DistributedSessionStore,
    SessionLockTimeoutError,
    get_distributed_session_store,
    set_distributed_session_store,
)

__all__ = [
    "DistributedSessionStore",
    "SessionLockTimeoutError",
    "get_distributed_session_store",
    "set_distributed_session_store",
]
