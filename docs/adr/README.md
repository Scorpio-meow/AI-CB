# AskMiao 架構決策紀錄 (Architecture Decision Records)

[繁體中文](README.md) | [English](README_en.md)

本目錄記錄 AskMiao 系統開發過程中的重要架構決策、技術選型背景、替換方案評估與最終權衡結果。

---

## 決策紀錄索引

| ADR 編號 | 標題 | 狀態 | 決策日期 | 摘要 |
|---|---|---|---|---|
| [ADR-0001](./0001-hybrid-rag-and-security.md) | 增強型混合 RAG 檢索架構與雙 Token 安全防護決策 | 已通過 (Accepted) — Redis 部分已被 ADR-0002 取代 | 2026-08-01 | 採用 FAISS + Whoosh + Cross-Encoder 混合 RAG 與 RSA-2048 JWT 雙 Token 防護 |
| [ADR-0002](./0002-platform-hardening-and-tool-extension-roadmap.md) | 2.x 平台強化與工具擴充架構路線圖 | 提議 (Proposed) | 2026-09-07 | CI、可插拔 Token 黑名單、測試補強、Alembic、ToolProvider 抽象、TSX 遷移收尾、可觀測性與設定治理 |

---

## ADR 撰寫規範

新增架構決策紀錄時，請遵循以下結構範本：

1. **標題與編號**：格式為 `ADR-XXXX: [決策標題]`，檔名 `XXXX-kebab-case-title.md`，並同步提供 `_en.md` 英文版。
2. **狀態**：`提議 (Proposed)` / `已通過 (Accepted)` / `已廢棄 (Deprecated)` / `已被取代 (Superseded)`。若僅部分內容被取代，維持原狀態並於狀態段下加註說明與指向新 ADR 的連結。
3. **背景 (Context)**：為何需要做出此項決策？面臨何種技術挑戰或業務需求？
4. **決策內容 (Decision)**：我們選擇了什麼方案？
5. **影響與權衡 (Consequences)**：該決策帶來的優點、風險與相應的權衡。
6. **未採納方案 (Alternatives Considered)**（選填）：評估過但未採用的方案與原因。
