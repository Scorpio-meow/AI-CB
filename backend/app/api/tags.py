from fastapi import APIRouter
import os
from collections.abc import Iterable, Mapping, Sequence
from typing import Optional

import httpx

router = APIRouter()


@router.get("/tags")
async def get_tags():
    """Return available LLM models by querying LLM_API_BASE `/api/tags` with env-based fallbacks."""

    fallback_models = _load_fallback_models()
    configured_default = os.getenv("MODEL_NAME")
    default_model: Optional[str] = configured_default
    models: list[str] = []

    try:
        remote_models, remote_default = await _fetch_remote_models()
        if remote_models:
            models = remote_models
            if remote_default:
                default_model = remote_default
        else:
            models = []
    except Exception as exc:
        # Keep track of the failure for troubleshooting while still providing fallbacks.
        print(f"[tags] Failed to load models from LLM_API_BASE: {exc}")

    if not models:
        models = fallback_models
        if not default_model:
            default_model = fallback_models[0] if fallback_models else None

    if default_model and default_model not in models and models:
        default_model = models[0]

    return {"tags": models, "default": default_model}


def _load_fallback_models() -> list[str]:
    available = os.getenv("AVAILABLE_MODELS", "gpt-oss:20b,gemma3:27b")
    models = [m.strip() for m in available.split(",") if m.strip()]
    if not models:
        models = ["gpt-oss:20b", "gemma3:27b"]
    return models


async def _fetch_remote_models() -> tuple[list[str], Optional[str]]:
    base = os.getenv("LLM_API_BASE", "").strip()
    if not base:
        raise RuntimeError("Environment variable LLM_API_BASE is required to query remote models.")

    timeout = float(os.getenv("LLM_TAGS_TIMEOUT", "10"))
    url = f"{base.rstrip('/')}/api/tags"

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
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
