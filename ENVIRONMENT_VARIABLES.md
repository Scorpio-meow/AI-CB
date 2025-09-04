# 環境變數說明文件

此文件說明 AI-CB 專案中所有環境變數的用途和配置方式。

## 後端環境變數 (backend/.env)

### LLM Models API Configuration
- `MODEL_NAME`: 使用的 LLM 模型名稱 (預設: gemma3:27b)
- `LLM_API_BASE`: LLM API 的基礎 URL
- `LLM_TIMEOUT`: LLM API 請求超時時間（秒）(預設: 120)

### Database Configuration
- `DATABASE_URL`: 資料庫連接 URL (預設: sqlite:///./chatbot.db)

### JWT Authentication Configuration
- `SECRET_KEY`: JWT 簽名的密鑰
- `ALGORITHM`: JWT 簽名演算法 (預設: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: 存取令牌過期時間（分鐘）(預設: 30)

### CORS Configuration
- `ALLOWED_ORIGINS`: 允許的來源 URL，用逗號分隔

### RAG System Configuration
#### Embedding Models
- `EMBEDDING_MODEL`: 文件嵌入模型 (預設: paraphrase-multilingual-MiniLM-L12-v2)
- `RERANKER_MODEL`: 重新排序模型 (預設: cross-encoder/ms-marco-MiniLM-L-6-v2)

#### Search Parameters
- `SIMILARITY_THRESHOLD`: 相似度閾值 (預設: 0.25)
- `TOP_K`: 初始搜尋結果數量 (預設: 50)
- `RERANK_TOP_K`: 重新排序候選數量 (預設: 80)
- `FINAL_K`: 最終結果數量 (預設: 10)
- `RERANK_WEIGHT`: 重新排序權重 (預設: 0.8)
- `FINAL_THRESHOLD`: 最終閾值 (預設: 0.1)

#### Hybrid Search Configuration
- `HYBRID_ALPHA`: 混合搜尋中向量搜尋的權重 (預設: 0.7)
- `NORMALIZATION`: 分數正規化方法 (預設: max, 可選: softmax)

#### Text Chunking Configuration
- `CHUNK_SIZE`: 文本分塊大小 (預設: 300)
- `CHUNK_OVERLAP`: 分塊重疊大小 (預設: 100)

#### Vector Store Configuration
- `VECTOR_STORE_TYPE`: 向量儲存類型 (預設: faiss)

#### Auto Reindexing Configuration
- `ENABLE_AUTO_REINDEX`: 是否啟用自動重建索引 (預設: 0)
- `REINDEX_HOURS`: 重建索引的間隔時間（小時）(預設: 24)

### File Upload Configuration
- `MAX_FILE_SIZE_MB`: 最大檔案大小（MB）(預設: 50)
- `UPLOAD_DIR`: 檔案上傳目錄 (預設: data/uploads)

### Background Tasks Configuration
- `UPLOADS_WATCHER_INTERVAL`: 檔案監控任務間隔（秒）(預設: 30)

### Server Configuration
- `HOST`: 伺服器主機地址 (預設: 127.0.0.1)
- `PORT`: 伺服器埠號 (預設: 8001)
- `RELOAD`: 是否啟用自動重載 (預設: true)

### Workflow API Configuration
- `WORKFLOW_TIMEOUT`: 工作流程 API 超時時間（秒）(預設: 180)

### Data Storage Paths
- `DATA_DIR`: 資料目錄 (預設: data)
- `FAISS_INDEX_PATH`: FAISS 索引檔案路徑 (預設: data/faiss_index.bin)
- `DOCUMENTS_PATH`: 文件儲存路徑 (預設: data/documents.pkl)
- `BM25_INDEX_DIR`: BM25 索引目錄 (預設: data/bm25_index)
- `METADATA_PATH`: 元資料檔案路徑 (預設: data/index_metadata.pkl)
- `WORKFLOW_OUTPUTS_DIR`: 工作流程輸出目錄 (預設: data/workflow_outputs)

### Logging Configuration
- `LOG_LEVEL`: 日誌等級 (預設: INFO)

### Development Configuration
- `DEBUG`: 是否啟用除錯模式 (預設: true)

## 前端環境變數 (frontend/.env)

### API Configuration
- `REACT_APP_API_URL`: 後端 API 的基礎 URL (預設: http://localhost:8001/api)

### WebSocket Configuration
- `REACT_APP_WS_URL`: WebSocket 連接 URL (預設: ws://localhost:8001)

### Development Configuration
- `REACT_APP_ENV`: 應用程式環境 (預設: development)

### Build Configuration
- `GENERATE_SOURCEMAP`: 是否生成 source map (預設: false)

## 設定步驟

1. 複製 `.env.example` 檔案為 `.env`
2. 根據您的環境修改相應的變數值
3. 確保所有必要的變數都已設定
4. 重啟應用程式以套用新的配置

## 注意事項

- 生產環境中務必修改 `SECRET_KEY` 為安全的隨機字串
- `LLM_API_BASE` 必須設定為可用的 LLM API 端點
- 資料庫 URL 應根據實際使用的資料庫系統進行調整
- 檔案路徑變數應使用絕對路徑或相對於專案根目錄的路徑
