# AskMiao 系統架構與設計文件

[繁體中文](architecture.md) | [English](architecture_en.md)

> 本文件說明 AskMiao 2.x 的實際系統架構：分層模組關係、增強型混合 RAG 檢索流程、RSA-2048 雙 Token 認證與記憶體黑名單、Agentic 自主研究迴圈、工具擴充子系統（OpenAPI 匯入與 MCP）、安全防護總覽、資料模型與部署模式。內容以程式碼為準（`backend/main.py`、`backend/app/core/config.py` 等），若文件與程式碼不符，請以程式碼為準並提交修正。

---

## 1. 系統整體分層架構圖

AskMiao 採用前後端分離與模組化架構。前端由 React 19 + TypeScript + Vite 8 + Bun 驅動，樣式採 CSS Modules 與設計代幣（`src/styles/tokens.css`）搭配自製 UI 元件庫（`src/components/ui/`），**不依賴 MUI**。後端由 FastAPI（`backend/main.py`）提供 RESTful API 與 SSE 串流，預設使用 SQLite 零依賴啟動，可選用 PostgreSQL；向量與關鍵字索引以本機檔案（FAISS、Whoosh）儲存。

```mermaid
flowchart TB
    subgraph Client ["前端應用層 (React 19 + TypeScript + Vite 8 + Bun)"]
        Router["App.jsx 路由 (PrivateRoute / AdminRoute)"]
        ChatPage["Chat/index.tsx 對話頁 (模型 / 推理程度 / Research Trace)"]
        ToolsPage["AiTools.jsx (/tools) 自訂 API 工具與 MCP 管理"]
        DocsPage["Documents.jsx (/documents, 管理員)"]
        AdminPage["AdminDashboard.jsx (/admin)"]
        UIKit["components/ui + CSS Modules + tokens.css"]
    end

    subgraph Middleware ["中介軟體層 (app/middleware.py)"]
        SecHeaders["SecurityHeadersMiddleware"]
        RateLimit["RateLimitMiddleware (RATE_LIMIT_ENABLED)"]
        CORS["CORSMiddleware (ALLOWED_ORIGINS 白名單)"]
    end

    subgraph Backend ["FastAPI 後端 (backend/main.py)"]
        AuthAPI["auth.py /api/auth"]
        ChatAPI["chat.py /api/chat (SSE 串流)"]
        DocAPI["documents.py /api/documents"]
        AdminAPI["admin.py /api/admin"]
        ApiToolsAPI["api_tools.py /api/api-tools"]
        McpAPI["mcp.py /api/mcp"]
        TagsAPI["tags.py /api/tags, /api/external-tags"]

        subgraph Lifespan ["core/lifespan.py 生命週期"]
            CreateTables["create_tables()"]
            RagSingleton["get_rag_system() 單例 (core/rag_manager.py)"]
            UploadsWatcher["tasks/uploads_watcher.py"]
            IndexRebuilder["tasks/index_rebuilder.py"]
        end

        subgraph RAG ["Agentic RAG 核心 (app/rag/)"]
            Facade["contextual_rag.py 門面"]
            Pipeline["pipeline.py 執行管線"]
            Agent["agent.py ResearchAgent"]
            Registry["tools.py ResearchToolRegistry"]
            Hybrid["retrievers/hybrid.py 混合檢索 + Cross-Encoder"]
        end

        LLMClient["core/llm_client.py 統一 LLM 客戶端"]
    end

    subgraph Storage ["儲存層"]
        DB[(SQLite 預設 / PostgreSQL 選用)]
        FAISS["FAISS 向量索引 (data/faiss_index.bin)"]
        Whoosh["Whoosh BM25 索引 (data/bm25_index)"]
        Uploads["data/uploads 原始文件"]
        HFCache["data/hf_home 模型快取"]
    end

    subgraph External ["外部系統"]
        LLMs["Azure OpenAI v1 / OpenAI / Anthropic / Gemini / Ollama"]
        WebSearch["DuckDuckGo / Ollama Web Search"]
        McpServers["MCP 伺服器 (stdio / http)"]
        RestApis["自訂 REST API (OpenAPI 匯入)"]
    end

    Router --> ChatPage & ToolsPage & DocsPage & AdminPage
    ChatPage & ToolsPage & DocsPage & AdminPage --> UIKit
    Client --> SecHeaders --> RateLimit --> CORS
    CORS --> AuthAPI & ChatAPI & DocAPI & AdminAPI & ApiToolsAPI & McpAPI & TagsAPI
    ChatAPI --> Facade --> Pipeline --> Agent --> Registry
    Registry --> Hybrid
    Agent --> LLMClient --> LLMs
    Registry -.-> WebSearch
    Registry -.-> McpServers
    Registry -.-> RestApis
    Hybrid --> FAISS & Whoosh
    DocAPI --> Uploads
    DocAPI --> Facade
    AuthAPI & ChatAPI & DocAPI & AdminAPI & ApiToolsAPI & McpAPI --> DB
    RagSingleton --> Facade
    Facade --> HFCache
```

