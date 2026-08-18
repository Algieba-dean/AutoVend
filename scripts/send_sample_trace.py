"""
Script to send sample agent execution traces to OpenTelemetry Collector via OTLP/HTTP.
This immediately populates Grafana Tempo with real trace data.
"""

import json
import random
import time
import urllib.request


def generate_trace_id():
    return "%032x" % random.getrandbits(128)


def generate_span_id():
    return "%016x" % random.getrandbits(64)


def send_sample_trace():
    url = "http://localhost:4318/v1/traces"
    headers = {"Content-Type": "application/json"}

    trace_id = generate_trace_id()
    root_span_id = generate_span_id()
    router_span_id = generate_span_id()
    llm_span_id = generate_span_id()
    rag_span_id = generate_span_id()

    now_ns = int(time.time() * 1e9)

    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "autovend-sales-agent"}},
                        {"key": "environment", "value": {"stringValue": "production"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "autovend.agent.tracer"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": root_span_id,
                                "name": "POST /api/chat/stream",
                                "kind": 1,
                                "startTimeUnixNano": str(now_ns - 1200000000),
                                "endTimeUnixNano": str(now_ns),
                                "attributes": [
                                    {"key": "http.method", "value": {"stringValue": "POST"}},
                                    {"key": "user.intent", "value": {"stringValue": "buy_car"}},
                                    {"key": "user.budget", "value": {"stringValue": "30w"}},
                                ],
                            },
                            {
                                "traceId": trace_id,
                                "spanId": router_span_id,
                                "parentSpanId": root_span_id,
                                "name": "Gate 1: Semantic Router Classification",
                                "kind": 1,
                                "startTimeUnixNano": str(now_ns - 1199000000),
                                "endTimeUnixNano": str(now_ns - 1196000000),
                                "attributes": [
                                    {"key": "router.matched_intent", "value": {"stringValue": "budget_objection"}},
                                    {"key": "router.similarity_score", "value": {"doubleValue": 0.892}},
                                    {"key": "router.latency_us", "value": {"doubleValue": 2.85}},
                                ],
                            },
                            {
                                "traceId": trace_id,
                                "spanId": llm_span_id,
                                "parentSpanId": root_span_id,
                                "name": "Local LLM Extraction (Qwen3-8B)",
                                "kind": 1,
                                "startTimeUnixNano": str(now_ns - 1180000000),
                                "endTimeUnixNano": str(now_ns - 900000000),
                                "attributes": [
                                    {"key": "llm.model", "value": {"stringValue": "qwen3-8b-bnb-4bit"}},
                                    {"key": "llm.provider", "value": {"stringValue": "vLLM-Local"}},
                                    {"key": "llm.ttft_ms", "value": {"doubleValue": 12.4}},
                                    {"key": "llm.prompt_tokens", "value": {"intValue": 245}},
                                    {"key": "llm.completion_tokens", "value": {"intValue": 68}},
                                ],
                            },
                            {
                                "traceId": trace_id,
                                "spanId": rag_span_id,
                                "parentSpanId": root_span_id,
                                "name": "ChromaDB RAG Retrieval (Vector Search)",
                                "kind": 1,
                                "startTimeUnixNano": str(now_ns - 890000000),
                                "endTimeUnixNano": str(now_ns - 870000000),
                                "attributes": [
                                    {"key": "db.system", "value": {"stringValue": "chromadb"}},
                                    {"key": "rag.top_k", "value": {"intValue": 3}},
                                    {"key": "rag.retrieved_cars", "value": {"stringValue": "Xiaomi SU7 Max, Tesla Model 3"}},
                                ],
                            },
                        ],
                    }
                ],
            }
        ]
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Successfully sent sample trace! Status: {resp.status}, Trace ID: {trace_id}")
            return trace_id
    except Exception as e:
        print(f"Error sending trace: {e}")
        return None


if __name__ == "__main__":
    for i in range(5):
        send_sample_trace()
        time.sleep(0.5)
