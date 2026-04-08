"""
配置管理模块

统一管理应用配置，包括环境变量、API密钥、模型参数等。
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """应用配置类"""

    # LLM API configuration - generic for OpenAI-compatible providers
    llm_api_key: Optional[str] = Field(default=None, env="LLM_API_KEY")
    llm_model: str = Field(default="llama-3.1-70b-versatile", env="LLM_MODEL")
    llm_base_url: str = Field(
        default="https://api.groq.com/openai/v1", env="LLM_BASE_URL"
    )
    llm_provider: str = Field(default="mock", env="LLM_PROVIDER")

    # Vector Database Configuration
    chroma_persist_dir: str = Field(
        default="./data/chroma_db", env="CHROMA_PERSIST_DIR"
    )
    chroma_collection_name: str = Field(
        default="vehicle_knowledge", env="CHROMA_COLLECTION_NAME"
    )

    # Embedding Model Configuration - BGE-M3
    embedding_model: str = Field(default="BAAI/bge-m3", env="EMBEDDING_MODEL")
    embedding_device: str = Field(default="auto", env="EMBEDDING_DEVICE")

    # Data Configuration
    vehicle_data_dir: str = Field(
        default="./DataInUse/VehicleData", env="VEHICLE_DATA_DIR"
    )

    # Application Settings
    app_environment: str = Field(default="development", env="APP_ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # 检索配置
    top_k: int = Field(default=10, description="检索返回的最大结果数")
    similarity_threshold: float = Field(default=0.7, description="相似度阈值")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.chroma_persist_dir,
            os.path.dirname(self.chroma_persist_dir),
        ]

        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

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