### 分層職責摘要

| 層級 | 主要模組 | 職責 |
|---|---|---|
| 前端 | `frontend/src/App.jsx`、`pages/*`、`components/ui/*`、`hooks/*`、`services/api.ts` | 路由守衛、對話與研究歷程呈現、工具與文件管理介面、Axios 攔截器與 Token 刷新 |
| 中介軟體 | `backend/app/middleware.py`、`core/security.py` | 安全標頭、速率限制、CORS 白名單 |
| API 路由 | `backend/app/api/*.py` | 七組路由，統一由 `main.py` 掛載 |
| 核心服務 | `core/jwt_auth.py`、`core/llm_client.py`、`core/security_logging.py`、`core/ssrf_protection.py` | 認證、LLM 供應商抽象、日誌脫敏、出站防護 |
| RAG 引擎 | `app/rag/*` | 檢索、重排序、Agent 迴圈、工具聚合 |
| 業務服務 | `services/chat_service.py`、`document_processor.py`、`openapi_parser.py`、`mcp_service.py` | 對話持久化、文件解析、OpenAPI 解析、MCP 客戶端 |
| 背景任務 | `tasks/uploads_watcher.py`、`tasks/index_rebuilder.py` | 上傳目錄清理、定時索引重建 |

---

## 2. 增強型混合 RAG 檢索與重排序管道

系統以密集向量搜尋（Dense）與稀疏關鍵字搜尋（Sparse）並行檢索，經歸一化融合後送入 Cross-Encoder 重排序。所有參數集中於 `backend/app/core/config.py`，可由 `.env` 覆寫。

```mermaid
flowchart LR
    Query["用戶查詢 (Query)"] --> Strategy{"retrievers/hybrid.py\nsmart_search 策略調配"}

    subgraph ParallelRetrieval ["並行雙軌檢索"]
        Strategy -->|向量比對| FAISS["indices/vector_store.py\nFAISS 內積搜尋 (bge-small-zh-v1.5, 384 維)"]
        Strategy -->|關鍵字比對| BM25["indices/bm25_store.py\nWhoosh BM25 (tokenizers.py Jieba 分詞)"]
    end

    FAISS --> Merge["歸一化分數融合\n(HYBRID_ALPHA, NORMALIZATION)"]
    BM25 --> Merge
    Merge --> Reranker["Cross-Encoder 重排序\n(RERANKER_MODEL, RERANK_WEIGHT)"]
    Reranker --> TopK["FINAL_K 篩選 + FINAL_THRESHOLD 過濾"]
    TopK --> Context["pipeline.py 上下文組裝"]
```

### 檢索參數（`config.py` 預設值）

