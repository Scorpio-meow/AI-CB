from fastapi import APIRouter
import os
import subprocess
import re

router = APIRouter()


@router.get("/tags")
async def get_tags():
    """Return available LLM models by querying `ollama list` and falling back to env vars."""
    try:
        # Run `ollama list` and parse output. Use a simple parse since CLI prints a table.
        proc = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        out = proc.stdout or ""
        lines = [l for l in out.splitlines() if l.strip()]
        models = []
        for line in lines:
            # Skip header if present
            if line.strip().upper().startswith("NAME"):
                continue
            # Split by two or more spaces to separate table columns
            parts = re.split(r"\s{2,}", line.strip())
            if parts:
                models.append(parts[0])

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
