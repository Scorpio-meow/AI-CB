# AskMiao (AI ChatBot)

基於增強型混合 RAG（檢索增強生成）與 Agentic 自主研究架構的企業級智慧知識庫對話系統。

[繁體中文](README.md) | [English](README_en.md)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Vite-8.0-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Bun](https://img.shields.io/badge/Bun-1.0+-FBF0DF?style=flat&logo=bun&logoColor=black)](https://bun.sh/)
[![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[快速開始](#快速開始) | [核心功能特色](#核心功能特色) | [系統架構與設計](#系統架構與設計) | [專案目錄結構](#專案目錄結構) | [環境配置矩陣](#環境配置矩陣) | [文件導覽](#文件導覽) | [貢獻指南](#貢獻指南) | [授權條款](#授權條款)

---

## 快速開始

### 環境要求

| 組件名稱 | 最低版本要求　　　 | 建議工具與用途說明　　　　　　　　　　　　　　　　　　　 |
| ----------| --------------------| ----------------------------------------------------------|
| Python　 | 3.10 或更高版本　　| 後端 FastAPI 伺服器、RAG 向量索引與 Agentic 自主研究引擎 |
| Bun　　　| 1.0 或更高版本　　 | 前端優先使用之套件管理與建構打包工具　　　　　　　　　　 |
| SQLite　 | 3.x（Python 內建） | 預設關聯式資料庫，支援零依賴即時啟動　　　　　　　　　　 |

### 1. 複製專案倉庫

```bash
git clone https://github.com/Scorpio-meow/AskMiao.git
cd AskMiao
```

### 2. 後端服務設定與啟動

```bash
cd backend

# 建立並啟用 Python 虛擬環境
py -m venv .venv

# Windows PowerShell 啟用：
.\.venv\Scripts\Activate.ps1
# Linux/macOS 啟用：
source .venv/bin/activate

# 安裝後端依賴套件
pip install -r requirements.txt

# 建立環境變數檔，並至少填入 DATABASE_URL、ADMIN_API_KEY、JWT_SECRET_KEY
# 零依賴啟動請設定 DATABASE_URL=sqlite:///./chatbot.db
cp .env.example .env

# 初始化資料庫表格與管理員帳號
py init_db.py

# 啟動 FastAPI 開發伺服器 (Port 8001)
py main.py
```

選用：改用 PostgreSQL（`backend/docker-compose.yml`，對外 port 7690）

```bash
docker compose -f docker-compose.yml up -d
# .env 中設定
# DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot
```

### 3. 前端服務設定與啟動 (使用 Bun)

```bash
cd ../frontend

# 使用 Bun 安裝前端依賴項目
bun install

# 建立前端環境變數檔 (PORT=3001，/api 代理至後端 8001)
cp .env.example .env

# 啟動 Vite 前端開發伺服器 (Port 3001)
bun run dev
```

伺服器啟動後，開啟瀏覽器造訪 `http://localhost:3001` 即可進入 AskMiao 知識庫對話系統（後端 `ALLOWED_ORIGINS` 預設已允許此來源）。

---

## 核心功能特色

1. **Agentic RAG 多輪自主研究**：
   - 內建 ReAct 自主研究 Agent（`ResearchAgent`），支援原生工具調用（Native Tool Calling）。
   - 提供內部知識庫搜尋（`search_knowledge_base`）、外部即時聯網搜尋（`web_search`，支援 Ollama 與 DuckDuckGo 雙引擎備援）與深度網頁抓取（`web_fetch`）。
   - 前端即時呈現可折疊之結構化研究歷程（Research Trace Timeline）與可點擊跳轉之來源標籤（Source Badges）。

2. **多檔位模型推理程度（Reasoning Effort）選擇**：
   - 頂部導覽列支援切換五種推理深度檔位：`無 (None)`、`輕度 (Low)`、`標準 (Medium)`、`深度 (High)`、`極致 (X-High)`。
   - 完整支援 Azure OpenAI v1 與 OpenAI 推理模型（如 GPT-5 系列、o-series）。
   - 依微軟 Foundry 規範自動處理工具調用與推理相容性限制。

3. **模組化增強型混合 RAG 檢索引擎**：
   - 結合 FAISS 稠密向量搜尋（Dense Retrieval）與 Whoosh BM25 中文稀疏文字檢索（Sparse Retrieval）。
   - 搭配 Cross-Encoder（預設 `BAAI/bge-reranker-base`）進行加權重排序，確保知識檢索精準度。
   - 支援自動動態調整 Alpha 權重與 RAG 檢索評估指標（Hit Rate, MRR）。

4. **自訂 API 工具與 MCP 工具擴充**：
   - 貼上 OpenAPI / Swagger 規格（2.0 / 3.0 / 3.1）或 URL，勾選端點即可匯入為 Agent 可呼叫的工具，支援 bearer / api_key / basic 認證。
   - 以 stdio 或 HTTP 連接 MCP（Model Context Protocol）伺服器，自動探索工具並註冊為 `mcp_{server}_{tool}`。
   - `/tools` 頁面統一管理，`GET /api/chat/tools` 可觀測 Agent 目前可用之全部工具。

5. **多模型提供商彈性整合**：
   - 提供統一的 LLM 調用抽象層，支援 Azure OpenAI v1、OpenAI 官方 API、Anthropic Claude、Google Gemini 與本地 Ollama 模型動態切換與自動多模型清單拆分。

6. **企業級安全、SSRF 防護與雙層日誌脫敏**：
   - 採用 RSA-2048 非對稱密鑰簽署之 JWT Access Token 與 HttpOnly 安全 Cookie。
   - 所有模型或用戶提供之 URL（網頁抓取、OpenAPI 載入、自訂 API 執行）皆經 `ssrf_protection.py` 驗證，阻擋私有與內部網段。
   - 內建物件層級遞迴脫敏與字串正則遮罩防護（`security_logging.py`），嚴格防範密碼、Token 與機敏資料洩漏至系統日誌。

---

## 系統架構與設計

```mermaid
flowchart TB
    subgraph Client ["前端應用層 (React 19 + TypeScript + Vite 8 + Bun)"]
        UI["Chat 對話介面 (CSS Modules + 自製 UI Kit)"]
        TraceView["研究歷程摺疊卡片 (ResearchTraceBlock)"]
        ToolsView["工具管理 (/tools, AiTools)"]
        DocManage["知識庫文件管理 (Documents)"]
        AdminView["系統管理後台 (AdminDashboard)"]
    end

    subgraph Backend ["後端服務層 (FastAPI + Python 3.10+)"]
        Middleware["中介軟體 (SecurityHeaders / RateLimit / CORS)"]
        AuthService["JWT 認證服務 (RSA-2048, /api/auth)"]
        ChatAPI["對話 SSE 端點 (/api/chat)"]
        DocAPI["文件上傳與索引端點 (/api/documents)"]
        ToolsAPI["自訂 API 工具 (/api/api-tools)"]
        McpAPI["MCP 伺服器 (/api/mcp)"]

        subgraph AgenticRAG ["Agentic RAG 核心管線"]
            Agent["自主研究 Agent (ResearchAgent)"]
            ToolRegistry["工具註冊中心 (ResearchToolRegistry)"]
            HybridRetriever["混合檢索器 (FAISS + BM25 + Cross-Encoder)"]
            LLMClient["統一 LLM 客戶端 (Azure / OpenAI / Claude / Gemini / Ollama)"]
        end
        SSRF["SSRF 出站防護 (ssrf_protection.py)"]
    end

    subgraph Storage ["資料與索引儲存層"]
        SQLiteDB[(SQLite 預設 / PostgreSQL 選用)]
        FAISSStore["FAISS 向量索引庫 (faiss_index.bin)"]
        BM25Store["Whoosh BM25 關鍵字索引目錄"]
        DocUploads["文件儲存目錄 (data/uploads)"]
    end

    UI & TraceView & ToolsView & DocManage & AdminView --> Middleware
    Middleware --> AuthService & ChatAPI & DocAPI & ToolsAPI & McpAPI

    ChatAPI --> Agent
    Agent --> ToolRegistry
    ToolRegistry --> HybridRetriever
    ToolRegistry -.-> |聯網搜尋| DuckDuckGo["DuckDuckGo / Ollama Web Search"]
    ToolRegistry -.-> |網頁深度抓取| WebContent["外部網頁內容 (HTTP Fetch)"]
    ToolRegistry -.-> |custom_api_tools| ExtApi["自訂 REST API"]
    ToolRegistry -.-> |mcp_servers| McpSrv["MCP 伺服器 (stdio / http)"]
    ToolRegistry --> SSRF

    Agent --> LLMClient
    HybridRetriever --> FAISSStore
    HybridRetriever --> BM25Store
    DocAPI --> DocUploads
    AuthService & ChatAPI & ToolsAPI & McpAPI --> SQLiteDB
```

---

## 專案目錄結構

```text
AskMiao/
├── backend/                        # 後端 FastAPI 專案
│   ├── app/
│   │   ├── api/                    # 路由端點 (auth, chat, documents, admin, api_tools, mcp, tags)
│   │   ├── core/                   # 核心設定、安全認證、日誌脫敏與 LLM 客戶端
│   │   │   ├── config.py           # 系統全域環境變數配置 (唯一真相來源)
│   │   │   ├── lifespan.py         # 啟動 / 關閉流程與背景任務
│   │   │   ├── jwt_auth.py         # RSA-2048 JWT 簽章與驗證
│   │   │   ├── redis_client.py     # TokenBlacklist (單程序記憶體實作)
│   │   │   ├── llm_client.py       # 多提供商 LLM 統一調用層
│   │   │   ├── ssrf_protection.py  # 出站 URL SSRF 驗證
│   │   │   └── security_logging.py # 敏感資料雙層遮罩日誌系統
│   │   ├── middleware.py           # SecurityHeaders / RateLimit / CORS
│   │   ├── models/                 # SQLAlchemy ORM 與 Pydantic 驗證模型
│   │   ├── rag/                    # 模組化 RAG 與 Agentic 研究核心
│   │   │   ├── agent.py            # ReAct 自主研究 Agent
│   │   │   ├── tools.py            # 內建工具 + 自訂 API + MCP 工具聚合
│   │   │   ├── pipeline.py         # RAG 執行管線與上下文組裝
│   │   │   ├── contextual_rag.py   # HybridContextualRAG 門面模組
│   │   │   ├── evaluator.py        # 檢索評估與自動 Alpha 調優
│   │   │   ├── indices/            # FAISS 與 BM25 索引管理模組
│   │   │   └── retrievers/         # 混合檢索與 Cross-Encoder 重排序器
│   │   ├── services/               # 業務邏輯 (chat, document_processor, openapi_parser, mcp_service)
│   │   └── tasks/                  # 背景排程任務 (定時索引重建、上傳監控)
│   ├── tests/                      # pytest 測試 (agentic, api_tools, mcp, openapi, rag, ssrf)
│   ├── docker-compose.yml          # 選用 PostgreSQL 17.9 (host port 7690)
│   ├── main.py                     # FastAPI 應用程式主進入點
│   ├── init_db.py                  # 資料庫初始化與預設管理員建立腳本
│   └── requirements.txt            # Python 依賴清單
├── frontend/                       # 前端 React 19 + TypeScript + Vite 8 專案
│   ├── src/
│   │   ├── pages/                  # 前端頁面元件
│   │   │   ├── Chat/               # Chat 模組 (index.tsx, MessageItem, TraceBlock, SourceBadges, Header)
│   │   │   ├── AiTools.jsx         # 自訂 API 工具與 MCP 管理 (/tools)
│   │   │   ├── Documents.jsx       # 知識庫文件上傳與管理頁面
│   │   │   ├── AdminDashboard.jsx  # 系統管理後台
│   │   │   ├── LoginPage.jsx / RegisterPage.jsx
│   │   │   └── ProfilePage.jsx     # 個人資料頁面
│   │   ├── components/ui/          # 自製 UI 元件庫 (CSS Modules + tokens.css)
│   │   ├── hooks/                  # React 自訂 Hooks (useChat, useAuth, useDocuments)
│   │   ├── services/               # Axios API 請求封裝與 Token 攔截器
│   │   └── styles/tokens.css       # 設計代幣
│   ├── package.json                # 前端專案設定 (使用 Bun 管理)
│   └── vite.config.js              # Vite 建構配置 (/api 代理)
├── docs/                           # 詳細系統規格與架構文件
│   ├── api.md / api_en.md          # API 參考文件
│   ├── architecture.md / _en.md    # 系統架構與設計
│   └── adr/                        # 架構決策紀錄 (ADR-0001, ADR-0002)
├── CLAUDE.md                       # AI 助手專案指引 (指令、慣例、陷阱)
├── llms.txt / llms_en.txt          # AI 友善結構索引
├── CHANGELOG.md / CHANGELOG_en.md  # 版本變更紀錄
└── LICENSE                         # MIT 授權條款
```

---

## 環境配置矩陣

### 後端環境變數 (`backend/.env`)

預設值以 `backend/app/core/config.py` 為準；`backend/.env.example` 提供的範例值可能與程式碼預設不同（例如 `LLM_API_BASE`、`CHUNK_SIZE`），設定時請以自身環境為主。

| 變數名稱 | 描述 | `config.py` 預設值 | 必填 |
|---|---|---|---|
| `DATABASE_URL` | 資料庫連線字串；零依賴請用 `sqlite:///./chatbot.db`，PostgreSQL 範例 `postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot` | 無（必填） | 是 |
| `JWT_SECRET_KEY` | JWT 簽署金鑰（RS256 金鑰載入失敗時開發環境降級為 HS256 使用） | 無（必填） | 是 |
| `ADMIN_API_KEY` | 系統管理員 API 金鑰 | 無（必填） | 是 |
| `LLM_API_BASE` | 本地 Ollama 或相容服務端點 URL（`.env.example` 為 `http://localhost:11434`） | `http://localhost:5000` | 否 |
| `MODEL_NAME` | 預設模型名稱 | 無 | 否 |
| `AVAILABLE_MODELS` | 逗號分隔之可用模型清單 | 無 | 否 |
| `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI v1 設定（部署名稱支援逗號分隔多模型） | 無 | 否 |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | 其他供應商金鑰 | 無 | 否 |
| `ENABLE_WEB_SEARCH` | 是否啟用 Agent 聯網搜尋工具 | `true` | 否 |
| `AGENT_MAX_TURNS` | Agent 最大工具調用輪數（未設定則由 Agent 內建上限決定） | 無 | 否 |
| `EMBEDDING_MODEL` | 向量嵌入模型 | `BAAI/bge-small-zh-v1.5` | 否 |
| `RERANKER_MODEL` | Cross-Encoder 重排序模型 | `BAAI/bge-reranker-base` | 否 |
| `HYBRID_ALPHA` / `TOP_K` / `RERANK_TOP_K` / `FINAL_K` | 混合檢索權重與召回數 | `0.75` / `30` / `50` / `8` | 否 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 文件切塊大小與重疊（`.env.example` 為 300 / 100） | `800` / `150` | 否 |
| `FORCE_CPU` / `USE_FAISS_GPU` | 推論裝置設定 | `true` / `false` | 否 |
| `ALLOWED_ORIGINS` | CORS 白名單（逗號分隔） | `http://localhost:3001,...` | 否 |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_PER_MINUTE` | 速率限制 | `true` / `60` | 否 |
| `EXTERNAL_TAGS_URL` | `/api/external-tags` 代理之遠端模型清單 URL | 無 | 否 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | Token 有效期 | `30` / `7` | 否 |
| `ENVIRONMENT` | `development` / `production`（生產環境強制 RSA 金鑰） | `development` | 否 |

### 前端環境變數 (`frontend/.env`)

| 變數名稱 | 描述 | 預設值 | 必填 |
|---|---|---|---|
| `PORT` | Vite 開發伺服器埠號 | `3001`（未設定時為 3000） | 否 |
| `VITE_API_BASE` | Vite `/api` 代理目標 | `http://localhost:8001` | 否 |
| `VITE_API_URL` | 後端伺服器絕對端點 (若跨域直連) | `http://localhost:8001` | 否 |

---

## 文件導覽

- [API 參考文件](./docs/api.md) — 完整 RESTful / SSE 端點、請求回應 JSON 規格與參數說明
- [系統架構與設計文件](./docs/architecture.md) — 分層架構、混合檢索、認證、Agentic 迴圈、工具擴充、安全、資料模型與部署模式
- [架構決策紀錄 (ADR)](./docs/adr/README.md) — ADR-0001 混合 RAG 與安全；[ADR-0002](./docs/adr/0002-platform-hardening-and-tool-extension-roadmap.md) 2.x 平台強化路線圖
- [AI 助手專案指引](./CLAUDE.md) — 建置、測試指令、慣例與常見陷阱
- [AI 友善結構導覽](./llms.txt) — 專供 AI Agent 與 LLM 讀取之結構導覽與約束
- [版本變更紀錄](./CHANGELOG.md) — 系統版本演進歷史

---

## 貢獻指南

歡迎參與 AskMiao 的開發與改進！請遵循以下流程：

1. Fork 本專案倉庫並建立您的功能分支 (`git checkout -b feature/amazing-feature`)。
2. 確保程式碼通過前端與後端型別檢查及測試：
   - 後端測試：`cd backend && pytest`
   - 前端型別檢查與測試：`bun x tsc --noEmit`、`bun run lint`、`bun run test`、`bun run build`
   - 修改 `docs/`、`README`、`llms.txt` 時請同步更新對應之 `_en` 英文版本。
3. 以 Conventional Commits 提交變更 (`git commit -m 'feat(tools): 新增 ...'`)。
4. 推送至分支 (`git push origin feature/amazing-feature`)。
5. 開啟 Pull Request 並詳細說明變更內容。

---

## 授權條款

本專案基於 MIT 授權條款發行。詳情請參閱 [LICENSE](LICENSE) 檔案。