| 參數 | 預設 | 說明 |
|---|---|---|
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 800 / 150 | `RecursiveCharacterTextSplitter` 切塊字元數與重疊 |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 384 維向量嵌入模型 |
| `RERANKER_MODEL` | `BAAI/bge-reranker-base` | Cross-Encoder 重排序模型 |
| `TOP_K` / `RERANK_TOP_K` / `FINAL_K` | 30 / 50 / 8 | 初檢召回、重排候選、最終輸出片段數 |
| `HYBRID_ALPHA` | 0.75 | 向量分數權重（1 - alpha 為 BM25 權重） |
| `RERANK_WEIGHT` | 0.85 | 重排序分數與融合分數的加權比例 |
| `SIMILARITY_THRESHOLD` / `FINAL_THRESHOLD` | 0.30 / 0.15 | 初檢與最終過濾閾值 |
| `NORMALIZATION` | `max` | 分數歸一化方式 |
| `FORCE_CPU` / `USE_FAISS_GPU` | `true` / `false` | 預設 CPU 推論；GPU 為選配 |

> 注意：`backend/.env.example` 提供的 `CHUNK_SIZE=300`、`CHUNK_OVERLAP=100` 會覆寫上述預設，兩者皆為有效組態；`docs/adr/0002` 的設定治理項目將統一來源。

`evaluator.py` 提供 Hit-Rate / MRR 評估與自動 Alpha 調優；`indices/` 內的索引檔案由 `tasks/index_rebuilder.py` 依 `REINDEX_HOURS` 定時重建。

---

## 3. RSA-2048 雙 Token 認證與記憶體黑名單

系統採用 Access Token（預設 30 分鐘，HTTP Header 傳輸）與 Refresh Token（預設 7 天，HttpOnly Cookie）雙令牌機制，由 `core/jwt_auth.py` 以 RS256 簽署（`core/rsa_keys.py` 載入金鑰；開發環境載入失敗時降級為 HS256 並記錄警告，生產環境則直接拋錯）。

**撤銷機制**：`core/redis_client.py` 中的 `TokenBlacklist` 目前為**單程序記憶體實作**（class-level dict + `threading.Lock`，惰性清理過期項目），`init_redis` / `get_redis` / `close_redis` 僅為相容 stub。登出時 `revoke_token()` 會把 Access Token 與 Refresh Token 的**完整字串**寫入黑名單，有效期取自 Token 的 `exp`。

```mermaid
sequenceDiagram
    autonumber
    actor Browser as 瀏覽器 / 前端
    participant Auth as api/auth.py
    participant JWT as core/jwt_auth.py
    participant BL as TokenBlacklist (記憶體)
    participant DB as SQLite / PostgreSQL

    Browser->>Auth: POST /api/auth/login (username, password)
    Auth->>DB: 查詢用戶並驗證 argon2 雜湊
    DB-->>Auth: 驗證通過
    Auth->>JWT: create_token_pair()
    JWT-->>Auth: access_token (30m) + refresh_token (7d)
    Auth-->>Browser: JSON access_token + Set-Cookie refresh_token (HttpOnly)

    Browser->>Auth: GET /api/auth/me (Authorization: Bearer)
    Auth->>JWT: verify_token()
    JWT->>BL: is_blacklisted(token)?
    BL-->>JWT: 否
    JWT-->>Auth: payload
    Auth-->>Browser: UserProfile

    Browser->>Auth: POST /api/auth/refresh (Cookie)
    Auth->>JWT: verify_refresh_token()
    JWT-->>Auth: 新 access_token
    Auth-->>Browser: Token

    Browser->>Auth: POST /api/auth/logout
    Auth->>JWT: revoke_token(access) / revoke_token(refresh)
    JWT->>BL: add_token(token, expires_in)
    Auth-->>Browser: 清除 Cookie，回傳登出成功
```

### 已知限制

- 黑名單存在於單一 Python 程序記憶體中：多 worker（`uvicorn --workers N`）或重啟後，已撤銷的 Token 在其他程序中仍可通過驗證，直到自然過期。
- 黑名單儲存整段 Token 而非 JTI，記憶體佔用較高。
- 上述兩點由 [ADR-0002](./adr/0002-platform-hardening-and-tool-extension-roadmap.md) 規劃可插拔黑名單後端解決；ADR-0001 中的 Redis 敘述已不適用。

