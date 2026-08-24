# Changelog

[繁體中文](CHANGELOG.md) | [English](CHANGELOG_en.md)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Comprehensive update across all project specification documents (`README.md`, `README_en.md`, `llms.txt`, `llms_en.txt`, `CHANGELOG.md`, `CHANGELOG_en.md`).

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