"""
Governance Context — shared state passing through the AOP Governance Layer.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GovernanceContext(BaseModel):
    """Execution context carrying payload and metadata across governance hooks."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str = ""
    trace_id: str = ""
    user_role: str = "customer"

    # Message payloads
    user_message: str = ""
    safe_message: str = ""
    pii_found: bool = False

    # Short-circuit & Semantic Router
    decision: Optional[Any] = None
    skip_extraction: bool = False
    interrupt_detected: bool = False

    # Tool Governance
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    tool_sanitized: bool = False
    tool_allowed: bool = True
    tool_result: Optional[Any] = None
    transaction_id: Optional[str] = None

    # Stage Governance
    proposals: List[Any] = Field(default_factory=list)
    stage_verdict: Optional[Any] = None

    # Response Generation & Compliance
    raw_generated_text: str = ""
    final_response_text: str = ""
    compliance_warnings: List[str] = Field(default_factory=list)

    # General metadata / state bag
    metadata: Dict[str, Any] = Field(default_factory=dict)
