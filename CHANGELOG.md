# 版本變更紀錄 (Changelog)

[繁體中文](CHANGELOG.md) | [English](CHANGELOG_en.md)

本專案遵守 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 規範，並遵循 [語意化版本 2.0.0](https://semver.org/lang/zh-TW/) 格式。

---

## [Unreleased]

### Added

- 全面更新與美化專案文件體系，引入中英雙語對照體系 (Bilingual Documentation)。
- 新增對應之英文版文檔：`README_en.md`, `docs/api_en.md`, `docs/architecture_en.md`, `docs/adr/README_en.md`, `docs/adr/0001-hybrid-rag-and-security_en.md`, `llms_en.txt` 與 `CHANGELOG_en.md`。
- 新增架構決策紀錄目錄與第一份決策文檔 [docs/adr/0001-hybrid-rag-and-security.md](./docs/adr/0001-hybrid-rag-and-security.md)。
- 新增架構決策紀錄索引文檔 [docs/adr/README.md](./docs/adr/README.md)。
- 擴充 [llms.txt](./llms.txt) 與 [llms_en.txt](./llms_en.txt) 為 2025 AI 友善標準結構檔。

### Changed

- 重構並美化 [README.md](./README.md)，補齊 Bun 快速部署指令、前後端環境變數矩陣與模組對照表。
- 重構並擴充 [docs/api.md](./docs/api.md)，補齊所有 RESTful API 端點參數表格、HTTP 狀態碼與標準錯誤回應 JSON schema。
- 重構並擴充 [docs/architecture.md](./docs/architecture.md)，加入 4 大標準純文字 Mermaid 架構圖與安全設計說明。
- 全套文件頁首加入 `[繁體中文](...) | [English](...)` 語言切換選單。

---

## [1.0.0] - 2026-08-01

### Added

- 增強型混合 RAG 檢索系統（FAISS + Whoosh BM25 + Cross-Encoder Reranker）。
- RSA-2048 JWT 認證與 Redis 令牌黑名單撤銷機制。
- 基於 React Flow 與 WebSocket 的多 Agent 協作討論看板。
- PostgreSQL 17.9 關聯式資料庫整合與遷移工具腳本。
- `security_logging.py` 敏感資料雙層脫敏機制（物件遞迴與正則遮罩）。