from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .services import LLMService

router = APIRouter(prefix="/llm", tags=["llm"])


class Message(BaseModel):
    role: str
    content: str


class GenerateRequest(BaseModel):
    messages: list[Message]
    context: str | None = None


class GenerateResponse(BaseModel):
    text: str


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    svc = LLMService()
    try:
        text = await svc.generate_response([m.dict() for m in req.messages], req.context)
        return GenerateResponse(text=text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await svc.aclose()


@router.post("/generate_stream")
async def generate_stream(req: GenerateRequest):
    svc = LLMService()
    async def gen():
        try:
            async for chunk in svc.stream_response([m.dict() for m in req.messages], req.context):
                yield f"data: {chunk}\n\n"
        finally:
            await svc.aclose()

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/ping")
async def ping():
    svc = LLMService()
    try:
        return await svc.ping()
    finally:
        await svc.aclose()
