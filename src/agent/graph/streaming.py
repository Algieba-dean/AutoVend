"""
Native LangGraph streaming helper (`src/agent/graph/streaming.py`).
"""

import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from src.agent.graph.state import OPEN_THINK_RE, AgentGraphState
from src.agent.guardrail.compliance import DualStreamComplianceGuard
from src.agent.schemas import SessionState


def sanitize_stream_segment(agent: Any, session_id: str, segment: str) -> str:
    """Run lightweight compliance & PII redaction on a buffered stream segment before emission."""
    if not segment:
        return ""
    try:
        post_ctx = agent.hook_manager.run_post_response(session_id, segment)
        cleaned = post_ctx.sanitized_response
        guard = DualStreamComplianceGuard.inspect(cleaned)
        return guard.guarded_text if not guard.is_compliant else cleaned
    except Exception:
        return segment


async def stream_graph_turn(
    agent: Any,
    session_id: str,
    user_message: str,
    session_state: Optional[SessionState] = None,
    retrieved_cars: Optional[List[Dict[str, Any]]] = None,
    skip_extraction: bool = False,
    propose_with_llm: bool = False,
) -> AsyncGenerator[Tuple[str, Any], None]:
    """
    Stream a turn natively via `agent.graph.astream(..., stream_mode=["messages", "updates"])`.

    Buffers tokens at sentence/clause boundaries and runs lightweight compliance/PII
    sanitization before yielding `("delta", chunk)`.
    """
    config = agent._build_run_config(session_id, session_state)
    graph_input: AgentGraphState = {
        "session_id": session_id,
        "user_message": user_message,
        "skip_extraction": skip_extraction,
        "retrieved_cars": retrieved_cars,
        "propose_with_llm": propose_with_llm,
    }
    if session_state is not None:
        graph_input["session_state"] = session_state

    emitted_metadata = False
    emitted_tokens = False
    latest_stage_changed = False
    latest_sess: Optional[SessionState] = session_state
    final_text = ""
    buf = ""
    stream_pending = ""
    streamed_so_far = ""
    in_think = False
    think_tag = ""
    boundary_re = re.compile(r"[。！？!?\n；;]")

    def _flush_ready_segments(force_all: bool = False) -> List[str]:
        nonlocal stream_pending
        if not stream_pending:
            return []
        if force_all:
            seg = sanitize_stream_segment(agent, session_id, stream_pending)
            stream_pending = ""
            return [seg] if seg else []
        matches = list(boundary_re.finditer(stream_pending))
        if not matches:
            return []
        cut = matches[-1].end()
        raw_seg = stream_pending[:cut]
        stream_pending = stream_pending[cut:]
        seg = sanitize_stream_segment(agent, session_id, raw_seg)
        return [seg] if seg else []

    async for mode, payload in agent.graph.astream(
        graph_input,
        config=config,
        stream_mode=["messages", "updates"],
    ):
        if mode == "updates" and isinstance(payload, dict):
            for _node_upd in payload.values():
                if isinstance(_node_upd, dict) and _node_upd.get("session_state") is not None:
                    latest_sess = _node_upd["session_state"]

            if "__interrupt__" in payload:
                interrupts = payload["__interrupt__"]
                first_int = interrupts[0] if interrupts else {}
                handoff_val = getattr(first_int, "value", first_int)
                handoff_dict = (
                    handoff_val if isinstance(handoff_val, dict) else {"payload": handoff_val}
                )
                if latest_sess is None:
                    try:
                        snap = agent.get_graph_state(session_id)
                        latest_sess = (getattr(snap, "values", None) or {}).get("session_state")
                    except Exception:
                        pass
                handoff_msg = (
                    "您好，当前您的购车需求已进入专属顾问人工服务通道，我已将您的偏好与候选车型摘要同步给门店专家，请稍候。"
                )
                if not emitted_metadata:
                    emitted_metadata = True
                    yield (
                        "metadata",
                        {
                            "session_state": latest_sess,
                            "stage_changed": latest_stage_changed,
                            "matched_cars": latest_sess.matched_cars if latest_sess else [],
                            "interrupted": True,
                            "handoff_context": handoff_dict,
                        },
                    )
                yield ("delta", handoff_msg)
                yield ("done", handoff_msg)
                return
            if "safe_degrade" in payload:
                deg_upd = payload["safe_degrade"]
                deg_sess = deg_upd.get("session_state") or latest_sess
                if not emitted_metadata and deg_sess is not None:
                    emitted_metadata = True
                    yield (
                        "metadata",
                        {
                            "session_state": deg_sess,
                            "stage_changed": latest_stage_changed,
                            "matched_cars": deg_sess.matched_cars,
                        },
                    )
                if "response_text" in deg_upd:
                    final_text = deg_upd["response_text"]
            if "arbitrate_stage" in payload:
                latest_stage_changed = bool(
                    payload["arbitrate_stage"].get("stage_changed", False)
                )
            if "run_plugins_and_subdag" in payload and not emitted_metadata:
                upd = payload["run_plugins_and_subdag"]
                sess: SessionState = upd["session_state"]
                latest_sess = sess
                emitted_metadata = True
                yield (
                    "metadata",
                    {
                        "session_state": sess,
                        "stage_changed": latest_stage_changed,
                        "matched_cars": sess.matched_cars,
                    },
                )
            if "generate_reply" in payload:
                gen_upd = payload["generate_reply"]
                if "response_text" in gen_upd:
                    final_text = gen_upd["response_text"]
            if "audit_hallucination" in payload:
                audit_upd = payload["audit_hallucination"]
                if "response_text" in audit_upd:
                    final_text = audit_upd["response_text"]
                if not audit_upd.get("audit_passed", True):
                    buf = ""
                    stream_pending = ""
                    in_think = False
                    think_tag = ""
        elif mode == "messages":
            msg_chunk, meta = payload
            if meta.get("langgraph_node") != "generate_reply":
                continue
            if getattr(msg_chunk, "tool_call_chunks", None) or getattr(
                msg_chunk, "tool_calls", None
            ):
                continue
            token = msg_chunk.content if isinstance(msg_chunk.content, str) else ""
            if not token:
                continue

            buf += token
            while buf:
                if in_think:
                    close_re = re.compile(rf"</{re.escape(think_tag)}>", re.IGNORECASE)
                    m_close = close_re.search(buf)
                    if m_close:
                        buf = buf[m_close.end() :].lstrip("\r\n")
                        in_think = False
                        think_tag = ""
                    else:
                        keep = len(think_tag) + 4
                        if len(buf) > keep:
                            buf = buf[-keep:]
                        break
                else:
                    m_open = OPEN_THINK_RE.search(buf)
                    if m_open:
                        before = buf[: m_open.start()]
                        if before:
                            stream_pending += before
                            for seg in _flush_ready_segments(force_all=False):
                                emitted_tokens = True
                                streamed_so_far += seg
                                yield ("delta", seg)
                        in_think = True
                        think_tag = m_open.group(1)
                        buf = buf[m_open.end() :]
                    else:
                        lt_idx = buf.rfind("<")
                        if lt_idx != -1 and (len(buf) - lt_idx) <= 12:
                            safe_part = buf[:lt_idx]
                            if safe_part:
                                stream_pending += safe_part
                                for seg in _flush_ready_segments(force_all=False):
                                    emitted_tokens = True
                                    streamed_so_far += seg
                                    yield ("delta", seg)
                            buf = buf[lt_idx:]
                            break
                        else:
                            stream_pending += buf
                            for seg in _flush_ready_segments(force_all=False):
                                emitted_tokens = True
                                streamed_so_far += seg
                                yield ("delta", seg)
                            buf = ""
                            break

    if not in_think and buf:
        stream_pending += buf
        buf = ""

    if final_text:
        if emitted_tokens:
            if streamed_so_far != final_text:
                if final_text.startswith(streamed_so_far):
                    tail = final_text[len(streamed_so_far) :]
                    if tail:
                        yield ("delta", tail)
                else:
                    yield ("replace", final_text)
        else:
            yield ("delta", final_text)
    elif stream_pending:
        for seg in _flush_ready_segments(force_all=True):
            emitted_tokens = True
            streamed_so_far += seg
            yield ("delta", seg)
        final_text = streamed_so_far

    yield ("done", final_text)
