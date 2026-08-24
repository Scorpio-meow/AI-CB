# AskMiao API Reference Manual

[繁體中文](api.md) | [English](api_en.md)

> This document specifies the RESTful API endpoints and WebSocket protocol provided by the AskMiao system. An interactive Swagger UI is available at `/docs` when the server is running.

---

## 1. Authentication Module

### 1.1 POST /api/auth/register

User registration endpoint.

**Headers:**

```http
Content-Type: application/json
```

**Request Body:**

| Field Name | Type | Required | Description | Constraints |
|---|---|---|---|---|
| username | string | Yes | Username | 3-50 chars, alphanumeric, underscore, hyphen |
| email | string | Yes | Email address | Valid email format |
| password | string | Yes | User password | At least 8 chars, uppercase/lowercase and digits |

**Responses:**

- **201 Created**: Registration successful, returns user object and Access Token.

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
  "message": "Registration successful"
}
```

- **400 Bad Request**: Username or Email already registered.

---

### 1.2 POST /api/auth/login

User authentication endpoint. Returns Access Token and sets Refresh Token into HttpOnly Cookie.

**Headers:**

```http
Content-Type: application/json
```

**Request Body:**

| Field Name | Type | Required | Description |
|---|---|---|---|
| username | string | Yes | Username or email address |
| password | string | Yes | User password |

**Responses:**

- **200 OK**: Login successful.

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
  "message": "Login successful"
}
```

- **401 Unauthorized**: Invalid credentials.

---

### 1.3 POST /api/auth/refresh

Silent Access Token refresh endpoint. Reads `refresh_token` from HttpOnly Cookie automatically.

**Headers:**
No Authorization header needed; system validates Cookie credentials automatically.

**Responses:**

- **200 OK**: Refresh successful, returns new Access Token.

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

- **401 Unauthorized**: Refresh Token expired or invalid.

---

### 1.4 GET /api/auth/me

Fetch profile information of current authenticated user.

**Headers:**

```http
Authorization: Bearer <access_token>
```

**Responses:**

- **200 OK**: Profile retrieved.

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

User logout endpoint. Blacklists current Access Token JTI in Redis and clears Refresh Token Cookie.

**Headers:**

```http
Authorization: Bearer <access_token>
```

**Responses:**

- **200 OK**: Logout successful.

```json
{
  "message": "Logout successful"
}
```

---

## 2. Chat & Agentic RAG Autonomous Research Module

### 2.1 POST /api/chat/send

Send a user query to trigger the ReAct autonomous ResearchAgent for multi-turn tool calling and contextual response generation.

**Headers:**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**

| Field Name | Type | Required | Description | Default |
|---|---|---|---|---|
| `content` | string | Yes | User query message content | - |
| `conversation_id` | integer | No | Conversation ID (or null for new session) | null |
| `model_name` | string | No | Target LLM model name (e.g. `gpt-5.6-luna`, `gemma4:26b`) | System default |
| `reasoning_effort` | string | No | Model reasoning depth (`none`, `low`, `medium`, `high`, `xhigh`) | `medium` |

**Responses (ChatResponse):**

- **200 OK**: Autonomous research response generated.

```json
{
  "conversation_id": 42,
  "message": {
    "id": 108,
    "content": "MiTAC Agent Builder is an enterprise-grade agentic AI platform...",
    "is_user": false,
    "created_at": "2026-08-24T18:04:07Z",
    "model_name": "gpt-5.6-luna",
    "reasoning_effort": "medium",
    "sources": [
      "https://example.com/mitac-agent-builder",
      "Company_Handbook.pdf"
    ],
    "sources_detail": [
      {
        "source": "https://example.com/mitac-agent-builder",
        "title": "MiTAC Agent Builder Overview",
        "url": "https://example.com/mitac-agent-builder",
        "snippet": "MiTAC Agent Builder orchestrates multi-agent workflows..."
      }
    ],
    "research_trace": [
      {
        "step": 1,
        "tool": "web_search",
        "arguments": {
          "query": "MiTAC Agent Builder"
        },
        "output_preview": "Retrieved 5 external results...",
        "duration_seconds": 1.25,
        "status": "success"
      }
    ]
  }
}
```

---

### 2.2 GET /api/chat/models

Retrieve all currently available LLM models and the default deployment.

