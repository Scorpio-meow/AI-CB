# AskMiao (AI ChatBot)

一個基於增強型混合 RAG（檢索增強生成）技術的智慧對話與多 Agent 協作系統。

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[快速開始](#快速開始) | [功能特色](#功能特色) | [技術架構](#技術架構) | [環境配置](#環境配置) | [API 文件](#api-文件) | [開發指南](#開發指南) | [部署說明](#部署說明) | [常見問題](#常見問題)

---

## 目錄

- [快速開始](#快速開始)
- [功能特色](#功能特色)
- [技術架構](#技術架構)
- [環境配置](#環境配置)
- [API 文件](#api-文件)
- [開發指南](#開發指南)
- [部署說明](#部署說明)
- [常見問題](#常見問題)
- [貢獻指南](#貢獻指南)
- [授權條款](#授權條款)

---

## 快速開始

### 環境要求

- Python：3.10 或更高版本
- Bun：推薦使用（或 Node.js 18.0 或更高版本）
- PostgreSQL：17.9 版本（開發與生產環境皆同）
- Redis：選用，推薦於生產環境中啟用以支援 Token 撤銷與快取功能

### 安裝與啟動步驟

#### 1. 複製專案倉庫

```bash
git clone https://github.com/Scorpio-meow/AI-CB.git
cd AI-CB
```

#### 2. 資料庫與快取服務設定 (Docker)

```bash
# 啟動 PostgreSQL 服務
docker run -d --name chatbot-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=chatbot \
  -p 7690:5432 \
  postgres:17.9

# 啟動 Redis 服務（選用，用於 Token 黑名單與快取）
docker run -d -p 7967:6379 --name chatbot-redis redis:latest
```

#### 3. 後端設定

```bash
# 進入後端目錄
cd backend

# 建立並啟用虛擬環境
python -m venv CBvenv
# Windows PowerShell 啟用：
.\CBvenv\Scripts\Activate.ps1
# Linux/macOS 啟用：
source CBvenv/bin/activate

# 安裝依賴項目
# 若需要使用 GPU 加速，請手動安裝對應版本的 PyTorch (以 CUDA 13.0 為例)：
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
pip install -r requirements.txt

# 複製並編輯環境變數設定檔
cp .env.example .env

# 初始化資料庫結構
python init_db.py

# (選用) 若需自舊版 SQLite 遷移資料至 PostgreSQL
python scripts/migrate_sqlite_to_postgres.py

# 啟動後端服務
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

#### 4. 前端設定 (首選 Bun)

```bash
# 進入前端目錄
cd ../frontend

# 使用 Bun 安裝依賴項目
bun install

# 啟動前端開發伺服器
bun run dev
```

*注意：若您的系統尚未安裝 Bun，亦可使用 npm 作為備用方案：*

```bash
# 使用 npm 安裝與啟動
npm install
npm run dev
```

### 驗證安裝狀態

- 後端 API 服務：[http://localhost:8001](http://localhost:8001)
- 前端開發頁面：[http://localhost:5173](http://localhost:5173)
- 互動式 API 文件 (Swagger UI)：[http://localhost:8001/docs](http://localhost:8001/docs)

您可使用以下指令進行後端健康檢查：

```bash
curl http://localhost:8001/health
# 預期回應: {"status":"healthy"}
```

---

## 功能特色

### 智慧對話系統
- 混合 RAG 檢索：結合向量搜尋（FAISS）與 BM25 關鍵字比對。
- 智慧重排序：使用 Cross-Encoder（bge-reranker-base 或 bge-reranker-v2-m3）提升檢索結果與查詢的相關性。
- 多模型支援：支援動態切換與配置多個主流的大型語言模型（LLM）端點，提供靈活的 API 路由。
- 對話管理：支援多個對話同時進行，並妥善保留歷史對話記錄。
- 即時通訊：基於 WebSocket 協議實現低延遲的實時對話與工作流狀態串流。

### 支援之大型語言模型 (LLM) 提供商
系統提供統一的呼叫接口，支援動態路由至以下提供商：
- Azure OpenAI：支援 v1 版本的 Azure OpenAI API，具備高穩定性與高可靠性。
- OpenAI API：支援 gpt-5.5、gpt-5.4、gpt-5.2、gpt-4o、gpt-4o-mini、o3、o3-mini、o1 等官方模型。
- Anthropic Claude：支援 claude-4-8-opus、claude-4-7-opus、claude-4-6-sonnet、claude-4-5-sonnet、claude-4-5-haiku、claude-5-fable。
- Google Gemini：透過 OpenAI 相容接口，支援 gemini-3.5-flash、gemini-3.1-flash-lite、gemini-3-pro、gemini-2.5-flash。
- Ollama (本地部署)：支援本地執行的 gemma4:26b、qwen3.6:27b、glm-5.2、laguna-xs-2.1 或其他開源模型作為預設或回退端點。

### 討論看板 (Discussion Board)
- 多 Agent 協作：以視覺化節點圖呈現多個 AI Agent 的討論流程與協作關係。
- React Flow 整合：直觀的拖拉式節點介面，便於調整與檢視工作流。
- 即時串流：Agent 的回覆內容採逐字即時顯示，提升使用者體驗。
- 標籤系統：可依標籤分類與篩選不同的討論主題。

### 安全與認證
- JWT 雙 Token 機制：Access Token（30 分鐘有效）搭配 Refresh Token（7 天有效）以維護連線安全。
- RSA 非對稱加密：使用 RSA-2048 簽章，適用於微服務與分散式架構。
- Token 黑名單：基於 Redis 實現的 Token 撤銷機制，確保登出安全。
- 靜默刷新：自動於背景更新 Access Token，提供無感知的安全體驗。
- 角色權限控制 (RBAC)：基於角色的細粒度權限管理，限制敏感操作。
- 速率限制 (Rate Limiting)：防止 API 遭惡意濫用（預設每分鐘 60 次）。

### 知識庫管理
- 多格式支援：可處理 PDF、TXT、DOCX 等多種常見文件格式。
- 串流上傳：支援大文件上傳（最大單檔 10MB）。
- 批次操作：支援單次批次上傳最多 10 個文件。
- 智慧分塊：使用 RecursiveCharacterTextSplitter 進行精準分塊（預設 300 字元，重疊 100 字元）。
- 混合索引：整合 FAISS 向量索引與 Whoosh 文字索引。
- 多編碼支援：自動檢測並處理 UTF-8、GBK、Big5 等多種編碼格式。

### Agent 工作流系統
- 自定義 Agent：用戶可根據需求創建專屬的 AI Agent。
- 可見性控制：支援公開或私有設定。
- 權限隔離：嚴格限制用戶僅能存取自身創建或公開發表的 Agent。
- 角色預設：系統內建多種專業角色範本，可快速套用。

### 後台管理
- 用戶管理：提供管理員完整的用戶 CRUD 操作介面。
- 對話監控：管理員可檢視所有用戶的對話歷史紀錄。
- 系統統計：提供系統使用量分析與硬體性能指標。
- 向量庫監控：即時掌握索引狀態、重建統計與檢索性能追蹤。

---

## 技術架構

### 後端技術棧

| 類別 | 技術組件 | 說明 |
|------|------|------|
| **Web 框架** | FastAPI 0.104+ | 高性能的非同步 Web 框架 |
| **ORM** | SQLAlchemy 2.0+ | 現代 Python SQL 工具包與物件關係對映器 |
| **AI/RAG 核心** | LangChain, Sentence-Transformers, FAISS, Whoosh | 用於向量檢索、文字檢索與 RAG 管道建立 |
| **LLM 路由** | OpenAI, Claude, Gemini, Azure OpenAI, Ollama | 統一客戶端，支援動態路由與模型切換 |
| **資料庫** | PostgreSQL 17.9 | 主要的關聯式資料庫 |
| **快取/儲存** | Redis | 用於 Token 黑名單與資料快取 |
| **安全性** | cryptography, python-jose, argon2-cffi | 密碼雜湊、非對稱加密與 JWT 處理 |
| **文件解析** | pypdf, python-docx, chardet, jieba | 文件內容提取、編碼偵測與中文分詞 |

### 前端技術棧

| 類別 | 技術組件 | 說明 |
|------|------|------|
| **核心框架** | React 19 | 用於建立使用者介面的 JavaScript 函式庫 |
| **UI 元件庫** | Material-UI (MUI) v7 | 現代化、響應式的元件庫 |
| **路由** | React Router v7 | 前端路由管理 |
| **HTTP 用戶端** | Axios | 承載 API 請求與攔截器設定 |
| **流程圖渲染** | React Flow | 用於 Discussions Board 的節點視覺化呈現 |
| **Markdown 渲染** | react-markdown, remark-gfm | 對話內容的 Markdown 與表格解析 |
| **建構工具** | Vite 7 | 極速的前端開發與建構工具 |
| **測試** | Vitest | 快速的前端單元測試框架 |

### RAG 系統架構圖

```mermaid
flowchart TD
    A["用戶查詢"] --> B["智慧檢索策略選擇<br/>(向量搜尋 / BM25 / 混合搜尋)"]
    B --> C["向量搜尋<br/>(FAISS)"]
    B --> D["BM25<br/>(Whoosh)"]
    B --> E["混合搜尋<br/>(融合)"]
    C --> F["Cross-Encoder 重新排序<br/>(BAAI/bge-reranker-base)"]
    D --> F
    E --> F
    F --> G["LLM 生成回答"]
    
    style A fill:#e1f5ff,stroke:#333,stroke-width:2px
    style B fill:#fff4e1,stroke:#333,stroke-width:2px
    style C fill:#e8f5e9,stroke:#333,stroke-width:2px
    style D fill:#e8f5e9,stroke:#333,stroke-width:2px
    style E fill:#e8f5e9,stroke:#333,stroke-width:2px
    style F fill:#ffe1f5,stroke:#333,stroke-width:2px
    style G fill:#e1ffe1,stroke:#333,stroke-width:2px
```

### 核心模型配置

- **嵌入模型 (Embedding Model)**：`BAAI/bge-small-zh-v1.5`（或多語言嵌入模型 `BAAI/bge-m3`）。
- **重排序模型 (Reranker Model)**：`BAAI/bge-reranker-base`（或 `BAAI/bge-reranker-v2-m3` 精準評估語意相關性）。
- **向量索引**：FAISS IndexFlatIP（基於內積相似度度量）。
- **BM25 搜尋**：Whoosh StandardAnalyzer 搭配 jieba 中文分詞器。

---

## 環境配置

### 後端環境變數 (backend/.env)

| 變數名稱 | 描述 | 預設值/範例 | 是否必填 |
|---|---|---|---|
| **LLM_API_BASE** | 本地 Ollama 服務或主要 LLM API 端點網址 | `http://localhost:5000` | 是 |
| **LLM_TIMEOUT** | LLM 請求超時時間（秒） | `120` | 否 |
| **AZURE_OPENAI_API_KEY** | Azure OpenAI API 金鑰 | `your_azure_key` | 否 |
| **AZURE_OPENAI_ENDPOINT** | Azure OpenAI 資源端點 URL | `https://your-resource.openai.azure.com` | 否 |
| **AZURE_OPENAI_DEPLOYMENT** | Azure OpenAI 部署模型名稱 | `gpt-4o` | 否 |
| **OPENAI_API_KEY** | OpenAI API 金鑰 | `your_openai_key` | 否 |
| **OPENAI_API_BASE** | OpenAI API 基礎路徑 | `https://api.openai.com/v1` | 否 |
| **ANTHROPIC_API_KEY** | Anthropic Claude API 金鑰 | `your_claude_key` | 否 |
| **ANTHROPIC_API_BASE** | Claude API 基礎路徑 | `https://api.anthropic.com` | 否 |
| **GEMINI_API_KEY** | Google Gemini API 金鑰 | `your_gemini_key` | 否 |
| **GEMINI_API_BASE** | Gemini API 基礎路徑 (OpenAI 相容) | `https://generativelanguage.googleapis.com` | 否 |
| **AVAILABLE_MODELS** | 前端對話介面可用模型清單 (以逗號分隔) | `gpt-5.5,claude-4-8-opus` | 否 |
| **ADMIN_API_KEY** | 管理員專屬的 API 金鑰 | `your_secure_admin_api_key` | 是 |
| **JWT_SECRET_KEY** | 用於簽署 JWT Token 的密鑰 | `your_jwt_secret_key` | 是 |
| **JWT_ALGORITHM** | 加密演算法（預設使用非對稱加密） | `RS256` | 否 |
| **ACCESS_TOKEN_EXPIRE_MINUTES** | Access Token 有效時間（分鐘） | `30` | 否 |
| **REFRESH_TOKEN_EXPIRE_DAYS** | Refresh Token 有效時間（天） | `7` | 否 |
| **ENVIRONMENT** | 運作環境模式（development / production） | `development` | 否 |
| **HOST** | 服務綁定主機位址 | `0.0.0.0` | 否 |
| **PORT** | 服務埠號 | `8001` | 否 |
| **DATABASE_URL** | PostgreSQL 連線字串 | `postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot` | 是 |
| **REDIS_HOST** | Redis 主機位址 | `localhost` | 否 |
| **REDIS_PORT** | Redis 埠號 | `7967` | 否 |
| **ENABLE_REDIS_CACHE** | 是否啟用 Redis 快取與 Token 黑名單 | `true` | 否 |
| **ALLOWED_ORIGINS** | 允許跨域請求 (CORS) 的來源網址列表 | `http://localhost:5173,http://127.0.0.1:5173` | 是 |
| **EMBEDDING_MODEL** | 向量嵌入模型名稱 | `BAAI/bge-small-zh-v1.5` | 否 |
| **RERANKER_MODEL** | 檢索重排序模型名稱 | `BAAI/bge-reranker-base` | 否 |
| **SIMILARITY_THRESHOLD** | 向量檢索相似度門檻值 | `0.30` | 否 |
| **TOP_K** | 初步向量檢索取回之分塊數量 | `30` | 否 |
| **RERANK_TOP_K** | 送入重排序模型之分塊數量上限 | `50` | 否 |
| **FINAL_K** | 重排序後最終保留並送入 LLM 的分塊數 | `8` | 否 |
| **HYBRID_ALPHA** | 向量檢索與關鍵字檢索權重比 (1.0 為純向量) | `0.75` | 否 |
| **CHUNK_SIZE** | 文件智慧分塊字元數 | `300` | 否 |
| **CHUNK_OVERLAP** | 相鄰分塊重疊字元數 | `100` | 否 |
| **MAX_FILE_SIZE_MB** | 限制上傳文件之最大大小 (MB) | `10` | 否 |
| **ENABLE_AUTO_REINDEX_TASK** | 是否啟用排程自動重建向量索引任務 | `1` | 否 |
| **REINDEX_HOURS** | 自動重建索引時間間隔（小時） | `24` | 否 |
| **RATE_LIMIT_ENABLED** | 是否啟用 API 速率限制 | `true` | 否 |
| **RATE_LIMIT_PER_MINUTE** | 每分鐘請求上限次數 | `60` | 否 |

### 前端環境變數 (frontend/.env)

| 變數名稱 | 描述 | 預設值/範例 | 是否必填 |
|---|---|---|---|
| **VITE_API_URL** | 後端 API 基礎路由地址 | `http://localhost:8001` | 是 |
| **VITE_WS_URL** | 後端 WebSocket 連線地址 | `ws://localhost:8001/api/workflow/ws` | 是 |
| **VITE_MODEL_POLL_INTERVAL_MS** | 模型狀態輪詢時間間隔 (毫秒) | `300000` | 否 |

---

## API 文件

本專案提供基於 OpenAPI 規範的交互式文件。您可在後端運行後，直接瀏覽 `http://localhost:8001/docs` 查看完整定義。

### 1. 身份認證模組

#### 用戶註冊
- **端點**：`POST /api/auth/register`
- **請求格式**：`application/json`
- **請求參數範例**：
  ```json
  {
    "username": "user123",
    "email": "user@example.com",
    "password": "SecurePass123!"
  }
  ```
- **主要回應**：
  - `200 OK`：註冊成功。
  - `400 Bad Request`：使用者名稱或電子郵件已存在。

#### 用戶登入
- **端點**：`POST /api/auth/login`
- **請求格式**：`application/json`
- **請求參數範例**：
  ```json
  {
    "username": "user123",
    "password": "SecurePass123!"
  }
  ```
- **主要回應**：
  - `200 OK`：返回 JWT access token 與過期時間。
  ```json
  {
    "access_token": "eyJhbGciOiJSUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
  }
  ```

#### 憑證刷新 (Silent Refresh)
- **端點**：`POST /api/auth/refresh`
- **請求格式**：無（從 Cookie 中自動讀取 `refresh_token`）
- **主要回應**：
  - `200 OK`：返回新的 `access_token`。

---

### 2. 對話功能模組

#### 發送對話訊息
- **端點**：`POST /api/chat/send`
- **請求標頭**：`Authorization: Bearer <access_token>`
- **請求格式**：`application/json`
- **請求參數範例**：
  ```json
  {
    "message": "請介紹一下 RAG 技術的優缺點。",
    "conversation_id": 123,
    "use_rag": true
  }
  ```
- **主要回應**：
  - `200 OK`：返回 AI 回應內容與使用的參考文獻資料來源。

#### WebSocket 即時雙向對話
- **端點**：`WS /ws/chat`
- **連線說明**：連接成功後，即可發送 JSON 格式資料進行流式對話。
- **發送資料格式**：
  ```json
  {
    "message": "您好，請協助我撰寫報告。",
    "conversation_id": 123
  }
  ```
- **接收資料格式**：
  ```json
  {
    "response": "這是一段流式的文字回應片段...",
    "done": false
  }
  ```

---

### 3. 文件與知識庫管理

#### 上傳文件
- **端點**：`POST /api/documents/upload`
- **請求標頭**：`Authorization: Bearer <access_token>`
- **請求格式**：`multipart/form-data`
- **參數**：`files`（支援多個檔案，單次上限 10 個檔案，單檔限制 <10MB）
- **主要回應**：
  - `200 OK`：返回各檔案上傳成功之狀態與指派的 ID。

#### 批次刪除文件
- **端點**：`POST /api/documents/bulk_delete`
- **請求標頭**：`Authorization: Bearer <access_token>`
- **請求格式**：`application/json`
- **請求參數範例**：
  ```json
  {
    "ids": [1, 2, 3]
  }
  ```

---

## 開發指南

### 專案結構樹

```text
AskMiao/
├── backend/                 # 後端服務主目錄
│   ├── app/                # 後端應用程式核心
│   │   ├── api/           # API 路由與控制器
│   │   ├── core/          # 系統配置、安全性與多 LLM 客戶端管理
│   │   ├── crud/          # 資料庫增刪查改操作
│   │   ├── models/        # SQLAlchemy 資料模型定義
│   │   ├── rag/           # RAG 核心檢索與重排模組
│   │   ├── schemas/       # Pydantic 驗證綱要
│   │   ├── services/      # 核心業務邏輯
│   │   ├── tasks/         # 背景排程任務
│   │   └── middleware.py  # 速率限制與安全中介軟體
│   ├── data/              # 向量索引與上傳文件儲存庫
│   ├── keys/              # RSA 非對稱金鑰對目錄
│   ├── logs/              # 系統執行日誌
│   ├── scripts/           # 維護與資料遷移工具腳本
│   ├── tests/             # 後端單元測試與整合測試
│   ├── main.py            # FastAPI 應用進入點
│   ├── init_db.py         # 初始化 PostgreSQL 資料庫結構
│   └── requirements.txt   # Python 依賴套件清單
│
└── frontend/               # 前端應用主目錄 (React 19)
    ├── src/               # 前端原始碼
    │   ├── components/   # 通用 UI 元件
    │   ├── contexts/     # 全域狀態管理 (Auth, Theme)
    │   ├── hooks/        # 自定義 React Hooks
    │   ├── pages/        # 頁面元件
    │   ├── services/     # API 請求封裝
    │   └── utils/        # 通用工具函式
    ├── vite.config.js     # Vite 建構設定檔
    └── package.json       # 前端依賴套件與指令配置
```

### 開發流程規範

1. **建立功能分支**：
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **本地開發與驗證**：
   - 後端：於 `backend/app/` 修改程式碼。
   - 前端：於 `frontend/src/` 修改元件，並優先以 `bun run dev` 進行本地熱重載測試。
3. **執行測試套件**：
   ```bash
   # 執行後端測試
   cd backend
   pytest

   # 執行前端測試
   cd ../frontend
   bun run test
   ```
4. **提交程式碼**：
   請遵循 Angular 規範撰寫 Commit Message（如：`feat: 增加對話歷史清空功能`）。

---

## 部署說明

### Docker Compose 容器化部署

本專案於 `backend/` 目錄下備有 `docker-compose.yml` 配置檔，可用於一鍵啟動後端、PostgreSQL 及 Redis。

```bash
cd backend
# 啟動所有容器服務（背景執行）
docker-compose up -d

# 查看容器運作日誌
docker-compose logs -f

# 停止並移除容器
docker-compose down
```

### 生產環境部署檢核清單

1. **環境變數調整**：
   - 將 `ENVIRONMENT` 變更為 `production`。
   - 將 `JWT_SECRET_KEY` 與 `ADMIN_API_KEY` 更換為極高強度的隨機字串。
   - 確認 `DATABASE_URL` 與 `REDIS_HOST` 指向生產環境資料庫伺服器。
   - 將 `ALLOWED_ORIGINS` 限制為正式對外服務的前端網域。
2. **傳輸安全**：
   - 強制啟用 HTTPS 加密傳輸，並在前端配置 Nginx 反向代理進行 SSL 憑證卸載。
3. **性能與並行優化**：
   - 後端使用 Uvicorn 或 Gunicorn 啟動多個 Worker 程序。
   - 啟用 PostgreSQL 連線池。
   - 前端靜態資源於建構後（`bun run build`）交由 CDN 或高效能 Nginx 進行分發。

---

## 常見問題

### Q: 如何手動將舊版 SQLite 資料移轉至 PostgreSQL？
我們在 `backend/scripts/` 中提供移轉指令，此腳本會自動讀取 SQLite 資料庫並寫入 PostgreSQL 中：
```bash
cd backend
python scripts/migrate_sqlite_to_postgres.py --source ./chatbot.db
```
可加上 `--dry-run` 參數進行預檢而不寫入資料庫：
```bash
python scripts/migrate_sqlite_to_postgres.py --dry-run
```

### Q: 如何強制手動重置 FAISS 向量索引？
雖然系統會定時（預設每 24 小時）自動重建，若需立即重置可執行：
```bash
cd backend
python scripts/reset_faiss.py
```

### Q: 模型的下載速度緩慢，有解決方案嗎？
在國內環境中下載 Hugging Face 模型時，可透過設定鏡像站以加速下載：
```powershell
# Windows PowerShell 設定方式
$env:HF_ENDPOINT = "https://hf-mirror.com"
```
```bash
# Linux/macOS 設定方式
export HF_ENDPOINT="https://hf-mirror.com"
```

### Q: 系統是否支援 GPU 硬體加速？
是的，如果您的硬體配有 NVIDIA 顯示卡，請依照您的 CUDA 版本安裝對應之 PyTorch，系統即會自動調用 GPU 資源進行向量化與重排序運算：
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

---

## 貢獻指南

我們非常歡迎各位提交 Pull Request 或回報 Issue！

1. Fork 本專案倉庫。
2. 建立您的 Feature 分支（`git checkout -b feature/AmazingFeature`）。
3. 提交您的修改（`git commit -m 'feat: add some AmazingFeature'`）。
4. 推送至遠端分支（`git push origin feature/AmazingFeature`）。
5. 建立一個新的 Pull Request。

請於送出前確保您的程式碼已通過全部測試項目、符合 PEP 8 與 ESLint 風格指南，且附帶合適的說明文件。

---

## 授權條款

本專案基於 MIT 授權條款進行授權，詳情請參閱 LICENSE 檔案。

---

**感謝您使用 AskMiao！**
如果您覺得本專案對您有所幫助，請給予我們一個 Star，這將是我們持續維護的最大動力！
