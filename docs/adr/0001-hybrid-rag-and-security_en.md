# ADR-0001: Contextual Hybrid RAG & Dual-Token Security Architecture

[繁體中文](0001-hybrid-rag-and-security.md) | [English](0001-hybrid-rag-and-security_en.md)

## Status

Accepted - 2026-08-01

> **Note (2026-09-07)**: The "Redis blacklist" and "Redis query cache" parts of this decision were replaced in 2.0.0 by a single-process in-memory implementation (see `backend/app/core/redis_client.py` and [CHANGELOG 2.0.0](../../CHANGELOG_en.md)); a pluggable blacklist backend is planned in [ADR-0002](./0002-platform-hardening-and-tool-extension-roadmap_en.md). The hybrid RAG pipeline, RSA-2048 dual-token auth, and two-layer redaction remain in effect.

---

## Context & Problem Statement

As an intelligent conversational and multi-Agent collaboration system, AskMiao faced two core technical challenges regarding retrieval precision and authentication security:

1. **Limitations of Single Retrieval Approaches**:
   - Pure dense vector search excels at semantic similarity but misses exact technical terms, proper names, or model codes, occasionally introducing hallucinations.
   - Pure sparse keyword search (e.g. BM25) excels at exact matching but lacks semantic understanding and synonym expansion.
2. **Authentication Security & Credential Leakage Prevention**:
   - Long-lived single JWT tokens pose security risks if intercepted, whereas pure session-based auth scales poorly in async microservices.
   - System logs risk inadvertently printing user passwords or API secrets, triggering CodeQL security alerts.

---

## Decision Outcome

After evaluation, the engineering team adopted the following architectural solution:

### 1. Contextual Hybrid RAG Pipeline

- Combines **FAISS dense vector retrieval** (powered by `BAAI/bge-small-zh-v1.5`) and **Whoosh BM25 keyword search** (with `Jieba` segmentation).
- Merges candidate passages via score normalization fusion and re-ranks Top-K contexts using a **Cross-Encoder model (`bge-reranker-base`)**.

### 2. RSA-2048 Dual-Token Auth & Redis Revocation Blacklist (Redis part superseded by ADR-0002)

- **Access Token**: Signed with RSA-2048 private key, 30-minute expiration, transmitted via Authorization header.
- **Refresh Token**: HttpOnly / Secure / SameSite Cookie, 7-day expiration.
- **Instant Revocation**: Blacklists Access Token JTI in Redis upon logout.

### 3. Two-Layer Sensitive Data Redaction (`security_logging.py`)

- Object-level recursive key masking via `sanitize_sensitive_data`.
- Secondary string-level regex filter applied prior to JSON logging, turning sensitive fields into `[REDACTED]`.

---

## Consequences & Trade-offs

### Positive Consequences

- **Significant Accuracy Boost**: Hybrid RAG with re-ranking drastically reduces hallucinations and improves exact domain-keyword retrieval.
- **Enhanced Security Profile**: Silent refresh balances UX with short-lived tokens, while two-layer log masking eliminates credential leakage risks and satisfies CodeQL audits.

### Negative Consequences & Risks

- **Increased System Complexity**: Backend must manage both FAISS vector indices and Whoosh text index files.
- **Computation Latency**: Cross-Encoder re-ranking adds dozens of milliseconds per query, mitigated by caching frequent queries in Redis.