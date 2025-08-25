import os

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8001").rstrip("/")
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
LLM_GENERATE_PATH = os.getenv("LLM_GENERATE_PATH", "/generate")
LLM_STREAM_PATH = os.getenv("LLM_STREAM_PATH", "/generate/stream")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-oss:20b")
