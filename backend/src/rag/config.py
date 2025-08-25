import os
from pathlib import Path

# Embedding model id for FastEmbed (E5 family hosted on HuggingFace).
# Use a supported model id like "intfloat/e5-base-v2".
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/e5-base-v2")

# Optional cache directory for storing/reading models locally.
# Defaults to backend/src/models. If you've placed the E5 model files there,
# FastEmbed will discover them when using the model id above.
_DEFAULT_CACHE = (Path(__file__).resolve().parents[1] / "models").as_posix()
EMBEDDING_CACHE_DIR = os.getenv("EMBEDDING_CACHE_DIR", _DEFAULT_CACHE)

# Simple local store path (JSON + npy) to keep vectors & metadatas
RAG_STORE_DIR = os.getenv("RAG_STORE_DIR", "./data/rag_store")

# Top-k retrieval
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
