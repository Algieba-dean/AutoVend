"""
FastAPI entry point for AutoVend Backend.

Wires up routes, initializes the LLM and SalesAgent on startup.
Backend is a thin orchestrator; all AI logic lives in agent/.
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.config import APP_ENVIRONMENT, DEBUG, OPENAI_API_KEY
from backend.app.routes import chat, profile, test_drive, voice
from src.agent.sales_agent import SalesAgent

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _local_llm_configured() -> bool:
    """True when a local vLLM endpoint is configured (see .env LOCAL_LLM_BASE_URL)."""
    from src.utils.config import config as core_config

    return bool(core_config.local_llm_base_url)


# ── Startup state (used by /health) ────────────────────────────
_startup_status = {
    "agent_ready": False,
    "rag_index_ready": False,
    "rag_index_error": "",
    "voice_ready": False,
    "voice_error": "",
    "pii_ready": False,
    "pii_error": "",
    "semantic_router_ready": False,
    "semantic_router_error": "",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan: initialize LLM, SalesAgent, and vehicle index on startup."""
    logger.info("Initializing hybrid LLM router and SalesAgent...")

    # The agent takes two LlamaIndex-protocol LLMs: one for schema-constrained
    # extraction (routed to the local vLLM server when configured — every turn
    # pays this cost), one for the customer-facing reply (routed to the cloud
    # API). RoutedLLM wraps the HybridRouter so the agent stays unaware that
    # routing exists; see src/llm/router.py for the policy and fallbacks.
    #
    # Without any credentials, fall back to LlamaIndex's MockLLM so the API
    # still boots and every non-generative path (retrieval, stage transitions,
    # storage) stays exercisable. Failing at first-token time instead would
    # make a missing key look like a runtime bug.
    if OPENAI_API_KEY or _local_llm_configured():
        from src.llm.llamaindex_adapter import build_agent_llms
        from src.llm.router import build_default_router

        router = build_default_router()
        app.state.llm_router = router
        extraction_llm, generation_llm = build_agent_llms(router)
        logger.info(f"LLM routing: {router.describe()}")
        agent = SalesAgent(llm=extraction_llm, generation_llm=generation_llm)
    else:
        from llama_index.core.llms import MockLLM

        app.state.llm_router = None
        llm = MockLLM(max_tokens=500)
        logger.warning("No LLM credentials configured — running with MockLLM.")
        agent = SalesAgent(llm=llm)
    chat.set_agent(agent)
    _startup_status["agent_ready"] = True

    # Initialize voice services
    try:
        from src.agent.voice.asr import WhisperASR
        from src.agent.voice.pipeline import VoicePipeline
        from src.agent.voice.tts import EdgeTTSService

        asr = WhisperASR(model_size="base", device="cpu", compute_type="int8")
        tts = EdgeTTSService()
        voice_pipeline = VoicePipeline(agent=agent, asr=asr, tts=tts)
        voice.set_voice_pipeline(voice_pipeline)
        voice.set_asr(asr)
        voice.set_tts(tts)
        _startup_status["voice_ready"] = True
        logger.info("Voice services initialized (ASR + TTS + Pipeline).")
    except Exception as e:
        _startup_status["voice_ready"] = False
        _startup_status["voice_error"] = str(e)
        logger.warning(f"Voice services not available: {e}")

    # PII interceptor. Built eagerly so the spaCy load happens at startup
    # rather than on some unlucky user's first message.
    try:
        from src.privacy import get_interceptor

        interceptor = get_interceptor()
        interceptor.detect("warmup")  # forces the analyzer to build
        chat.set_pii_interceptor(interceptor)
        _startup_status["pii_ready"] = True
        logger.info("PII interceptor ready.")
    except Exception as e:
        _startup_status["pii_error"] = str(e)
        logger.warning(
            f"PII interceptor unavailable: {e}. Messages will NOT be masked "
            "before reaching the LLM."
        )

    # Semantic router. Optional: without the anchor artifact every turn simply
    # takes the full path, which is what happened before this layer existed.
    try:
        from src.semantic_router import get_router as get_semantic_router

        semantic_router = get_semantic_router()
        if semantic_router is not None:
            chat.set_semantic_router(semantic_router)
            _startup_status["semantic_router_ready"] = True
            logger.info(f"Semantic router ready: {semantic_router.summary()}")
        else:
            _startup_status["semantic_router_error"] = (
                "anchors not built — run: python -m src.semantic_router.build"
            )
    except Exception as e:
        _startup_status["semantic_router_error"] = str(e)
        logger.warning(f"Semantic router unavailable: {e}")

    # Try to build the hybrid retrieval pipeline (indices may not exist yet).
    # Constructing it eagerly means the embedding model and SQLite catalogue are
    # warm before the first request instead of on a user's first turn.
    try:
        from src.retrieval.hybrid_pipeline import build_default_pipeline

        pipeline = build_default_pipeline(llm_router=getattr(app.state, "llm_router", None))
        chat.set_pipeline(pipeline)
        _startup_status["rag_index_ready"] = True
        logger.info("Hybrid retrieval pipeline ready.")
    except Exception as e:
        _startup_status["rag_index_error"] = str(e)
        logger.warning(
            f"Hybrid retrieval pipeline not available: {e}. "
            "Vehicle retrieval will be disabled. "
            "Run 'python -m src.main build-index' to build the indices."
        )

    logger.info("SalesAgent initialized.")
    yield
    logger.info("Shutting down.")


