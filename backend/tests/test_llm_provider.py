import pytest
import anyio
from unittest.mock import AsyncMock, MagicMock
from app.core.llm_provider import OllamaProvider, OpenAICompatibleProvider
from app.tools.registry import TOOL_REGISTRY, TOOL_SCHEMAS, register_tool
from pydantic import BaseModel, Field

# Dummy Tool for testing
class DummyArgs(BaseModel):
    val: str = Field(..., description="dummy value")

@register_tool("dummy_test_tool", "A dummy tool for test verification", DummyArgs)
async def dummy_test_tool(val: str) -> str:
    return f"Processed: {val}"

@pytest.mark.anyio
async def test_tool_calling_limit(mocker):
    # Mock cache
    mock_cache = MagicMock()
    mock_cache.enabled = True
    mock_cache.get_raw.return_value = "true"  # 模擬支援工具調用
    mocker.patch("app.core.llm_provider.get_cache", return_value=mock_cache)
    
    # Mock http client
    mock_http_client = AsyncMock()
    # 模擬 LLM 永遠回傳 tool_calls 要求呼叫工具 (無窮迴圈)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "thinking...",
            "tool_calls": [
                {
                    "function": {
                        "name": "dummy_test_tool",
                        "arguments": {"val": "hello"}
                    }
                }
            ]
        }
    }
    mock_http_client.post.return_value = mock_response
    mocker.patch("app.core.llm_provider.get_http_client", return_value=mock_http_client)

    provider = OllamaProvider("http://localhost:11434", "dummy-model")
    
    # 執行並確認在第 5 次迭代後安全中斷
    res = await provider.chat_with_tools(
        messages=[{"role": "user", "content": "run dummy tool"}],
        tools=TOOL_SCHEMAS,
        max_iterations=5
    )
    
    # 驗證 post 被呼叫了 5 次 (加一次初始探測 = 6次，探測由 mock_cache 攔截所以不觸發，僅迴圈呼叫 5 次)
    assert mock_http_client.post.call_count == 5
    assert res == "thinking..."


@pytest.mark.anyio
async def test_ollama_probe_caching(mocker):
    mock_cache = MagicMock()
    mock_cache.enabled = True
    mock_cache.get_raw.return_value = None  # 模擬快取未命中 (cache miss)
    mocker.patch("app.core.llm_provider.get_cache", return_value=mock_cache)

    mock_http_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "role": "assistant",
            "tool_calls": []
        }
    }
    mock_http_client.post.return_value = mock_response
    mocker.patch("app.core.llm_provider.get_http_client", return_value=mock_http_client)

    provider = OllamaProvider("http://localhost:11434", "test-probe-model")
    
    # 第一次呼叫 (會觸發探測)
    supported = await provider._check_tool_support()
    assert supported is True
    
    # 驗證是否對快取進行了查表與寫入
    mock_cache.get_raw.assert_called_once_with("ollama_tool_support:test-probe-model")
    mock_cache.set_raw.assert_called_once_with("ollama_tool_support:test-probe-model", "true", 3600)
