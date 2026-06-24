# AskMiao

<div align="center">

一個基於增強型混合 RAG（檢索增強生成）技術的智能對話系統

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[功能特色](#功能特色) • [快速開始](#快速開始) • [技術架構](#技術架構) • [API 文件](#api-文件)

</div>

---

## 目錄

- [功能特色](#功能特色)
- [技術架構](#技術架構)
- [快速開始](#快速開始)
- [環境配置](#環境配置)
- [API 文件](#api-文件)
- [開發指南](#開發指南)
- [部署](#部署)
- [常見問題](#常見問題)
- [貢獻](#貢獻)

---

## 功能特色

### 智能對話系統

- **混合 RAG 檢索**：結合向量搜尋（FAISS）和 BM25 關鍵詞匹配
- **智能重排序**：使用 Cross-Encoder 提升檢索結果相關性
- **多模型支援**：動態切換不同 LLM 模型
- **對話管理**：支援多對話同時進行，保留歷史記錄
- **即時通訊**：基於 WebSocket 的實時對話

### 討論看板（Discussion Board）

- **多 Agent 協作**：以視覺化節點圖呈現多個 AI Agent 的討論流程
- **React Flow 整合**：直觀的拖拉式節點介面
- **即時串流**：Agent 回覆逐字即時顯示
- **標籤系統**：依標籤分類與篩選討論主題

### 安全與認證

- **JWT 雙 Token 機制**：Access Token（30 分鐘）+ Refresh Token（7 天）
- **RSA 非對稱加密**：使用 RSA-2048 簽名，適用於微服務架構
- **Token 黑名單**：Redis 實現的撤銷機制
- **背景刷新**：自動更新 Token，無感體驗
- **角色權限控制**：基於 RBAC 的細粒度權限管理
- **速率限制**：防止 API 濫用（60 次/分鐘）

### 知識庫管理

- **多格式支援**：PDF、TXT、DOCX 文件處理
- **流式上傳**：支援大文件（最大 10MB）
- **批次操作**：批次上傳最多 10 個文件
- **智能分塊**：RecursiveCharacterTextSplitter（300 字符，100 重疊）
- **混合索引**：FAISS + Whoosh 雙重索引
- **多編碼支援**：自動檢測 UTF-8、GBK、Big5 等編碼

### Agent 工作流系統

- **自定義 Agent**：創建專屬的 AI Agent
- **可見性控制**：公開／私有設定
- **權限隔離**：使用者僅能存取自己的或公開的 Agent
- **角色預設**：內建多種專業角色模板

### 後台管理

- **使用者管理**：完整的 CRUD 操作
- **對話監控**：查看所有使用者對話紀錄
- **系統統計**：使用量分析與性能指標
- **向量庫監控**：索引狀態、重建統計、性能追蹤

---

## 技術架構

### 後端技術棧

| 類別 | 技術 |
|------|------|
| **Web 框架** | FastAPI 0.104+ |
| **ORM** | SQLAlchemy 2.0+ |
| **AI/ML** | LangChain, Sentence-Transformers, FlagEmbedding, FAISS, Whoosh |
| **LLM** | Ollama（本地部署）或任意 OpenAI 相容端點 |
| **資料庫** | PostgreSQL 17.9（開發/生產）、Redis（快取） |
| **安全** | cryptography, passlib, python-jose, argon2-cffi |
| **文件處理** | pypdf, python-docx, chardet, jieba |

### 前端技術棧

| 類別 | 技術 |
|------|------|
| **核心框架** | React 19 |
| **UI 組件庫** | Material-UI (MUI) v7 |
| **路由** | React Router v7 |
| **HTTP 客戶端** | Axios |
| **WebSocket** | 原生 WebSocket API |
| **流程圖** | React Flow（討論看板節點視覺化） |
| **Markdown 渲染** | react-markdown + remark-gfm |
| **構建工具** | Vite 7 |
| **測試框架** | Vitest |

### RAG 系統架構

```mermaid
flowchart TD
    A["使用者查詢"] --> B["智能檢索策略選擇<br/>(向量搜尋 / BM25 / 混合搜尋)"]
    B --> C["向量搜尋<br/>(FAISS)"]
    B --> D["BM25<br/>(Whoosh)"]
    B --> E["混合搜尋<br/>(融合)"]
    C --> F["Cross-Encoder 重新排序<br/>(BAAI/bge-reranker-v2-m3)"]
    D --> F
    E --> F
    F --> G["LLM 生成回答"]
    
    style A fill:#e1f5ff,stroke:#333,stroke-width:2px
    style B fill:#fff4e1,stroke:#333,stroke-width:2px
    style C fill:#e8f5e9,stroke:#333,stroke-width:2px
    style D fill:#e8f5e9,stroke:#333,stroke-width:2px
    style E fill:#e8f5e9,stroke:#333,stroke-width:2px
    style F fill:#ffe1f5,stroke:#333,stroke-width:2px
    style G fill:#e1ffe1,stroke:#333,stroke-width:2px
```

### 核心模型

- **嵌入模型**：`BAAI/bge-m3`（1024 維，支援 100+ 語言）
- **重排序模型**：`BAAI/bge-reranker-v2-m3`（提升檢索精度）
- **向量索引**：FAISS IndexFlatIP（內積相似度）
- **BM25 索引**：Whoosh StandardAnalyzer + jieba 中文分詞

---

## 快速開始

### 環境要求

- **Python**：3.10 或更高版本
- **Node.js**：18.0 或更高版本（或使用 Bun）
- **Redis**：可選（推薦生產環境）
- **資料庫**：PostgreSQL 17.9（開發/生產）

### 安裝步驟

#### 1. 克隆倉庫

```bash
git clone https://github.com/Scorpio-meow/AskMiao.git
cd AskMiao
```

#### 2. 後端設定

```bash
# 進入後端目錄
cd backend

# 創建並啟動虛擬環境
python -m venv CBvenv
.\CBvenv\Scripts\Activate.ps1  # Windows PowerShell
# 或
source CBvenv/bin/activate  # Linux/macOS

# 安裝相依套件
# 若需 GPU 加速，請先手動安裝 PyTorch：
# pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu130
pip install -r requirements.txt

# 配置環境變數（複製並編輯 .env 文件）
cp .env.example .env

# 初始化資料庫
python init_db.py

# （可選）若你有舊版 SQLite 資料，執行遷移到 PostgreSQL
python scripts/migrate_sqlite_to_postgres.py

# 啟動後端服務
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

#### 3. 前端設定

```bash
# 開啟新終端，進入前端目錄
cd frontend

# 安裝相依套件（推薦 Bun）
# Bun 安裝（Windows PowerShell）：
# powershell -c "irm bun.sh/install.ps1 | iex"
bun install

# 啟動前端開發伺服器
bun run dev

# 或使用 npm
npm install
npm run dev
```

> **備註**：本專案已在 `CBvenv` 的 PowerShell 激活腳本中加入 Bun 路徑（若安裝於 `~/.bun/bin`），啟動虛擬環境後 Bun 命令可以直接使用，否則請將 Bun 安裝目錄加入系統 PATH。

#### 4. PostgreSQL 設定（必要）

```bash
# 使用 Docker 啟動 PostgreSQL 17.9
docker run -d --name chatbot-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=chatbot \
  -p 7690:5432 \
  postgres:17.9
```

#### 5. Redis 設定（可選，用於生產環境）

```bash
# 使用 Docker（推薦）
docker run -d -p 7967:6379 --name chatbot-redis redis:latest

# 或使用 WSL（Windows）
wsl
sudo service redis-server start
```

### 驗證安裝

- **後端**：http://localhost:8001
- **前端**：http://localhost:5173（Vite 預設）
- **API 文件**：http://localhost:8001/docs

健康檢查：
```bash
curl http://localhost:8001/health
# 預期輸出: {"status":"healthy"}
```

---

## 環境配置

### 後端環境變數（`backend/.env`）

```env
# === 核心 LLM 配置 ===
LLM_API_BASE=https://your-llm-endpoint.com
LLM_TIMEOUT=120

# === 安全配置 ===
ADMIN_API_KEY=your_secure_admin_api_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# === 環境設定 ===
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8001
LOG_LEVEL=INFO

# === 資料庫配置 ===
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:7690/chatbot
# DATABASE_URL=sqlite:///./chatbot.db  # 僅臨時本地測試

# === Redis 配置 (Token 黑名單) ===
REDIS_HOST=localhost
REDIS_PORT=7967
REDIS_DB=0
# REDIS_PASSWORD=your_password  # 可選
ENABLE_REDIS_CACHE=true

# === CORS 配置 ===
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# === RAG 系統 - 模型配置 ===
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# === RAG 系統 - 檢索參數 ===
SIMILARITY_THRESHOLD=0.30
TOP_K=30
RERANK_TOP_K=50
FINAL_K=8
RERANK_WEIGHT=0.85
FINAL_THRESHOLD=0.15
HYBRID_ALPHA=0.75
NORMALIZATION=max

# === RAG 系統 - 文件處理 ===
CHUNK_SIZE=300
CHUNK_OVERLAP=100
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=data/uploads

# === RAG 系統 - 索引管理 ===
ENABLE_AUTO_REINDEX_TASK=1
REINDEX_HOURS=24
DATA_DIR=data

# === 速率限制 ===
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

### 前端環境變數（`frontend/.env`）

```env
# === API 連接 ===
VITE_API_URL=http://localhost:8001
VITE_API_BASE=http://localhost:8001

# === WebSocket 連接 ===
VITE_WS_URL=ws://localhost:8001

# === 功能開關 ===
VITE_ENABLE_DEBUG=true
```

---

## API 文件

### 認證相關

#### 使用者註冊
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "user123",
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

#### 使用者登入
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user123",
  "password": "SecurePass123!"
}

# 返回：
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Token 刷新
```http
POST /api/auth/refresh
Cookie: refresh_token=<token>

# 返回新的 access_token
```

### 聊天功能

#### 發送消息
```http
POST /api/chat/send
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "message": "你好，請問...",
  "conversation_id": 123,  # 可選
  "use_rag": true          # 可選
}
```

#### WebSocket 即時聊天
```javascript
const ws = new WebSocket('ws://localhost:8001/ws/chat');

ws.send(JSON.stringify({
  message: "你好",
  conversation_id: 123
}));

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.response);
};
```

### 文件管理

#### 上傳文件
```http
POST /api/documents/upload
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

files: [file1.pdf, file2.txt, ...]  # 最多 10 個，每個 <10MB
```

#### 批次刪除文件
```http
POST /api/documents/bulk_delete
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "ids": [1, 2, 3, 4, 5]
}
```

### 討論看板（Workflow）

#### 建立工作流
```http
POST /api/workflow/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "技術討論",
  "tag_ids": [1, 2]
}
```

完整 API 文件請造訪：http://localhost:8001/docs

---

## 開發指南

### 專案結構

```
AskMiao/
├── backend/                 # 後端服務
│   ├── app/                # 應用核心程式碼
│   │   ├── api/           # API 路由（auth, chat, documents, admin, custom_agent, tags, workflow）
│   │   ├── core/          # 核心功能（安全、設定）
│   │   ├── crud/          # 資料庫 CRUD 操作
│   │   ├── models/        # SQLAlchemy 資料模型
│   │   ├── rag/           # RAG 系統（contextual_rag.py）
│   │   ├── schemas/       # Pydantic 請求/回應模式
│   │   ├── services/      # 業務邏輯服務層
│   │   ├── tasks/         # 後台排程任務
│   │   └── middleware.py  # 速率限制等中介層
│   ├── data/              # 資料儲存（向量索引、文件）
│   ├── keys/              # RSA 金鑰
│   ├── logs/              # 日誌文件
│   ├── scripts/           # 工具腳本
│   │   ├── migrate_sqlite_to_postgres.py
│   │   ├── reset_faiss.py
│   │   └── docx_to_txt.py
│   ├── tests/             # 測試套件
│   ├── main.py            # 應用入口
│   ├── init_db.py         # 資料庫初始化
│   └── requirements.txt   # Python 相依套件
│
├── frontend/               # 前端應用（Vite + React 19）
│   ├── public/            # 靜態資源
│   ├── src/               # 原始碼
│   │   ├── components/   # 共用 React 組件（Layout, PrivateRoute, NetworkStatus）
│   │   ├── contexts/     # Context API（認證、主題）
│   │   ├── hooks/        # 自定義 Hooks
│   │   ├── pages/        # 頁面組件
│   │   │   ├── Chat.jsx
│   │   │   ├── Documents.jsx
│   │   │   ├── CustomAgents.jsx
│   │   │   ├── AdminDashboard.jsx
│   │   │   ├── ProfilePage.jsx
│   │   │   ├── LoginPage.jsx
│   │   │   ├── RegisterPage.jsx
│   │   │   └── DiscussionBoard/  # 多 Agent 討論看板
│   │   ├── services/     # API 服務（authService, customAgentService）
│   │   └── utils/        # 工具函數
│   ├── vite.config.js     # Vite 構建配置
│   └── package.json       # Node.js 相依套件
│
└── README.md              # 本文件
```

### 開發流程

1. **創建新分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **開發功能**
   - 後端：在 `backend/app/` 中添加程式碼
   - 前端：在 `frontend/src/` 中添加組件

3. **測試**
   ```bash
   # 後端測試
   cd backend
   pytest

   # 前端測試
   cd frontend
   bun run test
   # 或
   npm test
   ```

4. **提交程式碼**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/your-feature-name
   ```

### 程式碼風格

- **Python**：遵循 PEP 8
- **JavaScript/JSX**：遵循 ESLint 規則（參考 `eslint.config.js`）
- **提交消息**：使用 Conventional Commits

---

## 部署

### Docker 部署

```bash
# 使用 docker-compose（位於 backend/ 目錄）
cd backend
docker-compose up -d

# 查看日誌
docker-compose logs -f

# 停止服務
docker-compose down
```

### 生產環境配置

1. **設定環境變數**
   - 更改 `ENVIRONMENT=production`
   - 設定安全的 `JWT_SECRET_KEY` 和 `ADMIN_API_KEY`
   - 配置 PostgreSQL 資料庫
   - 啟用 Redis
   - 更新 `ALLOWED_ORIGINS` 為正式域名

2. **使用 HTTPS**
   - 配置 SSL 證書
   - 設定反向代理（Nginx）

3. **優化性能**
   - 使用 Gunicorn/Uvicorn workers
   - 啟用資料庫連線池
   - 配置 CDN
   - 前端執行 `bun run build` 構建靜態資源

---

## 常見問題

### Q: 如何把舊版 SQLite（chatbot.db）資料遷移到 PostgreSQL？
```bash
cd backend
python scripts/migrate_sqlite_to_postgres.py

# 指定來源檔
python scripts/migrate_sqlite_to_postgres.py --source ./chatbot.db

# 僅檢查不寫入
python scripts/migrate_sqlite_to_postgres.py --dry-run
```

### Q: 如何重置 FAISS 向量索引？
系統會依 `REINDEX_HOURS` 設定自動重建索引。手動重置：
```bash
cd backend
python scripts/reset_faiss.py
```

### Q: 如何更換 LLM 模型？
在 `backend/.env` 中修改 `LLM_API_BASE`，然後重啟後端服務。

### Q: 前端無法連接後端？
確認 `frontend/vite.config.js` 中的 proxy 設定是否正確，預設應代理至 `http://127.0.0.1:8001`。

### Q: 模型下載速度慢？
可設定 Hugging Face 鏡像站：
```bash
# Windows PowerShell
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

### Q: 如何啟用 GPU 加速？
安裝對應 CUDA 版本的 PyTorch：
```bash
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

---

## 貢獻

我們歡迎各種形式的貢獻！

1. Fork 本倉庫
2. 創建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟一個 Pull Request

請確保你的程式碼：
- 通過所有測試
- 遵循程式碼風格指南
- 包含適當的文件

---

## 聯繫方式

- **專案首頁**：[GitHub](https://github.com/Scorpio-meow/AskMiao)
- **問題反饋**：[Issues](https://github.com/Scorpio-meow/AskMiao/issues)
- **郵件**：yao921024@gmail.com

---

<div align="center">

**感謝使用 AskMiao！**

如果這個專案對你有幫助，請給我們一個 Star！

</div>
