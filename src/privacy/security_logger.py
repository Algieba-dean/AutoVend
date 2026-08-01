"""
Security Audit Logger for AutoVend Agent.

Captures security-relevant events (Prompt Injections, PII Masking, Unauthorized Tool Access,
Sanitized Tool Arguments) with trace IDs and outputs structured JSONL logs for SIEM integrations.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_SECURITY_LOG_DIR = PROJECT_ROOT / "evaluation" / "results"
DEFAULT_SECURITY_LOG_FILE = DEFAULT_SECURITY_LOG_DIR / "security_audit.jsonl"


@dataclass
class SecurityAuditEvent:
    """A structured security audit record."""

    trace_id: str
    session_id: str
    event_type: str  # e.g., "PROMPT_INJECTION", "PII_MASKED", "UNAUTHORIZED_TOOL", "ARGS_SANITIZED"
    severity: str  # "INFO", "WARNING", "CRITICAL"
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class SecurityAuditLogger:
    """
    SIEM-ready Security Audit Logger.
    """

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = Path(log_path) if log_path else DEFAULT_SECURITY_LOG_FILE

    def log_event(
        self,
        event_type: str,
        severity: str,
        session_id: str = "",
        trace_id: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> SecurityAuditEvent:
        """Log a security event to file and standard logger."""
        event = SecurityAuditEvent(
            trace_id=trace_id,
            session_id=session_id,
            event_type=event_type,
            severity=severity,
            details=details or {},
            timestamp=time.time(),
        )

        msg = f"[SECURITY AUDIT] [{severity}] [{event_type}] session={session_id} trace={trace_id}: {details}"
        if severity == "CRITICAL":
            logger.error(msg)
        elif severity == "WARNING":
            logger.warning(msg)
        else:
            logger.info(msg)

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.error(f"Failed to write security audit log to {self.log_path}: {exc}")

        return event


# Global singleton instance
security_audit_logger = SecurityAuditLogger()
