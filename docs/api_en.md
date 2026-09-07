# AskMiao API Reference

[繁體中文](api.md) | [English](api_en.md)

> This document describes the RESTful, SSE streaming, and WebSocket endpoints provided by AskMiao 2.x. Route prefixes follow `backend/main.py`; once the server is running, the Swagger UI at `/docs` can be used for interactive testing. Unless otherwise noted, every endpoint requires the `Authorization: Bearer <access_token>` header.

| Module | Prefix | Source |
|---|---|---|
| Authentication | `/api/auth` | `backend/app/api/auth.py` |
| Chat and autonomous research | `/api/chat` | `backend/app/api/chat.py` |
| Knowledge base documents (admin) | `/api/documents` | `backend/app/api/documents.py` |
| System administration (admin) | `/api/admin` | `backend/app/api/admin.py` |
| Custom API tools | `/api/api-tools` | `backend/app/api/api_tools.py` |
| MCP servers | `/api/mcp` | `backend/app/api/mcp.py` |
| Model tags | `/api/tags`, `/api/external-tags` | `backend/app/api/tags.py` |
| Health check | `/`, `/health` | `backend/main.py` |

---

## 1. Authentication Module (Authentication)

### 1.1 POST /api/auth/register

User registration. No authentication required.

**Request Body:**

| Field | Type | Required | Description | Format and constraints |
|---|---|---|---|---|
| username | string | Yes | Username | 3-50 characters; only alphanumerics, underscores, and hyphens |
| email | string | Yes | Email address | Standard email format |
| password | string | Yes | Password | At least 8 characters |

**Response:**

- **201 Created**: returns the user profile and an Access Token, and sets the Refresh Token as an HttpOnly cookie.

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
  "message": "Registration successful"
}
```

- **400 Bad Request**: the username or email already exists.

---

### 1.2 POST /api/auth/login

Validates credentials, returns an Access Token, and writes the Refresh Token to an HttpOnly cookie. No authentication required.

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| username | string | Yes | Username or email address |
| password | string | Yes | User password |

**Response:**

- **200 OK**: same format as the registration response.
- **401 Unauthorized**: incorrect username or password.

---

### 1.3 POST /api/auth/refresh

Silently refreshes the Access Token. The system reads `refresh_token` from the HttpOnly cookie; no Authorization header is required.

**Response:**

- **200 OK**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

- **401 Unauthorized**: the cookie is missing, or the Refresh Token is invalid, revoked, or expired.

---

### 1.4 GET /api/auth/me

Returns the profile of the currently logged-in user (`UserProfile`).

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

Updates the current user's email or password.

| Field | Type | Required | Description |
|---|---|---|---|
| email | string | No | New email address |
| current_password | string | No (required when changing the password) | Current password |
| new_password | string | No | New password, at least 8 characters |

Returns the updated `UserProfile`.

---

### 1.6 POST /api/auth/change-password

| Field | Type | Required | Description |
|---|---|---|---|
| current_password | string | Yes | Current password |
| new_password | string | Yes | New password, at least 8 characters |
| confirm_password | string | Yes | Must match new_password |

- **200 OK**: `{"message": "..."}`
- **400 / 401**: the current password is wrong or the new passwords do not match.

---

### 1.7 POST /api/auth/logout

Adds the current Access Token and the Refresh Token from the cookie to the blacklist (in-memory implementation, see [architecture document section 3](architecture_en.md)), and clears the Refresh cookie.

- **200 OK**: `{"message": "Logout successful"}`

---

### 1.8 POST /api/auth/validate-token

Checks whether the Access Token is still valid.

- **200 OK**: `{"message": "Token is valid"}`
- **401 Unauthorized**: invalid, expired, or revoked.

---

## 2. Chat and Agentic RAG Autonomous Research Module (Chat & Research)

### 2.1 POST /api/chat/send (SSE streaming)

Sends a message and starts a multi-turn autonomous research run with `ResearchAgent`. **The response is `text/event-stream`**; the frontend consumes it event by event over SSE. The user message is written to the database before the stream starts.

**Request headers:**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: text/event-stream
```

