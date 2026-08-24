import os
import logging
import torch
import uvicorn
from fastapi import FastAPI
from app.core.config import settings
from app.core.lifespan import lifespan
from app.middleware import setup_middlewares
from app.api import chat, admin, documents, tags as tags_router, auth

os.makedirs('logs', exist_ok=True)
log_level = settings.LOG_LEVEL.upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app.log', encoding='utf-8')
    ]
)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ChatBot API",
    description="ChatBot with Contextual RAG",
    version="1.0.0",
    lifespan=lifespan
)

setup_middlewares(app)

app.include_router(auth.router, tags=["authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(tags_router.router, prefix="/api", tags=["tags"])


@app.get("/")
async def root():
    return {"message": "ChatBot API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def create_app():
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
