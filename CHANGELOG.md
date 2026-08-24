# 版本變更紀錄 (Changelog)

[繁體中文](CHANGELOG.md) | [English](CHANGELOG_en.md)

本專案遵守 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 規範，並遵循 [語意化版本 2.0.0](https://semver.org/lang/zh-TW/) 格式。

---

## [Unreleased]

### Added
- 完整更新全套系統規格文檔（`README.md`, `README_en.md`, `llms.txt`, `llms_en.txt`, `CHANGELOG.md`, `CHANGELOG_en.md`）。

---

## [2.0.0] - 2026-08-24

### Added
- **Agentic RAG 自主研究管線**：
  - 實作 ReAct 自主研究代理人 `ResearchAgent`，支援多輪自主推理與 Native Tool Calling。
  - 提供 `ResearchToolRegistry` 原生工具集：內部知識庫搜尋（`search_knowledge_base`）、外部聯網搜尋（`web_search`，具備 Ollama 與 DuckDuckGo 雙引擎備援）與外部網頁內容深度抓取（`web_fetch`）。
- **模型推理程度（Reasoning Effort）選擇機制**：
  - 前端頂部導覽列提供 5 檔位切換：`無 (None)`、`輕度 (Low)`、`標準 (Medium)`、`深度 (High)`、`極致 (X-High)`。
  - 後端全面適配 Azure OpenAI v1 及 OpenAI 官方推理模型（GPT-5 系列、o1/o3/o4 系列），並依微軟 Foundry 規範自動處理工具調用時之相容性。
- **全新前端視覺與研究歷程展示**：
  - 新增 `ResearchTraceBlock`：可折疊之研究步驟時間軸與工具調用日誌展示。
  - 新增 `SourceBadges`：外部參考連結徽章，支援點擊直接另開視窗閱讀來源。
- **模組化 RAG 架構**：
  - 將 RAG 系統重構為高內聚模組：向量索引（`indices/`）、混合檢索（`retrievers/`）、執行管線（`pipeline.py`）、評估器（`evaluator.py`）與門面類別（`contextual_rag.py`）。

### Changed
- **架構輕量化與零依賴化**：
  - 預設改用 SQLite 關聯式資料庫與記憶體快取，無需啟動 Docker、PostgreSQL 或 Redis 即可一鍵本機啟動。
  - 移除過時之討論看板與自訂 Agent 模組，專注於高效知識庫問答與深度研究。
  - 移除查詢快取命中，確保每次問答均能反映最新文檔與即時聯網資訊。
- **前端版面體驗升級**：
  - 側邊欄整合為單一自適應實例，桌面端無縫卡片貼合，移動端自動切換抽屜。
  - 全面使用 Bun 作為前端套件管理與建構工具。

### Fixed
- **Azure OpenAI v1 API 相容性**：
  - 移除已過時之 `AZURE_OPENAI_API_VERSION` 依賴，採用標準 v1 端點路徑。
  - 移除推理模型中不支援的 `max_tokens` 與 `temperature` 參數，改採相容之 payload 結構。
- **系統穩定性與錯誤修復**：
  - 修復 `MessageResponse` 缺少 `Dict, Any` 導入引發之 `NameError`。
  - 修復 `HybridContextualRAG.generate_response()` 遺漏 `reasoning_effort` 參數傳遞之 `TypeError`。
  - 修復 `/api/chat/models` 遺漏 `settings` 導入導致 500 錯誤與模型選單未正確拆分逗號字串之問題。
  - 修復前端側邊欄雙重渲染重疊之版面異常。

---

## [1.0.0] - 2026-08-01

### Added
- 增強型混合 RAG 檢索系統（FAISS + Whoosh BM25 + Cross-Encoder Reranker）。
- RSA-2048 JWT 認證與令牌黑名單撤銷機制。
- `security_logging.py` 敏感資料雙層脫敏機制（物件遞迴與正則遮罩）。
- 文件管理與知識庫切分向量化背景任務。