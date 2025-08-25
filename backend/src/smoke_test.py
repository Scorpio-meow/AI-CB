import asyncio

from httpx import ASGITransport, AsyncClient
try:
    # When executed as a module: python -m src.smoke_test
    from .main import app  # type: ignore
except Exception:
    # When executed as a script from src folder: python smoke_test.py
    from main import app  # type: ignore


async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # health
        resp = await client.get("/health")
        print("/health:", resp.status_code, resp.json())

        # RAG ingest
        payload = {
            "items": [
                {"text": "FastAPI 是一個高效能的 Python Web 框架。", "metadata": {"lang": "zh"}},
                {"text": "E5-base-v2 是一個通用語義嵌入模型。", "metadata": {"source": "local"}},
            ]
        }
        resp = await client.post("/rag/ingest", json=payload)
        print("/rag/ingest:", resp.status_code, resp.json())

        # RAG query
        q = {"query": "什麼是 FastAPI?", "top_k": 3}
        resp = await client.post("/rag/query", json=q)
        print("/rag/query:", resp.status_code, resp.json())


if __name__ == "__main__":
    asyncio.run(main())
