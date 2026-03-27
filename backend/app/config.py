"""
Unified configuration for AutoVend Backend.
Loads settings from environment variables (via .env file).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (AutoVend/.env)
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# LLM Configuration (DeepSeek, OpenAI-compatible)
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "deepseek-chat")
OPENAI_URL: str = os.getenv("OPENAI_URL", "https://api.deepseek.com/v1")

# Embedding Model
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# ChromaDB
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma_db"))
CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "vehicle_knowledge")

# Vehicle Data Source
VEHICLE_DATA_DIR: str = os.getenv(
    "VEHICLE_DATA_DIR", str(_project_root / "DataInUse" / "VehicleData")
)

# Application Settings
APP_ENVIRONMENT: str = os.getenv("APP_ENVIRONMENT", "development")
DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))

# Storage directories
STORAGE_DIR = BASE_DIR / "storage"
SESSIONS_DIR = STORAGE_DIR / "sessions"
PROFILES_DIR = STORAGE_DIR / "profiles"
TEST_DRIVES_DIR = STORAGE_DIR / "test_drives"

# Ensure directories exist
for _dir in [DATA_DIR, STORAGE_DIR, SESSIONS_DIR, PROFILES_DIR, TEST_DRIVES_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)