**Request body (`MessageCreate`):**

| Field | Type | Required | Description | Default |
|---|---|---|---|---|
| `content` | string | Yes | The user's question | - |
| `conversation_id` | integer | No | Conversation ID; when null, a new conversation is created automatically | null |
| `model_name` | string | No | LLM model name to use (from `/api/chat/models`) | System default |
| `reasoning_effort` | string | No | `none` / `low` / `medium` / `high` / `xhigh` | `medium` |
| `attachments` | `FileAttachment[]` | No | Attachments (`filename`, `file_type`, `file_size`, `data_url`, `content`) for multimodal or text attachments | `[]` |

**SSE event sequence:**

| Event | data payload | Description |
|---|---|---|
| `start` | `{conversation_id, user_message_id}` | Stream started; returns the (possibly newly created) conversation ID |
| `step_start` | `{step, tool, arguments, ...}` | The Agent begins a tool call round |
| `step_end` | `{step, tool, arguments, output_preview, duration_seconds, status}` | Tool finished; accumulated into `research_trace` |
| `token` | `{content}` | A fragment of model output |
| `sources` | `{sources: string[], sources_detail: object[]}` | Reference sources |
| `done` | `{message_id, conversation_id, answer, sources, sources_detail, research_trace}` | The reply has been persisted |
| `error` | `{detail}` | Processing failed |

**Example stream:**

```text
event: start
data: {"conversation_id": 42, "user_message_id": 107}

event: step_start
data: {"step": 1, "tool": "search_knowledge_base", "arguments": {"query": "annual leave application process"}}

event: step_end
data: {"step": 1, "tool": "search_knowledge_base", "output_preview": "Found 3 chunks...", "duration_seconds": 0.42, "status": "success"}

event: token
data: {"content": "According to the employee handbook"}

event: sources
data: {"sources": ["EmployeeHandbook2026.pdf"], "sources_detail": [{"source": "EmployeeHandbook2026.pdf", "chunk_index": 3, "score": 0.91}]}

event: done
data: {"message_id": 108, "conversation_id": 42, "answer": "According to the employee handbook...", "sources": ["EmployeeHandbook2026.pdf"], "sources_detail": [...], "research_trace": [...]}
```

---

### 2.2 GET /api/chat/models

Returns the list of available models and the default model. Sources are consulted in order: `AVAILABLE_MODELS` / per-provider settings, then the remote `/api/tags` at `LLM_API_BASE` (Ollama). No authentication required.

```json
{
  "models": ["gpt-5.6-luna", "gpt-5.6-terra", "gemma4:26b"],
  "default": "gpt-5.6-luna"
}
```

---

### 2.3 GET /api/chat/tools

Returns the Function Calling tool definitions currently available to the Agent (built-in tools + enabled custom API tools + `discovered_tools` of enabled MCP servers).

```json
{
  "status": "success",
  "tools": [
    {"type": "function", "function": {"name": "search_knowledge_base", "description": "...", "parameters": {...}}},
    {"type": "function", "function": {"name": "filter_and_count_records", "...": "..."}},
    {"type": "function", "function": {"name": "web_search", "...": "..."}},
    {"type": "function", "function": {"name": "web_fetch", "...": "..."}},
    {"type": "function", "function": {"name": "get_pet_by_id", "description": "[External custom API]...", "...": "..."}},
    {"type": "function", "function": {"name": "mcp_mcp_time_get_current_time", "...": "..."}}
  ]
}
```

When `status` is `partial`, RAG system initialization failed; only built-in tools are returned, along with an `error` field.

---

### 2.4 Conversation History

