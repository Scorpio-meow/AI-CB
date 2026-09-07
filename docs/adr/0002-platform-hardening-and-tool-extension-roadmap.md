# ADR-0002: 2.x 平台強化與工具擴充架構路線圖

[繁體中文](0002-platform-hardening-and-tool-extension-roadmap.md) | [English](0002-platform-hardening-and-tool-extension-roadmap_en.md)

## 狀態

提議 (Proposed) - 2026-09-07

---

## 背景與問題陳述

2.0.0 的「輕量化」重構讓 AskMiao 可以在沒有 Docker、PostgreSQL 與 Redis 的環境一鍵啟動，隨後的 2.x 迭代又加入了自訂 API 工具（OpenAPI 匯入）、MCP 伺服器整合與 SSRF 出站防護。這些變更在帶來功能的同時，也累積了下列技術債與架構風險：

1. **Token 黑名單只存在於單一程序**：`core/redis_client.py` 的 `TokenBlacklist` 為 class-level dict，多 worker 或重啟後撤銷即失效，且儲存整段 Token 而非 JTI。
2. **沒有資料庫遷移機制**：資料表由 `Base.metadata.create_all` 建立；`custom_api_tools` 與 `mcp_servers` 欄位仍在演變，任何欄位變更都需手動 SQL。
3. **沒有 CI**：倉庫無 `.github/`，lint、型別檢查、pytest、vitest 與 CodeQL 皆靠人工執行；歷史上已有 CodeQL 告警需事後修補。
4. **測試缺口**：後端測試僅覆蓋 agentic research、API tools、MCP、OpenAPI parser、模組化 RAG 與 SSRF，缺少 auth、documents、chat 端點；前端 vitest 已配置但零測試檔。
5. **前端 JSX → TSX 遷移做到一半**：`pages/Chat.jsx` 為死檔、`utils/logger.js` 與 `utils/secureLogger.ts` 重複、多個頁面仍為未型別化 JSX；`backend/app/models/payloads.py` 殘留已移除的 workflow 型別。
6. **工具來源耦合**：`ResearchToolRegistry.get_tool_definitions()` 與 `execute_tool()` 以條件分支合併內建工具、`custom_api_tools` 表與 MCP `discovered_tools`，每新增一種來源都要修改同一個類別。
7. **設定漂移**：`config.py`、`.env.example` 與 README 對 `DATABASE_URL`、`LLM_API_BASE`、`CHUNK_SIZE` 等預設值敘述不一致。
8. **缺乏可觀測性**：日誌為純文字、無 request-id、無 metrics 端點，research trace 只存於 `messages.context_used` 無法查詢。

本 ADR 訂定下一階段的決策與優先順序，作為後續 PR 的依據；各項目落地時可拆分為獨立 ADR 或直接引用本文。

---

## 架構決策內容

依風險與投入成本排序為 P0（立即）、P1（下一個迭代）、P2（有餘裕時）。

### P0-1：建立 CI 管線

- 新增 `.github/workflows/ci.yml`，觸發於 push 與 pull request：
  - **backend**：`pip install -r requirements.txt`、`pytest -q`，環境設 `FORCE_CPU=true`、`DATABASE_URL=sqlite:///./test.db`、`RATE_LIMIT_ENABLED=false`；以 actions cache 快取 `data/hf_home`，或在測試中 mock 嵌入模型避免下載。
  - **frontend**：`bun install`、`bun run lint`、`bunx tsc --noEmit`、`bun run test`、`bun run build`。
  - **CodeQL**：Python 與 JavaScript/TypeScript 掃描。
- 將 CI 綠燈設為合併前提。

### P0-2：可插拔 Token 黑名單並改存 JTI

- 在 `core/` 定義 `BlacklistBackend` Protocol：`add(jti, expires_in)`、`is_blacklisted(jti)`、`remove(jti)`。
- 實作 `MemoryBlacklist`（預設，保留現有行為）與 `RedisBlacklist`（設定 `REDIS_URL` 時啟用；`redis` 成為 optional extra）。
- `jwt_auth.py` 改以 payload 的 `jti` 進出黑名單，`revoke_token()` 解析 Token 後只寫入 JTI 與剩餘 TTL。
- 啟動時若 `ENVIRONMENT=production` 且 worker 數 > 1 而未設定 `REDIS_URL`，記錄明確警告。

### P0-3：補齊核心測試

- 後端新增 `tests/test_auth.py`（register / login / refresh / logout 後黑名單生效 / validate-token）、`tests/test_documents.py`（upload 成功與失敗、delete、rebuild-index，RAG 以 fixture mock）、`tests/test_chat_send.py`（SSE 事件序列，LLM 客戶端 mock）。
- 前端以 vitest + Testing Library 建立基線：`components/ui` 主要元件（Button、Dialog、Tabs、Snackbar）與 `pages/Chat/ResearchTraceBlock.tsx`。
- 覆蓋率目標：後端 `app/api` 行覆蓋 ≥ 70%，前端 `components/ui` ≥ 50%；CI 報告但初期不阻擋合併。

