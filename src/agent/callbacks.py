"""
Unified LangChain BaseCallbackHandler + OpenTelemetry Span tracer (src/agent/callbacks.py).

Penetrates every LangGraph Node & Tool (`extract_slots`, `retrieve_vehicles`,
`grade_retrieval`, `tools`, `generate_reply`, `audit_hallucination`), capturing
per-node latency, token usage, prompt cache hits, and CostLedger cost.
"""

import time
from typing import Any, Dict, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.core.agentops import record_node_metrics, start_span
from src.llm.cost_ledger import cost_ledger


class AutoVendOtelCallbackHandler(BaseCallbackHandler):
    """Callback handler bridging LangGraph/LangChain execution to OTel Spans & Prometheus."""

    def __init__(self, session_id: str, trace_id: str = "", artifact_bundle_version: str = ""):
        super().__init__()
        self.session_id = session_id
        self.trace_id = trace_id or session_id
        self.artifact_bundle_version = artifact_bundle_version
        self._spans: Dict[str, Any] = {}
        self._start_times: Dict[str, float] = {}
        self._node_names: Dict[str, str] = {}
        self._last_node: str = "graph"
        self.total_cached_tokens: int = 0
        self._last_recorded_cost_usd: float = float(
            cost_ledger.get_session_summary(session_id).get("total_cost_usd", 0.0)
        )

    def _key(self, run_id: UUID) -> str:
        return str(run_id)

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        meta = metadata or {}
        node_name = meta.get("langgraph_node")
        if not node_name:
            return
        self._last_node = str(node_name)
        k = self._key(run_id)
        self._node_names[k] = str(node_name)
        self._start_times[k] = time.perf_counter()
        self._spans[k] = start_span(
            name=f"langgraph.node.{node_name}",
            trace_id=self.trace_id,
            attributes={
                "session.id": self.session_id,
                "langgraph.node": node_name,
                "artifact.bundle_version": self.artifact_bundle_version,
            },
        )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        k = self._key(run_id)
        node_name = self._node_names.pop(k, None)
        span = self._spans.pop(k, None)
        started = self._start_times.pop(k, None)
        if node_name and started is not None:
            dur = time.perf_counter() - started
            record_node_metrics(node_name=node_name, duration_s=dur)
        if span is not None:
            span.end(status_code="OK")

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        k = self._key(run_id)
        node_name = self._node_names.pop(k, None)
        span = self._spans.pop(k, None)
        started = self._start_times.pop(k, None)
        if node_name and started is not None:
            record_node_metrics(node_name=node_name, duration_s=time.perf_counter() - started)
        if span is not None:
            span.end(status_code="ERROR", status_message=str(error))

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        meta = metadata or {}
        node_name = str(meta.get("langgraph_node") or self._last_node or "llm")
        k = self._key(run_id)
        self._node_names[k] = node_name
        self._start_times[k] = time.perf_counter()
        self._spans[k] = start_span(
            name=f"llm.call.{node_name}",
            trace_id=self.trace_id,
            attributes={"session.id": self.session_id, "langgraph.node": node_name},
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        k = self._key(run_id)
        node_name = self._node_names.pop(k, self._last_node)
        span = self._spans.pop(k, None)
        started = self._start_times.pop(k, None)
        dur = time.perf_counter() - started if started is not None else 0.0

        llm_out = response.llm_output or {}
        token_usage = llm_out.get("token_usage") or llm_out.get("usage") or {}
        pt = int(token_usage.get("prompt_tokens", 0) or 0)
        ct = int(token_usage.get("completion_tokens", 0) or 0)
        details = token_usage.get("prompt_tokens_details") or {}
        cached = int(details.get("cached_tokens", 0) or token_usage.get("cached_tokens", 0) or 0)
        self.total_cached_tokens += cached

        cost_summary = cost_ledger.get_session_summary(self.session_id)
        current_total_cost = float(cost_summary.get("total_cost_usd", 0.0))
        cost_delta = max(0.0, current_total_cost - self._last_recorded_cost_usd)
        self._last_recorded_cost_usd = current_total_cost
        record_node_metrics(
            node_name=node_name,
            duration_s=dur,
            prompt_tokens=pt,
            completion_tokens=ct,
            cached_tokens=cached,
            cost_usd=cost_delta,
        )
        if span is not None:
            span.attributes.update(
                {
                    "gen_ai.usage.input_tokens": pt,
                    "gen_ai.usage.output_tokens": ct,
                    "gen_ai.usage.cached_tokens": cached,
                }
            )
            span.end(status_code="OK")

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        k = self._key(run_id)
        self._node_names.pop(k, None)
        self._start_times.pop(k, None)
        span = self._spans.pop(k, None)
        if span is not None:
            span.end(status_code="ERROR", status_message=str(error))

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "tool") if isinstance(serialized, dict) else "tool"
        k = self._key(run_id)
        self._node_names[k] = f"tool.{tool_name}"
        self._start_times[k] = time.perf_counter()
        self._spans[k] = start_span(
            name=f"langgraph.tool.{tool_name}",
            trace_id=self.trace_id,
            attributes={"session.id": self.session_id, "tool.name": tool_name},
        )

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        k = self._key(run_id)
        t_name = self._node_names.pop(k, "tool")
        started = self._start_times.pop(k, None)
        span = self._spans.pop(k, None)
        if started is not None:
            record_node_metrics(node_name=t_name, duration_s=time.perf_counter() - started)
        if span is not None:
            span.end(status_code="OK")

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        k = self._key(run_id)
        self._node_names.pop(k, None)
        self._start_times.pop(k, None)
        span = self._spans.pop(k, None)
        if span is not None:
            span.end(status_code="ERROR", status_message=str(error))