| Method | Path | Description | Response |
|---|---|---|---|
| GET | `/api/chat/conversations` | All conversations of the current user | `ConversationResponse[]` (`id`, `title`, `created_at`, `updated_at`, `messages`) |
| POST | `/api/chat/conversations` | Create an empty conversation | `ConversationResponse` |
| GET | `/api/chat/conversations/{id}` | A single conversation with its messages | `ConversationResponse` |
| GET | `/api/chat/conversations/{id}/messages?limit=100&offset=0` | Paginated messages | `MessageResponse[]` |
| DELETE | `/api/chat/conversations/{id}` | Delete a conversation | `{"message": "Conversation deleted"}` |

`MessageResponse` fields: `id`, `content`, `is_user`, `created_at`, `context_used`, `model_name`, `reasoning_effort`, `attachments`, `sources`, `sources_detail`, `research_trace`.

---

### 2.5 WebSocket /api/chat/ws/{user_id}

A reserved, simple bidirectional channel (currently only echoes messages; not the main chat path. Use the SSE endpoint in 2.1 for the main stream).

- Connection URL: `ws://localhost:8001/api/chat/ws/{user_id}`
- Send: `{"content": "..."}`
- Receive: `{"type": "message", "content": "Message received: ...", "timestamp": "now"}`

---

## 3. Knowledge Base and Document Management Module (Documents)

All endpoints require **administrator** privileges (`get_current_admin_user`).

### 3.1 GET /api/documents/

Lists all documents in the knowledge base; if a document lacks a summary, one is generated automatically before returning.

```json
[
  {
    "id": 101,
    "filename": "EmployeeHandbook2026.pdf",
    "file_type": "application/pdf",
    "description": "This document defines employee attendance, leave...",
    "uploaded_by": 1,
    "is_processed": true,
    "created_at": "2026-08-01T10:00:00Z"
  }
]
```

---

### 3.2 POST /api/documents/upload

`multipart/form-data` with the field name `file` (multiple files allowed, up to 10 per request; per-file size limit `MAX_FILE_SIZE_MB`). Supports PDF, TXT, DOCX, PPTX, XLSX, Markdown, and other types determined by `DocumentProcessor`. Each file is processed independently and its result reported separately.

```json
{
  "results": [
    {
      "filename": "EmployeeHandbook2026.pdf",
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
      "detail": "Filename validation failed: invalid filename or disallowed extension",
      "http_status": 400
    }
  ]
}
```

---

### 3.3 POST /api/documents/{document_id}/regenerate-summary

Regenerates the document's summary (`description`) with the LLM.

### 3.4 PUT /api/documents/{document_id}/summary

Manually overwrites the summary. Body: `{"description": "..."}`.

### 3.5 DELETE /api/documents/{document_id}

Removes the database record, the physical file, and the chunks in the vector index. Response: `{"message": "Document deleted successfully"}`.

### 3.6 POST /api/documents/rebuild-index

Clears the index and reprocesses all documents using the current `CHUNK_SIZE` / `CHUNK_OVERLAP`.

```json
{
  "message": "Index rebuild complete",
  "document_count": 12,
  "chunk_count": 348,
  "timestamp": "2026-09-07T08:00:00"
}
```

---

## 4. System Administration Module (Admin)

All endpoints require administrator privileges.

| Method | Path | Description |
|---|---|---|
| GET | `/api/admin/users` | All users |
| PUT | `/api/admin/users/{user_id}` | Update `username` / `email` / `is_active` / `is_admin` |
| DELETE | `/api/admin/users/{user_id}` | Delete a user |
| GET | `/api/admin/statistics` | User, conversation, message, and document statistics with a 7-day trend (cached for 180 seconds) |
| GET | `/api/admin/conversations` | All conversations system-wide |
| GET | `/api/admin/conversations/{id}/messages` | Messages of the specified conversation |
| DELETE | `/api/admin/conversations/{id}` | Delete a conversation |
| GET | `/api/admin/documents` | Document list |
| DELETE | `/api/admin/documents/{id}` | Delete a document |
| GET | `/api/admin/vector-store/info` | Index summary (document count, chunk count, dimensions, etc.) |
| GET | `/api/admin/vector-store/statistics` | Detailed index statistics |
| DELETE | `/api/admin/vector-store/clear` | Clear the vector store |
| POST | `/api/admin/vector-store/reindex` | Trigger `force_reindex()` |
| GET | `/api/admin/rag-config` | Retrieval parameters currently in effect (`chunk_size`, `top_k`, `hybrid_alpha`, `rerank_weight`, `device`, `use_faiss_gpu`, etc.) |

