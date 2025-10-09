# ChatBot 應用程式

一個具備使用者介面和後台管理介面的 ChatBot 應用程式，使用增強型混合 RAG（檢索增強生成）技術提供智能對話服務。

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)

## 📋 目錄

- [功能特色](#功能特色)
- [技術架構](#技術架構)
- [快速開始](#快速開始)
- [API 接口](#api-接口)
- [混合 RAG 系統](#混合-rag-系統)
- [開發工具](#開發工具)
- [部署指南](#部署指南)
- [相關文檔](#相關文檔)

## 🌟 功能特色

### 🤖 智能對話系統
- **混合 RAG 檢索**: 結合向量搜尋 (FAISS) 和 BM25 關鍵詞匹配的雙重檢索系統
- **Cross-Encoder 重新排序**: 使用 `ms-marco-MiniLM-L-6-v2` 提升檢索結果相關性
- **智能搜尋策略**: 根據查詢特徵自動選擇向量/BM25/混合搜尋模式
- **即時通訊**: 基於 WebSocket 的即時對話功能
- **對話記憶**: 支援多對話管理與歷史記錄保存
- **自動索引重建**: 24 小時周期自動維護索引性能
- **動態模型選擇**: 支援多個 LLM 模型，可動態切換 🆕

### � 安全與認證
- **JWT 雙 Token 機制**: Access Token (15分鐘) + Refresh Token (7天)
- **RSA 非對稱加密**: 使用 RSA-2048 簽名 JWT，支援微服務架構
- **Token 黑名單**: Redis 實現的 Token 撤銷機制
- **HttpOnly Cookie**: Refresh Token 安全存儲，防止 XSS 攻擊
- **靜默刷新**: Token 即將過期時自動刷新，無感更新
- **角色權限控制**: 基於 RBAC 的細粒度權限管理
- **密碼安全**: Bcrypt 加密 + 密碼強度驗證
- **速率限制**: 防止 API 濫用 (60次/分鐘)
- **安全日誌**: 所有關鍵操作記錄到 `logs/security.log`

### 📚 知識庫管理
- **多格式支援**: PDF, TXT, DOCX 文件處理
- **流式上傳**: 避免大文件記憶體問題，支援 10MB 文件上限
- **多檔上傳**: 批次上傳最多 10 個文件，單獨進度顯示
- **智能分塊**: RecursiveCharacterTextSplitter (600字符，150重疊)
- **混合索引**: FAISS IndexFlatIP + Whoosh BM25 雙重索引
- **多編碼支援**: UTF-8, GBK, Big5 等中文編碼自動檢測
- **批次刪除**: 高效的批次文檔刪除 API
- **FAQ 專用索引**: 支援 Q&A 對分割與檢索優化

### 🎯 Agent 工作流系統 🆕
- **自定義 Agent**: 用戶可創建專屬的 AI Agent
- **可見性控制**: 支援公開/私有 Agent 設定
- **權限隔離**: 用戶僅能訪問自己的或公開的 Agent
- **角色預設**: 內建多種專業角色模板
- **工作流輸出**: 自動保存 Agent 執行結果

### 🎛️ 後台管理
- **用戶管理**: 完整的 CRUD 操作
- **對話監控**: 查看所有用戶對話記錄
- **系統統計**: 使用量分析與性能指標
- **文件管理**: 知識庫文件批次管理
- **向量庫監控**: 索引狀態、重建統計、性能追蹤
- **API Key 保護**: 所有管理端點需要 `X-API-Key` 認證

### 📊 評估與監控
- **檢索質量指標**: Recall@k, Precision@k, MRR
- **性能基準測試**: 多種搜尋策略比較
- **配置優化工具**: 參數調優建議
- **自動化測試**: 完整的評估腳本套件


## 🏗️ 技術架構

### 後端技術棧
- **Web 框架**: FastAPI 0.104+ (高性能異步框架)
- **ORM**: SQLAlchemy 2.0+ (數據庫操作)
- **AI/ML 框架**:
  - LangChain (RAG 實現框架)
  - sentence-transformers (文本嵌入)
  - FAISS (向量檢索引擎)
  - Whoosh (全文檢索引擎)
- **LLM 集成**: Ollama (本地部署)
- **文檔處理**:
  - PyPDF2 (PDF 解析)
  - python-docx (Word 文檔)
  - chardet (編碼檢測)
- **數據庫**:
  - SQLite (開發環境)
  - PostgreSQL (生產環境，推薦)
  - Redis (Token 黑名單緩存)
- **安全**:
  - cryptography (RSA 加密)
  - passlib + bcrypt (密碼加密)
  - python-jose (JWT 處理)
- **其他**:
  - filelock (跨進程文件鎖)
  - uvicorn (ASGI 服務器)

### 前端技術棧
- **核心框架**: React 18
- **UI 組件庫**: Material-UI (MUI) v5
- **路由**: React Router v6
- **HTTP 客戶端**: Axios
- **狀態管理**: React Context API
- **WebSocket**: 原生 WebSocket API
- **構建工具**: Create React App

### RAG 系統核心
#### 向量模型與索引
- **嵌入模型**: `paraphrase-multilingual-MiniLM-L12-v2` (384維)
  - 支援 50+ 語言的多語言模型
  - 專為語義相似度優化
- **重新排序模型**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
  - 基於 MS MARCO 數據集訓練
  - 提升檢索結果精度
- **向量索引**: FAISS IndexFlatIP (內積相似度)
  - 精確搜索，適合中小規模數據集
  - CPU 友好，無需 GPU
- **BM25 索引**: Whoosh StandardAnalyzer
  - 基於 TF-IDF 的關鍵詞匹配
  - 使用 jieba 中文分詞

#### 智能檢索策略
系統根據查詢特徵自動選擇最佳檢索方法：

1. **向量搜尋**: 適合語義查詢
   - 概念性問題
   - 長句子查詢
   - 需要理解上下文的問題

2. **BM25 搜尋**: 適合關鍵詞匹配
   - 包含專有名詞
   - 精確詞彙查詢
   - 短關鍵詞搜索

3. **混合搜尋**: 平衡兩者優勢
   - 複雜查詢
   - 需要兼顧語義和關鍵詞
   - 預設策略

#### 數據持久化
```
backend/data/
├── faiss_index.bin      # FAISS 向量索引
├── documents.pkl        # 文檔元數據
├── index_metadata.pkl   # 索引重建統計
├── bm25_index/          # Whoosh BM25 索引目錄
└── uploads/             # 上傳文件存儲
```

#### 文檔處理流程
1. **文件上傳**: 流式寫入，支援大文件
2. **編碼檢測**: 自動檢測 UTF-8/GBK/Big5
3. **文本提取**: 格式化處理 PDF/DOCX/TXT
4. **文檔分塊**: RecursiveCharacterTextSplitter
   - chunk_size: 600 字符
   - chunk_overlap: 150 字符
5. **向量化**: 生成 384 維嵌入向量
6. **索引構建**: 同步更新 FAISS 和 BM25 索引
7. **元數據存儲**: 保存文檔和分塊信息

### 安全架構
#### JWT 認證流程
```
登入 → 生成 Access Token (15分鐘)
     → 生成 Refresh Token (7天, HttpOnly Cookie)
     → RSA 私鑰簽名

驗證 → RSA 公鑰驗證簽名
     → 檢查 Token 黑名單
     → 解析用戶信息

刷新 → 驗證 Refresh Token
     → 生成新 Access Token
     → 延長 Refresh Token (可選)

登出 → 將 Token 加入黑名單
     → 清除 Cookie
```

#### RSA 金鑰管理
- **金鑰位置**: `backend/keys/`
  - `jwt_private.pem`: 私鑰 (簽名)
  - `jwt_public.pem`: 公鑰 (驗證)
- **自動生成**: 首次啟動時自動創建
- **權限設定**: 私鑰僅後端可讀
- **微服務友好**: 公鑰可分發給其他服務驗證

### 核心改進與優化

#### 🎨 模型列表功能 (2025-10-08)
- **手動刷新按鈕**: UI 一鍵更新可用模型
- **載入狀態指示**: 實時進度反饋
- **智能通知系統**: Snackbar 非侵入式提示
- **可配置輪詢**: `MODEL_LIST_POLL_INTERVAL` 環境變數
- **詳細模型信息**: 顯示家族、大小、量化級別
- **完整測試腳本**: `test_model_list_improvements.py`

#### 🛡️ 安全增強 (2025-10-03)
- **RSA 非對稱加密**: 替代傳統對稱加密
- **Token 黑名單**: Redis 實現撤銷機制
- **HttpOnly Cookie**: 防止 XSS 攻擊
- **靜默刷新機制**: 自動 Token 更新
- **離線緩存**: IndexedDB 本地存儲
- **網絡狀態監控**: 自動重連機制

#### 🔧 RAG 系統優化 (2025-09-30)
- **單例 RAG 管理器**: 避免多實例衝突
- **跨進程文件鎖**: 解決 Windows Whoosh 鎖定問題
- **智能索引重建**: 獨立後台任務
- **動態用戶上下文**: 支援 `X-User-ID` header
- **FAQ 專用處理**: Q&A 對分割與檢索

#### 📁 文件管理改進
- **流式上傳**: 避免記憶體溢出
- **批次刪除 API**: `POST /api/documents/bulk_delete`
- **並行處理**: 同步刪除 DB、RAG、文件
- **狀態回報**: 詳細的每檔刪除結果
- **進度追蹤**: 前端單檔進度顯示


## 🚀 快速開始

### 📋 環境要求
- **Python**: 3.10 或更高版本
- **Node.js**: 16.0 或更高版本
- **Redis**: 可選，用於 Token 黑名單 (推薦生產環境)
- **數據庫**: SQLite (開發) / PostgreSQL (生產)
- **操作系統**: Windows / Linux / macOS

### ⚡ 快速啟動 (推薦使用 VS Code)

#### 方法一: VS Code 任務 (最簡單) ⭐

1. **打開專案**
   ```powershell
   cd C:\Users\MITAC\Documents\AI-CB
   code .
   ```

2. **執行任務**
   - 按 `Ctrl+Shift+P`
   - 輸入 "Tasks: Run Task"
   - 選擇 "啟動完整系統"

3. **訪問應用**
   - 前端: http://localhost:3000
   - 後端: http://localhost:8001
   - API 文檔: http://localhost:8001/docs

#### 方法二: PowerShell 腳本

```powershell
# 啟動後端
.\start-backend.ps1

# 啟動前端 (新終端)
.\start-frontend.ps1
```

#### 方法三: 手動啟動

**步驟 1: 後端設置**

```powershell
# 進入後端目錄
cd backend

# 啟動虛擬環境
.\CBvenv\Scripts\Activate.ps1

# 安裝依賴 (首次運行)
pip install -r requirements.txt

# 啟動後端服務
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

**步驟 2: 前端設置** (新終端)

```powershell
# 進入前端目錄
cd frontend

# 安裝依賴 (首次運行)
npm install

# 啟動前端開發服務器
npm start
```

**步驟 3: Redis 設置** (可選，用於生產環境)

```powershell
# 使用 Docker (推薦)
docker run -d -p 6379:6379 --name chatbot-redis redis:alpine

# 或使用 WSL
wsl
sudo service redis-server start
```

### 🔧 環境配置

#### 後端環境變數 (`backend/.env`)

```env
# === LLM API 配置 ===
MODEL_NAME=gpt-oss:20b
LLM_API_BASE=https://your-llm-endpoint.com
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000

# === 數據庫配置 ===
# 開發環境 (SQLite)
DATABASE_URL=sqlite:///./chatbot.db

# 生產環境 (PostgreSQL)
# DATABASE_URL=postgresql://user:password@localhost/chatbot

# === Redis 配置 (Token 黑名單) ===
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_password  # 如果有設置密碼

# === JWT 配置 ===
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=RS256

# === 安全配置 ===
# 生成方式: python -c "import secrets; print(secrets.token_urlsafe(32))"
ADMIN_API_KEY=your_secure_admin_api_key_here
SECRET_KEY=your_secret_key_here

# === CORS 配置 ===
ALLOWED_ORIGINS=http://localhost:3000,https://localhost:3000,http://127.0.0.1:3000

# === RAG 系統配置 ===
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
SIMILARITY_THRESHOLD=0.25
CHUNK_SIZE=600
CHUNK_OVERLAP=150
TOP_K=50
FINAL_K=10

# === 文件上傳限制 ===
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_UPLOAD=10

# === 模型列表配置 ===
MODEL_LIST_POLL_INTERVAL=300  # 秒，模型列表更新間隔

# === Agent 工作流配置 ===
WORKFLOW_TIMEOUT=180
WORKFLOW_CYCLE_LIMIT=2
WORKFLOW_MAX_HISTORY=20
WORKFLOW_MAX_CONTEXT=5
```

#### 前端環境變數 (`frontend/.env`)

```env
# === 開發環境配置 ===
HOST=localhost
PORT=3000

# === API 配置 ===
# 注意: 使用 package.json 中的 proxy，無需設置 REACT_APP_API_BASE

# === 功能開關 ===
REACT_APP_ENABLE_ANALYTICS=false
REACT_APP_ENABLE_DEBUG=true
```

#### 前端代理設置 (`frontend/package.json`)

```json
{
  "proxy": "http://localhost:8001"
}
```

### 🗄️ 數據庫初始化

**首次啟動時自動創建**
- SQLite 數據庫自動初始化
- 表結構自動遷移
- RSA 金鑰對自動生成

**創建管理員賬戶**
```powershell
cd backend
python scripts/create_admin.py
```

### ✅ 驗證安裝

#### 健康檢查
```powershell
# 後端健康檢查
curl http://localhost:8001/health
# 預期輸出: {"status":"healthy"}

# 前端訪問
# 瀏覽器打開: http://localhost:3000
```

#### 測試 API
```powershell
# 測試模型列表
python backend/scripts/test_model_list_improvements.py

# 測試 RAG 系統
python backend/scripts/test_rag_improvements.py

# 測試安全功能
python backend/scripts/test_security_enhancements.py
```

### 🎯 可用的 VS Code 任務

在 VS Code 中按 `Ctrl+Shift+P` → "Tasks: Run Task"：

- **啟動完整系統**: 同時啟動前後端 (推薦)
- **啟動後端開發服務器**: 僅啟動後端
- **啟動前端開發服務器**: 僅啟動前端
- **安裝後端依賴**: 安裝 Python 依賴
- **安裝前端依賴**: 安裝 Node.js 依賴
- **Docker 構建**: 構建 Docker 鏡像
- **Docker 啟動**: 啟動 Docker 容器


## 📡 API 接口

### 認證相關

#### 用戶註冊
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "user123",
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

#### 用戶登入
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user123",
  "password": "SecurePass123!"
}

Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
# Refresh Token 在 HttpOnly Cookie 中返回
```

#### Token 刷新
```http
POST /api/auth/refresh
Cookie: refresh_token=<token>

Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

#### 用戶登出
```http
POST /api/auth/logout
Authorization: Bearer <access_token>
Cookie: refresh_token=<token>
```

### 聊天功能

#### 發送消息
```http
POST /api/chat/send
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "message": "你好，請問...",
  "conversation_id": 123,  # 可選，不提供則創建新對話
  "use_rag": true          # 可選，是否使用 RAG 檢索
}

Response:
{
  "response": "根據資料顯示...",
  "conversation_id": 123,
  "sources": [...]  # 如果使用 RAG
}
```

#### WebSocket 即時聊天
```javascript
const ws = new WebSocket('ws://localhost:8001/ws/chat');

// 發送消息
ws.send(JSON.stringify({
  message: "你好",
  conversation_id: 123
}));

// 接收回應
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.response);
};
```

#### 獲取對話列表
```http
GET /api/chat/conversations
Authorization: Bearer <access_token>

Response:
[
  {
    "id": 123,
    "title": "關於產品的問題",
    "created_at": "2025-10-08T10:30:00",
    "updated_at": "2025-10-08T11:45:00",
    "message_count": 5
  }
]
```

#### 獲取對話詳情
```http
GET /api/chat/conversations/{id}
Authorization: Bearer <access_token>

Response:
{
  "id": 123,
  "title": "關於產品的問題",
  "messages": [
    {
      "role": "user",
      "content": "你好",
      "timestamp": "2025-10-08T10:30:00"
    },
    {
      "role": "assistant",
      "content": "您好！有什麼可以幫您的嗎？",
      "timestamp": "2025-10-08T10:30:05"
    }
  ]
}
```

#### 刪除對話
```http
DELETE /api/chat/conversations/{id}
Authorization: Bearer <access_token>
```

### 文件管理

#### 上傳文件
```http
POST /api/documents/upload
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

files: [file1.pdf, file2.txt, ...]  # 最多 10 個，每個 <10MB

Response:
{
  "success": [
    {
      "filename": "file1.pdf",
      "id": 1,
      "chunks": 15
    }
  ],
  "failed": []
}
```

#### 獲取文件列表
```http
GET /api/documents/
Authorization: Bearer <access_token>

Response:
[
  {
    "id": 1,
    "filename": "產品手冊.pdf",
    "file_type": "pdf",
    "size": 2048576,
    "chunk_count": 15,
    "uploaded_at": "2025-10-08T09:00:00"
  }
]
```

#### 刪除單個文件
```http
DELETE /api/documents/{id}
Authorization: Bearer <access_token>
```

#### 批次刪除文件 🆕
```http
POST /api/documents/bulk_delete
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "ids": [1, 2, 3, 4, 5]
}

Response:
{
  "results": [
    {"id": 1, "status": "deleted"},
    {"id": 2, "status": "deleted_with_warnings", "message": "..."},
    {"id": 3, "status": "failed", "error": "..."},
    {"id": 4, "status": "not_found"}
  ],
  "summary": {
    "total": 4,
    "deleted": 2,
    "failed": 1,
    "not_found": 1
  }
}
```

### Agent 工作流 🆕

#### 獲取可用專業角色
```http
GET /api/workflow/professions
Authorization: Bearer <access_token>

Response:
[
  "軟體工程師",
  "數據分析師",
  "產品經理",
  ...
]
```

#### 執行工作流
```http
POST /api/workflow/execute
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "input": ["需求分析", "技術方案設計"],
  "profession": "軟體工程師",
  "model": "gpt-oss:20b",
  "system_prompt": "你是一位專業的..."  # 可選
}

Response:
{
  "output": "分析結果...",
  "output_file": "/path/to/output.txt",
  "cycles": 2
}
```

### 模型管理

#### 獲取可用模型列表
```http
GET /api/models/list
Authorization: Bearer <access_token>

Response:
{
  "models": [
    {
      "name": "gpt-oss:20b",
      "family": "gpt-oss",
      "parameter_size": "20B",
      "quantization": "Q4_K_M"
    }
  ],
  "last_updated": "2025-10-08T12:00:00"
}
```

#### 手動刷新模型列表 🆕
```http
POST /api/models/refresh
Authorization: Bearer <access_token>

Response:
{
  "models": [...],
  "count": 5,
  "updated_at": "2025-10-08T12:05:00"
}
```

### 管理員功能

**所有管理員端點都需要 `X-API-Key` header**

#### 獲取用戶列表
```http
GET /api/admin/users
X-API-Key: your_admin_api_key

Response:
[
  {
    "id": 1,
    "username": "user123",
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2025-10-01T00:00:00"
  }
]
```

#### 更新用戶信息
```http
PUT /api/admin/users/{id}
X-API-Key: your_admin_api_key
Content-Type: application/json

{
  "username": "new_username",
  "email": "new@example.com",
  "is_active": false
}
```

#### 刪除用戶
```http
DELETE /api/admin/users/{id}
X-API-Key: your_admin_api_key
```

#### 獲取系統統計
```http
GET /api/admin/statistics
X-API-Key: your_admin_api_key

Response:
{
  "total_users": 100,
  "total_conversations": 500,
  "total_messages": 2500,
  "total_documents": 50,
  "total_chunks": 750,
  "index_size": "45.2 MB",
  "last_index_rebuild": "2025-10-08T00:00:00"
}
```

#### 獲取向量庫信息
```http
GET /api/admin/vector-store/info
X-API-Key: your_admin_api_key

Response:
{
  "total_chunks": 750,
  "index_size": "45.2 MB",
  "last_rebuild": "2025-10-08T00:00:00",
  "index_health": "good"
}
```

#### 清空向量庫
```http
DELETE /api/admin/vector-store/clear
X-API-Key: your_admin_api_key
```

### 錯誤回應格式

```json
{
  "detail": "錯誤描述",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-10-08T12:00:00"
}
```

常見 HTTP 狀態碼：
- `200`: 成功
- `201`: 創建成功
- `400`: 請求錯誤
- `401`: 未認證
- `403`: 無權限
- `404`: 資源不存在
- `422`: 驗證錯誤
- `429`: 請求過於頻繁
- `500`: 服務器錯誤


## 🧠 混合 RAG 系統

### 系統架構

本專案採用先進的混合檢索增強生成（Hybrid RAG）系統，結合多種檢索技術以提供最佳的問答質量。

```
用戶查詢
    ↓
查詢分析與策略選擇
    ↓
    ├─→ 向量搜尋 (FAISS)     ─┐
    ├─→ BM25 搜尋 (Whoosh)   ─┤
    └─→ 混合搜尋             ─┘
         ↓
    候選文檔集合
         ↓
Cross-Encoder 重新排序
         ↓
    Top-K 文檔
         ↓
    上下文構建
         ↓
    LLM 生成回答
         ↓
    返回結果
```

### 核心組件

#### 1. 向量搜尋 (FAISS)
- **嵌入模型**: `paraphrase-multilingual-MiniLM-L12-v2`
  - 384 維向量
  - 支援 50+ 語言
  - 專為語義相似度優化
- **索引類型**: IndexFlatIP (內積相似度)
  - 精確搜索，無近似誤差
  - CPU 友好，適合中小規模數據集
- **適用場景**:
  - 概念性查詢
  - 長句子問題
  - 需要理解上下文的查詢

#### 2. BM25 全文檢索 (Whoosh)
- **分詞器**: jieba (中文) + StandardAnalyzer
- **算法**: BM25F (Field-weighted BM25)
- **索引目錄**: `backend/data/bm25_index/`
- **適用場景**:
  - 精確關鍵詞匹配
  - 專有名詞查詢
  - 短關鍵詞搜索

#### 3. Cross-Encoder 重新排序
- **模型**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **訓練數據**: MS MARCO (微軟機器閱讀理解數據集)
- **作用**: 對候選文檔進行精確相關性評分
- **優勢**: 比單純向量檢索精度更高

### 智能搜尋策略

系統根據查詢特徵自動選擇最佳檢索方法：

#### 策略 1: 純向量搜尋
**觸發條件**:
- 查詢長度 > 20 字符
- 不包含特殊符號或精確詞彙
- 語義複雜的問題

**示例**: 
- "請解釋一下產品的核心優勢和競爭力"
- "如何提高團隊的工作效率"

#### 策略 2: 純 BM25 搜尋
**觸發條件**:
- 查詢包含專有名詞
- 短關鍵詞 (< 10 字符)
- 包含特定詞彙標記

**示例**:
- "API 文檔"
- "價格方案"
- "聯繫方式"

#### 策略 3: 混合搜尋 (預設)
**觸發條件**:
- 不符合上述兩種情況
- 需要平衡語義和關鍵詞

**融合方法**:
```python
# 歸一化分數
vector_scores_norm = normalize(vector_scores)
bm25_scores_norm = normalize(bm25_scores)

# 加權融合 (可配置)
final_scores = alpha * vector_scores_norm + (1-alpha) * bm25_scores_norm
```

**示例**:
- "產品如何收費"
- "退款流程是什麼"
- "技術支援服務"

### 工作流程詳解

#### 步驟 1: 文檔處理與索引構建

```python
# 1. 文檔上傳
uploaded_file → 編碼檢測 → 文本提取

# 2. 文檔分塊
full_text → RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=150,
    separators=["\n\n", "\n", "。", "!", "?", "；"]
)

# 3. 向量化
chunks → SentenceTransformer.encode() → vectors (384-dim)

# 4. 索引構建
vectors → FAISS.add()  # 向量索引
chunks → Whoosh.add()  # BM25 索引

# 5. 元數據保存
document_info → documents.pkl
index_metadata → index_metadata.pkl
```

#### 步驟 2: 檢索流程

```python
# 1. 查詢分析
user_query → analyze_query() → search_strategy

# 2. 執行檢索
if strategy == "vector":
    candidates = faiss_search(query, top_k=50)
elif strategy == "bm25":
    candidates = bm25_search(query, top_k=50)
else:  # hybrid
    vector_results = faiss_search(query, top_k=30)
    bm25_results = bm25_search(query, top_k=30)
    candidates = merge_results(vector_results, bm25_results)

# 3. Cross-Encoder 重新排序
reranked = cross_encoder.rank(query, candidates)

# 4. 提取 Top-K
top_docs = reranked[:final_k]  # 預設 10
```

#### 步驟 3: 答案生成

```python
# 1. 構建上下文
context = "\n\n".join([doc.content for doc in top_docs])
sources = [{"filename": doc.filename, "chunk_id": doc.id} for doc in top_docs]

# 2. 構建提示詞
prompt = f"""
根據以下上下文回答問題。如果上下文中沒有相關信息，請誠實說明。

上下文:
{context}

問題: {user_query}

回答:
"""

# 3. LLM 生成
response = llm.generate(prompt, temperature=0.7, max_tokens=1000)

# 4. 返回結果
return {
    "answer": response,
    "sources": sources,
    "strategy_used": strategy
}
```

### 評估指標

系統支援多種評估指標來監控檢索質量：

#### Recall@k (召回率)
```python
Recall@k = 相關文檔被檢索到的數量 / 所有相關文檔的數量
```
- **Recall@5**: 前 5 個結果中的召回率
- **Recall@10**: 前 10 個結果中的召回率

#### Precision@k (精確率)
```python
Precision@k = 前 k 個結果中相關文檔的數量 / k
```

#### MRR (Mean Reciprocal Rank)
```python
MRR = 1 / N * Σ(1 / rank_i)
```
其中 rank_i 是第 i 個查詢中第一個相關文檔的排名。

### 性能優化

#### 索引自動重建
- **觸發條件**: 
  - 24 小時周期
  - 新增文檔數 > 閾值
  - 手動觸發
- **重建流程**:
  1. 從數據庫載入所有文檔
  2. 清空舊索引
  3. 重新生成向量
  4. 重建 FAISS 和 BM25 索引
  5. 更新元數據

#### 單例 RAG 管理器
```python
# 全局唯一實例，避免多實例衝突
rag_instance = HybridContextualRAG()

# 跨進程文件鎖
with FileLock("rag.lock"):
    rag_instance.add_documents(docs)
```

#### 相似度閾值過濾
```python
# 過濾低相關度文檔
results = [doc for doc in results if doc.score >= SIMILARITY_THRESHOLD]
```

### FAQ 專用處理 🆕

系統支援對 FAQ 文檔的特殊處理：

#### FAQ 分割腳本
```powershell
# 從上傳文件中解析 Q&A 對
python backend/scripts/reindex_faq_split.py
```

**處理流程**:
1. 掃描 `uploads/` 目錄
2. 正則匹配 Q&A 模式
3. 每個 Q&A 對作為單獨的 chunk
4. 添加特殊 metadata: `question`, `answer`

#### FAQ 檢索評估
```powershell
# 評估 FAQ 檢索效果
python backend/scripts/evaluate_faq_retrieval.py
```

**評估指標**:
- Hit@1/3/5: 原始 Q&A 是否在前 k 個結果中
- MRR: 平均倒數排名
- 檢索策略分布統計

### 配置參數

| 參數 | 環境變數 | 預設值 | 說明 |
|------|---------|-------|------|
| 嵌入模型 | `EMBEDDING_MODEL` | paraphrase-multilingual-MiniLM-L12-v2 | 向量化模型 |
| 重排序模型 | `RERANKER_MODEL` | cross-encoder/ms-marco-MiniLM-L-6-v2 | Cross-Encoder 模型 |
| 相似度閾值 | `SIMILARITY_THRESHOLD` | 0.25 | 最低相似度分數 |
| 分塊大小 | `CHUNK_SIZE` | 600 | 文檔分塊字符數 |
| 分塊重疊 | `CHUNK_OVERLAP` | 150 | 相鄰分塊重疊字符數 |
| 候選數量 | `TOP_K` | 50 | 初始檢索結果數 |
| 最終數量 | `FINAL_K` | 10 | 重排序後返回數 |

### 故障排除

#### 問題 1: 檢索結果不相關
**解決方案**:
- 調低 `SIMILARITY_THRESHOLD`
- 增加 `TOP_K` 以獲取更多候選
- 檢查文檔分塊是否合理

#### 問題 2: 索引鎖定錯誤 (Windows)
**解決方案**:
```python
# 已內建跨進程鎖
from filelock import FileLock
with FileLock("bm25_index.lock"):
    # 索引操作
```

#### 問題 3: 記憶體不足
**解決方案**:
- 減少 `CHUNK_SIZE`
- 使用批次處理上傳文檔
- 考慮使用 FAISS IVF 索引 (適合大規模數據)


## 🛠️ 開發工具

### 專案結構

```
AI-CB/
├── backend/                          # 後端目錄
│   ├── app/                          # 應用程式核心
│   │   ├── api/                      # API 路由
│   │   │   ├── auth.py              # 認證端點
│   │   │   ├── chat.py              # 聊天端點
│   │   │   ├── documents.py         # 文檔管理
│   │   │   ├── admin.py             # 管理員端點
│   │   │   ├── models.py            # 模型管理
│   │   │   └── workflow.py          # Agent 工作流
│   │   ├── core/                     # 核心功能
│   │   │   ├── config.py            # 配置管理
│   │   │   ├── jwt_auth.py          # JWT 認證
│   │   │   ├── security.py          # 安全功能
│   │   │   └── dependencies.py      # 依賴注入
│   │   ├── crud/                     # 數據庫 CRUD
│   │   │   ├── user.py              # 用戶操作
│   │   │   ├── conversation.py      # 對話操作
│   │   │   ├── document.py          # 文檔操作
│   │   │   └── custom_agent.py      # Agent 操作
│   │   ├── models/                   # 數據模型
│   │   │   ├── database.py          # SQLAlchemy 模型
│   │   │   └── schemas.py           # Pydantic 模型
│   │   ├── rag/                      # RAG 系統
│   │   │   ├── hybrid_rag.py        # 混合 RAG 實現
│   │   │   ├── document_processor.py # 文檔處理器
│   │   │   └── vector_store.py      # 向量存儲
│   │   ├── services/                 # 業務服務
│   │   │   ├── chat_service.py      # 聊天服務
│   │   │   ├── llm_service.py       # LLM 服務
│   │   │   └── workflow_service.py  # 工作流服務
│   │   └── tasks/                    # 後台任務
│   │       └── index_rebuilder.py   # 索引重建任務
│   ├── data/                         # 數據存儲
│   │   ├── uploads/                 # 上傳文件
│   │   ├── workflow_outputs/        # 工作流輸出
│   │   ├── faiss_index.bin         # FAISS 索引
│   │   ├── documents.pkl           # 文檔元數據
│   │   ├── index_metadata.pkl      # 索引元數據
│   │   └── bm25_index/             # BM25 索引目錄
│   ├── keys/                         # 密鑰文件
│   │   ├── jwt_private.pem         # JWT 私鑰
│   │   └── jwt_public.pem          # JWT 公鑰
│   ├── logs/                         # 日誌文件
│   │   ├── app.log                 # 應用日誌
│   │   └── security.log            # 安全日誌
│   ├── scripts/                      # 工具腳本
│   │   ├── create_admin.py         # 創建管理員
│   │   ├── reset_faiss.py          # 重置向量庫
│   │   ├── reindex_faq_split.py    # FAQ 索引重建
│   │   ├── evaluate_faq_retrieval.py # FAQ 檢索評估
│   │   ├── test_*.py               # 各種測試腳本
│   │   └── migrate_*.py            # 數據庫遷移腳本
│   ├── main.py                       # FastAPI 應用入口
│   ├── requirements.txt              # Python 依賴
│   └── chatbot.db                    # SQLite 數據庫
├── frontend/                         # 前端目錄
│   ├── public/                       # 靜態資源
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── src/                          # 源代碼
│   │   ├── components/              # React 組件
│   │   │   ├── Chat/               # 聊天組件
│   │   │   ├── Admin/              # 管理組件
│   │   │   ├── Documents/          # 文檔管理組件
│   │   │   └── Common/             # 通用組件
│   │   ├── pages/                   # 頁面組件
│   │   │   ├── ChatPage.js
│   │   │   ├── AdminPage.js
│   │   │   ├── LoginPage.js
│   │   │   └── RegisterPage.js
│   │   ├── services/                # API 服務
│   │   │   ├── api.js              # Axios 實例
│   │   │   ├── authService.js      # 認證服務
│   │   │   ├── chatService.js      # 聊天服務
│   │   │   └── documentService.js  # 文檔服務
│   │   ├── contexts/                # React Context
│   │   │   └── AuthContext.js      # 認證上下文
│   │   ├── utils/                   # 工具函數
│   │   ├── App.js                   # 主應用組件
│   │   └── index.js                 # 入口文件
│   ├── package.json                  # Node.js 依賴
│   └── .env                          # 環境配置
├── CBvenv/                           # Python 虛擬環境
├── docs/                             # 文檔目錄
│   ├── SECURITY_ENHANCEMENTS.md     # 安全增強文檔
│   ├── JWT_Authentication_Guide.md  # JWT 認證指南
│   ├── MODEL_LIST_QUICK_REF.md      # 模型列表參考
│   ├── RAG_系統說明書.md             # RAG 系統文檔
│   └── WORKFLOW_REFACTORING_SUMMARY.md # 工作流重構說明
├── .vscode/                          # VS Code 配置
│   └── tasks.json                   # 任務配置
├── .github/                          # GitHub 配置
│   └── copilot-instructions.md      # Copilot 指令
├── docker-compose.yml                # Docker Compose 配置
├── README.md                         # 本文件
├── QUICK-START.md                    # 快速啟動指南
├── TROUBLESHOOTING.md                # 故障排除
└── *.ps1                             # PowerShell 腳本
```

### 常用腳本

#### 管理腳本

**創建管理員用戶**
```powershell
cd backend
python scripts/create_admin.py
# 按提示輸入用戶名、郵箱、密碼
```

**檢查用戶信息**
```powershell
python scripts/check_user.py <username>
```

**數據庫遷移**
```powershell
# 添加 Agent 可見性欄位
python scripts/migrate_add_agent_visibility.py

# 添加分區支援
python scripts/migrate_add_partitions.py

# 遷移到 JWT 認證
python scripts/migrate_to_jwt.py
```

#### RAG 系統腳本

**重置向量庫**
```powershell
python scripts/reset_faiss.py
# 警告: 這會清空所有索引數據！
```

**FAQ 專用索引**
```powershell
# 重建 FAQ 索引
python scripts/reindex_faq_split.py

# 評估 FAQ 檢索效果
python scripts/evaluate_faq_retrieval.py
```

#### 測試腳本

**測試 LLM 連接**
```powershell
# 測試 Ollama API
python scripts/test_ollama_api.py

# 測試模型連接
python scripts/test_model_connection.py

# 測試模型列表功能
python scripts/test_model_list_improvements.py
```

**測試認證系統**
```powershell
# 測試登入
python scripts/test_login.py

# 測試 JWT 修復
python scripts/test_jwt_fix.py

# 測試登入超時
python scripts/test_login_timeout.py
```

**測試 Agent 系統**
```powershell
# 測試 Agent 可見性
python scripts/test_agent_visibility.py

# 測試公開權限
python scripts/test_is_public_permission.py

# 測試用戶隔離
python scripts/test_user_isolation.py

# 測試完整隔離
python scripts/test_complete_isolation.py
```

**測試安全功能**
```powershell
# 測試安全增強
python scripts/test_security_enhancements.py

# 測試 CORS
python scripts/test_cors.py
python scripts/test_cors_quick.py
python scripts/test_devtunnels_cors.py
```

**測試其他功能**
```powershell
# 測試 WebSocket
python scripts/test_ws.py

# 測試分區功能
python scripts/test_partitions.py

# 測試聊天遷移
python scripts/test_chat_migration.py

# 測試管理員 API
python scripts/test_admin_api.py
```

### VS Code 開發配置

#### 推薦擴展
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "bradlc.vscode-tailwindcss"
  ]
}
```

#### 調試配置 (`.vscode/launch.json`)
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8001"
      ],
      "jinja": true,
      "cwd": "${workspaceFolder}/backend"
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

### Git 工作流

#### 分支策略
```
main (rollback/59cabe7)  # 主分支
├── feature/*            # 功能開發
├── bugfix/*             # 錯誤修復
└── hotfix/*             # 緊急修復
```

#### 提交規範
```
feat: 新功能
fix: 錯誤修復
docs: 文檔更新
style: 代碼格式調整
refactor: 代碼重構
test: 測試相關
chore: 構建/工具相關
```

**範例**:
```bash
git commit -m "feat: 添加批次刪除文檔 API"
git commit -m "fix: 修復 FAISS 索引鎖定問題"
git commit -m "docs: 更新 README.md 文檔"
```

### 開發工作流程

#### 1. 後端開發流程
```powershell
# 1. 創建功能分支
git checkout -b feature/new-feature

# 2. 啟動虛擬環境
cd backend
.\CBvenv\Scripts\Activate.ps1

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 開發功能
# 編輯代碼...

# 5. 測試
python scripts/test_*.py

# 6. 提交
git add .
git commit -m "feat: 描述"
git push origin feature/new-feature
```

#### 2. 前端開發流程
```powershell
# 1. 進入前端目錄
cd frontend

# 2. 安裝依賴
npm install

# 3. 啟動開發服務器
npm start

# 4. 開發功能
# 編輯代碼...

# 5. 構建測試
npm run build

# 6. 提交
git add .
git commit -m "feat: 描述"
```

#### 3. 全棧功能開發
```powershell
# 1. 同時啟動前後端
# 終端 1: 後端
cd backend
.\CBvenv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001

# 終端 2: 前端
cd frontend
npm start

# 2. 開發並測試
# 3. 提交代碼
```

### 性能監控

#### 後端性能
```python
# 查看日誌
tail -f backend/logs/app.log

# 查看安全日誌
tail -f backend/logs/security.log
```

#### 數據庫查詢
```python
# 啟用 SQLAlchemy 查詢日誌
# backend/.env
SQLALCHEMY_ECHO=True
```

#### API 性能測試
```powershell
# 使用 Apache Bench
ab -n 1000 -c 10 http://localhost:8001/health

# 使用 wrk
wrk -t4 -c100 -d30s http://localhost:8001/api/chat/conversations
```


## � 部署指南

### Docker 部署

#### 1. 使用 Docker Compose (推薦)

**完整部署配置** (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  # PostgreSQL 數據庫
  postgres:
    image: postgres:15-alpine
    container_name: chatbot-postgres
    environment:
      POSTGRES_DB: chatbot
      POSTGRES_USER: chatbot
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U chatbot"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis (Token 黑名單)
  redis:
    image: redis:7-alpine
    container_name: chatbot-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # 後端服務
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: chatbot-backend
    environment:
      - DATABASE_URL=postgresql://chatbot:${DB_PASSWORD}@postgres/chatbot
      - REDIS_HOST=redis
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - MODEL_NAME=${MODEL_NAME}
      - LLM_API_BASE=${LLM_API_BASE}
    volumes:
      - ./backend/data:/app/data
      - ./backend/logs:/app/logs
      - ./backend/keys:/app/keys
    ports:
      - "8001:8001"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  # 前端服務
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: chatbot-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

**啟動服務**:
```powershell
# 1. 設置環境變數
$env:DB_PASSWORD="your_db_password"
$env:REDIS_PASSWORD="your_redis_password"
$env:MODEL_NAME="gpt-oss:20b"
$env:LLM_API_BASE="https://your-llm-endpoint.com"

# 2. 構建並啟動
docker-compose up -d

# 3. 查看日誌
docker-compose logs -f

# 4. 停止服務
docker-compose down
```

#### 2. 手動 Docker 構建

**後端 Dockerfile**:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 創建必要目錄
RUN mkdir -p data/uploads data/workflow_outputs logs keys

# 暴露端口
EXPOSE 8001

# 啟動命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**前端 Dockerfile**:
```dockerfile
# 構建階段
FROM node:16-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# 生產階段
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**構建與運行**:
```powershell
# 構建後端
cd backend
docker build -t chatbot-backend:latest .

# 構建前端
cd ../frontend
docker build -t chatbot-frontend:latest .

# 運行後端
docker run -d `
  --name chatbot-backend `
  -p 8001:8001 `
  -v ${PWD}/../backend/data:/app/data `
  -e DATABASE_URL=postgresql://... `
  chatbot-backend:latest

# 運行前端
docker run -d `
  --name chatbot-frontend `
  -p 80:80 `
  chatbot-frontend:latest
```

### 生產環境部署

#### 1. Nginx 反向代理配置

```nginx
# /etc/nginx/sites-available/chatbot
upstream backend {
    server localhost:8001;
}

upstream frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 證書
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 安全標頭
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API 請求轉發到後端
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超時設置
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # WebSocket 請求
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # 前端靜態文件
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 文件上傳大小限制
    client_max_body_size 10M;
}
```

**啟用配置**:
```bash
sudo ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 2. Systemd 服務配置

**後端服務** (`/etc/systemd/system/chatbot-backend.service`):
```ini
[Unit]
Description=ChatBot Backend Service
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/chatbot/backend
Environment="PATH=/opt/chatbot/CBvenv/bin"
ExecStart=/opt/chatbot/CBvenv/bin/uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

# 安全設置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/chatbot/backend/data /opt/chatbot/backend/logs

[Install]
WantedBy=multi-user.target
```

**啟用服務**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable chatbot-backend
sudo systemctl start chatbot-backend
sudo systemctl status chatbot-backend
```

#### 3. SSL 證書 (Let's Encrypt)

```bash
# 安裝 Certbot
sudo apt-get install certbot python3-certbot-nginx

# 獲取證書
sudo certbot --nginx -d your-domain.com

# 自動續期
sudo certbot renew --dry-run
```

#### 4. PostgreSQL 配置

```sql
-- 創建數據庫和用戶
CREATE DATABASE chatbot;
CREATE USER chatbot WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE chatbot TO chatbot;

-- 優化配置 (postgresql.conf)
-- shared_buffers = 256MB
-- effective_cache_size = 1GB
-- max_connections = 100
```

#### 5. Redis 配置

```bash
# 編輯 /etc/redis/redis.conf
requirepass your_redis_password
maxmemory 256mb
maxmemory-policy allkeys-lru

# 重啟 Redis
sudo systemctl restart redis
```

### 環境檢查清單

#### 部署前檢查
- [ ] 生成強密碼和 API Key
- [ ] 配置環境變數
- [ ] 生成 RSA 金鑰對
- [ ] 設置數據庫連接
- [ ] 配置 Redis
- [ ] 設置文件上傳目錄權限
- [ ] 配置日誌輪轉
- [ ] 設置防火牆規則

#### 安全檢查
- [ ] HTTPS 證書已配置
- [ ] 強制 HTTPS 重定向
- [ ] CORS 僅允許信任的域名
- [ ] API Key 已妥善保管
- [ ] 數據庫密碼足夠強
- [ ] Redis 已設置密碼
- [ ] 文件上傳限制已配置
- [ ] 速率限制已啟用

#### 性能優化
- [ ] 數據庫連接池已配置
- [ ] Redis 已啟用
- [ ] Nginx gzip 壓縮已啟用
- [ ] 靜態文件緩存已配置
- [ ] 向量索引定期重建
- [ ] 日誌輪轉已配置

### 監控與維護

#### 日誌監控
```bash
# 查看應用日誌
tail -f /opt/chatbot/backend/logs/app.log

# 查看安全日誌
tail -f /opt/chatbot/backend/logs/security.log

# 查看 Nginx 訪問日誌
tail -f /var/log/nginx/access.log

# 查看 Nginx 錯誤日誌
tail -f /var/log/nginx/error.log
```

#### 性能監控
```bash
# 系統資源
htop

# 數據庫連接
psql -U chatbot -c "SELECT count(*) FROM pg_stat_activity;"

# Redis 狀態
redis-cli INFO stats

# Nginx 狀態
curl http://localhost/nginx_status
```

#### 定期維護
```bash
# 數據庫備份 (每日)
pg_dump -U chatbot chatbot > backup_$(date +%Y%m%d).sql

# 清理舊日誌 (每週)
find /opt/chatbot/backend/logs -name "*.log" -mtime +30 -delete

# 向量索引重建 (自動，24小時)
# 已通過後台任務自動執行

# 更新系統和依賴 (每月)
sudo apt-get update && sudo apt-get upgrade
pip install --upgrade -r requirements.txt
```

### 故障排除

#### 常見問題

**問題 1: 後端無法連接數據庫**
```bash
# 檢查數據庫狀態
sudo systemctl status postgresql

# 檢查連接
psql -U chatbot -h localhost -d chatbot

# 查看後端日誌
journalctl -u chatbot-backend -n 50
```

**問題 2: Redis 連接失敗**
```bash
# 檢查 Redis 狀態
sudo systemctl status redis

# 測試連接
redis-cli -a your_password ping

# 查看 Redis 日誌
sudo journalctl -u redis -n 50
```

**問題 3: Nginx 502 錯誤**
```bash
# 檢查後端服務
sudo systemctl status chatbot-backend

# 檢查 Nginx 配置
sudo nginx -t

# 查看錯誤日誌
tail -f /var/log/nginx/error.log
```

**問題 4: 文件上傳失敗**
```bash
# 檢查目錄權限
ls -la /opt/chatbot/backend/data/uploads

# 設置正確權限
sudo chown -R www-data:www-data /opt/chatbot/backend/data
sudo chmod -R 755 /opt/chatbot/backend/data
```

### 擴展建議

#### 水平擴展
```yaml
# docker-compose.yml - 多後端實例
services:
  backend-1:
    # ... 配置
  backend-2:
    # ... 配置
  
  # Nginx 負載均衡
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
```

#### 垂直擴展
- 增加服務器 CPU/內存
- 優化數據庫配置
- 增加 Redis 緩存大小
- 使用 FAISS GPU 版本 (大規模數據)

#### CDN 集成
- 靜態資源托管到 CDN
- 配置 CloudFlare/AWS CloudFront
- 啟用圖片壓縮和優化

## 🔧 故障排除

### 開發環境問題

#### 問題 1: 端口已被佔用
**錯誤訊息**: `Address already in use` 或 `Port 3000/8001 is already in use`

**解決方案**:
```powershell
# 查找佔用端口的進程
netstat -ano | findstr :3000
netstat -ano | findstr :8001

# 終止進程 (PID 從上面命令獲取)
taskkill /PID <PID> /F

# 或更改端口
# 後端: 在啟動命令中指定 --port 8002
# 前端: 在 .env 中設置 PORT=3001
```

#### 問題 2: 虛擬環境未啟動
**錯誤訊息**: `ModuleNotFoundError: No module named 'fastapi'`

**解決方案**:
```powershell
# 啟動虛擬環境
cd C:\Users\MITAC\Documents\AI-CB
.\CBvenv\Scripts\Activate.ps1

# 驗證虛擬環境
python --version
pip list
```

#### 問題 3: 依賴安裝失敗
**解決方案**:
```powershell
# 更新 pip
python -m pip install --upgrade pip

# 清除緩存重新安裝
pip cache purge
pip install -r requirements.txt
```

#### 問題 4: 前端代理不工作
**解決方案**:
```powershell
# 1. 確認 package.json 中有 proxy 設置
# 2. 重啟前端服務
# 3. 檢查後端是否運行
curl http://localhost:8001/health
```

### RAG 系統問題

#### 問題 5: FAISS 索引損壞
**解決方案**:
```powershell
# 重置索引
cd backend
python scripts/reset_faiss.py
```

#### 問題 6: 文檔編碼錯誤
系統已支援多編碼檢測 (UTF-8, GBK, Big5)。如仍有問題，手動轉換文件為 UTF-8。

### 獲取幫助

1. 查看完整日誌: `backend/logs/app.log` 和 `backend/logs/security.log`
2. 查看文檔: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
3. 運行健康檢查: `curl http://localhost:8001/health`

## 📚 相關文檔

### 核心文檔
- 📖 [快速啟動指南](./QUICK-START.md) - 5 分鐘快速上手
- 🔐 [安全增強文檔](./docs/SECURITY_ENHANCEMENTS.md) - RSA、Token 黑名單詳解
- 🔑 [JWT 認證指南](./docs/JWT_Authentication_Guide.md) - JWT 認證系統

### 功能文檔
- 🧠 [RAG 系統說明書](./docs/RAG_系統說明書.md) - 混合 RAG 完整說明
- 📊 [RAG 系統改進說明](./docs/RAG_系統改進說明_20250930.md) - RAG 優化細節
- 🎯 [Agent 可見性功能](./docs/AGENT_VISIBILITY_FEATURE.md) - Agent 權限控制
- 🔄 [工作流重構總結](./docs/WORKFLOW_REFACTORING_SUMMARY.md) - 工作流系統

### API 與模型
- 📡 [LLM API 遷移快速參考](./LLM_API_MIGRATION_QUICKREF.md) - LLM API 使用
- 🤖 [模型列表快速參考](./docs/MODEL_LIST_QUICK_REF.md) - 模型管理功能
- 📋 [模型列表改進](./docs/MODEL_LIST_IMPROVEMENTS.md) - 模型列表詳解

### 安全與最佳實踐
- 🛡️ [安全指南](./Security-Guidelines_Traditional-Chinese.md) - 安全開發規範
- 🔒 [安全實施](./SECURITY-IMPLEMENTATION.md) - 安全功能實施
- 🐛 [安全修復](./security-fixes.md) - 安全問題修復記錄

### 故障排除
- 🔧 [故障排除](./TROUBLESHOOTING.md) - 常見問題解決
- 🔍 [管理員 API 故障排除](./TROUBLESHOOTING_ADMIN_API.md) - 管理功能問題
- 🏠 [本地開發設置](./LOCAL_DEVELOPMENT_SETUP.md) - 本地環境配置

## 🤝 貢獻指南

歡迎貢獻！請遵循以下步驟：

1. Fork 本專案
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

### 代碼風格
- **Python**: 遵循 PEP 8
- **JavaScript**: 使用 ESLint + Prettier
- **提交訊息**: 遵循 Conventional Commits

## 👨‍💻 作者

Scorpio-meow

## 🙏 致謝

- FastAPI 團隊
- LangChain 團隊  
- sentence-transformers 團隊
- Material-UI 團隊
- 所有開源貢獻者

## 📞 聯繫方式

- GitHub: [@Scorpio-meow](https://github.com/Scorpio-meow)
- 專案連結: [https://github.com/Scorpio-meow/AI-CB](https://github.com/Scorpio-meow/AI-CB)

---

<div align="center">
  <p>Made with ❤️ by Scorpio-meow</p>
  <p>⭐ 如果這個專案對你有幫助，請給個 Star！</p>
</div>
- 啟用圖片壓縮和優化