from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, admin, documents, workflow, custom_agent
from app.models.database import create_tables
from app.tasks.uploads_watcher import scan_and_cleanup_uploads
import asyncio
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Silence uvicorn access logs (these produce lines like: "INFO:     127.0.0.1:0 - \"GET /socket.io/?...\"")
# Set to WARNING so access INFO lines are not printed. Keep error logs.
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# Get configuration from environment
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
UPLOADS_WATCHER_INTERVAL = int(os.getenv("UPLOADS_WATCHER_INTERVAL", "30"))

app = FastAPI(
    title="ChatBot API",
    description="ChatBot with Contextual RAG",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *ALLOWED_ORIGINS,
        "https://zq4n3gps-3000.asse.devtunnels.ms",
        "https://zq4n3gps-8001.asse.devtunnels.ms",
        "https://1848b1fg-3000.asse.devtunnels.ms",
        "https://1848b1fg-8001.asse.devtunnels.ms",
        "*"
    ],  # 允許轉送網址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
@app.on_event("startup")
async def startup_event():
    await create_tables()
    # start background uploads watcher
    app.state._uploads_watcher_task = asyncio.create_task(scan_and_cleanup_uploads(UPLOADS_WATCHER_INTERVAL))


@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, '_uploads_watcher_task', None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(custom_agent.router, prefix="/api/custom_agents", tags=["Custom Agents"])
from app.api import tags as tags_router
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
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
