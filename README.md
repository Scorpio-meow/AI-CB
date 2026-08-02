# AskMiao (AI ChatBot)

基於增強型混合 RAG（檢索增強生成）技術的智慧對話與多 Agent 協作系統。

[繁體中文](README.md) | [English](README_en.md)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Vite-7.0-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Bun](https://img.shields.io/badge/Bun-1.0+-FBF0DF?style=flat&logo=bun&logoColor=black)](https://bun.sh/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17.9-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[快速開始](#快速開始) | [核心功能特色](#核心功能特色) | [技術架構與元件](#技術架構與元件) | [環境配置矩陣](#環境配置矩陣) | [文件導覽](#文件導覽) | [貢獻指南](#貢獻指南) | [授權條款](#授權條款)

---

## 快速開始

### 環境要求

| 組件名稱 | 最低版本要求 | 建議工具/說明 |
|---|---|---|
| Python | 3.10 或更高版本 | 後端 API 伺服器與 RAG 檢索引晴 |
| Bun | 1.0 或更高版本 | 前端優先使用之套件管理與建構工具 |
| PostgreSQL | 17.9 版本 | 關聯式資料庫（儲存用戶、對話紀錄與 Agent 狀態） |
| Redis | 7.0 或更高版本 | 令牌黑名單與快取層（選用） |

### 1. 複製專案倉庫

```bash
git clone https://github.com/Scorpio-meow/AskMiao.git
cd AskMiao
```

### 2. 啟動資料庫服務 (Docker)

```bash
# 啟動 PostgreSQL 服務
docker run -d --name chatbot-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=chatbot \
  -p 7690:5432 \
  postgres:17.9

# 啟動 Redis 服務 (選用，用於 Token 黑名單與快取)
docker run -d -p 7967:6379 --name chatbot-redis redis:latest
```

### 3. 後端服務設定與啟動

```bash
cd backend

# 建立並啟用 Python 虛擬環境
python -m venv CBvenv

# Windows PowerShell 啟用：
.\CBvenv\Scripts\Activate.ps1
# Linux/macOS 啟用：
source CBvenv/bin/activate

# 安裝依賴套件
pip install -r requirements.txt

# 設定環境變數檔
cp .env.example .env

# 初始化資料庫表格與預設 Agent 狀態
python init_db.py

# 啟動 FastAPI 開發伺服器
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 4. 前端服務設定與啟動 (優先使用 Bun)

```bash
cd ../frontend

# 使用 Bun 安裝前端依賴項目
bun install

# 複製環境變數設定檔
cp .env.example .env

# 啟動 Vite 前端開發伺服器
bun run dev
```

伺服器啟動成功後，瀏覽器造訪 `http://localhost:5173` 即可開始使用 AskMiao。

---

## 核心功能特色

1. **增強型混合 RAG 檢索引晴**：整合 FAISS 向量搜尋（Dense Retrieval）與 Whoosh BM25 中文關鍵字檢索（Sparse Retrieval），最終由 Cross-Encoder (`bge-reranker-base`) 進行加權重排序，確保精準度與語意相關性。
2. **多提供商 LLM 彈性整合**：提供統一 API 抽象層，支援 OpenAI, Claude, Gemini, Azure OpenAI 及本地 Ollama 模型動態切換。
3. **多 Agent 協作討論看板**：採用 React Flow 視覺化節點關係圖與 WebSocket 即時廣播，呈現多 AI Agent 串流討論與結論收斂過程。
4. **安全雙 Token 認證機制**：使用 RSA-2048 私鑰簽署之 Access Token（有效期 30 分鐘）搭配 HttpOnly Secure Cookie 存放之 Refresh Token（有效期 7 天），支援 Redis 即時撤銷黑名單。
5. **敏感資料雙層脫敏防護**：於 `security_logging.py` 實作物件層級遞迴脫敏與字串正則遮罩防護，防止密碼、Token 與授權憑證洩漏至系統日誌。

---

## 技術架構與元件

```mermaid
flowchart TB
    subgraph Client ["前端層 (React 19 + Vite + Bun)"]
        UI["用戶介面 (MUI v7)"]
        Board["多 Agent 討論看板 (React Flow)"]
    end

    subgraph Server ["後端層 (FastAPI + Python 3.10+)"]
        Middleware["安全與日誌中介軟體 (Security Logging)"]
        AuthModule["認證模組 (RSA-2048 JWT)"]
        RAGModule["混合 RAG 引擎 (FAISS + BM25)"]
        WorkflowModule["多 Agent 工作流與 WebSocket 服務"]
    end

    subgraph Storage ["儲存與索引層"]
        DB[(PostgreSQL 17.9)]
        RedisCache[(Redis 快取 & 黑名單)]
        FAISSIndex["FAISS 向量索引"]
        BM25Index["Whoosh BM25 文字索引"]
    end

    UI --> Middleware
    Board --> WorkflowModule
    Middleware --> AuthModule
    Middleware --> RAGModule
    AuthModule --> DB
    AuthModule --> RedisCache
    RAGModule --> FAISSIndex
    RAGModule --> BM25Index
```

| 類別 | 元件名稱 | 說明 |
|---|---|---|
| **後端 API 框架** | FastAPI | 高效能非同步 Web 框架，自動生成 OpenAPI 規範 |
| **資料庫 & ORM** | PostgreSQL 17.9 + SQLAlchemy 2.0 | 關聯式資料儲存與非同步 ORM 操作 |
| **快取與安全層** | Redis | JWT 令牌撤銷黑名單與查詢快取 |
| **RAG 檢索與重排** | FAISS + Whoosh + Cross-Encoder | 向量與 BM25 關鍵字混合檢索重排序引擎 |
| **前端建構工具** | React 19 + Vite 7 + Bun | 現代化前端套件管理、開發與高效能打包 |
| **UI 與工作流** | MUI v7 + React Flow | 響應式介面設計與 Agent 流程圖渲染 |

---

## 環境配置矩陣

### 後端環境變數 (backend/.env)

| 變數名稱 | 描述 | 預設值 | 必填 |
|---|---|---|---|
| `DATABASE_URL` | PostgreSQL 資料庫連線字串 | `postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot` | 是 |
| `REDIS_URL` | Redis 服務連線字串 | `redis://localhost:7967/0` | 否 |
| `JWT_SECRET_KEY` | JWT 簽署金鑰 | `your_jwt_secret_key` | 是 |
| `LLM_API_BASE` | LLM 服務端點網址 | `http://localhost:5000` | 是 |
| `EMBEDDING_MODEL` | FAISS 向量嵌入模型名稱 | `BAAI/bge-small-zh-v1.5` | 否 |
| `RERANKER_MODEL` | Reranker 重排序模型名稱 | `BAAI/bge-reranker-base` | 否 |

### 前端環境變數 (frontend/.env)

| 變數名稱 | 描述 | 預設值 | 必填 |
|---|---|---|---|
| `VITE_API_BASE_URL` | 後端 RESTful API 基礎 URL | `http://localhost:8001` | 是 |
| `VITE_WS_BASE_URL` | 後端 WebSocket 基礎 URL | `ws://localhost:8001` | 是 |

---

## 文件導覽

- [API 參考文件](./docs/api.md) — 完整 RESTful 端點、請求回應 JSON 規格與 WebSocket 說明
- [系統架構與設計文件](./docs/architecture.md) — 系統模組關係圖、RAG 流程圖與安全架構
- [架構決策紀錄 (ADR)](./docs/adr/README.md) — 專案架構演進與重大決策紀錄
- [AI 友善結構導覽](./llms.txt) — 專供 AI Agent 與 LLM 分析之結構導覽與設計約束
- [版本變更紀錄](./CHANGELOG.md) — 系統版本演進歷史

---

## 貢獻指南

歡迎參與 AskMiao 的開發！若您希望進行貢獻，請遵循以下步驟：

1. Fork 本專案倉庫並建立您的功能分支 (`git checkout -b feature/amazing-feature`)。
2. 確保程式碼通過前端與後端型別檢查及測試（前端請使用 `bun run test` 或 `bun run check`）。
3. 提交您的變更 (`git commit -m 'Add some amazing feature'`)。
4. 推送至分支 (`git push origin feature/amazing-feature`)。
5. 開啟 Pull Request 並詳細說明變更內容。

---

## 授權條款

本專案基於 MIT 授權條款發行。詳情請參閱 [LICENSE](LICENSE) 檔案。