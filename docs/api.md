# AskMiao API 參考手冊

[繁體中文](api.md) | [English](api_en.md)

> 本文件說明 AskMiao 2.x 提供之 RESTful、SSE 串流與 WebSocket 端點。路由前綴以 `backend/main.py` 為準；伺服器啟動後可於 `/docs` 使用 Swagger UI 互動測試。除特別註明外，所有端點皆需 `Authorization: Bearer <access_token>` 標頭。

| 模組 | 前綴 | 原始碼 |
|---|---|---|
| 身份認證 | `/api/auth` | `backend/app/api/auth.py` |
| 對話與自主研究 | `/api/chat` | `backend/app/api/chat.py` |
| 知識庫文件（管理員） | `/api/documents` | `backend/app/api/documents.py` |
| 系統管理（管理員） | `/api/admin` | `backend/app/api/admin.py` |
| 自訂 API 工具 | `/api/api-tools` | `backend/app/api/api_tools.py` |
| MCP 伺服器 | `/api/mcp` | `backend/app/api/mcp.py` |
| 模型標籤 | `/api/tags`、`/api/external-tags` | `backend/app/api/tags.py` |
| 健康檢查 | `/`、`/health` | `backend/main.py` |

---

## 1. 身份認證模組 (Authentication)

### 1.1 POST /api/auth/register

用戶註冊。無需認證。

**請求參數 (Request Body):**

| 欄位名稱 | 型態 | 必填 | 說明 | 格式與限制 |
|---|---|---|---|---|
| username | string | 是 | 用戶名稱 | 3-50 字元，僅允許英數字、底線與連字號 |
| email | string | 是 | 電子郵件 | 標準 Email 格式 |
| password | string | 是 | 密碼 | 至少 8 字元 |

**回應結果:**

- **201 Created**：回傳用戶資料與 Access Token，並設定 Refresh Token HttpOnly Cookie。

```json
{
  "user": {
    "id": 1,
    "username": "miao_user",
    "email": "user@example.com",
    "role": "user",
    "is_active": true,
    "is_admin": false,
    "created_at": "2026-08-03T00:00:00Z",
    "last_login": null
  },
  "tokens": {
    "access_token": "eyJhbGciOiJSUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "message": "註冊成功"
}
```

- **400 Bad Request**：用戶名稱或 Email 已存在。

---

### 1.2 POST /api/auth/login

驗證憑證後回傳 Access Token，並將 Refresh Token 寫入 HttpOnly Cookie。無需認證。

**請求參數 (Request Body):**

| 欄位名稱 | 型態 | 必填 | 說明 |
|---|---|---|---|
| username | string | 是 | 用戶名稱或電子郵件 |
| password | string | 是 | 用戶密碼 |

**回應結果:**

- **200 OK**：格式同註冊回應。
- **401 Unauthorized**：帳號或密碼錯誤。

---

### 1.3 POST /api/auth/refresh

無感刷新 Access Token。系統從 HttpOnly Cookie 讀取 `refresh_token`，無需 Authorization 標頭。

**回應結果:**

- **200 OK**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

- **401 Unauthorized**：Cookie 不存在、Refresh Token 無效、已撤銷或過期。

---

### 1.4 GET /api/auth/me

取得當前登入用戶資料（`UserProfile`）。

```json
{
  "id": 1,
  "username": "miao_user",
  "email": "user@example.com",
  "role": "user",
  "is_active": true,
  "is_admin": false,
  "created_at": "2026-08-03T00:00:00Z",
  "last_login": "2026-08-03T01:00:00Z"
}
```

---

### 1.5 PUT /api/auth/me

更新當前用戶的 Email 或密碼。

| 欄位名稱 | 型態 | 必填 | 說明 |
|---|---|---|---|
| email | string | 否 | 新 Email |
| current_password | string | 否（改密碼時必填） | 目前密碼 |
| new_password | string | 否 | 新密碼，至少 8 字元 |

回傳更新後之 `UserProfile`。

---

### 1.6 POST /api/auth/change-password

| 欄位名稱 | 型態 | 必填 | 說明 |
|---|---|---|---|
| current_password | string | 是 | 目前密碼 |
| new_password | string | 是 | 新密碼，至少 8 字元 |
| confirm_password | string | 是 | 需與 new_password 相同 |

