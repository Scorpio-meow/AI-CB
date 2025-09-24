from fastapi import APIRouter
import os
import subprocess
import re
import threading

# Env flags
DISABLE_OLLAMA_LIST = os.getenv("DISABLE_OLLAMA_LIST", "true").lower() in ("1", "true", "yes", "y")
OLLAMA_LIST_TIMEOUT = float(os.getenv("OLLAMA_LIST_TIMEOUT", "1"))  # seconds, keep tiny under tunnels

router = APIRouter()


@router.get("/tags")
async def get_tags():
    """Return available LLM models by querying `ollama list` with a short timeout, falling back to env vars."""
    try:
        models = []

        if not DISABLE_OLLAMA_LIST:
            # Run `ollama list` with a very short timeout so UI doesn't hang under remote tunnels
            try:
                proc = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=OLLAMA_LIST_TIMEOUT,
                )
                out = proc.stdout or ""
                lines = [l for l in out.splitlines() if l.strip()]
                for line in lines:
                    # Skip header if present
                    if line.strip().upper().startswith("NAME"):
                        continue
                    # Split by two or more spaces to separate table columns
                    parts = re.split(r"\s{2,}", line.strip())
                    if parts:
                        models.append(parts[0])
            except Exception:
                # Swallow and fall through to env fallback
                models = []

        # Fallback to env var if parsing failed
        if not models:
            available = os.getenv("AVAILABLE_MODELS", "gpt-oss:20b,gemma3:27b")
            models = [m.strip() for m in available.split(",") if m.strip()]

        default_model = os.getenv("MODEL_NAME") or (models[0] if models else None)
        return {"tags": models, "default": default_model}

    except Exception:
        # On any error, fallback to configured env var list
        available = os.getenv("AVAILABLE_MODELS", "gpt-oss:20b,gemma3:27b")
        models = [m.strip() for m in available.split(",") if m.strip()]
        default_model = os.getenv("MODEL_NAME") or (models[0] if models else None)
        return {"tags": models, "default": default_model}
