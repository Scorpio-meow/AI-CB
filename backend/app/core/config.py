import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_DIR / ".env"
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )
    LLM_API_BASE: str = "http://localhost:5000"
    LLM_TIMEOUT: float = 120.0
    MODEL_NAME: str = "gemma4:26b"
    OLLAMA_API_KEY: Optional[str] = None
    ENABLE_WEB_SEARCH: bool = True
    AGENT_MAX_TURNS: int = 5
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    AVAILABLE_MODELS: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_API_BASE: str = "https://api.anthropic.com"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com"
    ADMIN_API_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    RELOAD: bool = True
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_RECYCLE: int = 3600
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    HF_HOME: str = "./data/hf_home"
    HUGGINGFACE_HUB_CACHE: str = "./data/hf_home/hub"
    TRANSFORMERS_CACHE: str = "./data/hf_home/transformers"
    SENTENCE_TRANSFORMERS_HOME: str = "./data/hf_home/sentence-transformers"
    HF_HUB_DISABLE_SYMLINKS_WARNING: int = 1
    FORCE_CPU: bool = True
    USE_FP16_QUANTIZATION: bool = False
    GPU_BATCH_SIZE: int = 128
    CPU_BATCH_SIZE: int = 32
    USE_FAISS_GPU: bool = False
    FAISS_GPU_DEVICE: int = 0
    FAISS_GPU_TEMP_MEMORY: int = 2147483648
    SIMILARITY_THRESHOLD: float = 0.30
    TOP_K: int = 30
    RERANK_TOP_K: int = 50
    FINAL_K: int = 8
    RERANK_WEIGHT: float = 0.85
    FINAL_THRESHOLD: float = 0.15
    HYBRID_ALPHA: float = 0.75
    NORMALIZATION: str = "max"
    CHUNK_SIZE: int = 300
    CHUNK_OVERLAP: int = 100
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "data/uploads"
    ENABLE_AUTO_REINDEX: int = 0
    ENABLE_AUTO_REINDEX_TASK: int = 1
    REINDEX_HOURS: int = 24
    DATA_DIR: str = "data"
    FAISS_INDEX_PATH: str = "data/faiss_index.bin"
    DOCUMENTS_PATH: str = "data/documents.pkl"
    BM25_INDEX_DIR: str = "data/bm25_index"
    METADATA_PATH: str = "data/index_metadata.pkl"
    ALLOWED_ORIGINS: str = "http://localhost:3001,https://localhost:3001,http://127.0.0.1:3001,https://127.0.0.1:3001"
    DEVTUNNEL_URL: str = ""
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    UPLOADS_WATCHER_INTERVAL: int = 30
    ENABLE_BATCH_ACCUMULATION: bool = False
    BATCH_ACCUMULATOR_SIZE: int = 32
    BASE_URL: str = "http://backend:8001"
    @property
    def allowed_origins_list(self) -> List[str]:
        if not self.ALLOWED_ORIGINS:
            return []
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        if self.DEVTUNNEL_URL and self.DEVTUNNEL_URL.strip():
            origins.append(self.DEVTUNNEL_URL.strip())
        return origins
settings = Settings()
