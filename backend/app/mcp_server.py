import sys
import httpx
import logging
import os
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# 設定日誌
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("AskMiaoMCPServer")

# 建立 FastMCP 伺服器實例
mcp = FastMCP(
    "AskMiao Knowledge Base",
    description="AskMiao RAG 知識庫文檔檢索與搜尋 MCP 伺服器"
)

# 載入 API 連線設定
BACKEND_HOST = os.getenv("HOST", "localhost")
BACKEND_PORT = os.getenv("PORT", "8001")
BACKEND_URL = os.getenv("ASKMIAO_API_URL", f"http://{BACKEND_HOST}:{BACKEND_PORT}")

# 預設為預留開發金鑰，實際部署時應從 .env 讀取
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING")

@mcp.tool()
async def search_documents(query: str, top_k: int = 5) -> str:
    """
    搜尋 AskMiao 知識庫以取得與 query 查詢句最相關的文檔內容。
    回傳經格式化之最佳匹配段落及其來源中繼資料。
    """
    url = f"{BACKEND_URL}/api/documents/search"
    headers = {
        "X-API-Key": ADMIN_API_KEY
    }
    params = {
        "query": query,
        "top_k": top_k
    }
    
    logger.info(f"MCP 收到請求 RAG 搜尋: '{query}'")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, params=params, timeout=30.0)
            if response.status_code == 401:
                return "錯誤: 認證失敗。請確認 MCP 啟動時的 ADMIN_API_KEY 與 AskMiao 後端設定一致。"
            response.raise_for_status()
            results = response.json()
            
            if not results:
                return "在 AskMiao 知識庫中未找到匹配的文檔段落。"
                
            formatted_docs = []
            for i, doc in enumerate(results):
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})
                score = doc.get("score", 0.0)
                source = metadata.get("source", "未知來源")
                formatted_docs.append(
                    f"[{i+1}] 來源: {source} (相關度評分: {score:.4f})\n內容:\n{content}\n"
                )
            return "\n---\n".join(formatted_docs)
            
        except httpx.HTTPStatusError as e:
            return f"錯誤: AskMiao 後端返回 HTTP 錯誤碼 {e.response.status_code}: {e.response.text}"
        except httpx.RequestError as e:
            return f"錯誤: 無法連線至 AskMiao 後端 ({BACKEND_URL})。請確認 FastAPI 服務已正確啟動。"

if __name__ == "__main__":
    # 以 stdio 模式執行 FastMCP
    mcp.run()
