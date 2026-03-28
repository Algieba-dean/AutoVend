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
from llama_index.llms.openai_like import OpenAILike
from starlette.middleware.base import BaseHTTPMiddleware

from agent.sales_agent import SalesAgent
from app.config import APP_ENVIRONMENT, DEBUG, OPENAI_API_KEY, OPENAI_MODEL, OPENAI_URL
from app.routes import chat, profile, test_drive, voice

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ── Startup state (used by /health) ────────────────────────────
_startup_status = {
    "agent_ready": False,
    "rag_index_ready": False,
    "rag_index_error": "",
    "voice_ready": False,
    "voice_error": "",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan: initialize LLM, SalesAgent, and vehicle index on startup."""
    logger.info("Initializing LLM and SalesAgent...")

    llm = OpenAILike(
        api_key=OPENAI_API_KEY,
        api_base=OPENAI_URL,
        model=OPENAI_MODEL,
        is_chat_model=True,
        temperature=0.7,
        max_tokens=500,
    )

    agent = SalesAgent(llm=llm)
    chat.set_agent(agent)
    _startup_status["agent_ready"] = True

    # Initialize voice services
    try:
        from agent.voice.asr import WhisperASR
        from agent.voice.pipeline import VoicePipeline
        from agent.voice.tts import EdgeTTSService

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

    # Try to load vehicle index (may not exist yet)
    try:
        from app.rag.vehicle_index import get_vehicle_index

        vehicle_index = get_vehicle_index()
        chat.set_vehicle_index(vehicle_index)
        _startup_status["rag_index_ready"] = True
        logger.info("Vehicle index loaded successfully.")
    except Exception as e:
        _startup_status["rag_index_error"] = str(e)
        logger.warning(
            f"Vehicle index not available: {e}. "
            "RAG retrieval will be disabled. "
            "Run 'python -m scripts.build_index' to build the index."
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

    return {
        "status": overall,
        "components": {
            "agent": "ok" if agent_ok else "unavailable",
            "rag_index": "ok" if rag_ok else "unavailable",
            "voice": "ok" if voice_ok else "unavailable",
        },
        "rag_index_error": _startup_status["rag_index_error"] or None,
        "voice_error": _startup_status["voice_error"] or None,
    }
