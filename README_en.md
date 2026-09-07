# AskMiao (AI ChatBot)

An enterprise-grade intelligent knowledge-base conversational system powered by Contextual Hybrid RAG (Retrieval-Augmented Generation) and Agentic Autonomous Research architectures.

[繁體中文](README.md) | [English](README_en.md)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Vite-8.0-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Bun](https://img.shields.io/badge/Bun-1.0+-FBF0DF?style=flat&logo=bun&logoColor=black)](https://bun.sh/)
[![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Quick Start](#quick-start) | [Core Features](#core-features) | [System Architecture](#system-architecture) | [Directory Structure](#directory-structure) | [Environment Variables](#environment-variables) | [Documentation](#documentation) | [Contributing](#contributing) | [License](#license)

---

## Quick Start

### Requirements

| Component | Minimum Version | Recommended Tool & Purpose |
|---|---|---|
| Python | 3.10 or higher | Backend FastAPI server, RAG vector indexing, and Agentic research engine |
| Bun | 1.0 or higher | Preferred package manager and build tool for frontend |
| SQLite | 3.x (Built-in) | Default relational database with zero-dependency local launch |

### 1. Clone Repository

```bash
git clone https://github.com/Scorpio-meow/AskMiao.git
cd AskMiao
```

### 2. Backend Setup & Launch

```bash
cd backend

# Create and activate Python virtual environment
py -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Create the environment file and fill in at least DATABASE_URL, ADMIN_API_KEY, JWT_SECRET_KEY
# For a zero-dependency launch set DATABASE_URL=sqlite:///./chatbot.db
cp .env.example .env

# Initialize database schema and admin account
py init_db.py

# Start FastAPI development server (Port 8001)
py main.py
```

Optional: use PostgreSQL instead (`backend/docker-compose.yml`, exposed on port 7690)

```bash
docker compose -f docker-compose.yml up -d
# Set in .env
# DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot
```

### 3. Frontend Setup & Launch (Bun Preferred)

```bash
cd ../frontend

# Install frontend dependencies using Bun
bun install

# Create the frontend environment file (PORT=3001, /api proxied to the backend on 8001)
cp .env.example .env

# Start Vite development server (Port 3001)
bun run dev
```

Once launched, navigate to `http://localhost:3001` in your browser to start using AskMiao (the backend `ALLOWED_ORIGINS` default already allows this origin).

---

## Core Features

1. **Agentic RAG & Multi-Turn Autonomous Research**:
   - Built-in ReAct research agent (`ResearchAgent`) supporting Native Tool Calling.
   - Comprehensive toolset including internal knowledge search (`search_knowledge_base`), real-time web search (`web_search` with Ollama & DuckDuckGo dual-engine fallback), and deep web fetch (`web_fetch`).
   - Collapsible research trace timeline (`ResearchTraceBlock`) and clickable reference badges (`SourceBadges`) in frontend UI.

2. **Reasoning Effort Multi-Tier Selection**:
   - Navigation header selector with 5 reasoning depth levels: `None (none)`, `Low (low)`, `Medium (medium)`, `High (high)`, and `Extreme (xhigh)`.
   - Full support for Azure OpenAI v1 and OpenAI reasoning models (GPT-5 series, o-series).
   - Automatic compatibility enforcement with tool calls per Microsoft Foundry specifications.

3. **Modular Contextual Hybrid RAG Pipeline**:
   - Integrates dense vector search (FAISS) and sparse Chinese keyword search (Whoosh BM25).
   - Re-ranked dynamically by Cross-Encoder (default `BAAI/bge-reranker-base`) for optimal precision.
   - Automated dynamic Alpha tuning and quantitative RAG evaluation metrics (Hit Rate, MRR).

4. **Custom API Tools & MCP Tool Extension**:
   - Paste an OpenAPI / Swagger spec (2.0 / 3.0 / 3.1) or URL, tick the endpoints, and import them as Agent-callable tools with bearer / api_key / basic auth support.
   - Connect MCP (Model Context Protocol) servers over stdio or HTTP; tools are discovered automatically and registered as `mcp_{server}_{tool}`.
   - Managed centrally on the `/tools` page; `GET /api/chat/tools` exposes every tool currently available to the Agent.

5. **Multi-Provider LLM Integration**:
   - Unified abstraction layer supporting dynamic switching between Azure OpenAI v1, OpenAI Official, Anthropic Claude, Google Gemini, and local Ollama models with automatic multi-model list normalization.

6. **Enterprise Security, SSRF Protection & Two-Layer Data Redaction**:
   - Dual-token security with RSA-2048 signed Access Tokens and HttpOnly Secure Cookies.
   - Every model- or user-supplied URL (web fetch, OpenAPI loading, custom API execution) is validated by `ssrf_protection.py`, blocking private and internal network ranges.
   - Recursive object-level masking and regex redaction (`security_logging.py`) preventing credential leaks in logs.

---

## System Architecture

```mermaid
flowchart TB
    subgraph Client ["Frontend Client (React 19 + TypeScript + Vite 8 + Bun)"]
        UI["Chat Interface (CSS Modules + in-house UI Kit)"]
        TraceView["Research Trace Timeline (ResearchTraceBlock)"]
        ToolsView["Tool Management (/tools, AiTools)"]
        DocManage["Document Management (Documents)"]
        AdminView["Admin Dashboard (AdminDashboard)"]
    end

    subgraph Backend ["Backend Layer (FastAPI + Python 3.10+)"]
        Middleware["Middleware (SecurityHeaders / RateLimit / CORS)"]
        AuthService["JWT Auth Service (RSA-2048, /api/auth)"]
        ChatAPI["Chat SSE Endpoint (/api/chat)"]
        DocAPI["Document Indexing Endpoint (/api/documents)"]
        ToolsAPI["Custom API Tools (/api/api-tools)"]
        McpAPI["MCP Servers (/api/mcp)"]

        subgraph AgenticRAG ["Agentic RAG Core Pipeline"]
            Agent["Research Agent (ResearchAgent)"]
            ToolRegistry["Tool Registry (ResearchToolRegistry)"]
            HybridRetriever["Hybrid Retriever (FAISS + BM25 + Cross-Encoder)"]
            LLMClient["Unified LLM Client (Azure / OpenAI / Claude / Gemini / Ollama)"]
        end
        SSRF["Outbound SSRF Protection (ssrf_protection.py)"]
    end

    subgraph Storage ["Storage & Index Layer"]
        SQLiteDB[(SQLite default / PostgreSQL optional)]
        FAISSStore["FAISS Vector Index (faiss_index.bin)"]
        BM25Store["Whoosh BM25 Index Directory"]
        DocUploads["Uploads Directory (data/uploads)"]
    end

    UI & TraceView & ToolsView & DocManage & AdminView --> Middleware
    Middleware --> AuthService & ChatAPI & DocAPI & ToolsAPI & McpAPI

    ChatAPI --> Agent
    Agent --> ToolRegistry
    ToolRegistry --> HybridRetriever
    ToolRegistry -.-> |Web Search| DuckDuckGo["DuckDuckGo / Ollama Web Search"]
    ToolRegistry -.-> |Deep Fetch| WebContent["External Web Content (HTTP Fetch)"]
    ToolRegistry -.-> |custom_api_tools| ExtApi["Custom REST APIs"]
    ToolRegistry -.-> |mcp_servers| McpSrv["MCP Servers (stdio / http)"]
    ToolRegistry --> SSRF

    Agent --> LLMClient
    HybridRetriever --> FAISSStore
    HybridRetriever --> BM25Store
    DocAPI --> DocUploads
    AuthService & ChatAPI & ToolsAPI & McpAPI --> SQLiteDB
```

---

## Directory Structure

```text
AskMiao/
├── backend/                        # Backend FastAPI project
│   ├── app/
│   │   ├── api/                    # Route endpoints (auth, chat, documents, admin, api_tools, mcp, tags)
│   │   ├── core/                   # Core configurations, auth, security logging & LLM client
│   │   │   ├── config.py           # Global settings & environment configuration (single source of truth)
│   │   │   ├── lifespan.py         # Startup / shutdown flow and background tasks
│   │   │   ├── jwt_auth.py         # RSA-2048 JWT signing and token verification
│   │   │   ├── redis_client.py     # TokenBlacklist (single-process in-memory implementation)
│   │   │   ├── llm_client.py       # Multi-provider LLM calling client
│   │   │   ├── ssrf_protection.py  # Outbound URL SSRF validation
│   │   │   └── security_logging.py # Sensitive data redaction logging system
│   │   ├── middleware.py           # SecurityHeaders / RateLimit / CORS
│   │   ├── models/                 # SQLAlchemy ORM and Pydantic schemas
│   │   ├── rag/                    # Modular RAG and Agentic research engine
│   │   │   ├── agent.py            # ReAct Research Agent
│   │   │   ├── tools.py            # Built-in tools + custom API + MCP tool aggregation
│   │   │   ├── pipeline.py         # RAG pipeline execution & prompt assembly
│   │   │   ├── contextual_rag.py   # HybridContextualRAG facade module
│   │   │   ├── evaluator.py        # Retrieval evaluation & auto-tune Alpha
│   │   │   ├── indices/            # FAISS and BM25 store handlers
│   │   │   └── retrievers/         # Hybrid search & Cross-Encoder re-rankers
│   │   ├── services/               # Business logic (chat, document_processor, openapi_parser, mcp_service)
│   │   └── tasks/                  # Background tasks (periodic reindexing, uploads watcher)
│   ├── tests/                      # pytest suite (agentic, api_tools, mcp, openapi, rag, ssrf)
│   ├── docker-compose.yml          # Optional PostgreSQL 17.9 (host port 7690)
│   ├── main.py                     # FastAPI application entry point
│   ├── init_db.py                  # Database initialization and admin seeder
│   └── requirements.txt            # Python dependencies
├── frontend/                       # Frontend React 19 + TypeScript + Vite 8 project
│   ├── src/
│   │   ├── pages/                  # Application page components
│   │   │   ├── Chat/               # Chat modules (index.tsx, MessageItem, TraceBlock, SourceBadges, Header)
│   │   │   ├── AiTools.jsx         # Custom API tools & MCP management (/tools)
│   │   │   ├── Documents.jsx       # Knowledge document upload & management
│   │   │   ├── AdminDashboard.jsx  # System admin dashboard
│   │   │   ├── LoginPage.jsx / RegisterPage.jsx
│   │   │   └── ProfilePage.jsx     # User profile view
│   │   ├── components/ui/          # In-house UI component library (CSS Modules + tokens.css)
│   │   ├── hooks/                  # Custom React hooks (useChat, useAuth, useDocuments)
│   │   ├── services/               # Axios API client & token interceptors
│   │   └── styles/tokens.css       # Design tokens
│   ├── package.json                # Frontend package configuration (Bun managed)
│   └── vite.config.js              # Vite build setup (/api proxy)
├── docs/                           # Documentation specifications
│   ├── api.md / api_en.md          # API Reference
│   ├── architecture.md / _en.md    # System Architecture & Design
│   └── adr/                        # Architecture Decision Records (ADR-0001, ADR-0002)
├── CLAUDE.md                       # AI assistant project guide (commands, conventions, pitfalls)
├── llms.txt / llms_en.txt          # AI-friendly system index
├── CHANGELOG.md / CHANGELOG_en.md  # Changelog
└── LICENSE                         # MIT License
```

---

## Environment Variables

### Backend Configuration (`backend/.env`)

Defaults are defined by `backend/app/core/config.py`; the sample values in `backend/.env.example` may differ from the code defaults (for example `LLM_API_BASE`, `CHUNK_SIZE`), so configure according to your own environment.

| Variable | Description | `config.py` Default | Required |
|---|---|---|---|
| `DATABASE_URL` | Database connection string; use `sqlite:///./chatbot.db` for zero-dependency, PostgreSQL example `postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot` | None (required) | Yes |
| `JWT_SECRET_KEY` | JWT signing secret (used as the HS256 fallback in development when RS256 keys fail to load) | None (required) | Yes |
| `ADMIN_API_KEY` | System Administrator API Key | None (required) | Yes |
| `LLM_API_BASE` | Local Ollama or compatible service endpoint URL (`.env.example` uses `http://localhost:11434`) | `http://localhost:5000` | No |
| `MODEL_NAME` | Default model name | None | No |
| `AVAILABLE_MODELS` | Comma-separated list of available models | None | No |
| `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI v1 settings (deployment name supports comma-separated multi-model) | None | No |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | Other provider keys | None | No |
| `ENABLE_WEB_SEARCH` | Enable Agent web search tools | `true` | No |
| `AGENT_MAX_TURNS` | Max tool-calling turns for the Agent (falls back to the Agent's built-in limit when unset) | None | No |
| `EMBEDDING_MODEL` | Embedding model | `BAAI/bge-small-zh-v1.5` | No |
| `RERANKER_MODEL` | Cross-Encoder re-ranking model | `BAAI/bge-reranker-base` | No |
| `HYBRID_ALPHA` / `TOP_K` / `RERANK_TOP_K` / `FINAL_K` | Hybrid retrieval weight and recall sizes | `0.75` / `30` / `50` / `8` | No |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Document chunk size and overlap (`.env.example` uses 300 / 100) | `800` / `150` | No |
| `FORCE_CPU` / `USE_FAISS_GPU` | Inference device settings | `true` / `false` | No |
| `ALLOWED_ORIGINS` | CORS allowlist (comma-separated) | `http://localhost:3001,...` | No |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_PER_MINUTE` | Rate limiting | `true` / `60` | No |
| `EXTERNAL_TAGS_URL` | Remote model list URL proxied by `/api/external-tags` | None | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | Token lifetimes | `30` / `7` | No |
| `ENVIRONMENT` | `development` / `production` (production enforces RSA keys) | `development` | No |

### Frontend Configuration (`frontend/.env`)

| Variable | Description | Default | Required |
|---|---|---|---|
| `PORT` | Vite dev server port | `3001` (3000 when unset) | No |
| `VITE_API_BASE` | Vite `/api` proxy target | `http://localhost:8001` | No |
| `VITE_API_URL` | Backend absolute URL for CORS direct connection | `http://localhost:8001` | No |

---

## Documentation

- [API Reference](./docs/api_en.md) - Full RESTful / SSE endpoints, request/response JSON schemas, and parameter details
- [Architecture & Design](./docs/architecture_en.md) - Layered architecture, hybrid retrieval, authentication, Agentic loop, tool extension, security, data model, and deployment modes
- [Architecture Decision Records (ADR)](./docs/adr/README_en.md) - ADR-0001 hybrid RAG and security; [ADR-0002](./docs/adr/0002-platform-hardening-and-tool-extension-roadmap_en.md) 2.x platform hardening roadmap
- [AI Assistant Project Guide](./CLAUDE.md) - Build and test commands, conventions, and common pitfalls
- [AI System Guide](./llms_en.txt) — Machine-readable guide for AI Agents and LLMs
- [Changelog](./CHANGELOG_en.md) — Version release history

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository and create your feature branch (`git checkout -b feature/amazing-feature`).
2. Ensure code passes type checks and tests:
   - Backend tests: `cd backend && pytest`
   - Frontend validation: `bun x tsc --noEmit`, `bun run lint`, `bun run test`, `bun run build`
   - When changing `docs/`, `README`, or `llms.txt`, update the corresponding `_en` English version as well.
3. Commit using Conventional Commits (`git commit -m 'feat(tools): add ...'`).
4. Push to your branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request with a clear description of your changes.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.