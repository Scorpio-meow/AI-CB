# 快速設置指南

## 環境配置

### 1. 後端設置
```bash
cd backend
# 複製環境變數文件
copy .env.example .env
```

編輯 `.env` 文件，配置以下必要項目：
- `MODEL_NAME`: 模型名稱（如 gpt-oss:20b 用於 Ollama 或 gpt-4o-mini 用於 LLM Models）
- `LLM_API_BASE`: API 基地址（Ollama ngrok 地址或 LLM Models API）
- `SECRET_KEY`: JWT 加密密鑰（建議使用隨機字符串）
- `DATABASE_URL`: 數據庫連接字符串（默認 SQLite）
注意：本分支/版本已移除用戶註冊與 JWT 認證系統，`SECRET_KEY` 與相關設定不再需要，請勿設定或依賴該變量。

### 2. 依賴安裝

確保已安裝必要套件：
```bash
# 進入虛擬環境
.\CBvenv\Scripts\Activate.ps1

# 安裝/更新依賴（包含新的混合 RAG 套件）
pip install -r requirements.txt

# 驗證關鍵套件
python -c "import PyPDF2, docx, faiss, whoosh, sklearn; print('所有套件已安裝')"
```

### 新增套件說明
- `whoosh==2.7.4`: BM25 全文檢索引擎
- `scikit-learn==1.3.2`: 評估指標計算
- `cross-encoder`: 重新排序模型（透過 sentence-transformers 安裝）

### 2. 啟動服務

#### 方法一：使用 PowerShell 腳本
```powershell
# 啟動完整系統
.\start-all.ps1

# 或分別啟動
.\start-backend.ps1  # 後端
.\start-frontend.ps1 # 前端
```

#### 方法二：使用 VS Code 任務
1. 按 `Ctrl+Shift+P` 打開命令面板
2. 輸入 "Tasks: Run Task"
3. 選擇 "啟動完整系統"

#### 方法三：使用 Docker
```bash
# 設置環境變數
export OPENAI_API_KEY=your_api_key_here
# 註：認證系統已移除，SECRET_KEY 不再使用

# 啟動服務
docker-compose up -d
```

### 3. 訪問應用程式
- 前端界面: http://localhost:3000
- 後端 API: http://127.0.0.1:8001
- API 文檔: http://127.0.0.1:8001/docs

### 4. 管理員設置
目前系統沒有啟用用戶註冊/登入或 JWT 認證系統，所有功能在開發分支中為開放使用。如需將認證重新加入：
1. 在 `backend/main.py` 中新增相應的 auth 路由與服務
2. 在前端加入認證上下文與 axios 攔截器

### 5. 文檔上傳測試
系統支援以下文件格式：
- TXT 文件（支援多種編碼）
- PDF 文件（使用 PyPDF2）
- DOCX 文件（使用 python-docx）
- 最大文件大小：50MB

### 上傳與刪除測試建議
- 系統使用流式寫入上傳以避免大量記憶體使用，前端支援多檔選擇與逐檔上傳進度、取消功能。請使用前端 UI 測試上傳，或使用 curl 上傳單檔：

```powershell
# 單檔上傳範例
curl -X POST "http://127.0.0.1:8001/api/documents/upload" -F "file=@C:/path/to/file.pdf"
```

- 測試批次刪除：可使用下列 curl 範例呼叫新的批次刪除 API：

```powershell
curl -X POST "http://127.0.0.1:8001/api/documents/bulk_delete" -H "Content-Type: application/json" -d "{ \"ids\": [1,2,3] }"
```

回傳格式範例：

```
{
	"results": [
		{ "id": 1, "status": "deleted" },
		{ "id": 2, "status": "deleted_with_warnings", "detail": "File remove failed: ..." },
		{ "id": 3, "status": "not_found" }
	]
}
```

## 系統初始化

