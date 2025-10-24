<!-- ChatBot 應用程式開發指引 -->

# ChatBot 專案架構指南

此專案是一個企業級 RAG 驅動的 ChatBot 應用程式，採用前後端分離架構，具備完整的安全機制和性能優化。

## 🏗️ 核心架構決策

### 後端架構 (FastAPI)
- **單例模式**: `RAGManager` 使用雙重檢查鎖定確保全局唯一 RAG 實例 (見 `app/core/rag_manager.py`)
- **非同步設計**: 所有 I/O 操作使用 async/await，路由函數定義為 `async def`
- **分層架構**: API → Service → CRUD → Models (嚴格分層，避免跨層調用)
- **依賴注入**: 使用 FastAPI `Depends()` 管理資料庫會話、認證狀態等

### 前端架構 (React)
- **路由保護**: 使用 `PrivateRoute` 和 `AdminRoute` 包裹受保護頁面 (見 `frontend/src/App.js`)
- **Layout 模式**: 所有頁面包裹在統一的 `Layout` 組件中，處理導航和認證狀態
- **API 代理**: 開發時通過 `package.json` proxy 轉發至後端 8001 端口

## 🔐 安全機制 (關鍵實現)

### JWT 雙 Token 系統
**實現位置**: `app/core/jwt_auth.py`
- **Access Token**: 15 分鐘有效期，存儲在 localStorage
- **Refresh Token**: 7 天有效期，存儲在 HttpOnly Cookie (防 XSS)
- **RSA 簽名**: 使用 RSA-2048 非對稱加密，公私鑰存放於 `backend/keys/`
- **降級策略**: 生產環境強制使用 RSA，開發環境允許降級至 HS256 並發出警告

### Token 黑名單機制
**實現位置**: `app/core/redis_client.py` - `TokenBlacklist` 類
- Redis 快取已撤銷的 Token，防止重放攻擊
- Token key 格式: `blacklist:token:{jti}` (使用 JWT ID)
- 自動過期時間與 Token TTL 同步

### 環境隔離的 CORS 策略
**實現位置**: `backend/main.py`
```python
# 生產環境: 嚴格白名單，禁用 regex
ALLOWED_ORIGINS = ["https://yourdomain.com"]
ALLOWED_ORIGIN_REGEX = None

# 開發環境: localhost 精確匹配
ALLOWED_ORIGINS = ["http://localhost:3000", ...]
# 移除不安全的 regex，改用 .env 中的 DEVTUNNEL_URL
```

### API Key 保護
管理員路由使用 `X-API-Key` header 認證 (見 `app/core/security.py` - `verify_admin_api_key`)

## 🤖 混合 RAG 系統核心

### 三層檢索架構
**實現位置**: `app/rag/contextual_rag.py` - `HybridContextualRAG` 類
1. **向量檢索**: FAISS IndexFlatIP (內積相似度)
2. **BM25 全文檢索**: Whoosh + Jieba 中文分詞
3. **Cross-Encoder 重排序**: `ms-marco-MiniLM-L-6-v2` 提升相關性

### GPU 加速配置
```python
# 自動檢測 CUDA 並載入模型
self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
self.local_embeddings = SentenceTransformer(model, device=self.device)
# 支援 FP16 量化 (USE_FP16_QUANTIZATION=true)
```

### 持久化策略
- **FAISS 索引**: `data/faiss_index.bin` (二進位格式)
- **文檔元數據**: `data/documents.pkl` (Pickle 序列化，包含 last_reindex 時間戳)
- **BM25 索引**: `data/bm25_index/` (Whoosh 文件目錄)

### 自動重建機制
**實現位置**: `app/tasks/index_rebuilder.py`
- 24 小時周期背景任務，檢查 `metadata.last_reindex` 決定是否重建
- 環境變數控制: `ENABLE_AUTO_REINDEX_TASK=1`, `REINDEX_INTERVAL_HOURS=24`

## 📂 文檔處理流程

### 上傳處理 (流式寫入)
**實現位置**: `app/api/documents.py`
```python
# 分塊讀取避免記憶體問題
contents = await file.read(CHUNK_SIZE)
f.write(contents)
```
- 檔案大小限制: 10MB (環境變數 `MAX_FILE_SIZE_MB`)
- 支援格式: TXT, PDF, DOCX

### 安全驗證
**實現位置**: `app/services/document_processor.py`
```python
# 魔數驗證檔案類型真實性
FILE_SIGNATURES = {
    'application/pdf': [b'%PDF'],
    'application/vnd...docx': [b'PK\x03\x04'],
}
```