- **200 OK**：`{"message": "..."}`
- **400 / 401**：目前密碼錯誤或新密碼不一致。

---

### 1.7 POST /api/auth/logout

將目前的 Access Token 與 Cookie 中的 Refresh Token 寫入黑名單（記憶體實作，見架構文件第 3 節），並清除 Refresh Cookie。

- **200 OK**：`{"message": "登出成功"}`

---

### 1.8 POST /api/auth/validate-token

檢查 Access Token 是否仍有效。

- **200 OK**：`{"message": "令牌有效"}`
- **401 Unauthorized**：無效、過期或已撤銷。

---

## 2. 對話與 Agentic RAG 自主研究模組 (Chat & Research)

### 2.1 POST /api/chat/send（SSE 串流）

發送訊息並啟動 `ResearchAgent` 多輪自主研究。**回應為 `text/event-stream`**，前端以 SSE 逐事件消費；用戶訊息會在串流開始前先寫入資料庫。

**請求標頭:**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: text/event-stream
```

**請求參數 (`MessageCreate`):**

| 欄位名稱 | 型態 | 必填 | 說明 | 預設值 |
|---|---|---|---|---|
| `content` | string | 是 | 用戶提問內容 | - |
| `conversation_id` | integer | 否 | 對話 ID；為 null 時自動建立新對話 | null |
| `model_name` | string | 否 | 指定 LLM 模型名稱（來自 `/api/chat/models`） | 系統預設 |
| `reasoning_effort` | string | 否 | `none` / `low` / `medium` / `high` / `xhigh` | `medium` |
| `attachments` | `FileAttachment[]` | 否 | 附件（`filename`, `file_type`, `file_size`, `data_url`, `content`），供多模態或文字附件使用 | `[]` |

**SSE 事件序列:**

| 事件 | data 內容 | 說明 |
|---|---|---|
| `start` | `{conversation_id, user_message_id}` | 串流開始，回傳（可能新建的）對話 ID |
| `step_start` | `{step, tool, arguments, ...}` | Agent 開始一輪工具呼叫 |
| `step_end` | `{step, tool, arguments, output_preview, duration_seconds, status}` | 工具完成，累積為 `research_trace` |
| `token` | `{content}` | 模型輸出片段 |
| `sources` | `{sources: string[], sources_detail: object[]}` | 參考來源 |
| `done` | `{message_id, conversation_id, answer, sources, sources_detail, research_trace}` | 回覆已持久化 |
| `error` | `{detail}` | 處理失敗 |

**範例串流:**

```text
event: start
data: {"conversation_id": 42, "user_message_id": 107}

event: step_start
data: {"step": 1, "tool": "search_knowledge_base", "arguments": {"query": "特休假申請流程"}}

event: step_end
data: {"step": 1, "tool": "search_knowledge_base", "output_preview": "找到 3 個片段...", "duration_seconds": 0.42, "status": "success"}

event: token
data: {"content": "依據員工規範"}

event: sources
data: {"sources": ["員工規範2026.pdf"], "sources_detail": [{"source": "員工規範2026.pdf", "chunk_index": 3, "score": 0.91}]}

