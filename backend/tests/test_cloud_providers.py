import pytest
from unittest.mock import AsyncMock, Mock, patch
import os
import httpx
from app.rag.contextual_rag import HybridContextualRAG

@pytest.mark.asyncio
async def test_call_llm_api_azure():
    with patch.dict(os.environ, {
        "AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "test_azure_key",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "default-dep"
    }):
        rag = HybridContextualRAG()
        
        # 使用普通的 Mock 模擬 Response 物件
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()  # 同步方法
        mock_response.json = Mock(return_value={  # 同步方法
            "choices": [{
                "message": {
                    "content": "Azure response text"
                }
            }]
        })
        
        # mock_post 是 AsyncMock，它 return_value 為普通的 mock_response
        with patch.object(httpx.AsyncClient, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            res = await rag.call_llm_api(prompt="Hello", model_name="azure:gpt-4o")
            
            assert res == "Azure response text"
            mock_post.assert_called_once()
            called_url = mock_post.call_args[0][0]
            called_json = mock_post.call_args[1]["json"]
            called_headers = mock_post.call_args[1]["headers"]
            
            assert "https://test-resource.openai.azure.com/openai/v1/chat/completions" in called_url
            assert called_headers["api-key"] == "test_azure_key"
            assert called_json["model"] == "gpt-4o"

@pytest.mark.asyncio
async def test_call_llm_api_anthropic():
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "test_anthropic_key"
    }):
        rag = HybridContextualRAG()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={
            "content": [{
                "text": "Anthropic response text"
            }]
        })
        
        with patch.object(httpx.AsyncClient, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            res = await rag.call_llm_api(prompt="Hello", model_name="anthropic:claude-3-5-sonnet")
            
            assert res == "Anthropic response text"
            mock_post.assert_called_once()
            called_url = mock_post.call_args[0][0]
            called_json = mock_post.call_args[1]["json"]
            called_headers = mock_post.call_args[1]["headers"]
            
            assert "https://api.anthropic.com/v1/messages" in called_url
            assert called_headers["x-api-key"] == "test_anthropic_key"
            assert called_json["model"] == "claude-3-5-sonnet"
            assert "system" in called_json

@pytest.mark.asyncio
async def test_call_llm_api_google():
    with patch.dict(os.environ, {
        "GEMINI_API_KEY": "test_gemini_key"
    }):
        rag = HybridContextualRAG()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={
            "candidates": [{
                "content": {
                    "parts": [{"text": "Google response text"}]
                }
            }]
        })
        
        with patch.object(httpx.AsyncClient, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            res = await rag.call_llm_api(prompt="Hello", model_name="google:gemini-1.5-flash")
            
            assert res == "Google response text"
            mock_post.assert_called_once()
            called_url = mock_post.call_args[0][0]
            called_json = mock_post.call_args[1]["json"]
            
            assert "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent" in called_url
            assert "key=test_gemini_key" in called_url
            assert "systemInstruction" in called_json
