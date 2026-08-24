import os
import logging
import asyncio
import httpx
from typing import List, Dict, Optional
from app.core.config import settings
logger = logging.getLogger(__name__)
_http_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()
async def get_llm_http_client() -> httpx.AsyncClient:
    global _http_client
    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.LLM_TIMEOUT),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return _http_client
async def close_llm_http_client():
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
DEFAULT_OPENAI_MODELS = ["gpt-5.5", "gpt-5.4", "gpt-5.2", "gpt-4o", "gpt-4o-mini", "o3", "o3-mini", "o1"]
DEFAULT_CLAUDE_MODELS = ["claude-4-8-opus", "claude-4-7-opus", "claude-4-6-sonnet", "claude-4-5-sonnet", "claude-4-5-haiku", "claude-5-fable"]
DEFAULT_GEMINI_MODELS = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3-pro", "gemini-2.5-flash"]
def is_azure_openai_enabled() -> bool:
    return bool(settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT)
def get_available_models() -> List[str]:
    available = os.getenv("AVAILABLE_MODELS", "").strip()
    if available:
        return [m.strip() for m in available.split(",") if m.strip()]
    
    models: List[str] = []
    
    if is_azure_openai_enabled():
        if settings.AZURE_OPENAI_DEPLOYMENT:
            deployments = [d.strip() for d in settings.AZURE_OPENAI_DEPLOYMENT.split(",") if d.strip()]
            for dep in deployments:
                if dep not in models:
                    models.append(dep)
        else:
            models.append("gpt-4o")
            
    if settings.OPENAI_API_KEY:
        for m in DEFAULT_OPENAI_MODELS:
            if m not in models:
                models.append(m)
        
    if settings.ANTHROPIC_API_KEY:
        for m in DEFAULT_CLAUDE_MODELS:
            if m not in models:
                models.append(m)
        
    if settings.GEMINI_API_KEY:
        for m in DEFAULT_GEMINI_MODELS:
            if m not in models:
                models.append(m)
        
    return models
async def call_llm(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
    timeout: Optional[float] = None,
    reasoning_effort: Optional[str] = None
) -> str:
    client = await get_llm_http_client()
    
    opt_timeout = httpx.Timeout(timeout) if timeout is not None else httpx.Timeout(settings.LLM_TIMEOUT)
    
    target_model = model_name or settings.MODEL_NAME
    
    if "claude-" in target_model and settings.ANTHROPIC_API_KEY:
        base_url = settings.ANTHROPIC_API_BASE.rstrip("/")
        url = f"{base_url}/v1/messages"
        
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        system_content = None
        filtered_messages = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_content = content
            else:
                anthropic_role = role
                if role not in ("user", "assistant"):
                    anthropic_role = "user"
                filtered_messages.append({
                    "role": anthropic_role,
                    "content": content
                })
        
        if not filtered_messages:
            filtered_messages.append({"role": "user", "content": "Hello"})
        elif filtered_messages[0]["role"] != "user":
            filtered_messages.insert(0, {"role": "user", "content": "Hi"})
            
        payload = {
            "model": target_model,
            "messages": filtered_messages,
            "max_tokens": 4096,
            "stream": False
        }
        if system_content:
            payload["system"] = system_content
            
        logger.info(f"Calling Anthropic API: model={target_model}, messages={len(filtered_messages)}, url={url}")
        
        response = await client.post(url, json=payload, headers=headers, timeout=opt_timeout)
        response.raise_for_status()
        
        data = response.json()
        content_items = data.get("content", [])
        if not content_items:
            raise RuntimeError("Anthropic returned empty content")
            
        response_text = content_items[0].get("text", "").strip()
        return response_text
    elif "gemini-" in target_model and settings.GEMINI_API_KEY:
        base_url = settings.GEMINI_API_BASE.rstrip("/")
        url = f"{base_url}/v1beta/openai/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.GEMINI_API_KEY}"
        }
        
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False
        }
        
        logger.info(f"Calling Google Gemini API: model={target_model}, messages={len(messages)}, url={url}")
        
        response = await client.post(url, json=payload, headers=headers, timeout=opt_timeout)
        response.raise_for_status()
        
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("Gemini OpenAI API returned empty choices")
            
        response_text = choices[0].get("message", {}).get("content", "").strip()
        return response_text
    elif (any(prefix in target_model for prefix in ("gpt-", "o1", "o3")) 
          and settings.OPENAI_API_KEY 
          and (not is_azure_openai_enabled() or target_model != settings.AZURE_OPENAI_DEPLOYMENT)):
        base_url = settings.OPENAI_API_BASE.rstrip("/")
        url = f"{base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
        }
        
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False
        }
        if reasoning_effort and reasoning_effort in ("none", "minimal", "low", "medium", "high", "xhigh", "max"):
            payload["reasoning_effort"] = reasoning_effort
        
        logger.info(f"Calling OpenAI API: model={target_model}, messages={len(messages)}, url={url}")
        
        response = await client.post(url, json=payload, headers=headers, timeout=opt_timeout)
        response.raise_for_status()
        
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI returned empty choices")
            
        response_text = choices[0].get("message", {}).get("content", "").strip()
        return response_text
    elif is_azure_openai_enabled():
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        url = f"{endpoint}/openai/v1/chat/completions"
        
        raw_deployment = model_name or settings.AZURE_OPENAI_DEPLOYMENT or "gpt-4o"
        deployment = raw_deployment.split(",")[0].strip()
        
        headers = {
            "Content-Type": "application/json",
            "api-key": settings.AZURE_OPENAI_API_KEY,
            "Authorization": f"Bearer {settings.AZURE_OPENAI_API_KEY}"
        }
        
        payload = {
            "model": deployment,
            "messages": messages,
            "stream": False
        }
        if reasoning_effort and reasoning_effort in ("none", "minimal", "low", "medium", "high", "xhigh", "max"):
            payload["reasoning_effort"] = reasoning_effort
        
        logger.info(f"Calling v1 Azure OpenAI: deployment={deployment}, messages={len(messages)}, url={url}")
        
        response = await client.post(url, json=payload, headers=headers, timeout=opt_timeout)
        response.raise_for_status()
        
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("Azure OpenAI returned empty choices")
            
        response_text = choices[0].get("message", {}).get("content", "").strip()
        return response_text
    else:
        base_url = settings.LLM_API_BASE.rstrip("/")
        url = f"{base_url}/api/chat"
        
        headers = {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true"
        }
        
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False
        }
        
        logger.info(f"Calling Ollama API: model={target_model}, messages={len(messages)}, url={url}")
        
        response = await client.post(url, json=payload, headers=headers, timeout=opt_timeout)
        response.raise_for_status()
        
        data = response.json()
        response_text = data.get("message", {}).get("content", "").strip()
        return response_text