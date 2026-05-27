"""
Personal-KB 后端配置管理
所有配置通过环境变量 / .env 文件加载
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    # -------------------- 项目 --------------------
    PROJECT_NAME: str = "Personal-KB"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)
    SECRET_KEY: str = "change-me-to-a-random-string-at-least-32-chars"

    # -------------------- 数据库 PostgreSQL --------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "personal_kb"
    POSTGRES_USER: str = "kb_user"
    POSTGRES_PASSWORD: str = "kb_password"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # -------------------- Redis --------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    # -------------------- MinIO --------------------
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "kb-assets"
    MINIO_SECURE: bool = False
    MINIO_PUBLIC_URL: str = "http://localhost:9000"

    # -------------------- Qdrant --------------------
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "kb_chunks"
    QDRANT_VECTOR_SIZE: int = 1024

    # -------------------- Model Gateway --------------------
    MODEL_GATEWAY_URL: str = "http://localhost:8900"
    DEFAULT_LLM: str = "qwen3:8b"
    DEFAULT_EMBEDDING: str = "bge-m3"
    DEFAULT_RERANK: str = "qwen3-reranker-0.6b"

    # -------------------- 存储路径 --------------------
    UPLOAD_DIR: str = "./uploads"
    NAS_MOUNT_PATH: str = "/mnt/nas"
    LOCAL_STORAGE_PATH: str = "./storage"

    # -------------------- 切片参数 --------------------
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120
    VECTOR_TOP_K: int = 40
    BM25_TOP_K: int = 40
    RERANK_TOP_K: int = 8
    MAX_CONTEXT_TOKENS: int = 6000

    # -------------------- OCR / ASR --------------------
    PADDLEOCR_LANG: str = "ch"
    WHISPER_MODEL: str = "medium"
    FFMPEG_PATH: str = "ffmpeg"

    # -------------------- JWT --------------------
    JWT_SECRET_KEY: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # -------------------- 路径 --------------------
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent


@lru_cache()
def get_settings() -> Settings:
    return Settings()
