# Changelog

[繁體中文](CHANGELOG.md) | [English](CHANGELOG_en.md)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Fully overhauled documentation system with complete bilingual (Traditional Chinese & English) support.
- Added English companion documentation: `README_en.md`, `docs/api_en.md`, `docs/architecture_en.md`, `docs/adr/README_en.md`, `docs/adr/0001-hybrid-rag-and-security_en.md`, `llms_en.txt`, and `CHANGELOG_en.md`.
- Introduced Architecture Decision Record (ADR) directory and first decision document [docs/adr/0001-hybrid-rag-and-security_en.md](./docs/adr/0001-hybrid-rag-and-security_en.md).
- Added ADR master index document [docs/adr/README_en.md](./docs/adr/README_en.md).
- Upgraded [llms.txt](./llms.txt) and [llms_en.txt](./llms_en.txt) to 2025 AI-friendly specification.

### Changed

- Restructured and polished [README.md](./README.md) and [README_en.md](./README_en.md) with Bun deployment setup, environment variable matrix, and module table.
- Expanded [docs/api.md](./docs/api.md) and [docs/api_en.md](./docs/api_en.md) covering all RESTful endpoints, parameters, HTTP status codes, and unified JSON error schemas.
- Enhanced [docs/architecture.md](./docs/architecture.md) and [docs/architecture_en.md](./docs/architecture_en.md) with 4 native Mermaid architecture diagrams and security design specs.
- Integrated `[繁體中文](...) | [English](...)` top-level language switcher bar across all documents.

---

## [1.0.0] - 2026-08-01

### Added

- Contextual Hybrid RAG Retrieval Engine (FAISS + Whoosh BM25 + Cross-Encoder Reranker).
- RSA-2048 JWT authentication with Redis token revocation blacklist.
- Multi-Agent discussion board with React Flow node UI and WebSockets.
- PostgreSQL 17.9 relational database integration and schema migration scripts.
- Two-layer sensitive data redaction in `security_logging.py` (object recursion + regex filter).