event: done
data: {"message_id": 108, "conversation_id": 42, "answer": "依據員工規範...", "sources": ["員工規範2026.pdf"], "sources_detail": [...], "research_trace": [...]}
```

---

### 2.2 GET /api/chat/models

取得可用模型清單與預設模型。來源依序為：`AVAILABLE_MODELS` / 各供應商設定 → `LLM_API_BASE` 遠端 `/api/tags`（Ollama）。無需認證。

```json
{
  "models": ["gpt-5.6-luna", "gpt-5.6-terra", "gemma4:26b"],
  "default": "gpt-5.6-luna"
}
```

---

### 2.3 GET /api/chat/tools

回傳 Agent 目前可用的 Function Calling 工具定義（內建工具 + 已啟用之自訂 API 工具 + 已啟用 MCP 伺服器的 `discovered_tools`）。

```json
{
  "status": "success",
  "tools": [
    {"type": "function", "function": {"name": "search_knowledge_base", "description": "...", "parameters": {...}}},
    {"type": "function", "function": {"name": "filter_and_count_records", "...": "..."}},
    {"type": "function", "function": {"name": "web_search", "...": "..."}},
    {"type": "function", "function": {"name": "web_fetch", "...": "..."}},
    {"type": "function", "function": {"name": "get_pet_by_id", "description": "【外部自訂 API】...", "...": "..."}},
    {"type": "function", "function": {"name": "mcp_mcp_time_get_current_time", "...": "..."}}
  ]
}
```

`status` 為 `partial` 時表示 RAG 系統初始化失敗，僅回傳內建工具並附 `error`。

---

### 2.4 對話紀錄

| 方法 | 路徑 | 說明 | 回應 |
|---|---|---|---|
| GET | `/api/chat/conversations` | 當前用戶所有對話 | `ConversationResponse[]`（`id`, `title`, `created_at`, `updated_at`, `messages`） |
| POST | `/api/chat/conversations` | 建立空白對話 | `ConversationResponse` |
| GET | `/api/chat/conversations/{id}` | 單一對話含訊息 | `ConversationResponse` |
| GET | `/api/chat/conversations/{id}/messages?limit=100&offset=0` | 分頁訊息 | `MessageResponse[]` |
| DELETE | `/api/chat/conversations/{id}` | 刪除對話 | `{"message": "對話已刪除"}` |

`MessageResponse` 欄位：`id`, `content`, `is_user`, `created_at`, `context_used`, `model_name`, `reasoning_effort`, `attachments`, `sources`, `sources_detail`, `research_trace`。

---

### 2.5 WebSocket /api/chat/ws/{user_id}

保留之簡易雙向通道（目前僅回聲訊息，非主要對話路徑；主要串流請使用 2.1 之 SSE）。

- 連線位址：`ws://localhost:8001/api/chat/ws/{user_id}`
- 送出：`{"content": "..."}`
- 收到：`{"type": "message", "content": "收到消息: ...", "timestamp": "now"}`

---

## 3. 知識庫與文件管理模組 (Documents)

所有端點需**管理員**權限（`get_current_admin_user`）。

### 3.1 GET /api/documents/

列出知識庫所有文件；若文件缺少摘要會自動生成後回傳。

```json
[
  {
    "id": 101,
    "filename": "員工規範2026.pdf",
    "file_type": "application/pdf",
    "description": "本文件規範員工出勤、請假...",
    "uploaded_by": 1,
    "is_processed": true,
    "created_at": "2026-08-01T10:00:00Z"
  }
]
```

---

### 3.2 POST /api/documents/upload

`multipart/form-data`，欄位名稱 `file`（可多檔，單次上限 10 個；單檔大小上限 `MAX_FILE_SIZE_MB`）。支援 PDF、TXT、DOCX、PPTX、XLSX、Markdown 等由 `DocumentProcessor` 判定的類型。每個檔案獨立處理並回報結果。

```json
{
  "results": [
    {
      "filename": "員工規範2026.pdf",
      "status": "success",
      "document_id": 101,
      "content_length": 15234,
      "content_type": "application/pdf",
      "qa_detected": false,
      "qa_pairs": 0,
      "http_status": 201
    },
    {
      "filename": "bad.exe",
      "status": "failed",
      "detail": "檔名驗證失敗: 無效的檔名或不允許的副檔名",
      "http_status": 400
    }
  ]
}
```

---

### 3.3 POST /api/documents/{document_id}/regenerate-summary

重新以 LLM 生成該文件之摘要（`description`）。

### 3.4 PUT /api/documents/{document_id}/summary

手動覆寫摘要。Body：`{"description": "..."}`。

### 3.5 DELETE /api/documents/{document_id}

移除資料庫紀錄、實體檔案與向量索引中的片段。回應 `{"message": "文件刪除成功"}`。

### 3.6 POST /api/documents/rebuild-index

清空索引並依目前 `CHUNK_SIZE` / `CHUNK_OVERLAP` 重新處理所有文件。

```json
{
  "message": "索引重建完成",
  "document_count": 12,
  "chunk_count": 348,
  "timestamp": "2026-09-07T08:00:00"
}
```

---

## 4. 系統管理模組 (Admin)

