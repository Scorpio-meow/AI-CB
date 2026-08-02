# AskMiao Architecture Decision Records (ADR)

[繁體中文](README.md) | [English](README_en.md)

This directory documents major architectural decisions, technology evaluations, trade-offs, and design rationales made during the development of AskMiao.

---

## ADR Index

| ADR ID | Title | Status | Date | Summary |
|---|---|---|---|---|
| [ADR-0001](./0001-hybrid-rag-and-security_en.md) | Contextual Hybrid RAG & Dual-Token Security Architecture | Accepted | 2026-08-01 | Adopts FAISS + Whoosh + Cross-Encoder RAG and RSA-2048 JWT dual-token defense |

---

## ADR Template & Guidelines

When submitting a new ADR, please use the following structure:

1. **Title & ID**: Format `ADR-XXXX: [Title]`
2. **Status**: `Proposed` / `Accepted` / `Deprecated` / `Superseded`
3. **Context**: Why are we making this decision? What technical challenges or business requirements drive this choice?
4. **Decision**: What is the chosen solution?
5. **Consequences**: What are the positive outcomes, risks, and engineering trade-offs?