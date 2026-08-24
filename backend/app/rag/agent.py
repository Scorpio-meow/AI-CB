import json
import logging
import time
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.rag.tools import ResearchToolRegistry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一個具備自主研究能力的智慧助理「AskMiao」。
你可以根據使用者的問題，自主調用以下工具來查證內部資料或外部即時網路資訊：
1. `search_knowledge_base`: 檢索公司規章、制度、技術文檔或內部已上傳文件。
2. `web_search`: 搜尋外部即時新聞、公開網站資訊或外部最新知識。
3. `web_fetch`: 當搜尋結果摘要不足時，可深入閱讀特定網頁的全文。

【行為規範】：
- 當問題涉及內部政策、請假、福利或特定業務文件時，請優先調用 `search_knowledge_base`。
- 當問題涉及外部時事、即時技術版本或內部無相關資料時，請調用 `web_search` 與 `web_fetch`。
- 若問題僅為一般問候或無須檢索即可回答之通識問題，可直接輸出回覆，無須調用工具。
- 彙整查得的資料後，請使用繁體中文（台灣習慣用語）給出條理清晰、客觀專業且附帶具體細節的回答。
- 請勿編造不存在的事實。
"""


class ResearchAgent:
    """多輪自主研究 Agent 控制器"""

    def __init__(self, tool_registry: ResearchToolRegistry):
        self.tools = tool_registry

    async def _call_azure_openai(
        self,
        messages: List[Dict[str, Any]],
        tools_def: List[Dict[str, Any]],
        model_name: Optional[str] = None,
        reasoning_effort: Optional[str] = "medium"
    ) -> Dict[str, Any]:
        """調用 v1 Azure OpenAI / AI Services 原生 Tool Calling"""
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip('/') if settings.AZURE_OPENAI_ENDPOINT else ""
        api_key = settings.AZURE_OPENAI_API_KEY or ""
        
        # 處理部署名稱匹配
        azure_deployments = [d.strip() for d in (settings.AZURE_OPENAI_DEPLOYMENT or "").split(",") if d.strip()]
        if model_name and (model_name in azure_deployments or any(prefix in model_name.lower() for prefix in ("gpt-", "o1", "o3", "o4"))):
            deployment = model_name
        else:
            deployment = azure_deployments[0] if azure_deployments else "gpt-4o"
        
        url = f"{endpoint}/openai/v1/chat/completions"
        headers = {
            "api-key": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload: Dict[str, Any] = {
            "model": deployment,
            "messages": messages,
        }
        if tools_def:
            payload["tools"] = tools_def
            payload["tool_choice"] = "auto"
            # 依微軟 Foundry 文件：Chat Completions 結合工具時，gpt-5.6 等模型必須設為 none
            if "gpt-5" in deployment.lower():
                payload["reasoning_effort"] = "none"
            elif reasoning_effort and reasoning_effort in ("none", "minimal", "low", "medium", "high", "xhigh", "max"):
                payload["reasoning_effort"] = reasoning_effort
        else:
            if reasoning_effort and reasoning_effort in ("none", "minimal", "low", "medium", "high", "xhigh", "max"):
                payload["reasoning_effort"] = reasoning_effort
            
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"v1 Azure OpenAI API 錯誤 ({resp.status_code}): {resp.text}")
            data = resp.json()
            choice = data["choices"][0]
            return choice["message"]

    async def _call_ollama(
        self,
        messages: List[Dict[str, Any]],
        tools_def: List[Dict[str, Any]],
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """調用 Ollama 原生 Tool Calling API"""
        base_url = settings.LLM_API_BASE.rstrip('/')
        target_model = model_name or settings.MODEL_NAME or "gemma4:26b"
        
        url = f"{base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 2048
            }
        }
        if tools_def:
            payload["tools"] = tools_def

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama API 錯誤 ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data.get("message", {})

    async def run_research(
        self,
        query: str,
        model_name: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        reasoning_effort: Optional[str] = "medium",
        max_turns: int = 5
    ) -> Dict[str, Any]:
        """執行自主研究與多輪工具調用"""
        start_time = time.time()
        tools_def = self.tools.get_tool_definitions()

        # 組裝對話訊息序列
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        if conversation_history:
            for turn in conversation_history[-6:]:
                messages.append(turn)

        messages.append({"role": "user", "content": query})

        research_trace: List[Dict[str, Any]] = []
        collected_sources: List[str] = []
        collected_sources_detail: List[Dict[str, Any]] = []
        final_answer = ""
        turns_used = 0

        # 智慧路由：依所選模型判斷優先使用 Azure 還是 Ollama
        azure_deployments = [d.strip() for d in (settings.AZURE_OPENAI_DEPLOYMENT or "").split(",") if d.strip()]
        use_azure = False
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            if model_name:
                if model_name in azure_deployments or any(prefix in model_name.lower() for prefix in ("gpt-", "o1", "o3", "o4")):
                    use_azure = True
            else:
                use_azure = True

        for turn in range(max_turns):
            turns_used += 1
            try:
                if use_azure:
                    assistant_msg = await self._call_azure_openai(
                        messages, tools_def, model_name, reasoning_effort=reasoning_effort
                    )
                else:
                    assistant_msg = await self._call_ollama(messages, tools_def, model_name)
            except Exception as e:
                logger.error(f"模型調用失敗 (第 {turn + 1} 輪): {e}")
                # 若為工具調用中斷，嘗試以既有資訊生成總結或拋出友好提示
                if not final_answer and not research_trace:
                    final_answer = f"在執行自主研究時遇到連線異常: {str(e)}"
                break

            # 檢查是否有 tool_calls
            tool_calls = assistant_msg.get("tool_calls")
            if not tool_calls:
                # 模型完成研究，產出最終答案
                final_answer = assistant_msg.get("content", "")
                break

            # 將 assistant 包含 tool_calls 的訊息加入歷史
            messages.append(assistant_msg)

            # 依序執行模型要求調用的工具
            for tc in tool_calls:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                raw_args = fn.get("arguments", {})
                
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {"query": raw_args}
                else:
                    args = raw_args or {}

                step_num = len(research_trace) + 1
                logger.info(f"🔍 [Agent Step {step_num}] 調用工具: {fn_name} 參數: {args}")

                tool_start = time.time()
                tool_output = await self.tools.execute_tool(fn_name, args)
                tool_duration = round(time.time() - tool_start, 2)

                # 收集參考來源
                if fn_name == "search_knowledge_base" and isinstance(tool_output, dict):
                    for doc in tool_output.get("documents", []):
                        src = doc.get("source", "內部文件")
                        if src not in collected_sources:
                            collected_sources.append(src)
                        collected_sources_detail.append({
                            "source": src,
                            "chunk": doc.get("chunk_index", 0),
                            "score": doc.get("score"),
                            "snippet": doc.get("content", "")[:200]
                        })
                elif fn_name == "web_search" and isinstance(tool_output, dict):
                    for res in tool_output.get("results", []):
                        title = res.get("title", "網頁來源")
                        url = res.get("url", "")
                        if title not in collected_sources:
                            collected_sources.append(title)
                        collected_sources_detail.append({
                            "source": title,
                            "url": url,
                            "snippet": res.get("content", "")[:200]
                        })
                elif fn_name == "web_fetch" and isinstance(tool_output, dict):
                    url = tool_output.get("url", "")
                    title = tool_output.get("title", url)
                    if title not in collected_sources:
                        collected_sources.append(title)
                    collected_sources_detail.append({
                        "source": title,
                        "url": url,
                        "snippet": tool_output.get("content", "")[:200]
                    })

                # 記錄研究足跡
                output_preview = json.dumps(tool_output, ensure_ascii=False)
                if len(output_preview) > 300:
                    output_preview = output_preview[:300] + "..."

                research_trace.append({
                    "step": step_num,
                    "tool": fn_name,
                    "arguments": args,
                    "output_preview": output_preview,
                    "duration_seconds": tool_duration,
                    "status": "error" if "error" in tool_output else "success"
                })

                # 將工具執行結果反饋給模型
                tool_call_id = tc.get("id") or f"call_{step_num}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": fn_name,
                    "content": json.dumps(tool_output, ensure_ascii=False)
                })

        total_time = round(time.time() - start_time, 2)

        return {
            "answer": final_answer,
            "sources": collected_sources[:6],
            "sources_detail": collected_sources_detail[:6],
            "research_trace": research_trace,
            "turns_used": turns_used,
            "total_time": total_time,
            "retrieval_strategy": "agentic_react"
        }
