# AI-CB (AI ChatBot)

<div align="center">

一個基於增強型混合 RAG（檢索增強生成）技術的智能對話系統

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[功能特色](#-功能特色) • [快速開始](#-快速開始) • [技術架構](#️-技術架構) • [API 文檔](#-api-文檔)

</div>

---

## 📋 目錄

- [功能特色](#-功能特色)
- [技術架構](#️-技術架構)
- [快速開始](#-快速開始)
- [環境配置](#-環境配置)
- [ API 文檔](#-api-文檔)
- [開發指南](#-開發指南)
- [部署](#-部署)
- [常見問題](#-常見問題)
- [貢獻](#-貢獻)

---

## 🌟 功能特色

### 🤖 智能對話系統

- **混合 RAG 檢索**：結合向量搜尋（FAISS）和 BM25 關鍵詞匹配
- **智能重排序**：使用 Cross-Encoder 提升檢索結果相關性
- **多模型支援**：動態切換不同 LLM 模型
- **對話管理**：支援多對話並行，保留歷史記錄
- **即時通訊**：基於 WebSocket 的實時對話

### 🔒 安全與認證

- **JWT 雙 Token 機制**：Access Token (15分鐘) + Refresh Token (7天)
- **RSA 非對稱加密**：使用 RSA-2048 簽名，適用於微服務架構
- **Token 黑名單**：Redis 實現的撤銷機制
- **靜默刷新**：自動更新 Token，無感體驗
- **角色權限控制**：基於 RBAC 的細粒度權限管理
- **速率限制**：防止 API 濫用（60次/分鐘）

### 📚 知識庫管理

- **多格式支援**：PDF、TXT、DOCX 文件處理
- **流式上傳**：支援大文件（最大 10MB）
- **批次操作**：批次上傳最多 10 個文件
- **智能分塊**：RecursiveCharacterTextSplitter（600字符，150重疊）
- **混合索引**：FAISS + Whoosh 雙重索引
- **多編碼支援**：自動檢測 UTF-8、GBK、Big5 等編碼

### 🎯 Agent 工作流系統

- **自定義 Agent**：創建專屬的 AI Agent
- **可見性控制**：公開/私有設定
- **權限隔離**：用戶僅能訪問自己的或公開的 Agent
- **角色預設**：內建多種專業角色模板

### 🎛️ 後台管理

- **用戶管理**：完整的 CRUD 操作
- **對話監控**：查看所有用戶對話記錄
- **系統統計**：使用量分析與性能指標
- **向量庫監控**：索引狀態、重建統計、性能追蹤

---

## 🏗️ 技術架構

### 後端技術棧

| 類別 | 技術 |
|------|------|
| **Web 框架** | FastAPI 0.104+ |
| **ORM** | SQLAlchemy 2.0+ |
| **AI/ML** | LangChain, Sentence-Transformers, FAISS, Whoosh |
| **LLM** | Ollama（本地部署） |
| **數據庫** | SQLite (開發) / PostgreSQL (生產)、Redis (緩存) |
| **安全** | cryptography, passlib, python-jose |
| **文檔處理** | PyPDF2, python-docx, chardet |

### 前端技術棧

| 類別 | 技術 |
|------|------|
| **核心框架** | React 18 |
| **UI 組件庫** | Material-UI (MUI) v5 |
| **路由** | React Router v6 |
| **HTTP 客戶端** | Axios |
| **WebSocket** | 原生 WebSocket API |
| **構建工具** | Create React App |

### RAG 系統架構

```mermaid
flowchart TD
    A["用戶查詢"] --> B["智能檢索策略選擇<br/>(向量搜尋 / BM25 / 混合搜尋)"]
    B --> C["向量搜尋<br/>(FAISS)"]
    B --> D["BM25<br/>(Whoosh)"]
    B --> E["混合搜尋<br/>(融合)"]
    C --> F["Cross-Encoder 重新排序<br/>(ms-marco-MiniLM-L-6-v2)"]
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

- **嵌入模型**：`paraphrase-multilingual-MiniLM-L12-v2`（384維，支援50+語言）
- **重排序模型**：`cross-encoder/ms-marco-MiniLM-L-6-v2`（提升檢索精度）
- **向量索引**：FAISS IndexFlatIP（內積相似度）
- **BM25 索引**：Whoosh StandardAnalyzer + jieba 中文分詞

---

## 🚀 快速開始

### 📋 環境要求

- **Python**：3.10 或更高版本
- **Node.js**：16.0 或更高版本
- **Redis**：可選（推薦生產環境）
- **數據庫**：SQLite（開發）/ PostgreSQL（生產）

### ⚡ 安裝步驟

#### 1. 克隆倉庫

```bash
git clone https://github.com/Scorpio-meow/AI-CB.git
cd AI-CB
```

#### 2. 後端設置

```bash
# 進入後端目錄
cd backend

# 創建並啟動虛擬環境
python -m venv CBvenv
.\CBvenv\Scripts\Activate.ps1  # Windows PowerShell
# 或
source CBvenv/bin/activate  # Linux/macOS

# 安裝依賴
pip install -r requirements.txt

# 配置環境變數（複製並編輯 .env 文件）
cp .env.example .env

# 初始化數據庫
python init_db.py

# 啟動後端服務
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

#### 3. 前端設置

```bash
# 開啟新終端，進入前端目錄
cd frontend

# 安裝依賴
npm install

# 啟動前端開發服務器
npm start
```

#### 4. Redis 設置（可選，用於生產環境）

```bash
# 使用 Docker（推薦）
docker run -d -p 6379:6379 --name chatbot-redis redis:alpine

# 或使用 WSL（Windows）
wsl
sudo service redis-server start
```

### ✅ 驗證安裝

- **後端**：http://localhost:8001
- **前端**：http://localhost:3000
- **API 文檔**：http://localhost:8001/docs

健康檢查：
```bash
curl http://localhost:8001/health
# 預期輸出: {"status":"healthy"}
```

---

## 🔧 環境配置

### 後端環境變數（`backend/.env`）

```env
# LLM API 配置
MODEL_NAME=gpt-oss:20b
LLM_API_BASE=https://your-llm-endpoint.com
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000

# 數據庫配置
DATABASE_URL=sqlite:///./chatbot.db  # 開發環境
# DATABASE_URL=postgresql://user:password@localhost/chatbot  # 生產環境

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_password  # 可選

# JWT 配置
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=RS256

# 安全配置
ADMIN_API_KEY=your_secure_admin_api_key_here
SECRET_KEY=your_secret_key_here

# CORS 配置
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# RAG 系統配置
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
SIMILARITY_THRESHOLD=0.25
CHUNK_SIZE=600
CHUNK_OVERLAP=150
TOP_K=50
FINAL_K=10

# 文件上傳限制
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_UPLOAD=10
```

### 前端環境變數（`frontend/.env`）

```env
# 開發環境配置
HOST=localhost
PORT=3000

# 功能開關
REACT_APP_ENABLE_ANALYTICS=false
REACT_APP_ENABLE_DEBUG=true
```

---

## 📡 API 文檔

### 認證相關

#### 用戶註冊
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "user123",
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

#### 用戶登入
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
  "expires_in": 900
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

完整 API 文檔請訪問：http://localhost:8001/docs

---

## 🛠️ 開發指南

### 項目結構

```
AI-CB/
├── backend/                 # 後端服務
│   ├── app/                # 應用核心代碼
│   │   ├── api/           # API 路由
│   │   ├── core/          # 核心功能（RAG、安全）
│   │   ├── models/        # 數據模型
│   │   ├── schemas/       # Pydantic 模式
│   │   └── tasks/         # 後台任務
│   ├── data/              # 數據存儲（向量索引、文檔）
│   ├── keys/              # RSA 金鑰
│   ├── logs/              # 日誌文件
│   ├── scripts/           # 工具腳本
│   ├── main.py            # 應用入口
│   └── requirements.txt   # Python 依賴
│
├── frontend/               # 前端應用
│   ├── public/            # 靜態資源
│   ├── src/               # 源代碼
│   │   ├── components/   # React 組件
│   │   ├── contexts/     # Context API
│   │   ├── pages/        # 頁面組件
│   │   └── utils/        # 工具函數
│   └── package.json       # Node.js 依賴
│
└── README.md              # 本文檔
```

### 開發流程

1. **創建新分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **開發功能**
   - 後端：在 `backend/app/` 中添加代碼
   - 前端：在 `frontend/src/` 中添加組件

3. **測試**
   ```bash
   # 後端測試
   cd backend
   pytest

   # 前端測試
   cd frontend
   npm test
   ```

4. **提交代碼**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/your-feature-name
   ```

### 代碼風格

- **Python**：遵循 PEP 8
- **JavaScript**：遵循 ESLint 規則
- **提交消息**：使用 Conventional Commits

---

## 📦 部署

### Docker 部署

```bash
# 構建並啟動服務
docker-compose up -d

# 查看日誌
docker-compose logs -f

# 停止服務
docker-compose down
```

### 生產環境配置

1. **設置環境變數**
   - 更改 `ENVIRONMENT=production`
   - 設置安全的 `SECRET_KEY` 和 `ADMIN_API_KEY`
   - 配置 PostgreSQL 數據庫
   - 啟用 Redis

2. **使用 HTTPS**
   - 配置 SSL 證書
   - 設置反向代理（Nginx）

3. **優化性能**
   - 使用 Gunicorn/Uvicorn workers
   - 啟用數據庫連接池
   - 配置 CDN

---

## ❓ 常見問題

### Q: 如何創建管理員賬戶？
```bash
cd backend
python scripts/create_admin.py
```

### Q: 如何重建向量索引？
系統會每 24 小時自動重建索引。手動重建：
```bash
cd backend
python scripts/rebuild_index.py
```

### Q: 如何更換 LLM 模型？
在 `backend/.env` 中修改 `MODEL_NAME`，然後重啟後端服務。

### Q: 前端無法連接後端？
檢查 `frontend/package.json` 中的 `proxy` 設置是否正確：
```json
"proxy": "http://127.0.0.1:8001"
```

---

## 🤝 貢獻

我們歡迎各種形式的貢獻！

1. Fork 本倉庫
2. 創建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟一個 Pull Request

請確保你的代碼：
- 通過所有測試
- 遵循代碼風格指南
- 包含適當的文檔

---

## 📞 聯繫方式

- **項目主頁**：[GitHub](https://github.com/Scorpio-meow/AI-CB)
- **問題反饋**：[Issues](https://github.com/Scorpio-meow/AI-CB/issues)
- **郵件**：yao921024@gmail.com

---

<div align="center">

**感謝使用 AI-CB！** ⭐

如果這個項目對你有幫助，請給我們一個 Star！


</div>