---

## 4. Agentic RAG 自主研究與多輪工具調用管線

`POST /api/chat/send` 以 **Server-Sent Events** 串流回應。`contextual_rag.py` 門面呼叫 `pipeline.py`，再由 `agent.py` 的 `ResearchAgent.stream_research()` 以 ReAct 模式進行多輪 Native Tool Calling；工具規格由 `tools.py` 的 `ResearchToolRegistry.get_tool_definitions()` 動態聚合三種來源。

```mermaid
flowchart LR
    Send["POST /api/chat/send\n(content, model_name, reasoning_effort, attachments)"] --> Facade["contextual_rag.py\ngenerate_response_stream"]
    Facade --> Pipeline["pipeline.py"]
    Pipeline --> Agent["agent.py ResearchAgent\nstream_research(max_turns=AGENT_MAX_TURNS)"]

    subgraph Registry ["tools.py ResearchToolRegistry.get_tool_definitions()"]
        Builtin["內建工具\nsearch_knowledge_base\nfilter_and_count_records\nweb_search\nweb_fetch"]
        Custom["custom_api_tools 表\n(is_enabled=true)"]
        Mcp["mcp_servers.discovered_tools\n→ mcp_{server}_{tool}"]
    end

    Agent -->|tool_calls| Registry
    Registry -->|"execute_tool(name, args)"| Exec{"分派"}
    Exec -->|內建| Hybrid["retrievers/hybrid.py\n或 DuckDuckGo / Ollama / safe_fetch_text"]
    Exec -->|mcp_*| McpExec["McpManager.execute_mcp_tool"]
    Exec -->|其他名稱| HttpExec["api_tools.execute_http_api_tool"]
    Hybrid & McpExec & HttpExec -->|觀察結果| Agent
    Agent --> LLM["core/llm_client.py\n(reasoning_effort 透傳)"]
    Agent -->|SSE 事件| Events["start → step_start / step_end → token → sources → done"]
```

### 自主研究核心機制

1. **動態工具描述**：`_generate_knowledge_base_description()` 依目前索引內容產生 `search_knowledge_base` 的描述，讓模型知道知識庫涵蓋哪些文件。
2. **結構化統計工具**：`filter_and_count_records` 針對日期、作者、關鍵字與指定文件做精確計數與清單，避免模型以估算回答「總共幾筆」。
3. **研究歷程（Research Trace）**：每輪工具呼叫的步驟、參數、輸出摘要與耗時以 `step_start` / `step_end` 事件即時推送，並在 `done` 事件與 `messages.context_used` 中持久化。
4. **來源標籤（Sources Detail）**：內部片段與外部網址統一為 `sources_detail`，前端 `SourceBadges.tsx` 提供點擊跳轉。
5. **推理程度（Reasoning Effort）**：`none` / `low` / `medium` / `high` / `xhigh` 透傳至 Azure OpenAI v1 與 OpenAI 推理模型，並依 Foundry 規範處理工具呼叫相容性。

---

## 5. 工具擴充子系統（OpenAPI 匯入與 MCP）

2.x 新增兩條把外部能力註冊為 Agent 工具的路徑，前端統一於 `/tools`（`pages/AiTools.jsx`）管理。

