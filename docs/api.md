# AskMiao API 參考手冊

[繁體中文](api.md) | [English](api_en.md)

> 本文件詳細說明 AskMiao 系統提供之 RESTful API 與 WebSocket 即時傳輸端點。系統亦提供 Swagger UI 動態文件頁面，伺服器啟動後可存取 `/docs` 進行互動式測試。

---

## 1. 身份認證模組 (Authentication)

### 1.1 POST /api/auth/register

用戶註冊端點。

**請求標頭 (Headers):**

```http
Content-Type: application/json
```

**請求參數 (Request Body):**

| 欄位名稱 | 型態 | 必填 | 說明 | 格式與限制 |
|---|---|---|---|---|
| username | string | 是 | 用戶名稱 | 3-50 字元，僅允許英數字、底線與連字號 |
| email | string | 是 | 電子郵件 | 標準 Email 格式 |
| password | string | 是 | 密碼 | 至少 8 字元，包含大小寫字母與數字 |

**回應結果:**

- **201 Created**: 註冊成功並回傳用戶資料與 Access Token。

```json
{
  "user": {
    "id": 1,
    "username": "miao_user",
    "email": "user@example.com",
    "is_admin": false,
    "created_at": "2026-08-03T00:00:00Z"
  },
  "tokens": {
    "access_token": "eyJhbGciOiJSUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "message": "註冊成功"
}
```

- **400 Bad Request**: 用戶名稱或 Email 已存在。

---

### 1.2 POST /api/auth/login

用戶登入端點。驗證憑證後回傳 Access Token，並將 Refresh Token 自動寫入 HttpOnly Cookie。

**請求標頭 (Headers):**

```http
Content-Type: application/json
```

**請求參數 (Request Body):**

| 欄位名稱 | 型態 | 必填 | 說明 |
|---|---|---|---|
| username | string | 是 | 用戶名稱或電子郵件 |
| password | string | 是 | 用戶密碼 |

**回應結果:**

- **200 OK**: 登入成功。

```json
{
  "user": {
    "id": 1,
    "username": "miao_user",
    "email": "user@example.com",
    "is_admin": false
  },
  "tokens": {
    "access_token": "eyJhbGciOiJSUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "message": "登入成功"
}
```

- **401 Unauthorized**: 帳號或密碼錯誤。

---

### 1.3 POST /api/auth/refresh

無感刷新 Access Token。系統自動從帶入之 HttpOnly Cookie 中讀取 `refresh_token` 進行驗證。

**請求標頭 (Headers):**
無需帶入 Authorization 標頭，系統自動驗證 Cookie 憑證。

**回應結果:**

- **200 OK**: 刷新成功，回傳新 Access Token。

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

- **401 Unauthorized**: Refresh Token 無效或已過期。

---

### 1.4 GET /api/auth/me

獲取當前登入用戶之個人基本資料與登入狀態。

**請求標頭 (Headers):**

```http
Authorization: Bearer <access_token>
```

**回應結果:**

- **200 OK**: 成功取得個人資料。

```json
{
  "id": 1,
  "username": "miao_user",
  "email": "user@example.com",
  "is_admin": false,
  "last_login": "2026-08-03T01:00:00Z"
}
```

---

### 1.5 POST /api/auth/logout

用戶登出。將當前 Access Token 之 JTI 寫入 Redis 黑名單，並清除 Cookie 中的 Refresh Token。

**請求標頭 (Headers):**

```http
Authorization: Bearer <access_token>
```

**回應結果:**

- **200 OK**: 成功登出並撤銷權限。

```json
{
  "message": "登出成功"
}
```

---

## 2. 對話與 Agentic RAG 自主研究模組 (Chat & Research)

### 2.1 POST /api/chat/send

發送對話訊息，啟動 ReAct 自主研究 Agent 執行多輪工具調用與知識檢索生成。

**請求標頭 (Headers):**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**請求參數 (Request Body):**

| 欄位名稱 | 型態 | 必填 | 說明 | 預設值 |
|---|---|---|---|---|
| `content` | string | 是 | 用戶提問或對話內容 | - |
| `conversation_id` | integer | 否 | 對話紀錄 ID（若為新對話則傳入 null） | null |
| `model_name` | string | 否 | 指定使用的 LLM 模型名稱（如 `gpt-5.6-luna`, `gemma4:26b`） | 系統預設模型 |
| `reasoning_effort` | string | 否 | 模型思考與推理程度 (`none`, `low`, `medium`, `high`, `xhigh`) | `medium` |

**回應結果 (ChatResponse):**

- **200 OK**: 成功生成回應。

```json
{
  "conversation_id": 42,
  "message": {
    "id": 108,
    "content": "MiTAC Agent Builder 是神通資訊科技所開發的企業級 Agentic AI 構建平台...",
    "is_user": false,
    "created_at": "2026-08-24T18:04:07Z",
    "model_name": "gpt-5.6-luna",
    "reasoning_effort": "medium",
    "sources": [
      "https://example.com/mitac-agent-builder",
      "公司規章手冊.pdf"
    ],
    "sources_detail": [
      {
        "source": "https://example.com/mitac-agent-builder",
        "title": "MiTAC Agent Builder 官方簡介",
        "url": "https://example.com/mitac-agent-builder",
        "snippet": "MiTAC Agent Builder 支援多 Agent 協作..."
      }
    ],
    "research_trace": [
      {
        "step": 1,
        "tool": "web_search",
        "arguments": {
          "query": "MiTAC Agent Builder 是什麼"
        },
        "output_preview": "檢索到 5 條外部結果...",
        "duration_seconds": 1.25,
        "status": "success"
      }
    ]
  }
}
```

