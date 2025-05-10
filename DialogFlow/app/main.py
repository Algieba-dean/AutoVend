"""
Main application file for AutoVend.
"""
import logging
import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html

from app.config import DEBUG, APP_SECRET_KEY, APP_ENVIRONMENT
from app.utils.sample_data import init_sample_data

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AutoVend API",
    description="API for the AutoVend intelligent automotive sales AI agent system",
    version="0.1.0",
    docs_url=None,  # We'll serve this manually for more control
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files if they exist
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Import router after app is created to avoid circular imports
from app.routes.api import router as api_router

# Include API router
app.include_router(api_router)


# Initialize sample data
@app.on_event("startup")
async def startup_event():
    """
    Initialize sample data on startup.
    """
    try:
        init_sample_data()
        logger.info("Sample data initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize sample data: {str(e)}")


# Custom Swagger UI route (can be secured if needed)
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - API Documentation",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js" if os.path.exists(static_dir) else "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css" if os.path.exists(static_dir) else "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css",
    )


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler.
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint, returns basic API information.
    """
    return {
        "name": "AutoVend API",
        "version": "0.1.0",
        "environment": APP_ENVIRONMENT,
        "docs": "/docs",
        "redoc": "/redoc",
    }


# Health check endpoint
@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok"} 