# ── Request-ID middleware ──────────────────────────────────────
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request_id to every response for traceability."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Create FastAPI app
app = FastAPI(
    title="AutoVend API",
    description="LlamaIndex-based intelligent automotive sales assistant API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(chat.router)
app.include_router(profile.router)
app.include_router(test_drive.router)
app.include_router(voice.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured validation errors for better client UX."""
    request_id = getattr(request.state, "request_id", "")
    errors = []
    for err in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            }
        )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": errors,
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    request_id = getattr(request.state, "request_id", "")
    logger.error(f"Unhandled exception (request_id={request_id}): {exc}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "request_id": request_id,
        },
    )


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "AutoVend API",
        "version": "2.0.0",
        "environment": APP_ENVIRONMENT,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check with dependency status."""
    agent_ok = _startup_status["agent_ready"]
    rag_ok = _startup_status["rag_index_ready"]
    overall = "ok" if agent_ok else "degraded"
    if not agent_ok:
        overall = "unhealthy"
    elif not rag_ok:
        overall = "degraded"

    voice_ok = _startup_status["voice_ready"]

    router = getattr(app.state, "llm_router", None)

    return {
        "status": overall,
        "components": {
            "agent": "ok" if agent_ok else "unavailable",
            "rag_index": "ok" if rag_ok else "unavailable",
            "voice": "ok" if voice_ok else "unavailable",
            # Both fail open: absent means the turn takes the long path, not
            # that the service is broken. PII being off is still worth seeing
            # at a glance, since it means messages reach the LLM unmasked.
            "pii_interceptor": "ok" if _startup_status["pii_ready"] else "disabled",
            "semantic_router": ("ok" if _startup_status["semantic_router_ready"] else "disabled"),
        },
        "llm_routing": router.describe() if router else {"mode": "mock"},
        "rag_index_error": _startup_status["rag_index_error"] or None,
        "voice_error": _startup_status["voice_error"] or None,
        "pii_error": _startup_status["pii_error"] or None,
        "semantic_router_error": _startup_status["semantic_router_error"] or None,
    }


@app.get("/telemetry/llm")
async def llm_telemetry():
    """
    Per-route LLM telemetry: call counts, latency and TTFT percentiles, token
    totals, and actual spend versus the all-cloud counterfactual.

    In-memory and process-local — resets on restart. This is the evidence for
    the local/cloud routing split, not a monitoring system.
    """
    from src.llm.telemetry import telemetry

    return telemetry.summary()