---

### 2.2 GET /api/chat/models

取得系統當前所有可用之語言模型清單與預設模型。

**回應結果:**

- **200 OK**: 成功回傳可用模型。

```json
{
  "models": [
    "gpt-5.6-luna",
    "gpt-5.6-terra"
  ],
  "default": "gpt-5.6-luna"
}
```

---

### 2.3 GET /api/chat/conversations

查詢當前用戶的所有歷史對話列表。

**請求標頭 (Headers):**

```http
Authorization: Bearer <access_token>
```

**查詢參數 (Query Parameters):**

| 欄位名稱 | 型態 | 必填 | 說明 | 預設值 |
|---|---|---|---|---|
| limit | integer | 否 | 取得筆數限制 | 20 |
| offset | integer | 否 | 分頁偏移量 | 0 |

**回應結果:**

- **200 OK**:

```json
{
  "total": 1,
  "items": [
    {
      "conversation_id": 42,
      "title": "特休假申請流程詢問",
      "updated_at": "2026-08-03T01:30:00Z"
    }
  ]
}
```

---

### 2.3 WebSocket /ws/chat

即時串流雙向對話通道。

**連線位址:** `ws://localhost:8001/ws/chat`

**用戶發送訊息 JSON 格式:**

```json
{
  "message": "請總結這份文件的重點",
  "conversation_id": 42,
  "token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**伺服器串流回應 JSON 格式:**

```json
{
  "response": "這是回應字元片段...",
  "done": false
}
```

完成串流時：

```json
{
  "response": "",
  "done": true,
  "sources": [
    { "source": "專案規範.pdf", "score": 0.92 }
  ]
}
```

---

## 3. 知識庫與文件管理模組 (Documents)

### 3.1 GET /api/documents/list

列出目前知識庫中已建立索引之文件列表。

**請求標頭 (Headers):**

```http
Authorization: Bearer <access_token>
```

**回應結果:**

- **200 OK**:

```json
{
  "documents": [
    {
      "id": 101,
      "filename": "員工規範2026.pdf",
      "size_bytes": 1048576,
      "chunk_count": 15,
      "status": "ready",
      "created_at": "2026-08-01T10:00:00Z"
    }
  ]
}
```

---

### 3.2 POST /api/documents/upload

上傳新文件至知識庫，系統自動切塊並建立 FAISS 向量索引與 Whoosh BM25 文字索引。

**請求標頭 (Headers):**

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**請求參數:**

- `files`: 檔案陣列（支援 PDF, TXT, DOCX 格式；單檔上限 10MB，單次上限 10 個檔案）。

**回應結果:**

- **200 OK**:

```json
{
  "uploaded_files": [
    {
      "id": 101,
      "filename": "員工規範2026.pdf",
      "status": "success",
      "chunks_created": 15
    }
  ]
}
```

---

### 3.3 POST /api/documents/bulk_delete

批次刪除指定知識庫文件並移除對應索引。

**請求標頭 (Headers):**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**請求參數 (Request Body):**

```json
{
  "ids": [101, 102]
}
```

**回應結果:**

- **200 OK**:

```json
{
  "message": "已成功刪除 2 個文件及其索引"
}
```

---

## 4. 多 Agent 協作工作流模組 (Workflow)

### 4.1 GET /api/workflow/agents

取得系統支援之可用 Agent 角色列表。

**請求標頭 (Headers):**

```http
Authorization: Bearer <access_token>
```

**回應結果:**

- **200 OK**:

```json
{
  "agents": [
    {
      "id": "researcher",
      "name": "研究員 Agent",
      "description": "負責檢索知識庫並提供相關背景事實"
    },
    {
      "id": "critic",
      "name": "審查員 Agent",
      "description": "負責審查研究結論並找出潛在矛盾點"
    }
  ]
}
```

---

### 4.2 POST /api/workflow/execute

發起多 Agent 協作討論任務。

**請求標頭 (Headers):**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**請求參數 (Request Body):**

```json
{
  "topic": "評估引入混合 RAG 對回應延遲之影響",
  "participating_agents": ["researcher", "critic"],
  "max_rounds": 3
}
```

**回應結果:**

- **202 Accepted**: 任務已排入佇列執行。

```json
{
  "workflow_id": "wf-882319",
  "status": "running",
  "message": "工作流已發起"
}
```

---

## 5. 全域錯誤回應規範 (Error Handling Schema)

系統採用標準 HTTP 狀態碼配合統一 JSON 格式的回應訊息。

### 錯誤回應 JSON 格式

```json
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "無效的存取令牌或令牌已過期",
    "details": null
  }
}
```

### 常見 HTTP 狀態碼列表

| HTTP 狀態碼 | 錯誤代碼 | 說明與可能的原因 |
|---|---|---|
| **400 Bad Request** | `INVALID_PARAMETER` | 請求 Body 格式錯誤或缺少必要欄位 |
| **401 Unauthorized** | `UNAUTHORIZED` | 缺少 Authorization 標頭或 JWT 憑證撤銷/過期 |
| **403 Forbidden** | `PERMISSION_DENIED` | 用戶權限不足（如非管理員存取管理介面） |
| **404 Not Found** | `RESOURCE_NOT_FOUND` | 請求的資源（對話、文件、Agent）不存在 |
| **422 Unprocessable Entity** | `VALIDATION_ERROR` | FastAPI 欄位資料型態或驗證失敗 |
| **500 Internal Server Error** | `SERVER_ERROR` | 伺服器內部非預期錯誤 |