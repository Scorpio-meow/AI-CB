# ChatBot 應用程式

一個具備使用者介面和後台管理介面的 ChatBot 應用程式，使用增強型混合 RAG（檢索增強生成）技術提供智能對話服務。

## 功能特色

### 🤖 智能對話
- **混合 RAG**: 結合向量搜尋和 BM25 關鍵詞匹配的混合檢索系統
- **Cross-Encoder 重新排序**: 使用 ms-marco-MiniLM-L-6-v2 提升檢索精度
- **智能搜尋策略**: 根據查詢特徵自動選擇最佳搜尋方法
- **即時聊天**: 支援 WebSocket 即時通訊
- **對話管理**: 多對話管理，支援對話歷史保存
- **自動重建索引**: 24 小時周期自動維護索引性能

### 👥 用戶管理
- **用戶註冊登入**: JWT 身份驗證系統（前後端代碼已準備，待整合）
- **權限控制**: 區分一般用戶和管理員權限

### 📚 知識庫管理
- **文件上傳**: 支援多種文件格式（PDF, TXT, DOCX）
- **流式上傳**: 避免大文件記憶體問題，支援多檔上傳和進度顯示
- **智能分塊**: 自動將文件分割為語義塊（600字符，150重疊）
- **混合索引**: FAISS IndexFlatIP + Whoosh BM25 雙重索引
- **多編碼支援**: 支援 UTF-8, GBK, Big5 等中文編碼
- **文檔處理**: PyPDF2 + python-docx 處理多格式文件
- **批次管理**: 支援批次刪除文檔與高效索引維護

### 🎛️ 後台管理
- **用戶管理**: 查看、編輯、刪除用戶
- **對話監控**: 查看用戶對話記錄
- **系統統計**: 使用量統計和分析
- **文件管理**: 知識庫文件管理
- **向量庫監控**: 索引狀態、重建統計、性能指標

### 📊 評估與監控
- **檢索質量評估**: Recall@k, Precision@k, MRR 指標
- **性能基準測試**: 多種搜尋方法比較
- **配置優化**: 不同參數組合的效果評估
- **自動化測試**: 包含評估腳本和測試工具

## 技術架構

### 後端
- **FastAPI**: 高性能 Web 框架
- **SQLAlchemy**: ORM 數據庫操作
- **LangChain**: RAG 實現框架
- **Ollama/GitHub Models**: 大型語言模型支援
- **FAISS**: 向量數據庫 (IndexFlatIP, 384維)
- **Whoosh**: BM25 全文檢索引擎
- **Cross-Encoder**: ms-marco-MiniLM-L-6-v2 重新排序
- **PyPDF2 + python-docx**: 文檔處理
- **SQLite/PostgreSQL**: 主數據庫
- **sentence-transformers**: paraphrase-multilingual-MiniLM-L12-v2 嵌入模型

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
# Ollama API 配置（推薦）
GITHUB_TOKEN=your-token-here
MODEL_NAME=gpt-oss:20b
GITHUB_API_BASE=https://your-ngrok-url.ngrok-free.app

# 或 GitHub Models API
GITHUB_TOKEN=your_github_token_here
MODEL_NAME=gpt-4o-mini
GITHUB_API_BASE=https://models.inference.ai.azure.com

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
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
SIMILARITY_THRESHOLD=0.25
CHUNK_SIZE=600
CHUNK_OVERLAP=150
TOP_K=50
FINAL_K=5
REINDEX_HOURS=24
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

## 混合 RAG 系統

### 核心特色
1. **多重檢索策略**: 向量搜尋 + BM25 關鍵詞匹配 + 智能路由
2. **Cross-Encoder 重新排序**: 提升檢索結果相關性
3. **自動索引維護**: 24小時周期重建，保持最佳性能
4. **評估驅動優化**: 內建 Recall、Precision、MRR 指標
5. **對話上下文感知**: 結合歷史對話提高回答相關性

### 搜尋策略
- **向量搜尋**: 語義相似度匹配，適合概念性查詢
- **BM25 搜尋**: 關鍵詞精確匹配，適合具體詞彙查詢
- **混合搜尋**: 結合兩種方法，平衡覆蓋面和精度
- **智能路由**: 根據查詢特徵自動選擇最佳策略

### 工作流程
1. 用戶提問
2. 查詢分析（中文檢測、精確詞彙檢測等）
3. 智能選擇檢索策略（向量/BM25/混合）
4. 執行檢索並獲取候選文檔
5. Cross-Encoder 重新排序
6. 提取 top-k 結果
7. 構建上下文提示
8. 生成回答並更新對話記憶

## 部署

### Whoosh 中文分詞說明

Whoosh 預設分析器對中文並不理想，建議安裝並使用 `jieba` 作為中文分詞器以提升 BM25 檢索品質。

- 如要啟用 jieba 支援，請在後端環境中安裝：

```bash
pip install jieba
```

- 本專案會自動檢測是否安裝了 `jieba`：若已安裝，會在 Whoosh 中使用基於 jieba 的自訂 Analyzer；否則回退使用 Whoosh 的 `StandardAnalyzer`（對中文效果有限）。

註：若在 Windows 上遇到檔案鎖定問題，請參考 README 中的索引重建與清理段落。

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
