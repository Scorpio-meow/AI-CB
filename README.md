# ChatBot 應用程式

一個具備使用者介面和後台管理介面的 ChatBot 應用程式，使用 Contextual RAG（檢索增強生成）技術提供智能對話服務。

## 功能特色

### 🤖 智能對話
- **Contextual RAG**: 基於對話歷史和文件知識庫的上下文感知回答
- **即時聊天**: 支援 WebSocket 即時通訊
- **對話管理**: 多對話管理，支援對話歷史保存

### 👥 用戶管理
- **用戶註冊登入**: JWT 身份驗證系統（前後端代碼已準備，待整合）
- **權限控制**: 區分一般用戶和管理員權限

### 📚 知識庫管理
- **文件上傳**: 支援多種文件格式（PDF, TXT, DOCX）
- **智能分塊**: 自動將文件分割為語義塊
- **向量搜尋**: 使用 FAISS IndexFlatIP 進行高效相似度搜尋
- **多編碼支援**: 支援 UTF-8, GBK, Big5 等中文編碼
- **文檔處理**: PyPDF2 + python-docx 處理多格式文件

### 🎛️ 後台管理
- **用戶管理**: 查看、編輯、刪除用戶
- **對話監控**: 查看用戶對話記錄
- **系統統計**: 使用量統計和分析
- **文件管理**: 知識庫文件管理

## 技術架構

### 後端
- **FastAPI**: 高性能 Web 框架
- **SQLAlchemy**: ORM 數據庫操作
- **LangChain**: RAG 實現框架
- **OpenAI/GitHub Models**: 大型語言模型支援
- **FAISS**: 向量數據庫 (IndexFlatIP)
- **PyPDF2 + python-docx**: 文檔處理
- **SQLite/PostgreSQL**: 主數據庫
- **sentence-transformers**: 多語言嵌入模型

### 前端
- **React 18**: 用戶界面框架
- **Material-UI**: UI 組件庫
- **React Router**: 路由管理
- **Axios**: HTTP 客戶端

## 安裝和運行

### 環境要求
- Python 3.10+
- Node.js 16+
- SQLite (開發) / PostgreSQL (生產)

### 後端設置

1. 進入後端目錄：
```bash
cd backend
```

2. 使用現有虛擬環境：
```bash
# Windows
.\CBvenv\Scripts\Activate.ps1
```

3. 安裝依賴（如需要）：
```bash
pip install -r requirements.txt
```

4. 配置環境變數：
```bash
copy .env.example .env
# 編輯 .env 文件，填入實際配置
```

5. 啟動後端服務：
```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 前端設置

1. 進入前端目錄：
```bash
cd frontend
```

2. 安裝依賴：
```bash
npm install
```

3. 啟動前端服務：
```bash
npm start
```

## 配置說明

### 環境變數

#### 後端 (.env)
```env
# GitHub Models API (推薦)
GITHUB_TOKEN=your_github_token_here
MODEL_NAME=openai/gpt-5-chat
GITHUB_API_BASE=https://models.github.ai/inference

# 或 OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# JWT 密鑰
SECRET_KEY=your_jwt_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 數據庫連接 (SQLite 為默認)
DATABASE_URL=sqlite:///./chatbot.db
# DATABASE_URL=postgresql://username:password@localhost/chatbot_db

# RAG 設置
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
SIMILARITY_THRESHOLD=0.3
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

#### 前端 (.env)
```env
REACT_APP_API_URL=http://127.0.0.1:8000
```

## API 接口

### 身份驗證（未整合）
- `POST /api/auth/register` - 用戶註冊
- `POST /api/auth/login` - 用戶登入
- `GET /api/auth/me` - 獲取當前用戶信息

### 聊天功能
- `POST /api/chat/send` - 發送消息
- `GET /api/chat/conversations` - 獲取對話列表
- `GET /api/chat/conversations/{id}` - 獲取對話詳情
- `DELETE /api/chat/conversations/{id}` - 刪除對話

### 文件管理
- `POST /api/documents/upload` - 上傳文件 (支援 TXT, PDF, DOCX)
- `GET /api/documents/` - 獲取文件列表
- `DELETE /api/documents/{id}` - 刪除文件
 - `POST /api/documents/bulk_delete` - 批次刪除文件（接受 JSON { ids: [1,2,3] }，回傳每 id 的刪除結果）

### 管理功能
- `GET /api/admin/users` - 獲取用戶列表
- `GET /api/admin/statistics` - 獲取系統統計
- `PUT /api/admin/users/{id}` - 更新用戶信息
- `DELETE /api/admin/users/{id}` - 刪除用戶
- `GET /api/admin/conversations` - 獲取所有對話
- `DELETE /api/admin/conversations/{id}` - 刪除對話
- `GET /api/admin/documents` - 獲取所有文檔
- `DELETE /api/admin/documents/{id}` - 刪除文檔
- `GET /api/admin/vector-store/info` - 獲取向量庫信息
- `GET /api/admin/vector-store/statistics` - 獲取向量庫統計
- `DELETE /api/admin/vector-store/clear` - 清空向量庫

## Contextual RAG 實現

### 核心特色
1. **對話上下文感知**: 結合歷史對話提高回答相關性
2. **智能文件檢索**: 基於語義相似度的文件片段檢索
3. **動態重排序**: 根據對話上下文重新排序檢索結果
4. **多層次匹配**: 關鍵詞匹配 + 語義匹配的混合策略

### 工作流程
1. 用戶提問
2. 提取對話歷史上下文
3. 增強查詢（查詢 + 上下文）
4. 向量檢索相關文件片段
5. 基於上下文重排序
6. 生成最終回答

## 部署

### Docker 部署

1. 構建後端鏡像：
```bash
cd backend
docker build -t chatbot-backend .
```

2. 構建前端鏡像：
```bash
cd frontend
docker build -t chatbot-frontend .
```

3. 使用 docker-compose：
```bash
docker-compose up -d
```

### 生產環境

1. 設置反向代理（Nginx）
2. 配置 HTTPS
3. 設置環境變數
4. 配置數據庫連接池
5. 設置日誌記錄

## 開發指南

### 項目結構
```
chatbot/
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── models/       # 數據模型
│   │   ├── services/     # 業務邏輯
│   │   └── rag/          # RAG 實現
│   ├── data/             # 數據文件
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # 組件
│   │   ├── pages/        # 頁面
│   │   ├── services/     # API 服務
│   │   └── contexts/     # React Context
│   └── package.json
└── README.md
```

### 開發流程
1. 後端 API 開發
2. 前端組件開發
3. 整合測試
4. 部署上線

## 貢獻

歡迎提交 Issue 和 Pull Request！

## 授權

MIT License

## 聯絡

如有問題，請聯絡開發團隊。
