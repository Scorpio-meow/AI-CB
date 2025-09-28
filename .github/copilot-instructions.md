<!-- ChatBot 應用程式開發指引 -->

# ChatBot 專案概述

此專案是一個具備使用者介面和後台管理介面的 ChatBot 應用程式，使用增強型混合 RAG（檢索增強生成）技術。

## 專案架構
- **後端**: FastAPI + SQLAlchemy + LangChain + Ollama/GitHub Models
- **前端**: React + Material-UI
- **數據庫**: SQLite (開發) / PostgreSQL (生產)
- **向量數據庫**: FAISS IndexFlatIP + Whoosh BM25 混合檢索
- **文檔處理**: PyPDF2 + python-docx + 多編碼支援

## 核心功能
- [x] 智能對話（混合 RAG + Cross-Encoder 重新排序）
- [x] 對話歷史管理
- [x] 多格式文件上傳 (TXT, PDF, DOCX)
- [x] 混合檢索系統 (FAISS + BM25)
- [x] 繁體中文優化處理
- [x] 管理員後台
- [x] WebSocket 即時通訊
- [x] 向量庫管理 (重置/清理)
- [x] 文件管理改進: 流式寫入、多檔上傳、前端 per-file progress/cancel 與批次刪除
- [x] 自動重建索引 (24小時周期)
- [x] 評估指標系統 (Recall@k, Precision@k, MRR)

## 開發設置已完成
- [x] 後端 API 架構 (FastAPI)
- [x] 前端 React 應用程式 (Material-UI)
- [x] 混合 RAG 實現 (HybridContextualRAG)
- [x] 數據庫模型 (SQLAlchemy)
- [x] 文檔處理系統 (DocumentProcessor: TXT/PDF/DOCX)
- [x] 混合向量儲存與持久化 (FAISS + Whoosh)
- [x] 多編碼支援 (UTF-8, GBK, Big5)
- [x] Docker 配置
- [x] VS Code 任務配置
- [x] 啟動腳本 (PowerShell)
- [x] Cross-Encoder 重新排序系統

## 技術細節
### 混合 RAG 系統
- **向量模型**: paraphrase-multilingual-MiniLM-L12-v2 (384維)
- **重新排序模型**: cross-encoder/ms-marco-MiniLM-L-6-v2
- **向量索引**: FAISS IndexFlatIP (內積相似度)
- **BM25 索引**: Whoosh StandardAnalyzer
- **智能搜尋策略**: 根據查詢特徵自動選擇向量/BM25/混合搜尋
- **持久化**: data/faiss_index.bin + data/documents.pkl + data/bm25_index/
- **文檔分塊**: RecursiveCharacterTextSplitter (600字符, 150重疊)
- **相似度閾值**: 0.25 (可配置)
- **自動重建**: 24小時周期，支援元數據追蹤

### 文檔處理
- **支援格式**: TXT, PDF, DOCX
- **編碼檢測**: chardet + 多編碼後備
- **檔案大小限制**: 50MB
- **安全處理**: 檔名清理, 類型驗證

### 文件管理與刪除
- 上傳端改為流式寫入 (避免一次性將整個檔案讀入記憶體)。前端支援多檔上傳、每檔進度與取消。
- 新增 API: `POST /api/documents/bulk_delete` 支援一次傳入多個 id 做批次刪除，後端採批次 DB 刪除並平行處理 RAG/實體檔案移除，回傳每個 id 的狀態（deleted / deleted_with_warnings / failed / not_found）。
- 刪除流程已改為在後端並行處理 RAG/檔案刪除並使用 batch SQL 刪除 DocumentChunk 與 Document，以提升效能和一致性。

### 虛擬環境
- **位置**: D:\CB\CBvenv
- **Python版本**: 3.10+
- **關鍵套件**: FastAPI, SQLAlchemy, FAISS, PyPDF2, python-docx, sentence-transformers
### 文件管理與刪除
- 上傳端改為流式寫入 (避免一次性將整個檔案讀入記憶體)。前端支援多檔上傳、每檔進度與取消。
- 新增 API: `POST /api/documents/bulk_delete` 支援一次傳入多個 id 做批次刪除，後端採批次 DB 刪除並平行處理 RAG/實體檔案移除，回傳每個 id 的狀態（deleted / deleted_with_warnings / failed / not_found）。
- 刪除流程已改為在後端並行處理 RAG/檔案刪除並使用 batch SQL 刪除 DocumentChunk 與 Document，以提升效能和一致性。

### 虛擬環境
- **位置**: D:\CB\CBvenv
- **Python版本**: 3.10+
- **關鍵套件**: FastAPI, SQLAlchemy, FAISS, PyPDF2, python-docx, sentence-transformers, whoosh, scikit-learn
- **已知相容性 pin**: `huggingface_hub==0.19.3`（用於解決 sentence-transformers 相容性問題）

## 快速啟動 (純本地開發環境)
1. **配置環境變數**：已配置為本地開發環境，無需外部隧道
2. **啟動虛擬環境**：`.\CBvenv\Scripts\Activate.ps1`
3. **使用 VS Code 任務**：
   - 啟動後端：運行任務 "啟動後端開發服務器"
   - 啟動前端：運行任務 "啟動前端開發服務器"
4. **訪問地址**：
   - 前端：http://localhost:3000
   - 後端：http://localhost:8000
   - API：http://localhost:3000/api/* (通過 proxy 轉發)

## 專案結構
```
chatbot/
├── backend/              # FastAPI 後端
│   ├── app/              # 應用程式核心
│   │   ├── api/          # API 路由
│   │   ├── models/       # 數據模型
│   │   ├── rag/          # RAG 系統
│   │   └── services/     # 業務服務
│   ├── data/             # 數據儲存
│   │   ├── uploads/      # 上傳檔案
│   │   ├── faiss_index.bin  # FAISS 索引
│   │   ├── documents.pkl    # 文檔元數據
│   │   └── bm25_index/      # BM25 索引
│   ├── scripts/          # 工具腳本
│   └── CBvenv/           # Python 虛擬環境
├── frontend/             # React 前端  
│   ├── src/              # 源代碼
│   │   ├── components/   # React 組件
│   │   ├── pages/        # 頁面組件
│   │   └── services/     # API 服務
│   └── node_modules/     # Node.js 依賴
├── .vscode/              # VS Code 配置
├── .github/              # GitHub 配置
├── docker-compose.yml    # Docker 配置
└── *.ps1                 # PowerShell 啟動腳本
```

## 開發環境說明
### 本地開發配置 (已移除 DevTunnels)
- **前端配置**: `frontend/.env` - 使用 localhost + proxy 轉發
- **後端配置**: `backend/.env` - 本地 CORS 設定
- **代理設定**: `frontend/package.json` - `"proxy": "http://localhost:8000"`

### 常用命令
- **重置 FAISS**: `python scripts/reset_faiss.py`
- **啟動後端**: `python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- **啟動前端**: `npm start` (會自動代理 API 到後端)
- **安裝套件**: `pip install -r requirements.txt`
- **測試 RAG**: `python scripts/test_rag_improvements.py`
- **測試 API**: `python scripts/test_ollama_api.py`

### 環境優化重點
- **簡化配置**: 無需管理外部隧道或複雜網路設定
- **本地開發**: 所有服務運行在 localhost，快速穩定
- **代理轉發**: 前端通過 Create React App 內建 proxy 處理 API 請求
- **CORS 最小化**: 後端僅允許本地開發環境訪問
