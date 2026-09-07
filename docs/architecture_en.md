# AskMiao System Architecture & Design

[繁體中文](architecture.md) | [English](architecture_en.md)

> This document describes the actual system architecture of AskMiao 2.x: layered module relationships, the enhanced hybrid RAG retrieval flow, RSA-2048 dual-token authentication with an in-memory blacklist, the Agentic autonomous research loop, the tool extension subsystem (OpenAPI import and MCP), a security overview, the data model, and deployment modes. The code is the source of truth (`backend/main.py`, `backend/app/core/config.py`, etc.); if this document and the code disagree, follow the code and submit a correction.

---

## 1. Overall Layered Architecture

AskMiao uses a decoupled frontend/backend, modular architecture. The frontend is powered by React 19 + TypeScript + Vite 8 + Bun, styled with CSS Modules and design tokens (`src/styles/tokens.css`) together with an in-house UI component library (`src/components/ui/`), and **does not depend on MUI**. The backend is FastAPI (`backend/main.py`), exposing RESTful APIs and SSE streaming; it starts with zero dependencies on SQLite by default, with PostgreSQL as an option. Vector and keyword indices are stored as local files (FAISS, Whoosh).

```mermaid
flowchart TB
    subgraph Client ["Frontend Application Layer (React 19 + TypeScript + Vite 8 + Bun)"]
        Router["App.jsx routing (PrivateRoute / AdminRoute)"]
        ChatPage["Chat/index.tsx chat page (model / reasoning effort / Research Trace)"]
        ToolsPage["AiTools.jsx (/tools) custom API tools and MCP management"]
        DocsPage["Documents.jsx (/documents, admin)"]
        AdminPage["AdminDashboard.jsx (/admin)"]
        UIKit["components/ui + CSS Modules + tokens.css"]
    end

    subgraph Middleware ["Middleware Layer (app/middleware.py)"]
        SecHeaders["SecurityHeadersMiddleware"]
        RateLimit["RateLimitMiddleware (RATE_LIMIT_ENABLED)"]
        CORS["CORSMiddleware (ALLOWED_ORIGINS allowlist)"]
    end

    subgraph Backend ["FastAPI Backend (backend/main.py)"]
        AuthAPI["auth.py /api/auth"]
        ChatAPI["chat.py /api/chat (SSE streaming)"]
        DocAPI["documents.py /api/documents"]
        AdminAPI["admin.py /api/admin"]
        ApiToolsAPI["api_tools.py /api/api-tools"]
        McpAPI["mcp.py /api/mcp"]
        TagsAPI["tags.py /api/tags, /api/external-tags"]

        subgraph Lifespan ["core/lifespan.py lifecycle"]
            CreateTables["create_tables()"]
            RagSingleton["get_rag_system() singleton (core/rag_manager.py)"]
            UploadsWatcher["tasks/uploads_watcher.py"]
            IndexRebuilder["tasks/index_rebuilder.py"]
        end

        subgraph RAG ["Agentic RAG Core (app/rag/)"]
            Facade["contextual_rag.py facade"]
            Pipeline["pipeline.py execution pipeline"]
            Agent["agent.py ResearchAgent"]
            Registry["tools.py ResearchToolRegistry"]
            Hybrid["retrievers/hybrid.py hybrid retrieval + Cross-Encoder"]
        end

        LLMClient["core/llm_client.py unified LLM client"]
    end

    subgraph Storage ["Storage Layer"]
        DB[(SQLite default / PostgreSQL optional)]
        FAISS["FAISS vector index (data/faiss_index.bin)"]
        Whoosh["Whoosh BM25 index (data/bm25_index)"]
        Uploads["data/uploads original documents"]
        HFCache["data/hf_home model cache"]
    end

    subgraph External ["External Systems"]
        LLMs["Azure OpenAI v1 / OpenAI / Anthropic / Gemini / Ollama"]
        WebSearch["DuckDuckGo / Ollama Web Search"]
        McpServers["MCP servers (stdio / http)"]
        RestApis["Custom REST APIs (OpenAPI import)"]
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

### Layer Responsibilities

| Layer | Main Modules | Responsibilities |
|---|---|---|
| Frontend | `frontend/src/App.jsx`, `pages/*`, `components/ui/*`, `hooks/*`, `services/api.ts` | Route guards, chat and research trace rendering, tool and document management UI, Axios interceptors and token refresh |
| Middleware | `backend/app/middleware.py`, `core/security.py` | Security headers, rate limiting, CORS allowlist |
| API Routes | `backend/app/api/*.py` | Seven route groups, all mounted by `main.py` |
| Core Services | `core/jwt_auth.py`, `core/llm_client.py`, `core/security_logging.py`, `core/ssrf_protection.py` | Authentication, LLM provider abstraction, log redaction, egress protection |
| RAG Engine | `app/rag/*` | Retrieval, reranking, agent loop, tool aggregation |
| Business Services | `services/chat_service.py`, `document_processor.py`, `openapi_parser.py`, `mcp_service.py` | Conversation persistence, document parsing, OpenAPI parsing, MCP client |
| Background Tasks | `tasks/uploads_watcher.py`, `tasks/index_rebuilder.py` | Upload directory cleanup, scheduled index rebuilds |

---

## 2. Enhanced Hybrid RAG Retrieval and Reranking Pipeline

The system runs dense vector search and sparse keyword search in parallel, fuses the normalized scores, and then passes the candidates to a Cross-Encoder reranker. All parameters are centralized in `backend/app/core/config.py` and can be overridden via `.env`.

```mermaid
flowchart LR
    Query["User query (Query)"] --> Strategy{"retrievers/hybrid.py\nsmart_search strategy dispatch"}

    subgraph ParallelRetrieval ["Parallel Dual-Track Retrieval"]
        Strategy -->|vector match| FAISS["indices/vector_store.py\nFAISS inner-product search (bge-small-zh-v1.5, 384 dims)"]
        Strategy -->|keyword match| BM25["indices/bm25_store.py\nWhoosh BM25 (tokenizers.py Jieba tokenization)"]
    end

    FAISS --> Merge["Normalized score fusion\n(HYBRID_ALPHA, NORMALIZATION)"]
    BM25 --> Merge
    Merge --> Reranker["Cross-Encoder reranking\n(RERANKER_MODEL, RERANK_WEIGHT)"]
    Reranker --> TopK["FINAL_K selection + FINAL_THRESHOLD filtering"]
    TopK --> Context["pipeline.py context assembly"]
```

### Retrieval Parameters (`config.py` defaults)

| Parameter | Default | Description |
|---|---|---|
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 800 / 150 | `RecursiveCharacterTextSplitter` chunk size in characters and overlap |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 384-dimensional embedding model |
| `RERANKER_MODEL` | `BAAI/bge-reranker-base` | Cross-Encoder reranking model |
| `TOP_K` / `RERANK_TOP_K` / `FINAL_K` | 30 / 50 / 8 | Initial recall, rerank candidates, final output chunk count |
| `HYBRID_ALPHA` | 0.75 | Vector score weight (1 - alpha is the BM25 weight) |
| `RERANK_WEIGHT` | 0.85 | Weighting ratio between the rerank score and the fused score |
| `SIMILARITY_THRESHOLD` / `FINAL_THRESHOLD` | 0.30 / 0.15 | Initial retrieval and final filtering thresholds |
| `NORMALIZATION` | `max` | Score normalization method |
| `FORCE_CPU` / `USE_FAISS_GPU` | `true` / `false` | CPU inference by default; GPU is optional |

> Note: `backend/.env.example` ships `CHUNK_SIZE=300` and `CHUNK_OVERLAP=100`, which override the defaults above; both are valid configurations. The configuration governance item in `docs/adr/0002` will unify the source of truth.

`evaluator.py` provides Hit-Rate / MRR evaluation and automatic Alpha tuning; the index files under `indices/` are rebuilt on a schedule by `tasks/index_rebuilder.py` according to `REINDEX_HOURS`.

---

## 3. RSA-2048 Dual-Token Authentication and In-Memory Blacklist

The system uses a dual-token scheme: an Access Token (30 minutes by default, sent in the HTTP header) and a Refresh Token (7 days by default, HttpOnly cookie), signed with RS256 by `core/jwt_auth.py` (`core/rsa_keys.py` loads the keys; if loading fails in development the system falls back to HS256 and logs a warning, while production raises an error).

**Revocation**: `TokenBlacklist` in `core/redis_client.py` is currently a **single-process in-memory implementation** (class-level dict + `threading.Lock`, with lazy cleanup of expired entries); `init_redis` / `get_redis` / `close_redis` are compatibility stubs only. On logout, `revoke_token()` writes the **full string** of both the Access Token and the Refresh Token into the blacklist, with the expiry taken from the token's `exp`.

```mermaid
sequenceDiagram
    autonumber
    actor Browser as Browser / Frontend
    participant Auth as api/auth.py
    participant JWT as core/jwt_auth.py
    participant BL as TokenBlacklist (in-memory)
    participant DB as SQLite / PostgreSQL

    Browser->>Auth: POST /api/auth/login (username, password)
    Auth->>DB: Look up user and verify argon2 hash
    DB-->>Auth: Verification passed
    Auth->>JWT: create_token_pair()
    JWT-->>Auth: access_token (30m) + refresh_token (7d)
    Auth-->>Browser: JSON access_token + Set-Cookie refresh_token (HttpOnly)

    Browser->>Auth: GET /api/auth/me (Authorization: Bearer)
    Auth->>JWT: verify_token()
    JWT->>BL: is_blacklisted(token)?
    BL-->>JWT: No
    JWT-->>Auth: payload
    Auth-->>Browser: UserProfile

    Browser->>Auth: POST /api/auth/refresh (Cookie)
    Auth->>JWT: verify_refresh_token()
    JWT-->>Auth: New access_token
    Auth-->>Browser: Token

    Browser->>Auth: POST /api/auth/logout
    Auth->>JWT: revoke_token(access) / revoke_token(refresh)
    JWT->>BL: add_token(token, expires_in)
    Auth-->>Browser: Clear cookie, return logout success
```

### Known Limitations

- The blacklist lives in the memory of a single Python process: with multiple workers (`uvicorn --workers N`) or after a restart, a revoked token still passes verification in other processes until it expires naturally.
- The blacklist stores the entire token rather than a JTI, so memory usage is higher.
- Both points are addressed by the pluggable blacklist backend planned in [ADR-0002](./adr/0002-platform-hardening-and-tool-extension-roadmap_en.md); the Redis description in ADR-0001 no longer applies.

---

## 4. Agentic RAG Autonomous Research and Multi-Turn Tool Calling Pipeline

`POST /api/chat/send` streams its response via **Server-Sent Events**. The `contextual_rag.py` facade calls `pipeline.py`, which hands off to `ResearchAgent.stream_research()` in `agent.py` for multi-turn Native Tool Calling in ReAct style; tool specifications are aggregated dynamically from three sources by `ResearchToolRegistry.get_tool_definitions()` in `tools.py`.

```mermaid
flowchart LR
    Send["POST /api/chat/send\n(content, model_name, reasoning_effort, attachments)"] --> Facade["contextual_rag.py\ngenerate_response_stream"]
    Facade --> Pipeline["pipeline.py"]
    Pipeline --> Agent["agent.py ResearchAgent\nstream_research(max_turns=AGENT_MAX_TURNS)"]

    subgraph Registry ["tools.py ResearchToolRegistry.get_tool_definitions()"]
        Builtin["Built-in tools\nsearch_knowledge_base\nfilter_and_count_records\nweb_search\nweb_fetch"]
        Custom["custom_api_tools table\n(is_enabled=true)"]
        Mcp["mcp_servers.discovered_tools\n→ mcp_{server}_{tool}"]
    end

    Agent -->|tool_calls| Registry
    Registry -->|"execute_tool(name, args)"| Exec{"Dispatch"}
    Exec -->|built-in| Hybrid["retrievers/hybrid.py\nor DuckDuckGo / Ollama / safe_fetch_text"]
    Exec -->|mcp_*| McpExec["McpManager.execute_mcp_tool"]
    Exec -->|other names| HttpExec["api_tools.execute_http_api_tool"]
    Hybrid & McpExec & HttpExec -->|observation| Agent
    Agent --> LLM["core/llm_client.py\n(reasoning_effort passthrough)"]
    Agent -->|SSE events| Events["start → step_start / step_end → token → sources → done"]
```

### Core Mechanisms of Autonomous Research

1. **Dynamic tool descriptions**: `_generate_knowledge_base_description()` builds the description of `search_knowledge_base` from the current index contents so the model knows which documents the knowledge base covers.
2. **Structured statistics tool**: `filter_and_count_records` performs exact counts and listings by date, author, keyword, and specific documents, so the model does not answer "how many in total" with an estimate.
3. **Research Trace**: the steps, arguments, output summaries, and elapsed time of each tool call are pushed in real time as `step_start` / `step_end` events, and persisted in the `done` event and in `messages.context_used`.
4. **Sources Detail**: internal chunks and external URLs are unified as `sources_detail`; the frontend `SourceBadges.tsx` provides click-through navigation.
5. **Reasoning Effort**: `none` / `low` / `medium` / `high` / `xhigh` are passed through to Azure OpenAI v1 and OpenAI reasoning models, with tool-calling compatibility handled according to the Foundry specification.

---

## 5. Tool Extension Subsystem (OpenAPI Import and MCP)

2.x adds two paths for registering external capabilities as Agent tools, both managed in the frontend at `/tools` (`pages/AiTools.jsx`).

```mermaid
flowchart LR
    subgraph OpenAPI ["Path A: Custom REST API Tools (api/api_tools.py)"]
        ParseSpec["POST /api/api-tools/parse-spec\n(URL or JSON/YAML content)"] --> Parser["services/openapi_parser.py\nOAS 2.0 / 3.0 / 3.1, $ref resolution"]
        Parser --> Pick["Frontend selects endpoints"]
        Pick --> Import["POST /api/api-tools/import\n(global_base_url / auth / headers)"]
        Import --> CustomTable[("custom_api_tools")]
        CustomTable --> HttpExec["execute_http_api_tool\nPath / Query / Header / Body assembly\nbearer / api_key / basic auth"]
    end

    subgraph MCP ["Path B: MCP Servers (api/mcp.py)"]
        Presets["GET /api/mcp/presets"] --> Create["POST /api/mcp/servers\n(transport: stdio | http)"]
        Create --> Client["services/mcp_service.py\nMcpStdioClient / McpHttpClient\nJSON-RPC initialize → tools/list"]
        Client --> Discover["POST /servers/{id}/discover\nwrites back discovered_tools / status"]
        Discover --> McpTable[("mcp_servers")]
        McpTable --> McpExec["McpManager.execute_mcp_tool\n(tools/call)"]
    end

    CustomTable & McpTable --> Registry["tools.py ResearchToolRegistry\nget_tool_definitions() aggregation"]
    Registry --> ChatTools["GET /api/chat/tools\n(inspect currently enabled tools)"]
    Registry --> Agent["ResearchAgent"]
    HttpExec & Client -.->|before egress| SSRF["core/ssrf_protection.py"]
```

### Design Highlights

- **Naming rules**: custom API tools use `custom_api_tools.name` directly as the function name; MCP tools are named `mcp_{server_name}_{tool_name}`, and `execute_tool` dispatches by prefix.
- **Auth and parameter locations**: `auth_type` (`none` / `bearer` / `api_key` / `basic`) and `param_locations` (path / query / header / body) are parsed and stored at import time, so the original spec does not need to be read at execution time.
- **Test endpoints**: `POST /api/api-tools/{id}/test` and `POST /api/mcp/servers/{id}/tools/{name}/test` allow tools to be verified without going through the Agent.
- **Known technical debt**: the merge and dispatch logic for the three sources is concentrated in conditional branches in `tools.py`; [ADR-0002](./adr/0002-platform-hardening-and-tool-extension-roadmap_en.md) plans to abstract it into a `ToolProvider` interface.

---

## 6. Security Overview

```mermaid
flowchart TB
    subgraph Transport ["Transport Layer"]
        H["SecurityHeadersMiddleware"]
        R["RateLimitMiddleware (RATE_LIMIT_PER_MINUTE)"]
        C["CORS allowlist (ALLOWED_ORIGINS, DEVTUNNEL_URL)"]
    end
    subgraph AuthLayer ["Authentication Layer"]
        J["RS256 JWT + HttpOnly Refresh Cookie"]
        B["TokenBlacklist (in-memory)"]
        A["get_current_admin_user / ADMIN_API_KEY"]
    end
    subgraph Input ["Input Layer"]
        V["core/input_validator.py filename and URL validation"]
        I["core/intrusion_detection.py"]
    end
    subgraph Egress ["Egress Layer (SSRF)"]
        S["core/ssrf_protection.py\nvalidate_url_ssrf / safe_fetch_text\nRejects private, loopback, link-local IPs; re-checks after DNS resolution"]
    end
    subgraph Logging ["Logging Layer"]
        L["core/security_logging.py two-layer redaction → [REDACTED]"]
        AU["core/audit_logger.py / security_monitor.py"]
    end
    Transport --> AuthLayer --> Input --> Egress --> Logging
```

### Egress SSRF Protection Call Sites

| Call Site | File |
|---|---|
| Agent `web_fetch` tool | `backend/app/rag/tools.py` |
| OpenAPI spec loaded from URL | `backend/app/services/openapi_parser.py` |
| Before custom API tool execution | `backend/app/api/api_tools.py` |
| General URL validation | `backend/app/core/input_validator.py` |

### Two-Layer Sensitive Data Redaction (`core/security_logging.py`)

1. **Object-level recursive redaction `sanitize_sensitive_data`**: walks dicts and lists, matches case-insensitive fields such as `password`, `token`, `secret`, `authorization`, and `cookie`, and replaces their values with `[REDACTED]`.
2. **String-level regex masking**: a second scan before JSON serialization or log output ensures that no key in any format leaks into `backend/logs/app.log`. This mechanism was introduced to fix the CodeQL `py/clear-text-logging-sensitive-data` alert.

---

## 7. Data Model

All tables are defined in `backend/app/models/__init__.py` and created at startup by `Base.metadata.create_all` in `models/database.py` (there are currently no Alembic migrations). JSON-typed columns are stored as serialized strings in `Text`.

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
        text description "AI summary"
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

## 8. Deployment Modes

| Mode | Database | Startup | Blacklist | Suitable For |
|---|---|---|---|---|
| **Lite (default)** | SQLite (`DATABASE_URL=sqlite:///./chatbot.db`) | `python main.py`, a single uvicorn process | In-memory | Local development, single-machine deployment, evaluation |
| **Standard** | PostgreSQL 17.9 (`backend/docker-compose.yml`, host port **7690**) | `docker compose -f backend/docker-compose.yml up -d`, then start the backend; `DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot` | In-memory (same limitations as above) | Multiple users, connection pooling and backups required |

Shared prerequisites:

- `DATABASE_URL`, `ADMIN_API_KEY`, and `JWT_SECRET_KEY` are required environment variables (`config.py` provides no defaults).
- The first startup downloads the embedding and reranking models into `HF_HOME` (default `./data/hf_home`), which requires internet access or pre-placed models.
- Index files (FAISS, Whoosh, `documents.pkl`) live in `DATA_DIR` and are not shared across multiple instances; horizontal scaling first requires solving blacklist and index sharing (see ADR-0002).

---

## 9. Architecture Decision Records (ADR)

- [ADR index and overview](./adr/README_en.md)
- [ADR-0001: Enhanced Hybrid RAG Retrieval Architecture and Dual-Token Security Decisions](./adr/0001-hybrid-rag-and-security_en.md): accepted; the Redis blacklist and caching portions have been superseded by the in-memory implementation in 2.0.0.
- [ADR-0002: 2.x Platform Hardening and Tool Extension Architecture Roadmap](./adr/0002-platform-hardening-and-tool-extension-roadmap_en.md): proposed; covers CI, a pluggable blacklist, test coverage, Alembic, the ToolProvider abstraction, completing the TSX migration, observability, and configuration governance.