所有端點需管理員權限。

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/api/admin/users` | 所有用戶 |
| PUT | `/api/admin/users/{user_id}` | 更新 `username` / `email` / `is_active` / `is_admin` |
| DELETE | `/api/admin/users/{user_id}` | 刪除用戶 |
| GET | `/api/admin/statistics` | 用戶、對話、訊息、文件統計與近 7 日趨勢（快取 180 秒） |
| GET | `/api/admin/conversations` | 全系統對話 |
| GET | `/api/admin/conversations/{id}/messages` | 指定對話訊息 |
| DELETE | `/api/admin/conversations/{id}` | 刪除對話 |
| GET | `/api/admin/documents` | 文件清單 |
| DELETE | `/api/admin/documents/{id}` | 刪除文件 |
| GET | `/api/admin/vector-store/info` | 索引摘要（文件數、片段數、維度等） |
| GET | `/api/admin/vector-store/statistics` | 詳細索引統計 |
| DELETE | `/api/admin/vector-store/clear` | 清空向量庫 |
| POST | `/api/admin/vector-store/reindex` | 觸發 `force_reindex()` |
| GET | `/api/admin/rag-config` | 目前生效之檢索參數（`chunk_size`, `top_k`, `hybrid_alpha`, `rerank_weight`, `device`, `use_faiss_gpu` 等） |

---

## 5. 自訂 API 工具模組 (Custom API Tools)

將任意 REST API 註冊為 Agent 可呼叫的工具。前綴 `/api/api-tools`，需登入。

### 5.1 POST /api/api-tools/parse-spec

解析 OpenAPI / Swagger 規格（OAS 2.0、3.0、3.1），支援 URL 或原始 JSON / YAML 內容；URL 載入會經 SSRF 驗證。

| 欄位名稱 | 型態 | 必填 | 說明 |
|---|---|---|---|
| spec_content_or_url | string | 是 | 規格 URL 或內容 |
| default_base_url | string | 否 | 規格未宣告 `servers` 時的預設 Base URL |

- **200 OK**：`{"status": "success", "data": {...}}`，`data` 含 `spec_version`、`base_url` 與可匯入端點清單（每項含 `name`, `display_name`, `description`, `method`, `path`, `full_url`, `parameters_schema`, `request_body_schema`, `param_locations`）。
- **400 Bad Request**：解析失敗或 URL 被 SSRF 防護拒絕。

---

### 5.2 POST /api/api-tools/import

批次匯入 `parse-spec` 產出的端點；同名工具會被更新而非重複建立。

| 欄位名稱 | 型態 | 必填 | 說明 |
|---|---|---|---|
| tools | `OpenApiImportItem[]` | 是 | 勾選之端點（欄位同 5.1 `data` 項目，另可帶 `base_url`, `headers`, `auth_type`, `auth_config`, `spec_version`） |
| global_base_url | string | 否 | 套用至所有項目的 Base URL |
| global_headers | object | 否 | 共用 Header |
| global_auth_type | string | 否 | `none` / `bearer` / `api_key` / `basic` |
| global_auth_config | object | 否 | 依 auth_type：`{token}` / `{key_name, key_value, key_in: header|query}` / `{username, password}` |

```json
{
  "status": "success",
  "message": "成功匯入 3 個新工具，更新 1 個既有工具。",
  "imported": 3,
  "updated": 1
}
```

---

### 5.3 工具 CRUD

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/api/api-tools?category=&is_enabled=&search=` | 清單，回應 `{"status", "total", "tools": [...]}` |
| POST | `/api/api-tools` | 手動建立（`CustomApiToolCreate`：`name`, `display_name`, `description`, `method`, `url`, `headers`, `auth_type`, `auth_config`, `parameters_schema`, `request_body_schema`, `param_locations`, `response_mapping`, `timeout`） |
| GET | `/api/api-tools/{tool_id}` | 單一工具 |
| PUT | `/api/api-tools/{tool_id}` | 更新（所有欄位皆選填） |
| PATCH | `/api/api-tools/{tool_id}/toggle` | 切換 `is_enabled` |
| DELETE | `/api/api-tools/{tool_id}` | 刪除 |

工具物件欄位：`id`, `name`, `display_name`, `description`, `category`, `method`, `url`, `base_url`, `path`, `headers`, `auth_type`, `auth_config`, `parameters_schema`, `request_body_schema`, `param_locations`, `response_mapping`, `is_enabled`, `timeout`, `spec_version`, `created_at`, `updated_at`。

---

### 5.4 POST /api/api-tools/{tool_id}/test

