# AskMiao (AI ChatBot)

An intelligent conversational and multi-Agent collaboration system powered by Contextual Hybrid RAG (Retrieval-Augmented Generation) technology.

[繁體中文](README.md) | [English](README_en.md)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Vite-7.0-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Bun](https://img.shields.io/badge/Bun-1.0+-FBF0DF?style=flat&logo=bun&logoColor=black)](https://bun.sh/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17.9-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Quick Start](#quick-start) | [Core Features](#core-features) | [System Architecture](#system-architecture) | [Environment Variables](#environment-variables) | [Documentation](#documentation) | [Contributing](#contributing) | [License](#license)

---

## Quick Start

### Requirements

| Component | Minimum Version | Description |
|---|---|---|
| Python | 3.10 or higher | Backend API server and RAG engine |
| Bun | 1.0 or higher | Preferred package manager and bundler for frontend |
| PostgreSQL | 17.9 | Relational database (stores users, chats, and agent states) |
| Redis | 7.0 or higher | Token revocation blacklist and cache layer (Optional) |

### 1. Clone Repository

```bash
git clone https://github.com/Scorpio-meow/AskMiao.git
cd AskMiao
```

### 2. Start Database Services (Docker)

```bash
# Start PostgreSQL service
docker run -d --name chatbot-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=chatbot \
  -p 7690:5432 \
  postgres:17.9

# Start Redis service (Optional for Token blacklist and cache)
docker run -d -p 7967:6379 --name chatbot-redis redis:latest
```

### 3. Backend Setup and Launch

```bash
cd backend

# Create and activate Python virtual environment
python -m venv CBvenv

# Windows PowerShell:
.\CBvenv\Scripts\Activate.ps1
# Linux/macOS:
source CBvenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Initialize database schema and default agents
python init_db.py

# Start FastAPI development server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 4. Frontend Setup and Launch (Bun Preferred)

```bash
cd ../frontend

# Install frontend dependencies using Bun
bun install

# Copy environment template
cp .env.example .env

# Start Vite development server
bun run dev
```

Once started, open your browser and navigate to `http://localhost:5173` to start using AskMiao.

---

## Core Features

1. **Contextual Hybrid RAG Engine**: Combines FAISS dense vector search with Whoosh BM25 keyword search, re-ranked dynamically via Cross-Encoder (`bge-reranker-base`) for optimal precision and context relevance.
2. **Multi-Provider LLM Integration**: Unified API abstraction supporting OpenAI, Claude, Gemini, Azure OpenAI, and local Ollama models.
3. **Multi-Agent Discussion Board**: Interactive node graph powered by React Flow and WebSocket streaming for real-time AI Agent collaboration and consensus building.
4. **Dual-Token Security Architecture**: Short-lived Access Tokens (30 min) signed with RSA-2048 combined with HttpOnly Refresh Cookies (7 days) and Redis-backed instant token revocation.
5. **Two-Layer Sensitive Data Masking**: Recursive object masking and regex-based string redaction in `security_logging.py` preventing credential and token leaks in system logs.

---

## System Architecture

```mermaid
flowchart TB
    subgraph Client ["Client Layer (React 19 + Vite + Bun)"]
        UI["User Interface (MUI v7)"]
        Board["Multi-Agent Board (React Flow)"]
    end

    subgraph Server ["Server Layer (FastAPI + Python 3.10+)"]
        Middleware["Security & Logging Middleware"]
        AuthModule["Auth Module (RSA-2048 JWT)"]
        RAGModule["Hybrid RAG Engine (FAISS + BM25)"]
        WorkflowModule["Workflow & WebSocket Service"]
    end

    subgraph Storage ["Storage & Indexing Layer"]
        DB[(PostgreSQL 17.9)]
        RedisCache[(Redis Cache & Blacklist)]
        FAISSIndex["FAISS Vector Index"]
        BM25Index["Whoosh BM25 Index"]
    end

    UI --> Middleware
    Board --> WorkflowModule
    Middleware --> AuthModule
    Middleware --> RAGModule
    AuthModule --> DB
    AuthModule --> RedisCache
    RAGModule --> FAISSIndex
    RAGModule --> BM25Index
```

| Component Category | Technology | Description |
|---|---|---|
| **Backend API Framework** | FastAPI | Async Web framework with automatic OpenAPI spec generation |
| **Database & ORM** | PostgreSQL 17.9 + SQLAlchemy 2.0 | Relational storage and async ORM operations |
| **Cache & Security** | Redis | JWT revocation blacklist and query caching |
| **RAG Retrieval & Rerank** | FAISS + Whoosh + Cross-Encoder | Dense vector + BM25 keyword search with re-ranking |
| **Frontend Toolchain** | React 19 + Vite 7 + Bun | Modern frontend build stack and package management |
| **UI & Workflow** | MUI v7 + React Flow | Responsive UI components and agent graph rendering |

---

## Environment Variables

### Backend Configuration (backend/.env)

| Variable | Description | Default | Required |
|---|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot` | Yes |
| `REDIS_URL` | Redis connection URL | `redis://localhost:7967/0` | No |
| `JWT_SECRET_KEY` | JWT signing secret key | `your_jwt_secret_key` | Yes |
| `LLM_API_BASE` | Primary LLM service endpoint URL | `http://localhost:5000` | Yes |
| `EMBEDDING_MODEL` | Embedding model for FAISS vector index | `BAAI/bge-small-zh-v1.5` | No |
| `RERANKER_MODEL` | Re-ranking model for search | `BAAI/bge-reranker-base` | No |

### Frontend Configuration (frontend/.env)

| Variable | Description | Default | Required |
|---|---|---|---|
| `VITE_API_BASE_URL` | Backend RESTful API base URL | `http://localhost:8001` | Yes |
| `VITE_WS_BASE_URL` | Backend WebSocket base URL | `ws://localhost:8001` | Yes |

---

## Documentation

- [API Reference](./docs/api_en.md) — Comprehensive RESTful endpoints, request/response JSON schemas, and WebSocket specs
- [Architecture & Design](./docs/architecture_en.md) — System modules, hybrid RAG pipeline, and security architecture
- [Architecture Decision Records (ADR)](./docs/adr/README_en.md) — Architectural decisions and trade-offs
- [AI System Guide](./llms_en.txt) — Machine-readable guide for AI Agents and LLMs
- [Changelog](./CHANGELOG_en.md) — Version release history

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository and create your feature branch (`git checkout -b feature/amazing-feature`).
2. Ensure code passes type checks and tests (use `bun run test` or `bun run check` on frontend).
3. Commit your changes (`git commit -m 'Add some amazing feature'`).
4. Push to your branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request with a clear summary of your changes.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.