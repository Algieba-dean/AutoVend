"""
Tool Execution Transaction Manager — state snapshots, audit logging, and reversible rollbacks.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.tools.base import BaseTool, ToolExecutionContext

logger = logging.getLogger(__name__)


@dataclass
class TransactionRecord:
    """Historical record of an executed tool transaction."""

    transaction_id: str
    tool_name: str
    session_id: str
    args: Dict[str, Any]
    output: Any
    snapshot: Dict[str, Any] = field(default_factory=dict)
    status: str = "COMMITTED"  # COMMITTED, ROLLED_BACK, FAILED
    created_at: float = field(default_factory=time.time)
    rolled_back_at: Optional[float] = None


class TransactionManager:
    """Manages transactional state changes and handles reversible rollbacks for tool executions."""

    def __init__(self):
        self._records: Dict[str, TransactionRecord] = {}
        self._session_index: Dict[str, List[str]] = {}

    def record(
        self,
        tool_name: str,
        session_id: str,
        args: Dict[str, Any],
        output: Any,
        snapshot: Optional[Dict[str, Any]] = None,
        transaction_id: Optional[str] = None,
    ) -> TransactionRecord:
        """Create and store a committed transaction record."""
        tx_id = transaction_id or f"tx_{uuid.uuid4().hex[:12]}"
        rec = TransactionRecord(
            transaction_id=tx_id,
            tool_name=tool_name,
            session_id=session_id,
            args=args,
            output=output,
            snapshot=snapshot or {},
            status="COMMITTED",
        )
        self._records[tx_id] = rec
        if session_id not in self._session_index:
            self._session_index[session_id] = []
        self._session_index[session_id].append(tx_id)
        logger.info(f"[{session_id}] Tool transaction recorded: {tx_id} for tool '{tool_name}'")
        return rec

    def get_transaction(self, transaction_id: str) -> Optional[TransactionRecord]:
        return self._records.get(transaction_id)

    def get_session_transactions(self, session_id: str) -> List[TransactionRecord]:
        tx_ids = self._session_index.get(session_id, [])
        return [self._records[tid] for tid in tx_ids if tid in self._records]

    def rollback(
        self,
        transaction_id: str,
        tool: Optional[BaseTool],
        context: ToolExecutionContext,
    ) -> bool:
        """Execute reversible rollback on a transaction."""
        rec = self._records.get(transaction_id)
        if not rec:
            logger.warning(f"Transaction not found for rollback: {transaction_id}")
            return False

        if rec.status == "ROLLED_BACK":
            logger.info(f"Transaction {transaction_id} is already rolled back.")
            return True

        success = False
        if tool is not None:
            success = tool.rollback(transaction_id, context)
        else:
            success = True

        if success:
            rec.status = "ROLLED_BACK"
            rec.rolled_back_at = time.time()
            logger.info(f"Transaction {transaction_id} ({rec.tool_name}) successfully rolled back.")
        else:
            logger.error(f"Failed to rollback transaction {transaction_id} ({rec.tool_name})")

        return success

    def rollback_latest_for_session(
        self,
        session_id: str,
        tool_resolver: Any,
        context: ToolExecutionContext,
    ) -> Optional[TransactionRecord]:
        """Rollback the most recent reversible transaction for a given session."""
        txs = self.get_session_transactions(session_id)
        for rec in reversed(txs):
            if rec.status == "COMMITTED":
                tool = tool_resolver(rec.tool_name)
                if self.rollback(rec.transaction_id, tool, context):
                    return rec
        return None
