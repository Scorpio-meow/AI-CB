import os
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import anyio
import httpx

from app.core.config import settings
from app.services.cache_service import get_cache
from app.services.workflow_service import get_http_client
from app.tools.registry import TOOL_REGISTRY, TOOL_SCHEMAS

logger = logging.getLogger(__name__)

class ToolExecutionError(Exception):
    """工具執行時的自訂異常"""
    pass

class BaseLLMProvider(ABC):
    def __init__(self, api_base: str, model_name: str):
        self.api_base = api_base
        self.model_name = model_name

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]] | None = None,
        max_iterations: int = 5
    ) -> str:
        """
        發送對話並支援 Tool Calling。
        
        :param messages: 原始對話歷史 (符合 standard roles: system, user, assistant)
        :param tools: 可選工具描述列表
        :param max_iterations: 最大 Tool Calling 迭代次數，避免無限迴圈
        :return: 最終生成的助理文字回覆
        """
        pass


class OllamaProvider(BaseLLMProvider):
    def __init__(self, api_base: str, model_name: str):
        super().__init__(api_base, model_name)
        self._tool_support_status: Optional[bool] = None

    async def _check_tool_support(self) -> bool:
        """
        運行期探測 (Capability Probing) 是否支援 Native Tool Calling。
        使用 Cache 快取結果以減少不必要的探測請求。
        """
        if self._tool_support_status is not None:
            return self._tool_support_status

        cache = get_cache()
        cache_key = f"ollama_tool_support:{self.model_name}"
        
        # 執行緒隔離讀取 Redis 快取
        cached_val = await anyio.to_thread.run_sync(lambda: cache.get_raw(cache_key))
        if cached_val is not None:
            self._tool_support_status = (cached_val == "true")
            logger.info(f"Ollama 模型 '{self.model_name}' 工具支援狀態 (快取命中): {self._tool_support_status}")
            return self._tool_support_status

        # 執行能力探測
        try:
            client = await get_http_client()
            url = f"{self.api_base}/api/chat"
            
            # 極簡的探測 Payload (Dummy Tool, Temperature=0, Max Tokens=1)
            probe_payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "hi"}],
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "_probe",
                        "description": "capability probe",
                        "parameters": {"type": "object", "properties": {}}
                    }
                }],
                "options": {"temperature": 0.0, "num_predict": 1},
                "stream": False
            }
            logger.info(f"正在對 Ollama 模型 '{self.model_name}' 發送工具調用能力探測...")
            response = await client.post(url, json=probe_payload)
            response.raise_for_status()
            data = response.json()
            
            message_obj = data.get("message", {})
            tool_calls = message_obj.get("tool_calls")
            # 只要 tool_calls 欄位存在且不為 None 即代表此模型架構支援
            supports = tool_calls is not None
            
            # 寫入快取 (1小時)
            cache_val = "true" if supports else "false"
            await anyio.to_thread.run_sync(lambda: cache.set_raw(cache_key, cache_val, 3600))
            
            self._tool_support_status = supports
            logger.info(f"探測結束，模型 '{self.model_name}' 工具支援判定為: {supports}")
            return supports
        except Exception as e:
            logger.error(f"Ollama 模型 '{self.model_name}' 工具能力探測失敗: {e}，預設降級為 XML 模式")
            return False

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]] | None = None,
        max_iterations: int = 5
    ) -> str:
        client = await get_http_client()
        url = f"{self.api_base}/api/chat"
        
        # 決定是否支援 native tool calling
        supports_native = await self._check_tool_support() if tools else False
        
        # 複製一份 local_messages 用於 Tool Calling 的遞迴上下文，避免污染傳入的原始歷史
        local_messages = list(messages)
        
        # 如果不支援 native 且有工具，則在 system prompt 中注入 XML 指引
        if tools and not supports_native:
            local_messages = self._inject_xml_instructions(local_messages, tools)

        iteration = 0
        while iteration < max_iterations:
            payload = {
                "model": self.model_name,
                "messages": local_messages,
                "stream": False
            }
            if tools and supports_native:
                payload["tools"] = tools

            logger.info(f"[Ollama] 發送請求，迭代次數: {iteration + 1}/{max_iterations}")
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            assistant_msg = data.get("message", {})
            local_messages.append(assistant_msg)
            
            # 提取 Tool Calls
            tool_calls = []
            if tools:
                if supports_native:
                    raw_calls = assistant_msg.get("tool_calls", [])
                    for rc in raw_calls:
                        func_info = rc.get("function", {})
                        args = func_info.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                pass
                        tool_calls.append({
                            "id": rc.get("id"),
                            "name": func_info.get("name"),
                            "arguments": args
                        })
                else:
                    # XML 模式解析
                    content = assistant_msg.get("content", "")
                    tool_calls = self._parse_xml_tool_calls(content)

            # 如果沒有工具調用，表示 LLM 已給出最終回覆
            if not tool_calls:
                return assistant_msg.get("content", "").strip()

            # 執行工具
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                logger.info(f"模型要求執行工具: {tool_name}，引數: {tool_args}")
                
                if tool_name not in TOOL_REGISTRY:
                    tool_result = f"Error: Tool '{tool_name}' not found."
                else:
                    try:
                        tool_func = TOOL_REGISTRY[tool_name]
                        tool_result = await tool_func(**tool_args)
                        # 確保回傳值為字串
                        if not isinstance(tool_result, str):
                            tool_result = json.dumps(tool_result, ensure_ascii=False)
                    except Exception as e:
                        logger.error(f"執行工具 '{tool_name}' 發生異常: {e}")
                        tool_result = f"ToolExecutionError: {str(e)}"

                logger.info(f"工具 '{tool_name}' 執行結果長度: {len(tool_result)}")
                
                # 回填工具結果
                if supports_native:
                    local_messages.append({
                        "role": "tool",
                        "content": tool_result,
                        "name": tool_name
                    })
                else:
                    # XML 模式：以 user 角色把結果餵回
                    local_messages.append({
                        "role": "user",
                        "content": f"<tool_response>\n<name>{tool_name}</name>\n<response>\n{tool_result}\n</response>\n</tool_response>"
                    })

            iteration += 1

        logger.warning(f"Ollama Tool Calling 達最大迭代上限 ({max_iterations})。安全中斷並回傳結果。")
        # 尋找最後一條文字內容回傳
        for msg in reversed(local_messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                return msg.get("content").strip()
        return "錯誤: 工具調用次數過多，未能生成最終文字結果。"

    def _inject_xml_instructions(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tools_desc = []
        for t in tools:
            func = t.get("function", {})
            tools_desc.append(f"- Name: {func.get('name')}\n  Description: {func.get('description')}\n  Args schema: {func.get('parameters')}")
        tools_desc_str = "\n".join(tools_desc)

        instruction = f"""
[SYSTEM INSTRUCTION: You have access to tools. 
Available tools:
{tools_desc_str}

If you need to call a tool, you MUST output your response in the following XML format (and nothing else):
<tool_call>
  <name>tool_name</name>
  <arguments>
    "param_name": "param_value"
  </arguments>
</tool_call>

Once you receive the tool response (marked with <tool_response>), continue your reasoning or provide the final answer.
When you output the final answer, write it naturally without any <tool_call> tags.]
"""
        # 尋找 system prompt 注入，若無則在最前新增一個
        new_messages = []
        injected = False
        for msg in messages:
            if msg.get("role") == "system" and not injected:
                new_content = msg.get("content", "") + "\n\n" + instruction
                new_messages.append({"role": "system", "content": new_content})
                injected = True
            else:
                new_messages.append(msg)
        if not injected:
            new_messages.insert(0, {"role": "system", "content": instruction})
        return new_messages

    def _parse_xml_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        pattern = re.compile(r"<tool_call>\s*<name>(.*?)</name>\s*<arguments>(.*?)</arguments>\s*</tool_call>", re.DOTALL)
        matches = pattern.findall(text)
        tool_calls = []
        for name, args_str in matches:
            name = name.strip()
            # 整理為 JSON
            args_str_clean = args_str.strip()
            # 補上外層大括號（如果模型忘了寫）
            if not args_str_clean.startswith("{"):
                args_str_clean = "{" + args_str_clean + "}"
            try:
                args = json.loads(args_str_clean)
            except Exception:
                # 簡單 KV 備選解析
                args = {}
                for line in args_str.strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k_clean = k.strip().strip('"').strip("'")
                        v_clean = v.strip().strip('"').strip("'").strip(",")
                        args[k_clean] = v_clean
            tool_calls.append({
                "id": None,
                "name": name,
                "arguments": args
            })
        return tool_calls


class OpenAICompatibleProvider(BaseLLMProvider):
    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]] | None = None,
        max_iterations: int = 5
    ) -> str:
        client = await get_http_client()
        # 轉換 api_base 為 completions 路由
        url = f"{self.api_base}/chat/completions" if not self.api_base.endswith("/chat/completions") else self.api_base
        
        local_messages = list(messages)
        iteration = 0
        
        while iteration < max_iterations:
            payload = {
                "model": self.model_name,
                "messages": local_messages,
                "stream": False
            }
            if tools:
                payload["tools"] = tools

            logger.info(f"[OpenAI] 發送請求，迭代次數: {iteration + 1}/{max_iterations}")
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data.get("choices", [{}])[0]
            assistant_msg = choice.get("message", {})
            local_messages.append(assistant_msg)

            tool_calls = assistant_msg.get("tool_calls", [])
            if not tool_calls:
                return assistant_msg.get("content", "").strip()

            for tc in tool_calls:
                call_id = tc.get("id")
                func_info = tc.get("function", {})
                tool_name = func_info.get("name")
                args_str = func_info.get("arguments", "{}")
                
                try:
                    tool_args = json.loads(args_str)
                except Exception:
                    tool_args = {}

                logger.info(f"模型要求執行工具: {tool_name}，ID: {call_id}，引數: {tool_args}")
                
                if tool_name not in TOOL_REGISTRY:
                    tool_result = f"Error: Tool '{tool_name}' not found."
                else:
                    try:
                        tool_func = TOOL_REGISTRY[tool_name]
                        tool_result = await tool_func(**tool_args)
                        if not isinstance(tool_result, str):
                            tool_result = json.dumps(tool_result, ensure_ascii=False)
                    except Exception as e:
                        logger.error(f"執行工具 '{tool_name}' 發生異常: {e}")
                        tool_result = f"ToolExecutionError: {str(e)}"

                logger.info(f"工具 '{tool_name}' 執行結果長度: {len(tool_result)}")
                
                local_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": tool_result
                })

            iteration += 1

        logger.warning(f"OpenAI Tool Calling 達最大迭代上限 ({max_iterations})。安全中斷並回傳結果。")
        for msg in reversed(local_messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                return msg.get("content").strip()
        return "錯誤: 工具調用次數過多，未能生成最終文字結果。"


def get_llm_provider() -> BaseLLMProvider:
    """
    根據 settings 中的配置動態取得 Provider 實例 (策略模式)
    """
    api_base = settings.LLM_API_BASE
    model_name = settings.MODEL_NAME
    
    # 判斷是否為 OpenAI 規格
    is_openai = "v1" in api_base or "openai" in api_base.lower()
    
    if is_openai:
        logger.info(f"初始化 OpenAI 規格 LLM Provider. Model: {model_name}")
        return OpenAICompatibleProvider(api_base, model_name)
    else:
        logger.info(f"初始化 Ollama 規格 LLM Provider. Model: {model_name}")
        return OllamaProvider(api_base, model_name)
