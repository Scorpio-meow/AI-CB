# Changelog

[繁體中文](CHANGELOG.md) | [English](CHANGELOG_en.md)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Custom API tools and OpenAPI import**: `/api/api-tools` endpoints (parse-spec, import, CRUD, toggle, test) and `services/openapi_parser.py` (OAS 2.0 / 3.0 / 3.1); imported endpoints become agent tools automatically.
- **MCP server integration**: `/api/mcp` endpoints (presets, servers CRUD, discover, toggle, tool test) and `services/mcp_service.py` (stdio / http transports); discovered tools are registered as `mcp_{server}_{tool}`.
- **SSRF egress protection**: `core/ssrf_protection.py`, applied to `web_fetch`, OpenAPI spec loading, and custom API execution.
- Frontend `/tools` page (`AiTools.jsx`); `GET /api/chat/tools` introspection endpoint; `filter_and_count_records` structured counting tool.
- **Architecture docs aligned with 2.x**: rewrote `docs/architecture.md` (layered architecture, in-memory blacklist, tool extension subsystem, security overview, ER diagram, deployment profiles) and `docs/api.md` (SSE event format, api-tools / mcp / tags / admin endpoints, removed the obsolete workflow section).
- Added [ADR-0002](docs/adr/0002-platform-hardening-and-tool-extension-roadmap_en.md): 2.x platform hardening and tool extension roadmap (CI, pluggable blacklist, test coverage, Alembic, ToolProvider, TSX completion, observability, configuration governance); ADR-0001 annotated to mark the Redis parts as superseded.
- Added `CLAUDE.md`: project guide for AI assistants and contributors.
- Updated `README.md`, `llms.txt`, and their English versions: documented tool extension and SSRF features, corrected the frontend port (3001), and based the environment matrix on `config.py` defaults.

---

## [2.0.0] - 2026-08-24

### Added
- **Agentic RAG Autonomous Research Pipeline**:
  - Implemented ReAct research agent (`ResearchAgent`) supporting multi-turn reasoning and Native Tool Calling.
  - Provided native toolset in `ResearchToolRegistry`: internal knowledge base search (`search_knowledge_base`), live web search (`web_search` with Ollama & DuckDuckGo dual fallback), and deep web fetch (`web_fetch`).
- **Reasoning Effort Multi-Tier Selection**:
  - Added 5 reasoning depth levels in the top navigation: `None (none)`, `Low (low)`, `Medium (medium)`, `High (high)`, and `Extreme (xhigh)`.
  - Fully compatible with Azure OpenAI v1 and OpenAI reasoning models (GPT-5 series, o-series), with automated tool-call compatibility handling.
- **Frontend Research Visualization**:
  - Added `ResearchTraceBlock`: Collapsible step-by-step research trace timeline with tool execution logs.
  - Added `SourceBadges`: Clickable external source reference badges that open in new tabs.
- **Modular RAG Engine Architecture**:
  - Refactored RAG subsystem into decoupled modules: index managers (`indices/`), hybrid retrievers (`retrievers/`), pipeline orchestrator (`pipeline.py`), evaluator (`evaluator.py`), and unified facade (`contextual_rag.py`).

### Changed
- **Zero-Dependency Lightweight Core**:
  - Defaulted to built-in SQLite relational database and in-memory caching, eliminating mandatory Docker/PostgreSQL/Redis setups for local development.
  - Streamlined architecture by retiring legacy discussion board and custom agent modules.
  - Removed cache hits to ensure all queries reflect grounded knowledge and live web data.
- **Frontend Experience & Layout**:
  - Unified sidebar into a single adaptive instance (docked on desktop, drawer on mobile).
  - Adopted Bun as the preferred toolchain for package management and building.

### Fixed
- **Azure OpenAI v1 API Compatibility**:
  - Removed legacy `AZURE_OPENAI_API_VERSION` dependency in favor of standard v1 endpoints.
  - Removed unsupported `max_tokens` and `temperature` parameters for reasoning models.
- **Stability & Bug Fixes**:
  - Fixed `NameError` caused by missing `Dict, Any` imports in `MessageResponse`.
  - Fixed `TypeError` in `HybridContextualRAG.generate_response()` missing `reasoning_effort` argument.
  - Fixed 500 error in `/api/chat/models` caused by missing `settings` import and added comma-separated deployment name normalization.
  - Fixed duplicate sidebar rendering on desktop viewports.

---

## [1.0.0] - 2026-08-01

### Added
- Contextual Hybrid RAG retrieval pipeline (FAISS + Whoosh BM25 + Cross-Encoder Reranker).
- RSA-2048 JWT authentication with token revocation blacklist.
- Sensitive data two-layer redaction (`security_logging.py`).
- Document upload, chunking, embedding, and background reindexing tasks.