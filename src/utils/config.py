"""
配置管理模块

统一管理应用配置，包括环境变量、API密钥、模型参数等。

两点约定：

1. **路径一律锚定到项目根目录**，而不是进程 CWD。否则 `uvicorn backend.app.main:app`
   与 `python -m src.main` 会各自建出一份 chroma_db。
2. **LLM 凭据支持 GROQ_* 别名**。历史上 `.env` 写的是 `GROQ_API_KEY`，而这里读的是
   `LLM_API_KEY`，键名对不上导致系统静默回落到 MockLLM。
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（src/utils/config.py -> src/utils -> src -> AutoVend）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"
DEFAULT_LLM_BASE_URL = "https://api.groq.com/openai/v1"


def _resolve(path: str) -> str:
    """把相对路径锚定到项目根目录，绝对路径原样返回。"""
    p = Path(path)
    return str(p if p.is_absolute() else (PROJECT_ROOT / p).resolve())


class Config(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # Allow extra environment variables
    )

    # LLM API configuration - generic for OpenAI-compatible providers.
    # GROQ_* 作为兼容别名（必须走 AliasChoices：os.getenv 读不到 .env 文件里的值）。
    llm_api_key: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("LLM_API_KEY", "GROQ_API_KEY")
    )
    llm_model: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("LLM_MODEL", "GROQ_MODEL")
    )
    llm_base_url: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("LLM_BASE_URL", "GROQ_BASE_URL")
    )
    llm_provider: Optional[str] = Field(default=None, validation_alias=AliasChoices("LLM_PROVIDER"))

    # Local inference server (vLLM, OpenAI-compatible).
    # Leave local_llm_base_url unset to route every task to the cloud.
    local_llm_base_url: Optional[str] = None
    local_llm_model: str = "local-llama"
    # vLLM does not authenticate by default; the OpenAI client still requires a
    # non-empty bearer token, so this is a placeholder rather than a secret.
    local_llm_api_key: str = "local"

    # Vector Database Configuration
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "vehicle_knowledge"

    # Structured filter database (SQLite)
    vehicle_db_path: str = "./data/vehicles.db"

    # Sparse (BM25) index
    bm25_index_path: str = "./data/bm25_index.pkl"

    # Embedding Model Configuration - BGE-M3
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "auto"

    # Data Configuration
    vehicle_data_dir: str = "./DataInUse/VehicleData"

    # Application Settings
    app_environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # 检索配置
    top_k: int = Field(default=10, description="检索返回的最大结果数")
    similarity_threshold: float = Field(default=0.7, description="相似度阈值")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._apply_credential_aliases()
        self._anchor_paths()
        self._ensure_directories()

    def _apply_credential_aliases(self) -> None:
        """
        LLM_* / GROQ_* 别名由 AliasChoices 解析；这里只补默认值和自动判定。

        provider 未显式指定时按 key 是否存在自动判定：有 key 走 groq，没有走 mock。
        这样本地开发默认可用真实模型，CI 无 secret 时自动降级为 mock 而不是报错。
        """
        if not self.llm_model:
            self.llm_model = DEFAULT_LLM_MODEL
        if not self.llm_base_url:
            self.llm_base_url = DEFAULT_LLM_BASE_URL
        if not self.llm_provider:
            self.llm_provider = "groq" if self.llm_api_key else "mock"

    def _anchor_paths(self) -> None:
        """所有数据路径锚定到项目根目录。"""
        self.chroma_persist_dir = _resolve(self.chroma_persist_dir)
        self.vehicle_db_path = _resolve(self.vehicle_db_path)
        self.bm25_index_path = _resolve(self.bm25_index_path)
        self.vehicle_data_dir = _resolve(self.vehicle_data_dir)

    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.chroma_persist_dir,
            os.path.dirname(self.chroma_persist_dir),
            os.path.dirname(self.vehicle_db_path),
        ]

        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

    @property
    def has_llm_credentials(self) -> bool:
        """是否配置了可用的 LLM 凭据（决定走真实模型还是 mock）"""
        return bool(self.llm_api_key)

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_environment.lower() == "production"

    @property
    def vehicle_data_path(self) -> Path:
        """车辆数据目录路径"""
        return Path(self.vehicle_data_dir)

    @property
    def chroma_path(self) -> Path:
        """ChromaDB存储路径"""
        return Path(self.chroma_persist_dir)


# 全局配置实例
config = Config()
