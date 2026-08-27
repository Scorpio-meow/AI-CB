import json
import logging
import time
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
import httpx
from app.core.config import settings
from app.rag.tools import ResearchToolRegistry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一個具備自主研究能力的智慧助理「AskMiao」。
你可以根據使用者的問題，自主調用以下工具來查證知識庫文件或外部即時網路資訊：
1. `search_knowledge_base`: 檢索已上傳之知識庫、文檔、貼文記錄、資料表或設定檔（適合語意查詢、內容查找、細節問答）。
2. `filter_and_count_records`: 精準統計與條件篩選知識庫中的結構化貼文/記錄（可用於計算特定發布月份/日期、特定作者、關鍵字或特定文件的精確總筆數 count，並列出完整清單）。
3. `web_search`: 搜尋外部即時新聞、公開網站資訊或最新知識。
4. `web_fetch`: 當搜尋結果摘要不足時，可深入閱讀特定網頁的全文。

【行為規範】：
- 當使用者詢問【總共有幾則/幾篇】、【統計數量】、【列出某年某月/某日所有已收錄貼文】或【某作者的全部發文清單】等需要精確計數或大批次列出的問題時，請【優先調用 `filter_and_count_records`】，以獲得 100% 精確的 `total_count` 總數與結構化記錄清單。
- 當使用者提供特定網址連結（如 Threads/IG/FB/X/特定文章網址）、帳號名、特定代碼或詢問文件內容時，請【優先調用 `search_knowledge_base`】檢索內部資料庫是否已收錄該連結或內容。
- 若 `web_fetch` 讀取外部網頁失敗（例如遭遇登入牆、動態渲染 SPA 僅取得標題），應【立即調用 `search_knowledge_base`】以該網址或作者關鍵字查詢內部知識庫。
- 若問題涉及外部即時新聞、時事或知識庫未收錄內容，再調用 `web_search`。
- 若問題僅為一般問候或日常打招呼，可直接輸出回覆，無須調用工具。
- 彙整查得的資料後，請使用繁體中文給出條理清晰、客觀專業且附帶具體細節的回答。
- 請勿編造不存在的事實。
"""


class ResearchAgent:
    """多輪自主研究 Agent 控制器 (支援 SSE 串流與即時步驟推播)"""

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

        azure_deployments = [d.strip() for d in (settings.AZURE_OPENAI_DEPLOYMENT or "").split(",") if d.strip()]
        deployment = model_name or (azure_deployments[0] if azure_deployments else "")

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
            if "gpt-5" in deployment.lower():
                payload["reasoning_effort"] = "none"
            elif reasoning_effort and reasoning_effort in ("none", "minimal", "low", "medium", "high", "xhigh", "max"):
                payload["reasoning_effort"] = reasoning_effort
        else:
            if reasoning_effort and reasoning_effort in ("none", "minimal", "low", "medium", "high", "xhigh", "max"):
                payload["reasoning_effort"] = reasoning_effort

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"v1 Azure OpenAI API 錯誤 ({resp.status_code}): {resp.text}")
            data = resp.json()
            choice = data["choices"][0]
            return choice["message"]

    async def _stream_azure_openai(
        self,
        messages: List[Dict[str, Any]],
        model_name: Optional[str] = None,
        reasoning_effort: Optional[str] = "medium"
    ) -> AsyncGenerator[str, None]:
        """調用 v1 Azure OpenAI 串流生成最終答案"""
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip('/') if settings.AZURE_OPENAI_ENDPOINT else ""
        api_key = settings.AZURE_OPENAI_API_KEY or ""

        azure_deployments = [d.strip() for d in (settings.AZURE_OPENAI_DEPLOYMENT or "").split(",") if d.strip()]
        deployment = model_name or (azure_deployments[0] if azure_deployments else "")

        url = f"{endpoint}/openai/v1/chat/completions"
        headers = {
            "api-key": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload: Dict[str, Any] = {
            "model": deployment,
            "messages": messages,
            "stream": True
        }
        if reasoning_effort and reasoning_effort in ("none", "minimal", "low", "medium", "high", "xhigh", "max"):
            payload["reasoning_effort"] = reasoning_effort

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    raise RuntimeError(f"Azure OpenAI 串流錯誤 ({resp.status_code}): {error_text.decode('utf-8')}")

                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line_content = line[6:].strip()
                        if line_content == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(line_content)
                            delta = chunk_data["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except Exception:
                            continue

    async def _call_ollama(
        self,
        messages: List[Dict[str, Any]],
        tools_def: List[Dict[str, Any]],
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """調用 Ollama 原生 Tool Calling API"""
        base_url = settings.LLM_API_BASE.rstrip('/')
        target_model = model_name or settings.MODEL_NAME or ""

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

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama API 錯誤 ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data.get("message", {})

    async def _stream_ollama(
        self,
        messages: List[Dict[str, Any]],
        model_name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """調用 Ollama 串流生成最終答案"""
        base_url = settings.LLM_API_BASE.rstrip('/')
        target_model = model_name or settings.MODEL_NAME or ""

        url = f"{base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": 0.3,
                "num_predict": 2048
            }
        }

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            async with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    raise RuntimeError(f"Ollama 串流錯誤 ({resp.status_code}): {error_text.decode('utf-8')}")
                
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk_data = json.loads(line)
                        content = chunk_data.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue

    async def stream_research(
        self,
        query: str,
        model_name: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        reasoning_effort: Optional[str] = "medium",
        attachments: Optional[List[Any]] = None,
        max_turns: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """非同步生成器：即時產生研究步驟事件與文字 token 串流（無輪數上限，由模型自主決定研究步數）"""
        start_time = time.time()
        tools_def = self.tools.get_tool_definitions()

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        if conversation_history:
            for turn_msg in conversation_history[-6:]:
                messages.append(turn_msg)


        doc_contexts = []
        image_data_urls = []

        if attachments:
            import base64
            import tempfile
            import os
            from app.services.document_processor import DocumentProcessor

            for att in attachments:
                fname = getattr(att, "filename", None) or (att.get("filename") if isinstance(att, dict) else "未知檔案")
                ftype = getattr(att, "file_type", None) or (att.get("file_type") if isinstance(att, dict) else "")
                data_url = getattr(att, "data_url", None) or (att.get("data_url") if isinstance(att, dict) else None)
                content = getattr(att, "content", None) or (att.get("content") if isinstance(att, dict) else None)

                if ftype.startswith("image/"):
                    if data_url:
                        image_data_urls.append(data_url)
                else:
                    extracted_text = content
                    if not extracted_text and data_url:
                        try:
                            if "," in data_url:
                                _, b64_data = data_url.split(",", 1)
                            else:
                                b64_data = data_url
                            file_bytes = base64.b64decode(b64_data)
                            suffix = os.path.splitext(fname)[1] or ".txt"
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                tmp.write(file_bytes)
                                tmp_path = tmp.name
                            try:
                                extracted_text = DocumentProcessor.extract_text_from_file(tmp_path, ftype)
                            finally:
                                if os.path.exists(tmp_path):
                                    os.remove(tmp_path)
                        except Exception as e:
                            logger.warning(f"即時解析附件 {fname} 失敗: {e}")

                    if extracted_text and extracted_text.strip():
                        doc_contexts.append(f"【附加檔案: {fname}】\n{extracted_text.strip()}")

        effective_query = query
        if doc_contexts:
            effective_query = "\n\n".join(doc_contexts) + f"\n\n【使用者問題】\n{query}"

        azure_deployments = [d.strip() for d in (settings.AZURE_OPENAI_DEPLOYMENT or "").split(",") if d.strip()]
        use_azure = False
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            if model_name:
                if model_name in azure_deployments or any(prefix in model_name.lower() for prefix in ("gpt-", "o1", "o3", "o4")):
                    use_azure = True
            else:
                use_azure = True


        if image_data_urls and use_azure:
            user_content = [{"type": "text", "text": effective_query}]
            for img_url in image_data_urls:
                user_content.append({"type": "image_url", "image_url": {"url": img_url}})
            messages.append({"role": "user", "content": user_content})
        elif image_data_urls:
            b64_list = []
            for img_url in image_data_urls:
                if "," in img_url:
                    b64_list.append(img_url.split(",", 1)[1])
                else:
                    b64_list.append(img_url)
            messages.append({"role": "user", "content": effective_query, "images": b64_list})
        else:
            messages.append({"role": "user", "content": effective_query})

        research_trace: List[Dict[str, Any]] = []
        collected_sources: List[str] = []
        collected_sources_detail: List[Dict[str, Any]] = []
        final_answer = ""
        turns_used = 0
        has_executed_tools = False

        while True:
            turns_used += 1
            if max_turns is not None and turns_used > max_turns:
                logger.info(f"Agent 已達到手動指定的輪數上限 ({max_turns})，停止後續工具調用")
                break

            try:
                if use_azure:
                    assistant_msg = await self._call_azure_openai(
                        messages, tools_def, model_name, reasoning_effort=reasoning_effort
                    )
                else:
                    assistant_msg = await self._call_ollama(messages, tools_def, model_name)
            except Exception as e:
                logger.error(f"模型調用失敗 (第 {turns_used} 輪): {e}")
                if not final_answer and not research_trace:
                    err_msg = f"在執行自主研究時遇到連線異常: {str(e)}"
                    yield {"event": "token", "data": {"content": err_msg}}
                    final_answer = err_msg
                break

            tool_calls = assistant_msg.get("tool_calls")
            if not tool_calls:
 
                content = assistant_msg.get("content", "")
                if content and not has_executed_tools:
                    final_answer = content

                    chunk_size = 4
                    for i in range(0, len(content), chunk_size):
                        sub = content[i:i+chunk_size]
                        yield {"event": "token", "data": {"content": sub}}
                        await asyncio.sleep(0.015)
                break

            has_executed_tools = True
            messages.append(assistant_msg)

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

 
                yield {
                    "event": "step_start",
                    "data": {
                        "step": step_num,
                        "tool": fn_name,
                        "arguments": args
                    }
                }

                tool_start = time.time()
                tool_output = await self.tools.execute_tool(fn_name, args)
                tool_duration = round(time.time() - tool_start, 2)

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

                output_preview = json.dumps(tool_output, ensure_ascii=False)
                if len(output_preview) > 300:
                    output_preview = output_preview[:300] + "..."

                step_info = {
                    "step": step_num,
                    "tool": fn_name,
                    "arguments": args,
                    "output_preview": output_preview,
                    "duration_seconds": tool_duration,
                    "status": "error" if "error" in tool_output else "success"
                }
                research_trace.append(step_info)

 
                yield {
                    "event": "step_end",
                    "data": step_info
                }

                tool_call_id = tc.get("id") or f"call_{step_num}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": fn_name,
                    "content": json.dumps(tool_output, ensure_ascii=False)
                })


        if has_executed_tools and not final_answer:
            try:
                if use_azure:
                    async for chunk in self._stream_azure_openai(messages, model_name, reasoning_effort=reasoning_effort):
                        final_answer += chunk
                        yield {"event": "token", "data": {"content": chunk}}
                else:
                    async for chunk in self._stream_ollama(messages, model_name):
                        final_answer += chunk
                        yield {"event": "token", "data": {"content": chunk}}
            except Exception as e:
                logger.error(f"串流生成最終答案失敗: {e}")
                err_msg = f"\n[回答生成中斷: {str(e)}]"
                final_answer += err_msg
                yield {"event": "token", "data": {"content": err_msg}}

        total_time = round(time.time() - start_time, 2)


        yield {
            "event": "sources",
            "data": {
                "sources": collected_sources[:6],
                "sources_detail": collected_sources_detail[:6]
            }
        }

        yield {
            "event": "done",
            "data": {
                "answer": final_answer,
                "sources": collected_sources[:6],
                "sources_detail": collected_sources_detail[:6],
                "research_trace": research_trace,
                "turns_used": turns_used,
                "total_time": total_time,
                "retrieval_strategy": "agentic_react"
            }
        }

    async def run_research(
        self,
        query: str,
        model_name: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        reasoning_effort: Optional[str] = "medium",
        attachments: Optional[List[Any]] = None,
        max_turns: Optional[int] = None
    ) -> Dict[str, Any]:
        """非串流封裝（向後相容）"""
        result: Dict[str, Any] = {
            "answer": "",
            "sources": [],
            "sources_detail": [],
            "research_trace": [],
            "turns_used": 0,
            "total_time": 0.0,
            "retrieval_strategy": "agentic_react"
        }
        async for item in self.stream_research(
            query,
            model_name=model_name,
            conversation_history=conversation_history,
            reasoning_effort=reasoning_effort,
            attachments=attachments,
            max_turns=max_turns
        ):
            if item.get("event") == "done":
                result.update(item.get("data", {}))
        return result
