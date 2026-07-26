"""
Configuration for the AutoVend FastAPI layer.

Data-plane settings (Chroma dir, vehicle data dir, embedding model, LLM
credentials) are NOT redefined here — they are re-exported from
`src.utils.config`, which is the single source of truth. Previously the two
config modules disagreed: this one pointed at `backend/data/chroma_db` while
the core library used `./data/chroma_db`, so the index built by one was
invisible to the other.

Only genuinely backend-specific settings (HTTP host/port, JSON storage dirs)
are defined locally.
"""

import os
from pathlib import Path

from src.utils.config import PROJECT_ROOT, config

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(config.chroma_persist_dir).parent

# ── Re-exported from the core config (single source of truth) ──────────
OPENAI_API_KEY: str = config.llm_api_key or ""
OPENAI_MODEL: str = config.llm_model
OPENAI_URL: str = config.llm_base_url

EMBEDDING_MODEL: str = config.embedding_model
CHROMA_PERSIST_DIR: str = config.chroma_persist_dir
CHROMA_COLLECTION_NAME: str = config.chroma_collection_name
VEHICLE_DATA_DIR: str = config.vehicle_data_dir

APP_ENVIRONMENT: str = config.app_environment
DEBUG: bool = config.debug

# ── Backend-only settings ──────────────────────────────────────────────
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))

# Storage directories (runtime JSON state) live at the project root so that
# `uvicorn` and CLI runs share one store.
STORAGE_DIR = PROJECT_ROOT / "storage"
SESSIONS_DIR = STORAGE_DIR / "sessions"
PROFILES_DIR = STORAGE_DIR / "profiles"
TEST_DRIVES_DIR = STORAGE_DIR / "test_drives"

# Ensure directories exist
for _dir in [DATA_DIR, STORAGE_DIR, SESSIONS_DIR, PROFILES_DIR, TEST_DRIVES_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)
