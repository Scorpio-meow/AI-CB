import os
import logging
import torch
import uvicorn
from fastapi import FastAPI

from app.core.config import settings
from app.core.lifespan import lifespan
from app.middleware import setup_middlewares
from app.api import chat, admin, documents, workflow, custom_agent
from app.api import tags as tags_router
from app.api import auth

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging
log_level = settings.LOG_LEVEL.upper()
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

app = FastAPI(
    title="ChatBot API",
    description="ChatBot with Contextual RAG",
    version="1.0.0",
    lifespan=lifespan
)

# Setup all middlewares (CORS, Rate Limiting, Security Headers)
setup_middlewares(app)

# Include routers
app.include_router(auth.router, tags=["authentication"])  # 認證端點 (無前綴, 直接 /api/auth)
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

def create_app():
    # 啟動時列印 GPU/FAISS 可用性資訊
    try:
        cuda_available = torch.cuda.is_available()
    except Exception:
        cuda_available = False

    logger.info(f"Startup status: torch.cuda.is_available() = {cuda_available}")

    try:
        import faiss
        faiss_gpu_available = hasattr(faiss, 'StandardGpuResources') and faiss.get_num_gpus() > 0
        logger.info(f"FAISS gpu available: {faiss_gpu_available}; num_gpus = {faiss.get_num_gpus() if faiss_gpu_available else 0}")
    except Exception as e:
        logger.warning("FAISS not importable or CPU-only. If you intended to use GPU FAISS, ensure faiss-gpu is installed and CUDA is configured. Error: %s", e)
        faiss_gpu_available = False

    return app

if __name__ == "__main__":
    host = settings.HOST
    port = settings.PORT
    reload_flag = settings.RELOAD
    
    uvicorn.run("main:app", host=host, port=port, reload=reload_flag)