**Responses:**

- **200 OK**: Model list retrieved.

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

Fetch user conversation history list.

**Headers:**

```http
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter | Type | Required | Description | Default |
|---|---|---|---|---|
| limit | integer | No | Max number of records | 20 |
| offset | integer | No | Pagination offset | 0 |

**Responses:**

- **200 OK**:

```json
{
  "total": 1,
  "items": [
    {
      "conversation_id": 42,
      "title": "Annual Leave Inquiry",
      "updated_at": "2026-08-03T01:30:00Z"
    }
  ]
}
```

---

### 2.3 WebSocket /ws/chat

Real-time streaming bidirectional chat channel.

**Connection URL:** `ws://localhost:8001/ws/chat`

**User Message JSON Payload:**

```json
{
  "message": "Please summarize key points of this file",
  "conversation_id": 42,
  "token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Server Stream Response JSON:**

```json
{
  "response": "Response token chunk...",
  "done": false
}
```

Stream completion payload:

```json
{
  "response": "",
  "done": true,
  "sources": [
    { "source": "Project_Spec.pdf", "score": 0.92 }
  ]
}
```

---

## 3. Knowledge Base & Document Management Module

### 3.1 GET /api/documents/list

List all indexed documents in the knowledge base.

**Headers:**

```http
Authorization: Bearer <access_token>
```

**Responses:**

- **200 OK**:

```json
{
  "documents": [
    {
      "id": 101,
      "filename": "Employee_Policy_2026.pdf",
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

Upload files to knowledge base for chunking, FAISS vector indexing, and Whoosh BM25 indexing.

**Headers:**

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request Parameters:**

- `files`: File array (Supports PDF, TXT, DOCX; max 10MB per file, max 10 files per request).

**Responses:**

- **200 OK**:

```json
{
  "uploaded_files": [
    {
      "id": 101,
      "filename": "Employee_Policy_2026.pdf",
      "status": "success",
      "chunks_created": 15
    }
  ]
}
```

---

### 3.3 POST /api/documents/bulk_delete

Delete specified knowledge base documents and their associated indices.

**Headers:**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "ids": [101, 102]
}
```

**Responses:**

- **200 OK**:

```json
{
  "message": "Successfully deleted 2 documents and indices"
}
```

---

## 4. Multi-Agent Collaboration Workflow Module

### 4.1 GET /api/workflow/agents

Retrieve available Agent role definitions supported by system.

**Headers:**

```http
Authorization: Bearer <access_token>
```

**Responses:**

- **200 OK**:

```json
{
  "agents": [
    {
      "id": "researcher",
      "name": "Researcher Agent",
      "description": "Retrieves facts from knowledge base and provides context"
    },
    {
      "id": "critic",
      "name": "Critic Agent",
      "description": "Reviews researcher outputs and identifies potential logic gaps"
    }
  ]
}
```

---

### 4.2 POST /api/workflow/execute

Initiate a multi-Agent collaborative discussion task.

**Headers:**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "topic": "Evaluate latency impact of Contextual Hybrid RAG",
  "participating_agents": ["researcher", "critic"],
  "max_rounds": 3
}
```

**Responses:**

- **202 Accepted**: Task queued for execution.

```json
{
  "workflow_id": "wf-882319",
  "status": "running",
  "message": "Workflow started"
}
```

---

## 5. Global Error Handling Schema

The API enforces standard HTTP status codes combined with unified JSON error payloads.

### Error Response JSON Payload

```json
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid or expired Access Token",
    "details": null
  }
}
```

### Common HTTP Status Codes

| HTTP Status | Error Code | Description & Possible Cause |
|---|---|---|
| **400 Bad Request** | `INVALID_PARAMETER` | Malformed request body or missing required field |
| **401 Unauthorized** | `UNAUTHORIZED` | Missing Authorization header or revoked/expired JWT |
| **403 Forbidden** | `PERMISSION_DENIED` | Insufficient permissions (e.g. non-admin accessing admin portal) |
| **404 Not Found** | `RESOURCE_NOT_FOUND` | Target resource (chat, document, agent) not found |
| **422 Unprocessable Entity** | `VALIDATION_ERROR` | FastAPI schema validation failed |
| **500 Internal Server Error** | `SERVER_ERROR` | Internal server exception |