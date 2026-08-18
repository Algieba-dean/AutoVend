"""
Generate real OpenTelemetry Traces using official Python OTel SDK
and send directly to OTel Collector OTLP HTTP receiver (localhost:4318).
"""

import time
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def main():
    # Setup Resource & Tracer
    resource = Resource.create({"service.name": "autovend-sales-agent", "environment": "production"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    tracer = trace.get_tracer("autovend.agent.tracer")

    print("Generating and pushing OTLP spans...")

    for session_idx in range(3):
        with tracer.start_as_current_span(f"Chat Session #{session_idx + 1}") as root_span:
            root_span.set_attribute("http.method", "POST")
            root_span.set_attribute("http.route", "/api/chat/stream")
            root_span.set_attribute("session.id", f"sess_{session_idx + 100}")

            # 1. Gate 1 Semantic Router
            with tracer.start_as_current_span("Gate 1: Semantic Router Classification") as router_span:
                router_span.set_attribute("router.intent", "budget_objection")
                router_span.set_attribute("router.similarity", 0.892)
                router_span.set_attribute("router.latency_us", 2.85)
                time.sleep(0.005)

            # 2. Local LLM Intent & Profile Extraction
            with tracer.start_as_current_span("Local LLM Extraction (Qwen3-8B)") as llm_span:
                llm_span.set_attribute("llm.provider", "vLLM-Local")
                llm_span.set_attribute("llm.model", "qwen3-8b-bnb-4bit")
                llm_span.set_attribute("llm.prompt_tokens", 245)
                llm_span.set_attribute("llm.completion_tokens", 68)
                llm_span.set_attribute("llm.ttft_ms", 12.4)
                time.sleep(0.12)

            # 3. Vector Database RAG Search
            with tracer.start_as_current_span("ChromaDB RAG Retrieval") as rag_span:
                rag_span.set_attribute("db.system", "chromadb")
                rag_span.set_attribute("rag.top_k", 3)
                rag_span.set_attribute("rag.matched_cars", "Xiaomi SU7, Tesla Model 3")
                time.sleep(0.03)

            # 4. Cloud LLM Synthesis
            with tracer.start_as_current_span("Cloud LLM Recommendation Synthesis (DeepSeek-V4)") as cloud_span:
                cloud_span.set_attribute("llm.provider", "DeepSeek-Cloud")
                cloud_span.set_attribute("llm.model", "deepseek-v4-flash")
                cloud_span.set_attribute("llm.prompt_tokens", 512)
                cloud_span.set_attribute("llm.completion_tokens", 180)
                time.sleep(0.25)

    # Force flush to ensure spans are transmitted
    provider.shutdown()
    print("Spans successfully flushed to OpenTelemetry Collector!")

if __name__ == "__main__":
    main()
