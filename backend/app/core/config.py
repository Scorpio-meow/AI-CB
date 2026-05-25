import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 獲取 backend 目錄的絕對路徑
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_DIR / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # === 核心 LLM 配置 ===
    LLM_API_BASE: str = "http://localhost:5000"
    LLM_TIMEOUT: float = 120.0
    MODEL_NAME: str = "gemma4:26b"

    # === 安全配置 ===
    ADMIN_API_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # === 環境設定 ===
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    RELOAD: bool = True
    LOG_LEVEL: str = "INFO"

    # === 資料庫配置 ===
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True

    # === Redis 配置 ===
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 7967
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    ENABLE_REDIS_CACHE: bool = True
    CACHE_TTL_SECONDS: int = 300

    # === RAG 系統 - 模型配置 ===
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"

    # === Hugging Face / Transformers Cache ===
    HF_HOME: str = "D:/AI-CB/backend/data/hf_home"
    HUGGINGFACE_HUB_CACHE: str = "D:/AI-CB/backend/data/hf_home/hub"
    TRANSFORMERS_CACHE: str = "D:/AI-CB/backend/data/hf_home/transformers"
    SENTENCE_TRANSFORMERS_HOME: str = "D:/AI-CB/backend/data/hf_home/sentence-transformers"
    HF_HUB_DISABLE_SYMLINKS_WARNING: int = 1

    # === RAG 系統 - GPU 配置 ===
    FORCE_CPU: bool = True
    USE_FP16_QUANTIZATION: bool = False
    GPU_BATCH_SIZE: int = 128
    CPU_BATCH_SIZE: int = 32
    USE_FAISS_GPU: bool = False
    FAISS_GPU_DEVICE: int = 0
    FAISS_GPU_TEMP_MEMORY: int = 2147483648

    # === RAG 系統 - 檢索參數 ===
    SIMILARITY_THRESHOLD: float = 0.30
    TOP_K: int = 30
    RERANK_TOP_K: int = 50
    FINAL_K: int = 8
    RERANK_WEIGHT: float = 0.85
    FINAL_THRESHOLD: float = 0.15
    HYBRID_ALPHA: float = 0.75
    NORMALIZATION: str = "max"

    # === RAG 系統 - 文檔處理 ===
    CHUNK_SIZE: int = 300
    CHUNK_OVERLAP: int = 100
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "data/uploads"

    # === RAG 系統 - 索引管理 ===
    ENABLE_AUTO_REINDEX: int = 0
    ENABLE_AUTO_REINDEX_TASK: int = 1
    REINDEX_HOURS: int = 24
    DATA_DIR: str = "data"
    FAISS_INDEX_PATH: str = "data/faiss_index.bin"
    DOCUMENTS_PATH: str = "data/documents.pkl"
    BM25_INDEX_DIR: str = "data/bm25_index"
    METADATA_PATH: str = "data/index_metadata.pkl"

    # === CORS 配置 ===
    ALLOWED_ORIGINS: str = "http://localhost:3001,https://localhost:3001,http://127.0.0.1:3001,https://127.0.0.1:3001"
    DEVTUNNEL_URL: str = ""

    # === 速率限制 ===
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    # === 背景任務 ===
    UPLOADS_WATCHER_INTERVAL: int = 30
    ENABLE_BATCH_ACCUMULATION: bool = False
    BATCH_ACCUMULATOR_SIZE: int = 32

    # === 健康檢查 ===
    BASE_URL: str = "http://backend:8001"

    # === 工作流設定 ===
    WORKFLOW_CYCLE_LIMIT: int = 2
    WORKFLOW_MAX_HISTORY: int = 20
    WORKFLOW_MAX_CONTEXT: int = 5

    @property
    def allowed_origins_list(self) -> List[str]:
        if not self.ALLOWED_ORIGINS:
            return []
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        if self.DEVTUNNEL_URL and self.DEVTUNNEL_URL.strip():
            origins.append(self.DEVTUNNEL_URL.strip())
        return origins

# 建立全局單例 Settings
settings = Settings()
