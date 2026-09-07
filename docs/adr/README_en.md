# AskMiao Architecture Decision Records (ADR)

[繁體中文](README.md) | [English](README_en.md)

This directory documents major architectural decisions, technology evaluations, trade-offs, and design rationales made during the development of AskMiao.

---

## ADR Index

| ADR ID | Title | Status | Date | Summary |
|---|---|---|---|---|
| [ADR-0001](./0001-hybrid-rag-and-security_en.md) | Contextual Hybrid RAG & Dual-Token Security Architecture | Accepted — Redis parts superseded by ADR-0002 | 2026-08-01 | Adopts FAISS + Whoosh + Cross-Encoder RAG and RSA-2048 JWT dual-token defense |
| [ADR-0002](./0002-platform-hardening-and-tool-extension-roadmap_en.md) | 2.x Platform Hardening & Tool Extension Roadmap | Proposed | 2026-09-07 | CI, pluggable token blacklist, test coverage, Alembic, ToolProvider abstraction, TSX migration completion, observability, and configuration governance |

---

## ADR Template & Guidelines

When submitting a new ADR, please use the following structure:

1. **Title & ID**: Format `ADR-XXXX: [Title]`, file name `XXXX-kebab-case-title.md`, with a matching `_en.md` English version.
2. **Status**: `Proposed` / `Accepted` / `Deprecated` / `Superseded`. If only part of a decision is superseded, keep the original status and add a note under it linking to the newer ADR.
3. **Context**: Why are we making this decision? What technical challenges or business requirements drive this choice?
4. **Decision**: What is the chosen solution?
5. **Consequences**: What are the positive outcomes, risks, and engineering trade-offs?
6. **Alternatives Considered** (optional): Options evaluated but not adopted, and why.
