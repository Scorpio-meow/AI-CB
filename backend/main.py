from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os as _os
_env_path = _os.path.join(_os.path.dirname(__file__), '.env')
load_dotenv(_env_path)
from app.api import chat, admin, documents, workflow, custom_agent
from app.models.database import create_tables
from app.tasks.uploads_watcher import scan_and_cleanup_uploads
from app.tasks.index_rebuilder import start_index_rebuilder
from app.core.rag_manager import get_rag_system
from app.core.security import (
    SecurityHeadersMiddleware, 
    RateLimitMiddleware,
    validate_api_endpoint
)
import asyncio
import os
import logging

# Load environment variables
load_dotenv()

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('logs/app.log', encoding='utf-8')  # File output
    ]
)

# Reduce uvicorn access log noise
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Get configuration from environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# 根據環境配置 CORS
if ENVIRONMENT == "production":
    # 生產環境：嚴格的白名單
    DEFAULT_ALLOWED_ORIGINS = [
        "https://yourdomain.com",
        "https://www.yourdomain.com"
    ]
    # 🔒 安全加固：生產環境禁用 regex
    DEFAULT_ALLOWED_ORIGIN_REGEX = None
    logger.info("🔒 生產環境模式：使用嚴格的 CORS 白名單")
else:
    # 開發環境：允許 localhost
    DEFAULT_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "https://127.0.0.1:3000",
    ]
    # 🔒 安全加固：開發環境也移除 regex，改用精確白名單
    # 如需使用 DevTunnels，請在 .env 中明確指定完整 URL
    devtunnel_url = os.getenv("DEVTUNNEL_URL", "").strip()
    if devtunnel_url:
        DEFAULT_ALLOWED_ORIGINS.append(devtunnel_url)
        logger.warning(f"⚠️  開發環境添加 DevTunnel: {devtunnel_url}")
    
    DEFAULT_ALLOWED_ORIGIN_REGEX = None  # 移除不安全的 regex
    logger.info("🔓 開發環境模式：使用精確的 localhost 白名單")

_raw_allowed_origins = os.getenv("ALLOWED_ORIGINS")
if _raw_allowed_origins:
    ALLOWED_ORIGINS = [origin.strip() for origin in _raw_allowed_origins.split(",") if origin.strip()]
else:
    ALLOWED_ORIGINS = DEFAULT_ALLOWED_ORIGINS

# 🔒 安全加固：完全移除 CORS regex 支援
# 所有環境都使用精確的白名單
ALLOWED_ORIGIN_REGEX = None
if os.getenv("ALLOWED_ORIGIN_REGEX"):
    logger.error("❌ ALLOWED_ORIGIN_REGEX 已被禁用，請改用精確的 ALLOWED_ORIGINS 或 DEVTUNNEL_URL")
    if ENVIRONMENT == "production":
        raise RuntimeError("生產環境禁止使用 CORS regex 配置")

UPLOADS_WATCHER_INTERVAL = int(os.getenv("UPLOADS_WATCHER_INTERVAL", "30"))

# 修正：使用 lifespan 事件處理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting ChatBot application...")
    
    # Initialize database tables
    await create_tables()
    
    # Initialize global RAG system (singleton)
    logger.info("Initializing global RAG system...")
    rag_system = get_rag_system()
    logger.info(f"RAG system initialized: {rag_system.get_vector_store_info()}")
    
    # Start background tasks
    uploads_watcher_task = asyncio.create_task(scan_and_cleanup_uploads(UPLOADS_WATCHER_INTERVAL))
    app.state._uploads_watcher_task = uploads_watcher_task
    logger.info("Uploads watcher task started")
    
    # Start periodic index rebuilder
    index_rebuilder_task = await start_index_rebuilder()
    app.state._index_rebuilder_task = index_rebuilder_task
    if index_rebuilder_task:
        logger.info("Index rebuilder task started")
    
    logger.info("ChatBot application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ChatBot application...")
    
    # Cancel uploads watcher
    task = getattr(app.state, '_uploads_watcher_task', None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("Uploads watcher task stopped")
    
    # Cancel index rebuilder
    rebuilder_task = getattr(app.state, '_index_rebuilder_task', None)
    if rebuilder_task:
        rebuilder_task.cancel()
        try:
            await rebuilder_task
        except asyncio.CancelledError:
            pass
        logger.info("Index rebuilder task stopped")
    
    logger.info("ChatBot application shutdown complete")

app = FastAPI(
    title="ChatBot API",
    description="ChatBot with Contextual RAG",
    version="1.0.0",
    lifespan=lifespan  # 使用新的 lifespan 參數
)

# Security middleware - 添加安全標頭
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting middleware - 防止 API 濫用
rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
if rate_limit_enabled:
    rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    app.add_middleware(RateLimitMiddleware, calls=rate_limit_per_minute, period=60)
    logger.info(f"Rate limiting enabled: {rate_limit_per_minute} requests per minute")

# CORS middleware - 安全配置
# 構建 CORS 配置
cors_kwargs = {
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    "allow_headers": ["*"],
}

# 🔒 安全加固：所有環境統一使用白名單策略
cors_kwargs["allow_origins"] = ALLOWED_ORIGINS
logger.info(f"CORS 白名單: {ALLOWED_ORIGINS}")

# 記錄安全配置
if ENVIRONMENT == "production":
    logger.info("� CORS 生產模式：嚴格白名單")
else:
    logger.info("🔓 CORS 開發模式：精確白名單（無 regex）")

app.add_middleware(
    CORSMiddleware,
    **cors_kwargs,
)

# Include routers
from app.api import tags as tags_router
from app.api import auth  # 添加認證路由

app.include_router(auth.router, tags=["authentication"])  # 認證端點 (無前綴,直接 /api/auth)
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(custom_agent.router, prefix="/api/custom_agents", tags=["Custom Agents"])
app.include_router(tags_router.router, prefix="/api", tags=["tags"])

@app.get("/")
async def root():
    return {"message": "ChatBot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Handle Socket.IO polling requests (for dev tools/HMR)
@app.get("/socket.io/")
async def socket_io_fallback():
    return {"error": "Socket.IO not supported. Use WebSocket at /api/workflow/ws"}

if __name__ == "__main__":
    import uvicorn
    
    # 修正：提供預設值，避免 None 類型錯誤
    host = os.getenv("HOST", "0.0.0.0")
    port_str = os.getenv("PORT", "8000")
    
    try:
        port = int(port_str)
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f"PORT environment variable must be an integer, got: {port_str}") from exc
    
    reload_env = os.getenv("RELOAD", "true")
    reload_flag = str(reload_env).lower() in ("1", "true", "yes")
    
    uvicorn.run(app, host=host, port=port, reload=reload_flag)
