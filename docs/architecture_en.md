# AskMiao System Architecture & Design

[繁體中文](architecture.md) | [English](architecture_en.md)

> This document details the overall system architecture, core module relationships, Contextual Hybrid RAG retrieval pipeline, RSA-2048 dual-token authentication, and multi-Agent collaboration design for AskMiao.

---

## 1. High-Level Layered Architecture

AskMiao adopts a decoupled frontend-backend architecture. The frontend is built with React 19 and Vite 7, while the backend is powered by FastAPI delivering asynchronous RESTful APIs and WebSocket services. PostgreSQL 17.9 handles relational persistence, and Redis manages caching and token blacklists.

```mermaid
flowchart TB
    subgraph Client ["Client Layer (React 19 + Vite + Bun)"]
        UI["User Interface (MUI v7)"]
        Board["Multi-Agent Board (React Flow)"]
    end

    subgraph Gateway ["API Gateway & Middleware Layer"]
        CORSMiddleware["CORS & Rate Limiting Middleware"]
        SecurityLogging["Security Logging Middleware (security_logging.py)"]
    end

    subgraph Backend ["FastAPI Core Services"]
        AuthModule["Auth Module (RSA-2048 JWT)"]
        RAGModule["Hybrid RAG Retriever (contextual_rag.py)"]
        WorkflowModule["Workflow Service (workflow_service.py)"]
        ChatModule["Chat & History Handler"]
    end

    subgraph Storage ["Storage & Indexing Layer"]
        DB[(PostgreSQL 17.9 Database)]
        RedisCache[(Redis Cache & JTI Blacklist)]
        FAISSIndex["FAISS Vector Index (Dense Retrieval)"]
        BM25Index["Whoosh BM25 Index (Sparse Retrieval)"]
    end

    UI --> CORSMiddleware
    Board --> WorkflowModule
    CORSMiddleware --> SecurityLogging
    SecurityLogging --> AuthModule
    SecurityLogging --> RAGModule
    SecurityLogging --> ChatModule
    AuthModule --> DB
    AuthModule --> RedisCache
    RAGModule --> FAISSIndex
    RAGModule --> BM25Index
    ChatModule --> DB
```

---

## 2. Contextual Hybrid RAG Retrieval & Re-ranking Pipeline

The system employs parallel dual-track retrieval combining dense vector search (FAISS) and sparse keyword search (Whoosh BM25). Candidates are merged via score normalization and re-ranked using a Cross-Encoder model.

```mermaid
flowchart LR
    Query["User Query Input"] --> Strategy{"Retrieval Strategy Dispatcher"}
    
    subgraph ParallelRetrieval ["Parallel Dual-Track Retrieval"]
        Strategy -->|Vector Search| FAISS["FAISS Dense Search (Inner Product, BGE-Small)"]
        Strategy -->|Keyword Search| BM25["Whoosh BM25 (Jieba Segmentation)"]
    end

    FAISS --> Merge["Score Normalization Fusion (HYBRID_ALPHA Weighted)"]
    BM25 --> Merge
    
    Merge --> Reranker["Cross-Encoder Re-ranking (bge-reranker-base)"]
    Reranker --> TopK["Select Top-K Context Passages"]
    TopK --> LLM["LLM Context Assembly & Generation"]
```

### Retrieval Pipeline Details

1. **Text Chunking**: Uploaded documents are processed via `RecursiveCharacterTextSplitter` (default 300 characters chunk size, 100 characters overlap).
2. **Vector Embedding**: Uses 384-dimensional vector space powered by `BAAI/bge-small-zh-v1.5`.
3. **Keyword Retrieval (BM25)**: Powered by `Whoosh` and `Jieba` custom domain dictionary.
4. **Re-ranking**: Cross-Encoder (`bge-reranker-base`) computes cross-attention relevance scores, filtering irrelevant chunks and maximizing accuracy.

---

## 3. RSA-2048 Dual-Token Auth & Blacklist Lifecycle

