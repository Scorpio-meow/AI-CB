# CLAUDE.md

AskMiao 是以 FastAPI + React 19 建構的企業知識庫對話系統：混合 RAG（FAISS + Whoosh BM25 + Cross-Encoder）搭配 ReAct 自主研究 Agent，並可透過 OpenAPI 匯入與 MCP 伺服器擴充工具。本檔案給 AI 助手與新進貢獻者快速掌握指令、架構、慣例與陷阱；完整說明見 `docs/architecture.md`、`docs/api.md`、`llms.txt`。

## 文件規則

- 所有文件皆為繁體中文 + 英文雙語：每個 `X.md` / `X.txt` 都有對應的 `X_en.md` / `X_en.txt`，修改其中一個必須同步另一個。
- 文件內容以程式碼為準。修改路由、設定或資料表時，同步更新 `docs/api.md`、`docs/architecture.md`、`llms.txt` 與 `README.md` 的對應段落，並在 `CHANGELOG.md` 的 `[Unreleased]` 加入條目。
- 重大架構決策以 ADR 記錄（`docs/adr/README.md` 有範本與索引），檔名 `XXXX-kebab-case.md`。

## 常用指令

### 後端（`backend/`，Python 3.10+）

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env        # 至少填 DATABASE_URL、ADMIN_API_KEY、JWT_SECRET_KEY
python init_db.py           # 建表與預設管理員
python main.py              # http://localhost:8001，Swagger 於 /docs
pytest                      # pytest.ini: testpaths=tests, -q
```

選用 PostgreSQL：`docker compose -f docker-compose.yml up -d`（host port 7690），`DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot`。

### 前端（`frontend/`，Bun）

```bash
cd frontend
bun install
cp .env.example .env        # PORT=3001，/api 代理至 8001
bun run dev                 # http://localhost:3001
bun run lint                # eslint（目前只掃 js,jsx）
bunx tsc --noEmit           # 型別檢查
bun run test                # vitest（目前尚無測試檔）
bun run build               # 輸出至 frontend/build
```

## 架構速覽

- **進入點**：`backend/main.py` 掛載七組路由：`/api/auth`、`/api/chat`、`/api/admin`、`/api/documents`、`/api/api-tools`、`/api/mcp`、`/api/tags` + `/api/external-tags`。中介軟體於 `app/middleware.py`（SecurityHeaders → RateLimit → CORS）。
- **啟動流程**：`app/core/lifespan.py` 依序 `create_tables()` → `get_rag_system()` 單例（`core/rag_manager.py`）→ `tasks/uploads_watcher.py` → `tasks/index_rebuilder.py`。
- **RAG 分層**：`rag/contextual_rag.py`（門面）→ `rag/pipeline.py` → `rag/agent.py`（`ResearchAgent`）→ `rag/tools.py`（`ResearchToolRegistry`）；索引在 `rag/indices/`，融合與重排序在 `rag/retrievers/hybrid.py`。
- **對話端點是 SSE**：`POST /api/chat/send` 回傳 `text/event-stream`，事件為 `start`、`step_start`、`step_end`、`token`、`sources`、`done`、`error`。前端於 `pages/Chat/index.tsx` 消費。
- **工具三來源**：內建（`search_knowledge_base`、`filter_and_count_records`、`web_search`、`web_fetch`）+ `custom_api_tools` 表（function name 即 `name`）+ `mcp_servers.discovered_tools`（命名 `mcp_{server}_{tool}`）。`GET /api/chat/tools` 可查目前聚合結果。
- **設定**：`app/core/config.py`（pydantic-settings）是唯一真相來源；`DATABASE_URL`、`ADMIN_API_KEY`、`JWT_SECRET_KEY` 無預設值。
- **資料表**：`app/models/__init__.py`，由 `create_all` 建立，沒有 Alembic。
- **前端**：React 19 + TypeScript + Vite 8；樣式用 CSS Modules 與 `src/styles/tokens.css`，元件庫在 `src/components/ui/`。路由在 `src/App.jsx`（`/chat`、`/tools`、`/documents`、`/admin`、`/profile`）。

## 慣例

- **Commit**：Conventional Commits，主旨以繁體中文撰寫，例如 `feat(tools): 新增 OpenAPI 匯入`、`fix(security): 修復 SSRF`、`docs: 更新架構文件`。
- **日誌脫敏**：任何會進日誌的物件都要經 `core/security_logging.py`；密碼、Token、Authorization、Cookie 必須呈現為 `[REDACTED]`。不要 `print` 或 `logger.info` 原始請求內容。
- **出站請求**：所有由用戶或模型提供的 URL 必須經 `core/ssrf_protection.py` 的 `validate_url_ssrf` 或 `safe_fetch_text`，不要直接 `requests.get` / `httpx.get`。
- **認證**：需登入的端點用 `get_current_user` / `get_current_user_id`，管理員端點用 `get_current_admin_user`。
- **前端**：新程式碼寫 `.tsx`；使用 `components/ui` 元件與 CSS Modules，不要引入 MUI 或其他 UI 框架；API 呼叫走 `services/api.ts`（已含 Token 刷新攔截器）。
- **新增工具來源**：目前需同時修改 `tools.py` 的 `get_tool_definitions()` 與 `execute_tool()`；ADR-0002 規劃改為 `ToolProvider` 介面。

## 常見陷阱

- `DATABASE_URL` 未設定時後端啟動即失敗；`.env.example` 預設為 SQLite，PostgreSQL 範例使用 compose 對外的 7690 埠。
- `FORCE_CPU=true` 為預設；首次啟動會下載 `bge-small-zh-v1.5` 與 `bge-reranker-base` 至 `./data/hf_home`，需要外網。
- `TokenBlacklist`（`core/redis_client.py`）是單程序記憶體實作，多 worker 或重啟後撤銷失效；不要假設有 Redis。
- `frontend/src/pages/Chat.jsx` 是死檔，`App.jsx` 實際載入 `pages/Chat/index.tsx`；請勿修改 `Chat.jsx`。
- `utils/logger.js` 與 `utils/secureLogger.ts` 重複，新程式碼用 `secureLogger.ts`。
- `RATE_LIMIT_ENABLED=true` 時本機壓測或測試可能被 429，測試環境請關閉。
- `.env.example` 的 `CHUNK_SIZE=300` 會覆寫 `config.py` 的 800；改動切塊參數後需 `POST /api/documents/rebuild-index`。
- 索引檔（FAISS、Whoosh、`documents.pkl`）在 `data/`，被 `.gitignore` 排除；`scripts/reset_faiss.py` 可重置。

## 文件地圖

| 文件 | 內容 |
|---|---|
| `README.md` / `README_en.md` | 快速開始、功能、目錄、環境變數矩陣 |
| `llms.txt` / `llms_en.txt` | AI 導向的檔案地圖與系統約束 |
| `docs/architecture.md` | 分層架構、檢索、認證、Agent 迴圈、工具擴充、安全、資料模型、部署 |
| `docs/api.md` | 所有端點的請求 / 回應規格 |
| `docs/adr/` | ADR-0001（混合 RAG 與安全）、ADR-0002（2.x 強化路線圖） |
| `CHANGELOG.md` | 版本紀錄，新變更寫入 `[Unreleased]` |
