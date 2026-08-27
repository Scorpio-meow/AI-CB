import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
logger = logging.getLogger(__name__)
def clean_html(html_content: str) -> str:
    """清理 HTML 標籤並擷取核心文字內容"""
    if not html_content:
        return ""

    cleaned = re.sub(r'<(script|style|noscript)[^>]*>[\s\S]*?</\1>', '', html_content, flags=re.IGNORECASE)

    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)

    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned[:4000]
class ResearchToolRegistry:
    """研究工具註冊中心：提供知識庫檢索、聯網搜尋與網頁深入閱讀工具"""
    def __init__(self, retriever=None):
        self.retriever = retriever
    def set_retriever(self, retriever):
        self.retriever = retriever
    async def search_knowledge_base(self, query: str, top_k: int = 3, target_document: Optional[str] = None) -> Dict[str, Any]:
        """檢索本機與企業內部知識庫（包含 FAISS 向量與 BM25 關鍵字混合檢索，可選限定特定文件）"""
        if not self.retriever:
            return {"error": "知識庫檢索器尚未初始化", "documents": []}
        
        try:
            doc_score_pairs = self.retriever.smart_search(query)
            if target_document:
                target_clean = target_document.strip().lower()
                filtered = [
                    (doc, score) for doc, score in doc_score_pairs
                    if target_clean in (doc.metadata.get("source", "")).lower() or target_clean in (doc.metadata.get("original_filename", "")).lower()
                ]
                if filtered:
                    doc_score_pairs = filtered

            exact_hits_count = len([p for p in doc_score_pairs if p[1] is not None and p[1] >= 0.95])
            effective_k = max(top_k, exact_hits_count)
            selected_pairs = doc_score_pairs[:effective_k]
            
            docs_info = []
            for doc, score in selected_pairs:
                docs_info.append({
                    "source": doc.metadata.get("source", "未知文件"),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "score": round(float(score), 4) if score is not None else None,
                    "content": doc.page_content.strip()
                })
            
            return {
                "query": query,
                "target_document": target_document,
                "total_found": len(doc_score_pairs),
                "returned": len(docs_info),
                "documents": docs_info
            }
        except Exception as e:
            logger.error(f"search_knowledge_base 執行失敗: {e}")
            return {"error": f"檢索知識庫時發生錯誤: {str(e)}", "documents": []}
    async def filter_and_count_records(
        self,
        date_range: Optional[str] = None,
        author: Optional[str] = None,
        keyword: Optional[str] = None,
        target_document: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        精準統計與條件篩選知識庫中的結構化記錄/貼文/文件。
        計算特定發布月份/日期（如 2026年8月、2025-10-22）、特定作者、關鍵字或特定文件的總筆數（精確 count），
        並回傳符合條件的記錄清單。
        """
        if not self.retriever or not hasattr(self.retriever, "vector_store") or not self.retriever.vector_store.documents:
            return {"error": "知識庫尚未載入", "total_count": 0, "records": []}
        try:
            docs = self.retriever.vector_store.documents
            target_dates = []
            if date_range:
 
                for m in re.finditer(r'(\d{4})[-/](\d{1,2})(?:[-/](\d{1,2}))?', date_range):
                    y = m.group(1)
                    mth = int(m.group(2))
                    d = int(m.group(3)) if m.group(3) else None
                    if d is not None:
                        target_dates.extend([f"{y}-{mth:02d}-{d:02d}", f"{y}年{mth}月{d}日", f"{y}年{mth:02d}月{d:02d}日"])
                    else:
                        target_dates.extend([f"{y}-{mth:02d}", f"{y}年{mth}月", f"{y}年{mth:02d}月"])
                for m in re.finditer(r'(\d{4})年\s*(\d{1,2})月(?:\s*(\d{1,2})日)?', date_range):
                    y = m.group(1)
                    mth = int(m.group(2))
                    d = int(m.group(3)) if m.group(3) else None
                    if d is not None:
                        target_dates.extend([f"{y}-{mth:02d}-{d:02d}", f"{y}年{mth}月{d}日", f"{y}年{mth:02d}月{d:02d}日"])
                    else:
                        target_dates.extend([f"{y}-{mth:02d}", f"{y}年{mth}月", f"{y}年{mth:02d}月"])
                target_dates = list(set(target_dates))
            matched_records = []
            for doc in docs:
                if target_document:
                    src = (doc.metadata.get("source", "")).lower()
                    orig = (doc.metadata.get("original_filename", "")).lower()
                    t_clean = target_document.strip().lower()
                    if t_clean not in src and t_clean not in orig:
                        continue
                content = doc.page_content
                c_lower = content.lower()
 
                if target_dates:
                    if "timestamp:" in content or "timestampTitle:" in content:
                        has_date = any(
                            re.search(rf'timestamp:\s*{re.escape(td)}', content) or
                            re.search(rf'timestampTitle:\s*{re.escape(td)}', content)
                            for td in target_dates
                        )
                    else:
                        has_date = any(td in content for td in target_dates)
                    if not has_date:
                        continue
 
                if author:
                    auth_clean = author.lstrip("@").lower()
                    if auth_clean not in c_lower:
                        continue
 
                if keyword:
                    if keyword.lower() not in c_lower:
                        continue
                matched_records.append({
                    "source": doc.metadata.get("source", "未知文件"),
                    "record_index": doc.metadata.get("record_index"),
                    "author": doc.metadata.get("author"),
                    "link": doc.metadata.get("link"),
                    "content": content.strip()
                })
            total_count = len(matched_records)
            returned_records = matched_records[:limit]
            return {
                "total_count": total_count,
                "filter_criteria": {
                    "date_range": date_range,
                    "author": author,
                    "keyword": keyword,
                    "target_document": target_document
                },
                "returned_count": len(returned_records),
                "summary": f"在知識庫中精確統計到 {total_count} 則符合條件的記錄/貼文（本次回傳前 {len(returned_records)} 則）。",
                "records": returned_records
            }
        except Exception as e:
            logger.error(f"filter_and_count_records 執行失敗: {e}")
            return {"error": f"統計篩選時發生錯誤: {str(e)}", "total_count": 0, "records": []}
    async def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """執行聯網搜尋以獲取外部即時資訊（優先調用 Ollama 官方搜尋 API，失敗時自動調用 DuckDuckGo 備援）"""
        ollama_key = settings.OLLAMA_API_KEY or ''
        

        if ollama_key:
            try:
                search_endpoint = settings.OLLAMA_SEARCH_ENDPOINT
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        search_endpoint,
                        headers={"Authorization": f"Bearer {ollama_key}"},
                        json={"query": query, "max_results": max_results}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("results", [])
                        return {
                            "query": query,
                            "engine": "ollama",
                            "count": len(results),
                            "results": results
                        }
                    else:
                        logger.warning(f"Ollama Web Search API 返回狀態碼 {resp.status_code}，切換至備援引擎")
            except Exception as e:
                logger.warning(f"Ollama Web Search 失敗: {e}，切換至備援引擎")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            ddg_endpoint = settings.DUCKDUCKGO_SEARCH_ENDPOINT
            async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(
                    ddg_endpoint,
                    params={"q": query}
                )
                if resp.status_code == 200:
                    results = []

                    links = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', resp.text)
                    titles = re.findall(r'<a class="result__a"[^>]*>([\s\S]*?)</a>', resp.text)
                    snippets = re.findall(r'<a class="result__snippet"[^>]*>([\s\S]*?)</a>', resp.text)
                    
                    for i in range(min(len(titles), max_results)):
                        clean_title = clean_html(titles[i]) if i < len(titles) else ""
                        raw_link = links[i][0] if i < len(links) else ""
                        clean_snippet = clean_html(snippets[i]) if i < len(snippets) else ""
                        

                        actual_url = raw_link
                        uddg_match = re.search(r'uddg=([^&]+)', raw_link)
                        if uddg_match:
                            import urllib.parse
                            actual_url = urllib.parse.unquote(uddg_match.group(1))
                        if clean_title and actual_url:
                            results.append({
                                "title": clean_title,
                                "url": actual_url,
                                "snippet": clean_snippet
                            })
                    return {
                        "query": query,
                        "engine": "duckduckgo_fallback",
                        "count": len(results),
                        "results": results
                    }
                else:
                    return {"query": query, "error": f"搜尋失敗，狀態碼: {resp.status_code}", "results": []}
        except Exception as e:
            logger.error(f"DuckDuckGo 搜尋失敗: {e}")
            return {"query": query, "error": f"外部搜尋發生錯誤: {str(e)}", "results": []}
    async def web_fetch(self, url: str) -> Dict[str, Any]:
        """深入讀取指定網頁全文（優先使用 Ollama Web Fetch，失敗時直接 HTTP 抓取並解析 HTML）"""
        ollama_key = settings.OLLAMA_API_KEY or ''

        if ollama_key:
            try:
                fetch_endpoint = settings.OLLAMA_FETCH_ENDPOINT
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        fetch_endpoint,
                        headers={"Authorization": f"Bearer {ollama_key}"},
                        json={"url": url}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return {
                            "url": url,
                            "title": data.get("title", ""),
                            "content": data.get("content", "")[:3500]
                        }
            except Exception as e:
                logger.warning(f"Ollama Web Fetch 失敗: {e}，切換為直接連線讀取")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    title_match = re.search(r'<title[^>]*>(.*?)</title>', resp.text, re.IGNORECASE)
                    title = title_match.group(1).strip() if title_match else url
                    clean_text = clean_html(resp.text)
                    return {
                        "url": url,
                        "title": title,
                        "content": clean_text[:3500]
                    }
                else:
                    return {"url": url, "error": f"網頁讀取失敗，狀態碼: {resp.status_code}", "content": ""}
        except Exception as e:
            logger.error(f"web_fetch 失敗 ({url}): {e}")
            return {"url": url, "error": f"無法存取該網址: {str(e)}", "content": ""}
    def _generate_knowledge_base_description(self) -> str:
        """根據知識庫收錄的每一份文件內容結構，純動態生成互不相同且專屬之主題描述（無任何硬編碼）"""
        from app.services.document_processor import DocumentProcessor
        doc_items = []
        try:
            from app.models.database import SessionLocal
            from app.models import Document
            db = SessionLocal()
            docs = db.query(Document).all()
            for d in docs:
                desc = getattr(d, "description", None)
                if not desc and d.content:
                    desc = DocumentProcessor.generate_document_summary(d.filename, d.content, d.file_type or "")
                doc_items.append((d.filename, desc or f"收錄內部文件《{d.filename}》。"))
            db.close()
        except Exception as e:
            logger.warning(f"從資料庫讀取文件描述失敗: {e}")

        if not doc_items and self.retriever and hasattr(self.retriever, "vector_store") and hasattr(self.retriever.vector_store, "documents"):
            seen = set()
            for d in self.retriever.vector_store.documents:
                src = d.metadata.get("source") or d.metadata.get("original_filename")
                if src and src not in seen:
                    seen.add(src)
                    desc = DocumentProcessor.generate_document_summary(src, d.page_content)
                    doc_items.append((src, desc))
        if not doc_items:
            return "檢索已上傳之內部知識庫與專業文件資料。當使用者提供特定網址連結、作者帳號或查詢內部檔案時必須優先調用。"
        doc_descriptions = []
        for idx, (filename, desc) in enumerate(doc_items, start=1):
            doc_descriptions.append(f"{idx}. 《{filename}》：{desc}")
        catalog_text = "\n".join(doc_descriptions)
        return (
            "檢索內部知識庫。目前知識庫收錄以下各具不同主題之專屬文件庫，調用時請針對相應主題檢索：\n"
            f"{catalog_text}\n"
            "當使用者提問涉及上述任一文件的專屬領域時，必須優先調用此工具。"
        )
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """回傳 OpenAI / Ollama / Azure OpenAI 相容之 Function Calling 工具規格清單（包含內部預設工具與已啟用的自訂 API Tools）"""
        kb_desc = self._generate_knowledge_base_description()
        base_tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": kb_desc,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "要檢索的繁體中文、英文關鍵字、作者帳號或特定網址"
                            },
                            "target_document": {
                                "type": "string",
                                "description": "可選：指定要限定搜尋的特定文件名稱（例如 'config.js' 或特定檔案名稱）。若不確定可留空檢索全庫。"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "返回的最相關文件片段數量（預設 3，最大 5）",
                                "default": 3
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "filter_and_count_records",
                    "description": "精準統計與條件篩選知識庫中的結構化貼文/記錄/文件。可用於計算特定發布月份/日期（如 '2026年8月'、'2025-10-22'）、特定作者（如 '@xv.n_4'）、特定關鍵字或特定文件的總筆數（精確 count），並可取得符合條件的完整或批次清單。當使用者詢問『總共有幾則』、『統計』、『列出某年某月所有貼文』或『某作者的全部記錄』時【必須優先調用此工具】。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date_range": {
                                "type": "string",
                                "description": "篩選發布日期或月份（如 '2026-08', '2026年8月', '2025-10-22', '2025年10月22日'）。優先匹配發布時間。"
                            },
                            "author": {
                                "type": "string",
                                "description": "篩選特定作者帳號（如 '@xv.n_4' 或 'xv.n_4'）"
                            },
                            "keyword": {
                                "type": "string",
                                "description": "篩選內容中包含的關鍵字"
                            },
                            "target_document": {
                                "type": "string",
                                "description": "限定的文件名稱（例如 'threads-full-data-2026-08-24.js'）"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "返回清單筆數上限（預設 50，最大 200）",
                                "default": 50
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "執行外部網路搜尋，獲取最新公開即時資訊、時事新聞或內部知識庫未涵蓋的外部公開資料。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜尋引擎關鍵字"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "最大搜尋結果筆數（預設 5）",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_fetch",
                    "description": "深入閱讀與抓取指定公開網頁的全文內容。當 web_search 返回的摘要不足以完整回答時，可調用此工具深入閱讀特定網址。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "要讀取的完整網址（http:// 或 https://）"
                            }
                        },
                        "required": ["url"]
                    }
                }
            }
        ]

        try:
            from app.models.database import SessionLocal
            from app.models import CustomApiTool, McpServer
            from app.services.mcp_service import McpManager
            db = SessionLocal()
            custom_tools = db.query(CustomApiTool).filter(CustomApiTool.is_enabled == True).all()
            for ct in custom_tools:
                p_schema = {"type": "object", "properties": {}}
                if ct.parameters_schema:
                    try:
                        p_schema = json.loads(ct.parameters_schema)
                    except Exception:
                        pass
                
                desc = ct.description or ct.display_name or ct.name
                base_tools.append({
                    "type": "function",
                    "function": {
                        "name": ct.name,
                        "description": f"【外部自訂 API】{ct.display_name}：{desc}",
                        "parameters": p_schema
                    }
                })

            mcp_servers = db.query(McpServer).filter(McpServer.is_enabled == True).all()
            for ms in mcp_servers:
                if ms.discovered_tools:
                    try:
                        tools_list = json.loads(ms.discovered_tools)
                        for mt in tools_list:
                            fdef = McpManager.convert_mcp_tool_to_function_def(
                                server_name=ms.name,
                                server_display_name=ms.display_name,
                                mcp_tool=mt
                            )
                            base_tools.append(fdef)
                    except Exception as e:
                        logger.warning(f"解析 MCP 伺服器 {ms.name} 工具快取失敗: {e}")
            db.close()
        except Exception as e:
            logger.warning(f"動態載入外部工具或 MCP 失敗: {e}")
        return base_tools
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """執行指定名稱之工具並回傳結果"""
        if name == "search_knowledge_base":
            query = arguments.get("query", "")
            top_k = int(arguments.get("top_k", 3))
            target_document = arguments.get("target_document")
            return await self.search_knowledge_base(query, top_k, target_document)
        elif name == "filter_and_count_records":
            date_range = arguments.get("date_range")
            author = arguments.get("author")
            keyword = arguments.get("keyword")
            target_document = arguments.get("target_document")
            limit = int(arguments.get("limit", 50))
            return await self.filter_and_count_records(date_range, author, keyword, target_document, limit)
        elif name == "web_search":
            query = arguments.get("query", "")
            max_results = int(arguments.get("max_results", 5))
            return await self.web_search(query, max_results)
        elif name == "web_fetch":
            url = arguments.get("url", "")
            return await self.web_fetch(url)
        elif name.startswith("mcp_"):

            try:
                from app.models.database import SessionLocal
                from app.models import McpServer
                from app.services.mcp_service import McpManager
                from app.api.mcp import _serialize_mcp_server
                import re
                db = SessionLocal()
                mcp_servers = db.query(McpServer).filter(McpServer.is_enabled == True).all()
                target_server = None
                target_tool_name = None
                for ms in mcp_servers:
                    if ms.discovered_tools:
                        try:
                            tools_list = json.loads(ms.discovered_tools)
                            for mt in tools_list:
                                clean_s = re.sub(r'[^a-zA-Z0-9_]', '_', ms.name).lower()
                                clean_t = re.sub(r'[^a-zA-Z0-9_]', '_', mt.get("name", "")).lower()
                                expected_fn = f"mcp_{clean_s}_{clean_t}"
                                if expected_fn == name:
                                    target_server = ms
                                    target_tool_name = mt.get("name")
                                    break
                        except Exception:
                            pass
                    if target_server:
                        break
                if target_server and target_tool_name:
                    s_dict = _serialize_mcp_server(target_server)
                    db.close()
                    res = await McpManager.execute_mcp_tool(s_dict, target_tool_name, arguments)
                    return res
                db.close()
                return {"error": f"找不到對應且啟用的 MCP 伺服器工具: {name}"}
            except Exception as e:
                logger.error(f"執行 MCP 工具 {name} 時發生異常: {e}")
                return {"error": f"執行 MCP 工具失敗: {str(e)}"}
        else:

            try:
                from app.models.database import SessionLocal
                from app.models import CustomApiTool
                from app.api.api_tools import execute_http_api_tool, _serialize_tool_model
                db = SessionLocal()
                custom_tool = db.query(CustomApiTool).filter(CustomApiTool.name == name).first()
                if custom_tool and custom_tool.is_enabled:
                    tool_dict = _serialize_tool_model(custom_tool)
                    db.close()
                    return await execute_http_api_tool(tool_dict, arguments)
                db.close()
            except Exception as e:
                logger.error(f"執行自訂 API 工具 {name} 時發生異常: {e}")
                return {"error": f"執行自訂 API 工具失敗: {str(e)}"}
            return {"error": f"未知的工具名稱: {name}"}