```mermaid
flowchart LR
    subgraph OpenAPI ["路徑 A：自訂 REST API 工具 (api/api_tools.py)"]
        ParseSpec["POST /api/api-tools/parse-spec\n(URL 或 JSON/YAML 內容)"] --> Parser["services/openapi_parser.py\nOAS 2.0 / 3.0 / 3.1, $ref 解析"]
        Parser --> Pick["前端勾選端點"]
        Pick --> Import["POST /api/api-tools/import\n(global_base_url / auth / headers)"]
        Import --> CustomTable[("custom_api_tools")]
        CustomTable --> HttpExec["execute_http_api_tool\nPath / Query / Header / Body 組裝\nbearer / api_key / basic 認證"]
    end

    subgraph MCP ["路徑 B：MCP 伺服器 (api/mcp.py)"]
        Presets["GET /api/mcp/presets"] --> Create["POST /api/mcp/servers\n(transport: stdio | http)"]
        Create --> Client["services/mcp_service.py\nMcpStdioClient / McpHttpClient\nJSON-RPC initialize → tools/list"]
        Client --> Discover["POST /servers/{id}/discover\n寫回 discovered_tools / status"]
        Discover --> McpTable[("mcp_servers")]
        McpTable --> McpExec["McpManager.execute_mcp_tool\n(tools/call)"]
    end

    CustomTable & McpTable --> Registry["tools.py ResearchToolRegistry\nget_tool_definitions() 聚合"]
    Registry --> ChatTools["GET /api/chat/tools\n(觀測目前啟用工具)"]
    Registry --> Agent["ResearchAgent"]
    HttpExec & Client -.->|出站前| SSRF["core/ssrf_protection.py"]
```

### 設計重點

- **命名規則**：自訂 API 工具以 `custom_api_tools.name` 直接作為 function name；MCP 工具以 `mcp_{server_name}_{tool_name}` 命名，`execute_tool` 依前綴分派。
- **認證與位置**：`auth_type`（`none` / `bearer` / `api_key` / `basic`）與 `param_locations`（path / query / header / body）皆由匯入時解析寫入，執行期不需再讀取原始規格。
- **測試端點**：`POST /api/api-tools/{id}/test` 與 `POST /api/mcp/servers/{id}/tools/{name}/test` 允許在不經過 Agent 的情況下驗證工具。
- **已知技術債**：三種來源的合併與分派邏輯集中在 `tools.py` 的條件分支中，[ADR-0002](./adr/0002-platform-hardening-and-tool-extension-roadmap.md) 規劃抽象為 `ToolProvider` 介面。

---

## 6. 安全防護總覽

```mermaid
flowchart TB
    subgraph Transport ["傳輸層"]
        H["SecurityHeadersMiddleware"]
        R["RateLimitMiddleware (RATE_LIMIT_PER_MINUTE)"]
        C["CORS 白名單 (ALLOWED_ORIGINS, DEVTUNNEL_URL)"]
    end
    subgraph AuthLayer ["認證層"]
        J["RS256 JWT + HttpOnly Refresh Cookie"]
        B["TokenBlacklist (記憶體)"]
        A["get_current_admin_user / ADMIN_API_KEY"]
    end
    subgraph Input ["輸入層"]
        V["core/input_validator.py 檔名與 URL 驗證"]
        I["core/intrusion_detection.py"]
    end
    subgraph Egress ["出站層 (SSRF)"]
        S["core/ssrf_protection.py\nvalidate_url_ssrf / safe_fetch_text\n拒絕私有、loopback、link-local IP；DNS 解析後再檢查"]
    end
    subgraph Logging ["日誌層"]
        L["core/security_logging.py 雙層脫敏 → [REDACTED]"]
        AU["core/audit_logger.py / security_monitor.py"]
    end
    Transport --> AuthLayer --> Input --> Egress --> Logging
```

### 出站 SSRF 防護套用點

| 呼叫點 | 檔案 |
|---|---|
| Agent `web_fetch` 工具 | `backend/app/rag/tools.py` |
| OpenAPI 規格由 URL 載入 | `backend/app/services/openapi_parser.py` |
| 自訂 API 工具執行前 | `backend/app/api/api_tools.py` |
| 通用 URL 驗證 | `backend/app/core/input_validator.py` |

### 敏感資料雙層脫敏（`core/security_logging.py`）

1. **物件層級遞迴脫敏 `sanitize_sensitive_data`**：遍歷字典與列表，匹配 `password`、`token`、`secret`、`authorization`、`cookie` 等不分大小寫欄位，值統一替換為 `[REDACTED]`。
2. **字串層級正則遮罩**：在 JSON 序列化或日誌輸出前二次掃描，確保任何格式的金鑰不會遺留於 `backend/logs/app.log`。此機制用於修復 CodeQL `py/clear-text-logging-sensitive-data` 告警。

