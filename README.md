# AskMiao (AI ChatBot)

基於增強型混合 RAG（檢索增強生成）與 Agentic 自主研究架構的企業級智慧知識庫對話系統。

[繁體中文](README.md) | [English](README_en.md)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Vite-7.0-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Bun](https://img.shields.io/badge/Bun-1.0+-FBF0DF?style=flat&logo=bun&logoColor=black)](https://bun.sh/)
[![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[快速開始](#快速開始) | [核心功能特色](#核心功能特色) | [系統架構與設計](#系統架構與設計) | [專案目錄結構](#專案目錄結構) | [環境配置矩陣](#環境配置矩陣) | [文件導覽](#文件導覽) | [貢獻指南](#貢獻指南) | [授權條款](#授權條款)

---

## 快速開始

### 環境要求

| 組件名稱 | 最低版本要求　　　 | 建議工具與用途說明　　　　　　　　　　　　　　　　　　　 |
| ----------| --------------------| ----------------------------------------------------------|
| Python　 | 3.10 或更高版本　　| 後端 FastAPI 伺服器、RAG 向量索引與 Agentic 自主研究引擎 |
| Bun　　　| 1.0 或更高版本　　 | 前端優先使用之套件管理與建構打包工具　　　　　　　　　　 |
| SQLite　 | 3.x（Python 內建） | 預設關聯式資料庫，支援零依賴即時啟動　　　　　　　　　　 |

### 1. 複製專案倉庫

```bash
git clone https://github.com/Scorpio-meow/AskMiao.git
cd AskMiao
```

### 2. 後端服務設定與啟動

```bash
cd backend

# 建立並啟用 Python 虛擬環境
py -m venv .venv

# Windows PowerShell 啟用：
.\.venv\Scripts\Activate.ps1
# Linux/macOS 啟用：
source .venv/bin/activate

# 安裝後端依賴套件
pip install -r requirements.txt

# 設定環境變數檔 (預設即為 SQLite 零依賴配置)
cp .env.example .env

# 初始化資料庫表格與管理員帳號
py init_db.py

# 啟動 FastAPI 開發伺服器 (Port 8001)
py main.py
```

### 3. 前端服務設定與啟動 (使用 Bun)

```bash
cd ../frontend

# 使用 Bun 安裝前端依賴項目
bun install

# 啟動 Vite 前端開發伺服器 (Port 5173 / 3001)
bun run dev
```

伺服器啟動後，開啟瀏覽器造訪 `http://localhost:5173` 即可進入 AskMiao 知識庫對話系統。

---

## 核心功能特色

1. **Agentic RAG 多輪自主研究**：
   - 內建 ReAct 自主研究 Agent（`ResearchAgent`），支援原生工具調用（Native Tool Calling）。
   - 提供內部知識庫搜尋（`search_knowledge_base`）、外部即時聯網搜尋（`web_search`，支援 Ollama 與 DuckDuckGo 雙引擎備援）與深度網頁抓取（`web_fetch`）。
   - 前端即時呈現可折疊之結構化研究歷程（Research Trace Timeline）與可點擊跳轉之來源標籤（Source Badges）。

2. **多檔位模型推理程度（Reasoning Effort）選擇**：
   - 頂部導覽列支援切換五種推理深度檔位：`無 (None)`、`輕度 (Low)`、`標準 (Medium)`、`深度 (High)`、`極致 (X-High)`。
   - 完整支援 Azure OpenAI v1 與 OpenAI 推理模型（如 GPT-5 系列、o-series）。
   - 依微軟 Foundry 規範自動處理工具調用與推理相容性限制。

3. **模組化增強型混合 RAG 檢索引擎**：
   - 結合 FAISS 稠密向量搜尋（Dense Retrieval）與 Whoosh BM25 中文稀疏文字檢索（Sparse Retrieval）。
   - 搭配 Cross-Encoder (`ms-marco-MiniLM-L-6-v2` / `bge-reranker-base`) 進行加權重排序，確保知識檢索精準度。
   - 支援自動動態調整 Alpha 權重與 RAG 檢索評估指標（Hit Rate, MRR）。

4. **多模型提供商彈性整合**：
   - 提供統一的 LLM 調用抽象層，支援 Azure OpenAI v1、OpenAI 官方 API、Anthropic Claude、Google Gemini 與本地 Ollama 模型動態切換與自動多模型清單拆分。

5. **企業級安全與雙層日誌脫敏**：
   - 採用 RSA-2048 非對稱密鑰簽署之 JWT Access Token 與 HttpOnly 安全 Cookie。
   - 內建物件層級遞迴脫敏與字串正則遮罩防護（`security_logging.py`），嚴格防範密碼、Token 與機敏資料洩漏至系統日誌。

---

## 系統架構與設計

```mermaid
flowchart TB
    subgraph Client ["前端應用層 (React 19 + TypeScript + Vite + Bun)"]
        UI["Chat 對話介面 (MUI v7)"]
        TraceView["研究歷程摺疊卡片 (ResearchTraceBlock)"]
        DocManage["知識庫文件管理 (Documents)"]
        AdminView["系統管理後台 (AdminDashboard)"]
    end

    subgraph Backend ["後端服務層 (FastAPI + Python 3.10+)"]
        SecurityMW["安全日誌中介軟體 (Security Logging)"]
        AuthService["JWT 認證服務 (RSA-2048)"]
        ChatAPI["對話 API 端點 (/api/chat)"]
        DocAPI["文件上傳與索引端點 (/api/documents)"]
        
        subgraph AgenticRAG ["Agentic RAG 核心管線"]
            Agent["自主研究 Agent (ResearchAgent)"]
            ToolRegistry["工具註冊中心 (ResearchToolRegistry)"]
            HybridRetriever["混合檢索器 (FAISS + BM25 + Cross-Encoder)"]
            LLMClient["統一 LLM 客戶端 (Azure / OpenAI / Claude / Gemini / Ollama)"]
        end
    end

    subgraph Storage ["資料與索引儲存層"]
        SQLiteDB[(SQLite / PostgreSQL 資料庫)]
        FAISSStore["FAISS 向量索引庫 (faiss_index.bin)"]
        BM25Store["Whoosh BM25 關鍵字索引目錄"]
        DocUploads["文件儲存目錄 (data/uploads)"]
    end

    UI --> SecurityMW
    SecurityMW --> ChatAPI
    SecurityMW --> DocAPI
    SecurityMW --> AuthService
    
    ChatAPI --> Agent
    Agent --> ToolRegistry
    ToolRegistry --> HybridRetriever
    ToolRegistry -.-> |聯網搜尋| DuckDuckGo["DuckDuckGo / Ollama Web Search"]
    ToolRegistry -.-> |網頁深度抓取| WebContent["外部網頁內容 (HTTP Fetch)"]
    
    Agent --> LLMClient
    HybridRetriever --> FAISSStore
    HybridRetriever --> BM25Store
    DocAPI --> DocUploads
    AuthService --> SQLiteDB
```

---

## 專案目錄結構

```text
AskMiao/
├── backend/                        # 後端 FastAPI 專案
│   ├── app/
│   │   ├── api/                    # RESTful API 路由端點 (auth, chat, documents, admin)
│   │   ├── core/                   # 核心設定、安全認證、日誌脫敏與 LLM 客戶端
│   │   │   ├── config.py           # 系統全域環境變數配置
│   │   │   ├── jwt_auth.py         # RSA-2048 JWT 簽章與驗證
│   │   │   ├── llm_client.py       # 多提供商 LLM 統一調用層
│   │   │   └── security_logging.py # 敏感資料雙層遮罩日誌系統
│   │   ├── models/                 # SQLAlchemy ORM 與 Pydantic 驗證模型
│   │   ├── rag/                    # 模組化 RAG 與 Agentic 研究核心
│   │   │   ├── agent.py            # ReAct 自主研究 Agent
│   │   │   ├── tools.py            # 本地 RAG、聯網搜尋與網頁解析工具集
│   │   │   ├── pipeline.py         # RAG 執行管線與上下文組裝
│   │   │   ├── contextual_rag.py   # HybridContextualRAG 門面模組
│   │   │   ├── evaluator.py        # 檢索評估與自動 Alpha 調優
│   │   │   ├── indices/            # FAISS 與 BM25 索引管理模組
│   │   │   └── retrievers/         # 混合檢索與 Cross-Encoder 重排序器
│   │   ├── services/               # 業務邏輯服務層 (ChatService, DocumentService)
│   │   └── tasks/                  # 背景排程任務 (定時索引重建、上傳監控)
│   ├── tests/                      # 後端單元測試與自主研究驗收測試
│   ├── main.py                     # FastAPI 應用程式主進入點
│   ├── init_db.py                  # 資料庫初始化與預設管理員建立腳本
│   └── requirements.txt            # Python 依賴清單
├── frontend/                       # 前端 React 19 + Vite 專案
│   ├── src/
│   │   ├── pages/                  # 前端頁面元件
│   │   │   ├── Chat/               # Chat 模組 (MessageItem, TraceBlock, SourceBadges, Header)
│   │   │   ├── Documents/          # 知識庫文件上傳與管理頁面
│   │   │   ├── Admin/              # 系統管理後台
│   │   │   ├── Login/ & Register/  # 登入與註冊頁面
│   │   │   └── Profile/            # 個人資料頁面
│   │   ├── hooks/                  # React 自訂 Hooks (useChat, useAuth)
│   │   ├── services/               # Axios API 請求封裝與 Token 攔截器
│   │   └── components/             # 通用元件與 Layout
│   ├── package.json                # 前端專案設定 (使用 Bun 管理)
│   └── vite.config.js              # Vite 建構配置
├── docs/                           # 詳細系統規格與架構文件
│   ├── api.md                      # API 參考文件 (繁體中文)
│   ├── api_en.md                   # API 參考文件 (英文)
│   ├── architecture.md             # 系統架構與設計 (繁體中文)
│   ├── architecture_en.md          # 系統架構與設計 (英文)
│   └── adr/                        # 架構決策紀錄 (ADR)
├── llms.txt                        # AI 友善結構索引 (繁體中文)
├── llms_en.txt                     # AI 友善結構索引 (英文)
├── CHANGELOG.md                    # 版本變更紀錄 (繁體中文)
├── CHANGELOG_en.md                 # 版本變更紀錄 (英文)
└── LICENSE                         # MIT 授權條款
```

---

## 環境配置矩陣

### 後端環境變數 (`backend/.env`)

| 變數名稱 | 描述 | 範例 / 預設值 | 必填 |
|---|---|---|---|
| `ENABLE_WEB_SEARCH` | 是否啟用 Agent 聯網搜尋工具 | `true` | 否 |
| `AGENT_MAX_TURNS` | Agent 自主研究最大工具調用輪數 | `5` | 否 |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API 金鑰 | `your_azure_api_key` | 否 |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI v1 服務端點 URL | `https://your-resource.services.ai.azure.com` | 否 |
| `AZURE_OPENAI_DEPLOYMENT`| Azure OpenAI 部署名稱 (支援逗號分隔多模型) | `gpt-5.6-luna,gpt-5.6-terra` | 否 |
| `OPENAI_API_KEY` | OpenAI 官方 API 金鑰 (選填) | `sk-...` | 否 |
| `ANTHROPIC_API_KEY` | Anthropic Claude API 金鑰 (選填) | `sk-ant-...` | 否 |
| `GEMINI_API_KEY` | Google Gemini API 金鑰 (選填) | `AIza...` | 否 |
| `LLM_API_BASE` | 本地 Ollama 服務端點 URL | `http://localhost:5000` | 否 |
| `MODEL_NAME` | 本地預設模型名稱 | `gemma4:26b` | 否 |
| `JWT_SECRET_KEY` | JWT 簽署金鑰 | `cb_jwt_sec_...` | 是 |
| `ADMIN_API_KEY` | 系統管理員 API 金鑰 | `cb_admin_key_...` | 是 |
| `DATABASE_URL` | 資料庫連線字串 | `sqlite:///./chatbot.db` | 否 |
| `EMBEDDING_MODEL` | 向量嵌入模型名稱 | `paraphrase-multilingual-MiniLM-L12-v2` | 否 |
| `RERANKER_MODEL` | 重排序模型名稱 | `cross-encoder/ms-marco-MiniLM-L-6-v2` | 否 |

### 前端環境變數 (`frontend/.env`)

| 變數名稱 | 描述 | 預設值 | 必填 |
|---|---|---|---|
| `VITE_API_BASE` | 後端 API 代理或基礎路徑 | `/api` | 否 |
| `VITE_API_URL` | 後端伺服器絕對端點 (若跨域直連) | `http://localhost:8001` | 否 |

---

## 文件導覽

- [API 參考文件](./docs/api.md) — 完整 RESTful 端點、請求回應 JSON 規格與參數說明
- [系統架構與設計文件](./docs/architecture.md) — 模組關係圖、Agentic RAG 管線與安全架構
- [架構決策紀錄 (ADR)](./docs/adr/README.md) — 專案架構演進與技術選型紀錄
- [AI 友善結構導覽](./llms.txt) — 專供 AI Agent 與 LLM 讀取之結構導覽與約束
- [版本變更紀錄](./CHANGELOG.md) — 系統版本演進歷史

---

## 貢獻指南

歡迎參與 AskMiao 的開發與改進！請遵循以下流程：

1. Fork 本專案倉庫並建立您的功能分支 (`git checkout -b feature/amazing-feature`)。
2. 確保程式碼通過前端與後端型別檢查及測試：
   - 後端測試：`pytest tests/`
   - 前端型別檢查與測試：`bun x tsc --noEmit`、`bun run build`、`bun run lint`
3. 提交您的變更 (`git commit -m 'feat: Add amazing feature'`)。
4. 推送至分支 (`git push origin feature/amazing-feature`)。
5. 開啟 Pull Request 並詳細說明變更內容。

---

## 授權條款

本專案基於 MIT 授權條款發行。詳情請參閱 [LICENSE](LICENSE) 檔案。