### 批次刪除
**API**: `POST /api/documents/bulk_delete`
- 並行處理 RAG/檔案刪除，使用 batch SQL 刪除 `DocumentChunk` 和 `Document`
- 回傳每個 ID 的狀態: `deleted` / `deleted_with_warnings` / `failed` / `not_found`

## 🛠️ 開發工作流程

### 環境啟動順序
1. 激活虛擬環境: `.\CBvenv\Scripts\Activate.ps1`
2. 啟動後端: 運行 VS Code 任務 "啟動後端開發服務器" (端口 8001)
3. 啟動前端: 運行任務 "啟動前端開發服務器" (端口 3000)
4. 訪問: `http://localhost:3000` (API 通過 proxy 轉發)

### 數據庫遷移
- SQLAlchemy 自動建表: `Base.metadata.create_all(bind=engine)`
- 初始化資料庫: `python backend/init_db.py`

### 測試命令
- RAG 評估: `python scripts/test_rag_improvements.py`
- GPU 測試: 運行 VS Code 任務 "🧪 測試 GPU 加速"

## 🎯 專案特定慣例

### 模型繼承規則
- 所有 SQLAlchemy 模型繼承自 `Base` (定義於 `app/models/database.py`)
- Pydantic Schema 放在 `app/schemas/`，與 API 路由對應

### 錯誤處理模式
```python
# 統一使用 HTTPException
raise HTTPException(status_code=500, detail=f"錯誤訊息: {str(e)}")
```

### 日誌配置
- 應用日誌: `logs/app.log`
- 安全日誌: `logs/security.log` (記錄認證失敗、API Key 驗證等)
- 使用 `logger = logging.getLogger(__name__)` 獲取模組級 logger

### 環境變數必需項
**關鍵變數** (必須在 `.env` 中設定):
```bash
MODEL_NAME=gpt-oss:20b  # LLM 模型名稱
LLM_API_BASE=http://localhost:11434  # Ollama API 端點
DATABASE_URL=sqlite:///./chatbot.db
ADMIN_API_KEY=<隨機生成的安全金鑰>
```

## 🔧 關鍵整合點

### WebSocket 連接管理
**實現位置**: `app/api/chat.py` - `ConnectionManager` 類
- 維護 `user_connections` 字典映射 user_id 到 WebSocket
- 使用 `await websocket.accept()` 建立連接

### Custom Agent 系統
**實現位置**: `app/api/custom_agent.py`
- 用戶僅能訪問自己創建的或公開的 Agent (基於 `is_public` 和 `created_by` 過濾)
- CRUD 操作需 JWT 認證: `current_user: dict = Depends(get_current_active_user)`

### 生產部署選項
- **Gunicorn + Uvicorn**: `start_production.ps1` (支援 24-32 workers)
- **Waitress**: `start_waitress.ps1` (Windows 穩定版)
- 兩者皆支援參數化配置 worker/thread 數量

## 📋 常見任務檢查清單

### 新增 API 端點
1. 在 `app/api/` 建立路由檔案，定義 `router = APIRouter()`
2. 在 `backend/main.py` 中 `app.include_router(router, prefix="/api/xxx")`
3. 新增對應 Schema 至 `app/schemas/`
4. 需要認證的端點加上 `Depends(get_current_active_user)` 或 `Depends(verify_admin_api_key)`

### 修改 RAG 檢索邏輯
1. 編輯 `app/rag/contextual_rag.py` 的 `retrieve_context` 或 `generate_response` 方法
2. 修改後運行 `rag_system.force_reindex()` 重建索引
3. 使用 `scripts/test_rag_improvements.py` 驗證變更

### 前端新增頁面
1. 在 `frontend/src/pages/` 建立組件
2. 在 `frontend/src/App.js` 的 `createBrowserRouter` 添加路由
3. 使用 `PrivateRoute` 或 `AdminRoute` 包裹需要認證的頁面

## 技術細節
### 混合 RAG 系統
- **向量模型**: paraphrase-multilingual-MiniLM-L12-v2 (384維)
- **重新排序模型**: cross-encoder/ms-marco-MiniLM-L-6-v2
- **向量索引**: FAISS IndexFlatIP (內積相似度)
- **BM25 索引**: Whoosh StandardAnalyzer
- **智能搜尋策略**: 根據查詢特徵自動選擇向量/BM25/混合搜尋
- **持久化**: data/faiss_index.bin + data/documents.pkl + data/bm25_index/
- **文檔分塊**: RecursiveCharacterTextSplitter (600字符, 150重疊)
- **相似度閾值**: 0.25 (可配置)
- **自動重建**: 24小時周期，支援元數據追蹤