---

## 7. 資料模型

所有資料表定義於 `backend/app/models/__init__.py`，由 `models/database.py` 的 `Base.metadata.create_all` 在啟動時建立（目前無 Alembic 遷移）。JSON 型欄位以 `Text` 儲存序列化字串。

```mermaid
erDiagram
    users ||--o{ conversations : owns
    conversations ||--o{ messages : contains
    users ||--o{ documents : uploaded_by
    users ||--o{ custom_api_tools : created_by
    users ||--o{ mcp_servers : created_by

    users {
        int id PK
        string username UK
        string email UK
        string hashed_password
        bool is_active
        bool is_admin
        string role
        datetime created_at
        datetime last_login
    }
    conversations {
        int id PK
        int user_id FK
        string title
        datetime created_at
        datetime updated_at
    }
    messages {
        int id PK
        int conversation_id FK
        text content
        bool is_user
        text context_used "sources / sources_detail / research_trace JSON"
        string model_name
        datetime created_at
    }
    documents {
        int id PK
        string filename
        text content
        string file_type
        text description "AI 摘要"
        int uploaded_by FK
        bool is_processed
        datetime created_at
    }
    custom_api_tools {
        int id PK
        string name UK
        string display_name
        text description
        string category
        string method
        string url
        string base_url
        string path
        text headers "JSON"
        string auth_type
        text auth_config "JSON"
        text parameters_schema "JSON Schema"
        text request_body_schema "JSON"
        text param_locations "JSON"
        text response_mapping
        bool is_enabled
        int timeout
        string spec_version
        text raw_spec
        int created_by FK
    }
    mcp_servers {
        int id PK
        string name UK
        string display_name
        text description
        string transport_type "stdio | http"
        string command
        text args "JSON"
        text env_vars "JSON"
        string url
        text headers "JSON"
        bool is_enabled
        string status "disconnected | connected | error"
        text last_error
        text discovered_tools "JSON"
        int timeout
        int created_by FK
    }
```

---

## 8. 部署模式

| 模式 | 資料庫 | 啟動方式 | 黑名單 | 適用情境 |
|---|---|---|---|---|
| **Lite（預設）** | SQLite（`DATABASE_URL=sqlite:///./chatbot.db`） | `python main.py`，單一 uvicorn 程序 | 記憶體 | 本機開發、單機部署、評估 |
| **Standard** | PostgreSQL 17.9（`backend/docker-compose.yml`，host port **7690**） | `docker compose -f backend/docker-compose.yml up -d` 後啟動後端；`DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot` | 記憶體（限制同上） | 多用戶、需要連線池與備份 |

共同前提：

- `DATABASE_URL`、`ADMIN_API_KEY`、`JWT_SECRET_KEY` 為必填環境變數（`config.py` 無預設值）。
- 首次啟動會下載嵌入與重排序模型至 `HF_HOME`（預設 `./data/hf_home`），需要外網或預先放置模型。
- 索引檔案（FAISS、Whoosh、`documents.pkl`）位於 `DATA_DIR`，多實例部署時不共享；水平擴展需先解決黑名單與索引共享問題（見 ADR-0002）。

---

## 9. 架構決策紀錄 (ADR)

- [ADR 索引與說明](./adr/README.md)
- [ADR-0001: 增強型混合 RAG 檢索架構與雙 Token 安全防護決策](./adr/0001-hybrid-rag-and-security.md) — 已通過；其中 Redis 黑名單與快取部分已由 2.0.0 的記憶體實作取代。
- [ADR-0002: 2.x 平台強化與工具擴充架構路線圖](./adr/0002-platform-hardening-and-tool-extension-roadmap.md) — 提議中；涵蓋 CI、可插拔黑名單、測試補強、Alembic、ToolProvider 抽象、TSX 遷移收尾、可觀測性與設定治理。
