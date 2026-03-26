"""
FastAPI entry point for AutoVend RAG Backend.

Wires up routes, initializes the LLM and workflow engine on startup.
"""

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from llama_index.llms.openai_like import OpenAILike

from app.config import APP_ENVIRONMENT, DEBUG, OPENAI_API_KEY, OPENAI_MODEL, OPENAI_URL
from app.routes import chat, profile, test_drive
from app.workflow.stage_workflow import StageWorkflow

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan: initialize LLM and workflow on startup."""
    logger.info("Initializing LLM and workflow engine...")

    llm = OpenAILike(
        api_key=OPENAI_API_KEY,
        api_base=OPENAI_URL,
        model=OPENAI_MODEL,
        is_chat_model=True,
        temperature=0.7,
        max_tokens=500,
    )

    # Try to load vehicle index (may not exist yet)
    vehicle_index = None
    try:
        from app.rag.vehicle_index import get_vehicle_index
        vehicle_index = get_vehicle_index()
        logger.info("Vehicle index loaded successfully.")
    except Exception as e:
        logger.warning(
            f"Vehicle index not available: {e}. "
            "RAG retrieval will be disabled. "
            "Run 'python -m scripts.build_index' to build the index."
        )

    workflow = StageWorkflow(llm=llm, vehicle_index=vehicle_index)
    chat.set_workflow(workflow)

    logger.info("Workflow engine initialized.")
    yield
    logger.info("Shutting down.")


# Create FastAPI app
app = FastAPI(
    title="AutoVend RAG API",
    description="LlamaIndex-based intelligent automotive sales assistant API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "AutoVend RAG API",
        "version": "1.0.0",
        "environment": APP_ENVIRONMENT,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