---

## 5. Custom API Tools Module (Custom API Tools)

Registers arbitrary REST APIs as tools the Agent can call. Prefix `/api/api-tools`; login required.

### 5.1 POST /api/api-tools/parse-spec

Parses an OpenAPI / Swagger specification (OAS 2.0, 3.0, 3.1) from either a URL or raw JSON / YAML content; URL loading goes through SSRF validation.

| Field | Type | Required | Description |
|---|---|---|---|
| spec_content_or_url | string | Yes | Specification URL or content |
| default_base_url | string | No | Default Base URL used when the spec does not declare `servers` |

- **200 OK**: `{"status": "success", "data": {...}}`, where `data` contains `spec_version`, `base_url`, and the list of importable endpoints (each with `name`, `display_name`, `description`, `method`, `path`, `full_url`, `parameters_schema`, `request_body_schema`, `param_locations`).
- **400 Bad Request**: parsing failed or the URL was rejected by SSRF protection.

---

### 5.2 POST /api/api-tools/import

Bulk-imports endpoints produced by `parse-spec`; tools with the same name are updated rather than duplicated.

| Field | Type | Required | Description |
|---|---|---|---|
| tools | `OpenApiImportItem[]` | Yes | Selected endpoints (same fields as the 5.1 `data` items; may also carry `base_url`, `headers`, `auth_type`, `auth_config`, `spec_version`) |
| global_base_url | string | No | Base URL applied to all items |
| global_headers | object | No | Shared headers |
| global_auth_type | string | No | `none` / `bearer` / `api_key` / `basic` |
| global_auth_config | object | No | Depends on auth_type: `{token}` / `{key_name, key_value, key_in: header|query}` / `{username, password}` |

```json
{
  "status": "success",
  "message": "Imported 3 new tools and updated 1 existing tool.",
  "imported": 3,
  "updated": 1
}
```

---

### 5.3 Tool CRUD

| Method | Path | Description |
|---|---|---|
| GET | `/api/api-tools?category=&is_enabled=&search=` | List; response `{"status", "total", "tools": [...]}` |
| POST | `/api/api-tools` | Manual creation (`CustomApiToolCreate`: `name`, `display_name`, `description`, `method`, `url`, `headers`, `auth_type`, `auth_config`, `parameters_schema`, `request_body_schema`, `param_locations`, `response_mapping`, `timeout`) |
| GET | `/api/api-tools/{tool_id}` | A single tool |
| PUT | `/api/api-tools/{tool_id}` | Update (all fields optional) |
| PATCH | `/api/api-tools/{tool_id}/toggle` | Toggle `is_enabled` |
| DELETE | `/api/api-tools/{tool_id}` | Delete |

Tool object fields: `id`, `name`, `display_name`, `description`, `category`, `method`, `url`, `base_url`, `path`, `headers`, `auth_type`, `auth_config`, `parameters_schema`, `request_body_schema`, `param_locations`, `response_mapping`, `is_enabled`, `timeout`, `spec_version`, `created_at`, `updated_at`.

---

### 5.4 POST /api/api-tools/{tool_id}/test

Executes the tool directly with the given arguments (bypassing the Agent). Body: `{"arguments": {"petId": 1}}`. Returns the `execute_http_api_tool` result (including status code, elapsed time, and response content, or `error`). The target URL goes through SSRF validation before execution.

---

