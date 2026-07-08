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
    """獲取或建立全域的 LLM HTTP 客戶端 (連接池模式)"""
    global _http_client
    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.LLM_TIMEOUT),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return _http_client

async def close_llm_http_client():
    """關閉全域的 LLM HTTP 客戶端"""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None

DEFAULT_OPENAI_MODELS = ["gpt-5.5", "gpt-5.4", "gpt-5.2", "gpt-4o", "gpt-4o-mini", "o3", "o3-mini", "o1"]
DEFAULT_CLAUDE_MODELS = ["claude-4-8-opus", "claude-4-7-opus", "claude-4-6-sonnet", "claude-4-5-sonnet", "claude-4-5-haiku", "claude-5-fable"]
DEFAULT_GEMINI_MODELS = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3-pro", "gemini-2.5-flash"]

def is_azure_openai_enabled() -> bool:
    """檢查是否啟用了 Azure OpenAI"""
    return bool(settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT)

def get_available_models() -> List[str]:
    """獲取配置的可用模型列表"""
    # 優先讀取環境變數中的 AVAILABLE_MODELS
    available = os.getenv("AVAILABLE_MODELS", "").strip()
    if available:
        return [m.strip() for m in available.split(",") if m.strip()]
    
    models = []
    
    # 1. Azure OpenAI
    if is_azure_openai_enabled():
        if settings.AZURE_OPENAI_DEPLOYMENT:
            models.append(settings.AZURE_OPENAI_DEPLOYMENT)
        else:
            models.append("gpt-4o")
            
    # 2. OpenAI
    if settings.OPENAI_API_KEY:
        models.extend(DEFAULT_OPENAI_MODELS)
        
    # 3. Claude (Anthropic)
    if settings.ANTHROPIC_API_KEY:
        models.extend(DEFAULT_CLAUDE_MODELS)
        
    # 4. Gemini (Google)
    if settings.GEMINI_API_KEY:
        models.extend(DEFAULT_GEMINI_MODELS)
        
    return models

async def call_llm(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
    timeout: Optional[float] = None
) -> str:
    """統一的 LLM 調用接口，支援 OpenAI、Claude、Gemini、Azure OpenAI 與 Ollama 格式。
    
    Args:
        messages: 對話歷史與當前訊息列表
        model_name: 覆寫模型/部署名稱
        timeout: 請求超時時間(秒)
        
    Returns:
        LLM 回覆的純文字內容
    """
    client = await get_llm_http_client()
    
    # 決定超時設定
    opt_timeout = httpx.Timeout(timeout) if timeout is not None else httpx.Timeout(settings.LLM_TIMEOUT)
    
    # 決定使用的模型名稱
    target_model = model_name or settings.MODEL_NAME
    
    # 1. 判斷是否走 Anthropic Claude
    if "claude-" in target_model and settings.ANTHROPIC_API_KEY:
        base_url = settings.ANTHROPIC_API_BASE.rstrip("/")
        url = f"{base_url}/v1/messages"
        
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # 轉換 messages：提取 system 訊息並過濾，轉換角色名稱
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
        
        # Anthropic 要求 messages 不得為空，且第一條必須是 user 角色
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

    # 2. 判斷是否走 Google Gemini (使用 OpenAI 相容端點)
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
        
        logger.info(f"Calling OpenAI API: model={target_model}, messages={len(messages)}, url={url}")
        
        response = await client.post(url, json=payload, headers=headers, timeout=opt_timeout)
        response.raise_for_status()
        
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI returned empty choices")
            
        response_text = choices[0].get("message", {}).get("content", "").strip()
        return response_text

    # 4. 判斷是否走 Azure OpenAI
    elif is_azure_openai_enabled():
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        url = f"{endpoint}/openai/v1/chat/completions"
        
        deployment = model_name or settings.AZURE_OPENAI_DEPLOYMENT or "gpt-4o"
        
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
        
        logger.info(f"Calling v1 Azure OpenAI: deployment={deployment}, messages={len(messages)}, url={url}")
        
        response = await client.post(url, json=payload, headers=headers, timeout=opt_timeout)
        response.raise_for_status()
        
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("Azure OpenAI returned empty choices")
            
        response_text = choices[0].get("message", {}).get("content", "").strip()
        return response_text

    # 5. 回退至 Ollama / LLM_API_BASE 模式
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