### 文檔處理
- **支援格式**: TXT, PDF, DOCX
- **編碼檢測**: chardet + 多編碼後備
- **檔案大小限制**: 50MB
- **安全處理**: 檔名清理, 類型驗證

### 文件管理與刪除
- 上傳端改為流式寫入 (避免一次性將整個檔案讀入記憶體)。前端支援多檔上傳、每檔進度與取消。
- 新增 API: `POST /api/documents/bulk_delete` 支援一次傳入多個 id 做批次刪除，後端採批次 DB 刪除並平行處理 RAG/實體檔案移除，回傳每個 id 的狀態（deleted / deleted_with_warnings / failed / not_found）。
- 刪除流程已改為在後端並行處理 RAG/檔案刪除並使用 batch SQL 刪除 DocumentChunk 與 Document，以提升效能和一致性。

### 虛擬環境
- **位置**: D:\CB\CBvenv
- **Python版本**: 3.10+
- **關鍵套件**: FastAPI, SQLAlchemy, FAISS, PyPDF2, python-docx, sentence-transformers
### 文件管理與刪除
- 上傳端改為流式寫入 (避免一次性將整個檔案讀入記憶體)。前端支援多檔上傳、每檔進度與取消。
- 新增 API: `POST /api/documents/bulk_delete` 支援一次傳入多個 id 做批次刪除，後端採批次 DB 刪除並平行處理 RAG/實體檔案移除，回傳每個 id 的狀態（deleted / deleted_with_warnings / failed / not_found）。
- 刪除流程已改為在後端並行處理 RAG/檔案刪除並使用 batch SQL 刪除 DocumentChunk 與 Document，以提升效能和一致性。

### 虛擬環境
- **位置**: D:\CB\CBvenv
- **Python版本**: 3.10+
- **關鍵套件**: FastAPI, SQLAlchemy, FAISS, PyPDF2, python-docx, sentence-transformers, whoosh, scikit-learn
- **已知相容性 pin**: `huggingface_hub==0.19.3`（用於解決 sentence-transformers 相容性問題）

## 快速啟動 (純本地開發環境)
1. **配置環境變數**：已配置為本地開發環境，無需外部隧道
2. **啟動虛擬環境**：`.\CBvenv\Scripts\Activate.ps1`
3. **使用 VS Code 任務**：
   - 啟動後端：運行任務 "啟動後端開發服務器"
   - 啟動前端：運行任務 "啟動前端開發服務器"
4. **訪問地址**：
   - 前端：http://localhost:3000
   - 後端：http://localhost:8000
   - API：http://localhost:3000/api/* (通過 proxy 轉發)

## 專案結構
```
chatbot/
├── backend/              # FastAPI 後端
│   ├── app/              # 應用程式核心
│   │   ├── api/          # API 路由
│   │   ├── models/       # 數據模型
│   │   ├── rag/          # RAG 系統
│   │   └── services/     # 業務服務
│   ├── data/             # 數據儲存
│   │   ├── uploads/      # 上傳檔案
│   │   ├── faiss_index.bin  # FAISS 索引
│   │   ├── documents.pkl    # 文檔元數據
│   │   └── bm25_index/      # BM25 索引
│   ├── scripts/          # 工具腳本
│   └── CBvenv/           # Python 虛擬環境
├── frontend/             # React 前端  
│   ├── src/              # 源代碼
│   │   ├── components/   # React 組件
│   │   ├── pages/        # 頁面組件
│   │   └── services/     # API 服務
│   └── node_modules/     # Node.js 依賴
├── .vscode/              # VS Code 配置
├── .github/              # GitHub 配置
├── docker-compose.yml    # Docker 配置
└── *.ps1                 # PowerShell 啟動腳本
```

## 開發環境說明
### 本地開發配置 (已移除 DevTunnels)
- **前端配置**: `frontend/.env` - 使用 localhost + proxy 轉發
- **後端配置**: `backend/.env` - 本地 CORS 設定
- **代理設定**: `frontend/package.json` - `"proxy": "http://localhost:8000"`

### 常用命令
- **重置 FAISS**: `python scripts/reset_faiss.py`
- **啟動後端**: `python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- **啟動前端**: `npm start` (會自動代理 API 到後端)
- **安裝套件**: `pip install -r requirements.txt`
- **測試 RAG**: `python scripts/test_rag_improvements.py`
- **測試 API**: `python scripts/test_ollama_api.py`

### 環境優化重點
- **簡化配置**: 無需管理外部隧道或複雜網路設定
- **本地開發**: 所有服務運行在 localhost，快速穩定
- **代理轉發**: 前端通過 Create React App 內建 proxy 處理 API 請求
- **CORS 最小化**: 後端僅允許本地開發環境訪問
