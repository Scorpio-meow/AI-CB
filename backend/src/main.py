from fastapi import FastAPI
from dotenv import load_dotenv
from pathlib import Path

# Ensure we load env vars from backend/.env regardless of current working directory
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

app = FastAPI(title="HR Expert Knowledge ChatBot API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}

# Routers
from .llm.routes import router as llm_router  # noqa: E402
from .rag.routes import router as rag_router  # noqa: E402

app.include_router(llm_router)
app.include_router(rag_router)