Short-lived Access Tokens (30 min) signed with RSA-2048 private key are paired with Refresh Tokens (7 days) stored in HttpOnly / Secure / SameSite Cookies, backed by Redis instant revocation.

```mermaid
sequenceDiagram
    autonumber
    actor User as Client / User
    participant API as FastAPI Server
    participant Redis as Redis Blacklist
    participant DB as PostgreSQL

    User->>API: 1. POST /api/auth/login (Credentials)
    API->>DB: 2. Verify Password Hash
    DB-->>API: 3. Authentication Succeeded
    API->>User: 4. Return Access Token (JSON) + Set Refresh Token (HttpOnly Cookie)

    User->>API: 5. GET /api/auth/me (With Authorization Header)
    API->>Redis: 6. Check if Access Token JTI is in Blacklist
    Redis-->>API: 7. Not Blacklisted (Valid)
    API-->>User: 8. Return User Profile

    User->>API: 9. POST /api/auth/logout (Logout Request)
    API->>Redis: 10. Write Access Token JTI to Redis Blacklist (TTL 30 min)
    API-->>User: 11. Clear Refresh Cookie & Return Success
```

---

## 4. Agentic RAG Autonomous Research & Tool Pipeline

The system employs a ReAct autonomous agent architecture (`ResearchAgent`), using Native Tool Calling for multi-turn dynamic research and contextual synthesis.

```mermaid
flowchart LR
    UserQuery["User Query"] --> Agent["Autonomous Research Agent (ResearchAgent)"]
    
    subgraph ToolLoop ["Multi-Turn Tool Calling Loop (Up to 5 Turns)"]
        Agent -->|Decisions & Args| Tools{"Tool Registry (ResearchToolRegistry)"}
        Tools -->|Internal Search| LocalRAG["search_knowledge_base\n(FAISS + BM25 + Cross-Encoder)"]
        Tools -->|Live Web Search| WebSearch["web_search\n(DuckDuckGo / Ollama Dual Engine)"]
        Tools -->|Deep Fetch| WebFetch["web_fetch\n(HTTP Fetch & Parser)"]
        
        LocalRAG -->|Document Chunks| ToolResult["Tool Execution Results"]
        WebSearch -->|Live Snippets & URLs| ToolResult
        WebFetch -->|Extracted Page Text| ToolResult
        ToolResult -->|Observations Injected| Agent
    end

    Agent -->|Synthesizes Trace & Citations| FinalAnswer["Structured Response Output\n(Answer + Research Trace + Sources)"]
```

### Key Autonomous Capabilities

1. **Context-Aware Decision Making**: The agent autonomously determines whether internal documentation, live web search, or full web page scraping is required to answer the query accurately.
2. **Research Trace Auditing**: Every tool step, arguments, execution duration, and output preview are captured in structured format for real-time visualization in the frontend timeline component.
3. **Interactive Source Attribution**: Integrates internal knowledge chunks with external web links, allowing users to verify facts and open primary sources with one click.

---

## 5. Security & Two-Layer Sensitive Data Redaction

To enforce security standards and resolve CodeQL warnings (`py/clear-text-logging-sensitive-data`), two mandatory redaction defenses are implemented in `backend/app/core/security_logging.py`:

1. **Object-Level Recursive Masking (`sanitize_sensitive_data`)**:
   - Recursively traverses dictionaries and lists.
   - Matches sensitive key names (case-insensitive `password`, `token`, `secret`, `authorization`, `cookie`, etc.).
   - Replaces matching values with `[REDACTED]`.
2. **Regex String-Level Defense**:
   - Secondary regex filter executed prior to JSON serialization and log emission.
   - Guarantees zero leak of sensitive credentials in system logs.

---

## 6. Architecture Decision Records (ADR)

Major architectural decisions are recorded in standalone ADR documents:

- [ADR Index](./adr/README_en.md)
- [ADR-0001: Contextual Hybrid RAG & Dual-Token Security Architecture](./adr/0001-hybrid-rag-and-security_en.md)