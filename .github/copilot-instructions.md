<!-- ChatBot 應用程式開發指引 -->

# ChatBot 專案概述

此專案是一個具備使用者介面和後台管理介面的 ChatBot 應用程式，使用 Contextual RAG（檢索增強生成）技術。

## 專案架構
- **後端**: FastAPI + SQLAlchemy + LangChain + OpenAI/GitHub Models
- **前端**: React + Material-UI
- **數據庫**: SQLite (開發) / PostgreSQL (生產)
- **向量數據庫**: FAISS IndexFlatIP with 持久化儲存
- **身份驗證**: JWT
- **文檔處理**: PyPDF2 + python-docx + 多編碼支援

## 核心功能
- [ ] 用戶註冊登入系統（待整合）
- [x] 智能對話（Contextual RAG）
- [x] 對話歷史管理
- [x] 多格式文件上傳 (TXT, PDF, DOCX)
- [x] FAISS 向量儲存與檢索
- [x] 繁體中文優化處理
- [x] 管理員後台
- [x] WebSocket 即時通訊
- [x] 向量庫管理 (重置/清理)

## 開發設置已完成
- [x] 後端 API 架構 (FastAPI)
- [x] 前端 React 應用程式 (Material-UI)
- [x] Contextual RAG 實現 (FAISS + paraphrase-multilingual-MiniLM-L12-v2)
- [x] 數據庫模型 (SQLAlchemy)
- [ ] 用戶認證系統 (JWT) - 代碼已寫但未整合
- [x] 文檔處理系統 (DocumentProcessor: TXT/PDF/DOCX)
- [x] FAISS 向量儲存與持久化
- [x] 多編碼支援 (UTF-8, GBK, Big5)
- [x] Docker 配置
- [x] VS Code 任務配置
- [x] 啟動腳本 (PowerShell)

## 技術細節
### RAG 系統
- **向量模型**: paraphrase-multilingual-MiniLM-L12-v2 (384維)
- **索引類型**: FAISS IndexFlatIP (內積相似度)
- **持久化**: data/faiss_index.bin + data/documents.pkl
- **文檔分塊**: RecursiveCharacterTextSplitter (1000字符, 200重疊)
- **相似度閾值**: 0.3 (可配置)

### 文檔處理
- **支援格式**: TXT, PDF, DOCX
- **編碼檢測**: chardet + 多編碼後備
- **檔案大小限制**: 50MB
- **安全處理**: 檔名清理, 類型驗證

### 虛擬環境
- **位置**: D:\CB\CBvenv
- **Python版本**: 3.10+
- **關鍵套件**: FastAPI, SQLAlchemy, FAISS, PyPDF2, python-docx, sentence-transformers

## 快速啟動
1. 配置環境變數（複製 `.env.example` 到 `.env`）
2. 啟動虛擬環境：`.\CBvenv\Scripts\Activate.ps1`
3. 運行 `start-all.ps1` 啟動完整系統
4. 或使用 VS Code 任務面板啟動各個服務
5. 訪問 http://localhost:3000 (前端) 和 http://127.0.0.1:8000 (後端)

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
│   │   └── documents.pkl    # 文檔元數據
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

## 常用命令
- **重置 FAISS**: `python scripts/reset_faiss.py`
- **啟動後端**: `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000`
- **啟動前端**: `npm start`
- **安裝套件**: `pip install PyPDF2==3.0.1 python-docx==1.1.0`
