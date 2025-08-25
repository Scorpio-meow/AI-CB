from __future__ import annotations

import httpx
from typing import List, Optional

from .config import LLM_BASE_URL, TIMEOUT, LLM_MODEL


class LLMService:
    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = base_url or LLM_BASE_URL
        self.timeout = timeout or TIMEOUT
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def generate_response(self, messages: List[dict], context: Optional[str] = None) -> str:
        # OpenAI-compatible /v1/chat/completions (non-stream)
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "stream": False,
        }
        resp = await self._client.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        try:
            # choices[0].message.content
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content")
            )
            return (content or "").strip()
        except Exception:
            return ""

    async def aclose(self):
        await self._client.aclose()

    async def stream_response(self, messages: List[dict], context: Optional[str] = None):
        """Yield chunks from OpenAI-compatible stream (SSE)."""
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "stream": True,
        }
        try:
            async with self._client.stream("POST", "/v1/chat/completions", json=payload) as resp:
                resp.raise_for_status()
                async for raw in resp.aiter_lines():
                    if not raw:
                        continue
                    if not raw.startswith("data:"):
                        continue
                    data = raw[5:].strip()
                    if data == "[DONE]":
                        break
                    # Parse partial choice
                    try:
                        obj = httpx.Response(200, content=data).json()
                    except Exception:
                        # As a fallback, just yield the raw line content
                        yield data
                        continue
                    choices = obj.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
        except Exception:
            # Fallback: call non-stream and chunk
            text = await self.generate_response(messages, context)
            step = 64
            for i in range(0, len(text), step):
                yield text[i : i + step]

    async def ping(self) -> dict:
        try:
            resp = await self._client.get("/v1/models")
            resp.raise_for_status()
            return {"ok": True, "data": resp.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}
