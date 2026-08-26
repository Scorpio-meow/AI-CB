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
    # 移除 script 與 style 區塊
    cleaned = re.sub(r'<(script|style|noscript)[^>]*>[\s\S]*?</\1>', '', html_content, flags=re.IGNORECASE)
    # 移除所有 HTML 標籤
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    # 正規化空白與換行
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

            selected_pairs = doc_score_pairs[:top_k]
            
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

    async def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """執行聯網搜尋以獲取外部即時資訊（優先調用 Ollama 官方搜尋 API，失敗時自動調用 DuckDuckGo 備援）"""
        ollama_key = getattr(settings, 'OLLAMA_API_KEY', '') or ''
        
        # 1. 嘗試使用 Ollama 官方 Web Search API
        if ollama_key:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://ollama.com/api/web_search",
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

        # 2. 備援：使用 DuckDuckGo 免金鑰搜尋
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query}
                )
                if resp.status_code == 200:
                    results = []
                    # 解析 DuckDuckGo HTML 結果
                    links = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', resp.text)
                    titles = re.findall(r'<a class="result__a"[^>]*>([\s\S]*?)</a>', resp.text)
                    snippets = re.findall(r'<a class="result__snippet"[^>]*>([\s\S]*?)</a>', resp.text)
                    
                    for i in range(min(len(titles), max_results)):
                        clean_title = clean_html(titles[i]) if i < len(titles) else ""
                        raw_link = links[i][0] if i < len(links) else ""
                        clean_snippet = clean_html(snippets[i]) if i < len(snippets) else ""
                        
                        # 解析真實 URL (DuckDuckGo 包含 uddg 跳轉)
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
        ollama_key = getattr(settings, 'OLLAMA_API_KEY', '') or ''

        # 1. 嘗試使用 Ollama 官方 Web Fetch API
        if ollama_key:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://ollama.com/api/web_fetch",
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

        # 2. 備援：直接 HTTP 抓取網頁並清理
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

        # 若資料庫無記錄，嘗試從檢索器記憶體中動態推導
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
        """回傳 OpenAI / Ollama / Azure OpenAI 相容之 Function Calling 工具規格清單"""
        kb_desc = self._generate_knowledge_base_description()
        return [
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

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """執行指定名稱之工具並回傳結果"""
        if name == "search_knowledge_base":
            query = arguments.get("query", "")
            top_k = int(arguments.get("top_k", 3))
            target_document = arguments.get("target_document")
            return await self.search_knowledge_base(query, top_k, target_document)
        elif name == "web_search":
            query = arguments.get("query", "")
            max_results = int(arguments.get("max_results", 5))
            return await self.web_search(query, max_results)
        elif name == "web_fetch":
            url = arguments.get("url", "")
            return await self.web_fetch(url)
        else:
            return {"error": f"未知的工具名稱: {name}"}