以指定參數直接執行工具（不經 Agent）。Body：`{"arguments": {"petId": 1}}`。回傳 `execute_http_api_tool` 結果（含狀態碼、耗時與回應內容，或 `error`）。目標 URL 執行前會經 SSRF 驗證。

---

## 6. MCP 伺服器模組 (Model Context Protocol)

前綴 `/api/mcp`，需登入。支援 `stdio`（子程序）與 `http` 兩種傳輸，透過 JSON-RPC `initialize` → `tools/list` → `tools/call` 與伺服器互動。

### 6.1 GET /api/mcp/presets

回傳內建範本（如 `mcp_time` 時區工具），可直接作為 6.2 的請求內容。

### 6.2 伺服器 CRUD

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/api/mcp/servers?is_enabled=` | 清單，回應 `{"status", "total", "servers": [...]}` |
| POST | `/api/mcp/servers` | 建立（`McpServerCreate`）；建立後立即嘗試探索工具 |
| GET | `/api/mcp/servers/{server_id}` | 單一伺服器 |
| PUT | `/api/mcp/servers/{server_id}` | 更新 |
| DELETE | `/api/mcp/servers/{server_id}` | 刪除 |
| PATCH | `/api/mcp/servers/{server_id}/toggle` | 切換 `is_enabled` |

`McpServerCreate` 欄位：

| 欄位名稱 | 型態 | 必填 | 說明 |
|---|---|---|---|
| name | string | 是 | 唯一識別（小寫；作為工具名前綴 `mcp_{name}_`） |
| display_name | string | 是 | 顯示名稱 |
| description | string | 否 | 說明 |
| transport_type | string | 否 | `stdio`（預設）或 `http` |
| command / args / env_vars | string / string[] / object | stdio 時必填 command | 子程序啟動設定 |
| url / headers | string / object | http 時必填 url | HTTP 端點 |
| timeout | integer | 否 | 秒，預設 30 |

伺服器物件另含 `status`（`disconnected` / `connected` / `error`）、`last_error`、`discovered_tools`。

### 6.3 POST /api/mcp/servers/{server_id}/discover

即時連線並執行 `tools/list`，結果寫回 `discovered_tools`。

```json
{
  "status": "success",
  "message": "成功連線並探索到 2 項 MCP 工具",
  "tools_count": 2,
  "tools": [{"name": "get_current_time", "description": "...", "inputSchema": {...}}],
  "init_info": {...},
  "server": {...}
}
```

- **400 Bad Request**：連線失敗，`status` 設為 `error` 並記錄 `last_error`。

### 6.4 POST /api/mcp/servers/{server_id}/tools/{tool_name}/test

直接呼叫指定 MCP 工具。Body：`{"arguments": {...}}`。回應 `{"status", "server_name", "tool_name", "result"}`。

---

## 7. 模型標籤模組 (Tags)

無需認證。

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/api/tags` | 回傳 `{"tags": [...], "default": "..."}`；優先使用已設定之供應商模型，否則向 `LLM_API_BASE` 查詢並以內建清單備援 |
| GET | `/api/external-tags` | 直接代理 `EXTERNAL_TAGS_URL`（或 `LLM_API_BASE/api/tags`）的原始回應；未設定時回 400 |

---

## 8. 健康檢查

| 方法 | 路徑 | 回應 |
|---|---|---|
| GET | `/` | `{"message": "ChatBot API is running"}` |
| GET | `/health` | `{"status": "healthy"}` |

---

## 9. 全域錯誤回應規範 (Error Handling)

系統沿用 FastAPI 預設格式，錯誤訊息置於 `detail`：

```json
{
  "detail": "無效的存取令牌或令牌已過期"
}
```

| HTTP 狀態碼 | 常見原因 |
|---|---|
| **400 Bad Request** | 參數錯誤、OpenAPI 解析失敗、MCP 連線失敗、SSRF 防護拒絕 |
| **401 Unauthorized** | 缺少 Authorization 標頭、Token 過期或已撤銷 |
| **403 Forbidden** | 非管理員存取管理端點 |
| **404 Not Found** | 對話、文件、工具或 MCP 伺服器不存在 |
| **422 Unprocessable Entity** | Pydantic 欄位驗證失敗 |
| **429 Too Many Requests** | 超過 `RATE_LIMIT_PER_MINUTE` |
| **500 Internal Server Error** | 伺服器內部錯誤；日誌已脫敏，細節不回傳給客戶端 |
