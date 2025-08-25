from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .embeddings import EmbeddingService
from .store import SimpleVectorStore, DocChunk
from .config import RAG_TOP_K
from ..llm.services import LLMService

router = APIRouter(prefix="/rag", tags=["rag"])


class IngestItem(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: dict | None = None


class IngestRequest(BaseModel):
    items: List[IngestItem]


class QueryRequest(BaseModel):
    query: str
    top_k: int | None = None


class QueryResultItem(BaseModel):
    id: str
    text: str
    score: float
    metadata: dict | None = None


class QueryResponse(BaseModel):
    results: List[QueryResultItem]


class AskRequest(BaseModel):
    query: str
    top_k: int | None = None
    messages: list[dict] | None = None


class AskResponse(BaseModel):
    text: str


@router.post("/ingest")
async def ingest(req: IngestRequest):
    emb = EmbeddingService()
    store = SimpleVectorStore()

    texts = [it.text for it in req.items]
    vecs = emb.embed_passages(texts)
    metas = [
        DocChunk(id=it.id or str(uuid4()), text=it.text, metadata=it.metadata or {})
        for it in req.items
    ]
    store.add(vecs, metas)
    return {"added": len(metas)}


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    emb = EmbeddingService()
    store = SimpleVectorStore()

    qv = emb.embed_query(req.query)
    top_k = req.top_k or RAG_TOP_K
    items = store.topk(qv, k=top_k)
    return QueryResponse(
        results=[
            QueryResultItem(id=m.id, text=m.text, score=s, metadata=m.metadata)
            for m, s in items
        ]
    )


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    emb = EmbeddingService()
    store = SimpleVectorStore()

    qv = emb.embed_query(req.query)
    top_k = req.top_k or RAG_TOP_K
    items = store.topk(qv, k=top_k)

    context = "\n\n".join([f"[score={s:.3f}] {m.text}" for m, s in items])
    messages = req.messages or []
    # Inject a system message with retrieval context
    messages = [
        {"role": "system", "content": f"Use the following context if relevant:\n{context}"}
    ] + messages

    llm = LLMService()
    try:
        text = await llm.generate_response(messages, context)
        return AskResponse(text=text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await llm.aclose()