### 首次設置（必須執行）
```bash
# 進入後端目錄並激活虛擬環境
cd backend
.\CBvenv\Scripts\Activate.ps1

# 初始化數據庫
python init_db.py

# 初始化混合 RAG 索引（首次啟動會自動建立）
python -c "from app.rag.contextual_rag import HybridContextualRAG; rag = HybridContextualRAG(); print('混合 RAG 系統初始化完成')"
```

### 系統重置（可選）
如需重置向量數據庫和文檔索引：
```bash
python scripts/reset_faiss.py
```

這將清除所有索引文件：
- `data/faiss_index.bin`（FAISS 向量索引）
- `data/documents.pkl`（文檔元數據）
- `data/bm25_index/`（BM25 全文索引）

## 混合 RAG 系統配置

### 向量模型配置
- **向量化模型**: paraphrase-multilingual-MiniLM-L12-v2（384維）
- **重新排序模型**: cross-encoder/ms-marco-MiniLM-L-6-v2
- **相似度閾值**: 0.25（可在 contextual_rag.py 中調整）

### 文檔分塊設置
- **分塊大小**: 600 字符
- **重疊大小**: 150 字符
- **支援格式**: TXT, PDF, DOCX
- **編碼支援**: UTF-8, GBK, Big5 自動檢測

### 檢索策略
系統會根據查詢特徵自動選擇最適合的檢索方法：
- **向量搜尋**: 適用於語義相似性查詢
- **BM25 搜尋**: 適用於關鍵字精確匹配
- **混合搜尋**: 結合向量和 BM25 結果
- **Cross-Encoder 重新排序**: 提升結果相關性

### 自動重建索引
- 系統每 24 小時自動檢查並重建索引
- 支援元數據追蹤以避免不必要的重建
- 手動重建：執行上述重置腳本

## 常見問題

### Q: 前端無法連接到後端
A: 檢查後端服務是否正常運行在 http://127.0.0.1:8001

### Q: 數據庫連接失敗
A: 確認 PostgreSQL 服務正在運行，或使用 SQLite（默認配置）。

### Q: PDF/DOCX 處理失敗
A: 確認已安裝 PyPDF2 和 python-docx：
```bash
pip install PyPDF2==3.0.1 python-docx==1.1.0
```

### Q: FAISS/RAG 索引問題
A: 可以重置混合 RAG 索引：
```bash
python scripts/reset_faiss.py
```

### Q: 混合檢索效果不佳
A: 檢查並調整以下參數：
- 相似度閾值：在 `contextual_rag.py` 中調整 `similarity_threshold`
- 重新排序模型：確認 cross-encoder 模型正常載入
- BM25 索引：檢查 `data/bm25_index/` 目錄是否存在

### Q: 評估指標計算失敗
A: 確認安裝了評估相關套件：
```bash
pip install scikit-learn==1.3.2 whoosh==2.7.4
```

## 開發說明

- 後端使用 FastAPI，支持自動 API 文檔生成
- 前端使用 React + Material-UI，響應式設計
- **混合 RAG 系統**：
  - FAISS IndexFlatIP（向量檢索）
  - Whoosh BM25（全文檢索）
  - Cross-Encoder 重新排序
  - 智能搜尋策略選擇
- 支援繁體中文優化的嵌入模型：paraphrase-multilingual-MiniLM-L12-v2
- 支持多用戶對話和管理員後台
- 文檔處理支援 TXT, PDF, DOCX 格式
- 自動重建索引（24小時周期）
- 評估指標系統（Recall@k, Precision@k, MRR）

## 工具腳本

- `scripts/reset_faiss.py` - 重置混合 RAG 向量庫和索引
- `scripts/test_rag_improvements.py` - 測試 RAG 系統功能
- `scripts/test_ollama_api.py` - 測試 API 連接
- `start-all.ps1` - 啟動完整系統
- `start-backend.ps1` - 單獨啟動後端
- `start-frontend.ps1` - 單獨啟動前端

更多詳細信息請查看 `README.md` 文件。
