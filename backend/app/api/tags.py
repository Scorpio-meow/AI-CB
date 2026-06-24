from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi import status
import os
import logging
from collections.abc import Iterable, Mapping, Sequence
from typing import Optional

import requests

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/tags")
async def get_tags():
    """Return available LLM models by querying LLM_API_BASE `/api/tags` with env-based fallbacks."""

    fallback_models = _load_fallback_models()
    configured_default = os.getenv("MODEL_NAME")
    default_model: Optional[str] = configured_default
    models: list[str] = []

    try:
        remote_models, remote_default = _fetch_remote_models()
        if remote_models:
            models = remote_models
            if remote_default:
                default_model = remote_default
        else:
            models = []
    except Exception as exc:
        # Log the full exception on the server but do not expose details to the client.
        logger.exception("Failed to load models from LLM_API_BASE")

    # 合併 fallback 模型，確保配置的雲端模型能顯示在選單中
    for model in fallback_models:
        if model not in models:
            models.append(model)

    if not default_model:
        default_model = fallback_models[0] if fallback_models else None

    if default_model and default_model not in models and models:
        default_model = models[0]

    return {"tags": models, "default": default_model}


def _load_fallback_models() -> list[str]:
    available = os.getenv("AVAILABLE_MODELS", "gemma4:26b,gemma3:27b")
    models = [m.strip() for m in available.split(",") if m.strip()]
    if not models:
        models = ["gemma4:26b", "gemma3:27b"]
    return models


def _fetch_remote_models() -> tuple[list[str], Optional[str]]:
    """Fetch remote model list.

    Precedence:
    1. EXTERNAL_TAGS_URL (full URL, already points to /api/tags or equivalent)
    2. Construct from LLM_API_BASE + '/api/tags'

    Extra behavior:
    - If URL 包含 ngrok-free.app 或設定 ADD_NGROK_HEADER=true，加入 header
      {"ngrok-skip-browser-warning": "true"}
    - Timeout 由 LLM_TAGS_TIMEOUT 控制 (預設 10 秒)
    """

    custom_url = os.getenv("EXTERNAL_TAGS_URL", "").strip()
    base = os.getenv("LLM_API_BASE", "").strip()

    if custom_url:
        url = custom_url
    else:
        if not base:
            raise RuntimeError(
                "Environment variable LLM_API_BASE is required to query remote models (or set EXTERNAL_TAGS_URL)."
            )
        url = f"{base.rstrip('/')}/api/tags"

    timeout = float(os.getenv("LLM_TAGS_TIMEOUT", "10"))

    headers: dict[str, str] = {}
    if (
        "ngrok-free.app" in url
        or os.getenv("ADD_NGROK_HEADER", "").lower() in {"1", "true", "yes", "on"}
    ):
        headers["ngrok-skip-browser-warning"] = "true"

    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    models, default_model = _parse_model_payload(payload)
    return models, default_model


def _parse_model_payload(payload: object) -> tuple[list[str], Optional[str]]:
    models: list[str] = []
    default_model: Optional[str] = None

    if isinstance(payload, list):
        models = _normalize_model_list(payload)
    elif isinstance(payload, dict):
        candidate_arrays = [
            payload.get("models"),
            payload.get("tags"),
            payload.get("data"),
            payload.get("items"),
        ]

        for candidate in candidate_arrays:
            items = _coerce_to_iterable(candidate)
            if items:
                models = _normalize_model_list(items)
                if models:
                    break

        default_keys = ["default", "default_model", "defaultModel", "defaultTag"]
        for key in default_keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                default_model = value.strip()
                break

        # Some APIs wrap the useful data under a `data` key with `items`
        if not models and "data" in payload and isinstance(payload["data"], Mapping):
            inner = _coerce_to_iterable(payload["data"].get("items"))
            if inner:
                models = _normalize_model_list(inner)

    return models, default_model


def _normalize_model_list(items: Iterable[object]) -> list[str]:
    normalized: list[str] = []
    for item in items:
        if isinstance(item, str):
            value = item.strip()
        elif isinstance(item, dict):
            value = _first_present(item, ["name", "value", "model", "tag", "id", "label"])
        else:
            continue

        if not value:
            continue

        if value not in normalized:
            normalized.append(value)
    return normalized


def _first_present(source: dict, keys: list[str]) -> Optional[str]:
    for key in keys:
        candidate = source.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    # Some APIs nest name under `attributes` or similar structures.
    nested = source.get("attributes")
    if isinstance(nested, dict):
        return _first_present(nested, keys)
    return None


def _coerce_to_iterable(candidate: object) -> Iterable[object] | None:
    if candidate is None:
        return None

    if isinstance(candidate, (list, tuple, set)):
        return candidate

    if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes, bytearray)):
        return candidate

    if isinstance(candidate, Mapping):
        for key in ("items", "models", "tags", "data", "values"):
            if key in candidate:
                nested = _coerce_to_iterable(candidate[key])
                if nested:
                    return nested

    return None


@router.get("/external-tags")
def get_external_tags():
    """Proxy endpoint: fetch the external tags JSON and return it directly.

    Uses EXTERNAL_TAGS_URL or constructs from LLM_API_BASE. Adds the ngrok header
    when appropriate. Returns 502 with a fallback models list if upstream fails.
    """
    custom_url = os.getenv("EXTERNAL_TAGS_URL", "").strip()
    base = os.getenv("LLM_API_BASE", "").strip()

    if custom_url:
        url = custom_url
    else:
        if not base:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={
                "error": "No external tags URL configured (set EXTERNAL_TAGS_URL or LLM_API_BASE)."
            })
        url = f"{base.rstrip('/')}/api/tags"

    timeout = float(os.getenv("LLM_TAGS_TIMEOUT", "10"))
    headers: dict[str, str] = {}
    if (
        "ngrok-free.app" in url
        or os.getenv("ADD_NGROK_HEADER", "").lower() in {"1", "true", "yes", "on"}
    ):
        headers["ngrok-skip-browser-warning"] = "true"

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        fallback_models = _load_fallback_models()
        if isinstance(data, dict):
            for key in ("models", "tags", "data", "items"):
                if key in data and isinstance(data[key], list):
                    existing_names = []
                    for item in data[key]:
                        if isinstance(item, str):
                            existing_names.append(item)
                        elif isinstance(item, dict) and "name" in item:
                            existing_names.append(item["name"])
                    for f_model in fallback_models:
                        if f_model not in existing_names:
                            data[key].append(f_model)
        return JSONResponse(content=data)
    except Exception as exc:
        # Upstream failed — log the exception and return 502 with fallback models to keep UI usable.
        logger.exception("Failed to fetch external tags from %s", url)
        fallback = _load_fallback_models()
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": "Failed to fetch external tags", "models": fallback},
        )