### P1-1：導入 Alembic 遷移

- `alembic init backend/alembic`，以現行 `Base.metadata` 產生基線 revision。
- `lifespan.py` 改為：SQLite 開發模式維持 `create_all`；其他情況執行 `alembic upgrade head`（或由部署腳本執行）。
- SQLite 需啟用 batch mode 以支援 ALTER。

### P1-2：統一工具擴充介面 `ToolProvider`

- 定義 `ToolProvider` Protocol：`list_definitions() -> list[dict]`、`can_handle(name) -> bool`、`execute(name, arguments) -> Any`。
- 實作 `BuiltinToolProvider`（現有四個內建工具）、`CustomApiToolProvider`（讀 `custom_api_tools`）、`McpToolProvider`（讀 `mcp_servers.discovered_tools`）。
- `ResearchToolRegistry` 退化為聚合器：組合 providers、檢查名稱衝突、統一注入 SSRF 檢查與逾時，並維持 `GET /api/chat/tools` 回傳格式不變。
- 新增來源（例如未來的資料庫查詢工具）只需新增一個 provider。

### P1-3：完成 TSX 遷移與死碼清理

- 刪除 `frontend/src/pages/Chat.jsx`、`frontend/src/utils/logger.js`（統一使用 `secureLogger.ts`）、`backend/app/models/payloads.py` 中的 workflow 型別。
- 逐頁將 `App.jsx`、`Layout.jsx`、`PrivateRoute.jsx`、`AdminDashboard.jsx`、`Documents.jsx`、`AiTools.jsx`、`LoginPage.jsx`、`RegisterPage.jsx`、`ProfilePage.jsx` 轉為 `.tsx`，每頁一個 PR。
- `package.json` 的 lint script 擴充為 `--ext js,jsx,ts,tsx`。

### P2-1：可觀測性

- 結構化 JSON 日誌（沿用 `security_logging.py` 脫敏）與 request-id 中介軟體。
- 以 `prometheus-fastapi-instrumentator` 暴露 `/metrics`，label 不得包含用戶輸入或敏感值。
- 將 `research_trace` 從 `messages.context_used` 抽出為獨立資料表以支援查詢與統計（需先完成 P1-1）。

### P2-2：設定治理

- `config.py` 為唯一真相來源：`DATABASE_URL` 給予 `sqlite:///./chatbot.db` 預設值；`.env.example` 與 README 環境矩陣改由腳本從 `Settings` 產生或以測試比對。
- 統一 `CHUNK_SIZE` / `CHUNK_OVERLAP` 等在 `.env.example` 與 `config.py` 之間的差異，並在 CHANGELOG 明示。

---

## 決定產生的影響與權衡

### 正面影響

- **正確性**：黑名單跨程序生效後，登出撤銷才真正可靠；Alembic 讓欄位演變可追溯。
- **可維護性**：CI 與測試基線阻止回歸；ToolProvider 讓工具來源可獨立演進；TSX 收尾消除雙軌程式碼。
- **可運維性**：metrics 與 request-id 讓效能與錯誤可歸因。

### 負面影響與風險

- **選用依賴回歸**：`RedisBlacklist` 與 `/metrics` 重新引入外部元件，但預設模式維持零依賴，不影響 Lite 部署。
- **一次性重構成本**：ToolProvider 與 TSX 遷移需觸碰核心檔案，需以 CI 與測試作為安全網，並拆成小 PR。
- **CI 時間**：嵌入模型下載可能使 pytest 變慢，需以 cache 或 mock 控制。
- **SQLite 遷移限制**：ALTER 支援有限，Alembic batch mode 會重建資料表，大型資料量需注意。

---

## 未採納方案

| 方案 | 未採納原因 |
|---|---|
| 強制所有部署使用 Redis | 違反 2.0.0 零依賴設計目標；改為選用後端即可解決多 worker 問題 |
| 更換 ORM（如 SQLModel、Tortoise）以取得內建遷移 | 遷移成本遠高於導入 Alembic，且現有 SQLAlchemy 模型可直接沿用 |
| 以 LangChain Tools / OpenAI Agents SDK 取代自製 Registry | 引入大型框架會與現有 Azure v1 / Ollama 原生 tool calling 相容性處理衝突；ToolProvider 抽象已足夠 |
| 一次性以單一 PR 完成 TSX 遷移 | 變更面過大、難以審查；改為逐頁拆分 |