## 6. MCP Server Module (Model Context Protocol)

Prefix `/api/mcp`; login required. Supports both `stdio` (subprocess) and `http` transports, and interacts with servers via JSON-RPC `initialize` -> `tools/list` -> `tools/call`.

### 6.1 GET /api/mcp/presets

Returns built-in presets (such as the `mcp_time` time zone tool) that can be used directly as the request body for 6.2.

### 6.2 Server CRUD

| Method | Path | Description |
|---|---|---|
| GET | `/api/mcp/servers?is_enabled=` | List; response `{"status", "total", "servers": [...]}` |
| POST | `/api/mcp/servers` | Create (`McpServerCreate`); tool discovery is attempted immediately after creation |
| GET | `/api/mcp/servers/{server_id}` | A single server |
| PUT | `/api/mcp/servers/{server_id}` | Update |
| DELETE | `/api/mcp/servers/{server_id}` | Delete |
| PATCH | `/api/mcp/servers/{server_id}/toggle` | Toggle `is_enabled` |

`McpServerCreate` fields:

| Field | Type | Required | Description |
|---|---|---|---|
| name | string | Yes | Unique identifier (lowercase; used as the tool name prefix `mcp_{name}_`) |
| display_name | string | Yes | Display name |
| description | string | No | Description |
| transport_type | string | No | `stdio` (default) or `http` |
| command / args / env_vars | string / string[] / object | command required for stdio | Subprocess launch settings |
| url / headers | string / object | url required for http | HTTP endpoint |
| timeout | integer | No | Seconds, default 30 |

The server object also contains `status` (`disconnected` / `connected` / `error`), `last_error`, and `discovered_tools`.

### 6.3 POST /api/mcp/servers/{server_id}/discover

Connects immediately and runs `tools/list`; the result is written back to `discovered_tools`.

```json
{
  "status": "success",
  "message": "Connected successfully and discovered 2 MCP tools",
  "tools_count": 2,
  "tools": [{"name": "get_current_time", "description": "...", "inputSchema": {...}}],
  "init_info": {...},
  "server": {...}
}
```

- **400 Bad Request**: connection failed; `status` is set to `error` and `last_error` is recorded.

### 6.4 POST /api/mcp/servers/{server_id}/tools/{tool_name}/test

Calls the specified MCP tool directly. Body: `{"arguments": {...}}`. Response: `{"status", "server_name", "tool_name", "result"}`.

---

## 7. Model Tags Module (Tags)

No authentication required.

| Method | Path | Description |
|---|---|---|
| GET | `/api/tags` | Returns `{"tags": [...], "default": "..."}`; prefers configured provider models, otherwise queries `LLM_API_BASE` and falls back to the built-in list |
| GET | `/api/external-tags` | Proxies the raw response from `EXTERNAL_TAGS_URL` (or `LLM_API_BASE/api/tags`); returns 400 when not configured |

---

## 8. Health Check

| Method | Path | Response |
|---|---|---|
| GET | `/` | `{"message": "ChatBot API is running"}` |
| GET | `/health` | `{"status": "healthy"}` |

---

## 9. Global Error Response Conventions (Error Handling)

The system uses the FastAPI default format, with the error message in `detail`:

```json
{
  "detail": "Invalid access token or token has expired"
}
```

| HTTP status code | Common causes |
|---|---|
| **400 Bad Request** | Invalid parameters, OpenAPI parsing failure, MCP connection failure, SSRF protection rejection |
| **401 Unauthorized** | Missing Authorization header, token expired or revoked |
| **403 Forbidden** | Non-administrator accessing an admin endpoint |
| **404 Not Found** | Conversation, document, tool, or MCP server does not exist |
| **422 Unprocessable Entity** | Pydantic field validation failed |
| **429 Too Many Requests** | Exceeded `RATE_LIMIT_PER_MINUTE` |
| **500 Internal Server Error** | Internal server error; logs are sanitized and details are not returned to the client |
