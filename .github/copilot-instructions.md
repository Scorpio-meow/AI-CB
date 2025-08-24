<!-- ChatBot 應用程式開發指引 -->

# ChatBot 專案概述

此專案是一個具備使用者介面和後台管理介面的 ChatBot 應用程式，使用 Contextual RAG（檢索增強生成）技術。

## 專案架構
- **後端**: FastAPI + SQLAlchemy + LangChain + OpenAI
- **前端**: React + Material-UI
- **數據庫**: PostgreSQL
- **向量數據庫**: FAISS
- **身份驗證**: JWT

## 核心功能
- [x] 用戶註冊登入系統
- [x] 智能對話（Contextual RAG）
- [x] 對話歷史管理
- [x] 文件上傳和知識庫管理
- [x] 管理員後台
- [x] WebSocket 即時通訊

## 開發設置已完成
- [x] 後端 API 架構
- [x] 前端 React 應用程式
- [x] Contextual RAG 實現
- [x] 數據庫模型
- [x] 用戶認證系統
- [x] Docker 配置
- [x] VS Code 任務配置

## 快速啟動
1. 配置環境變數（複製 `.env.example` 到 `.env`）
2. 運行 `start-all.ps1` 啟動完整系統
3. 或使用 VS Code 任務面板啟動各個服務

## 專案結構
```
chatbot/
├── backend/          # FastAPI 後端
├── frontend/         # React 前端  
├── .vscode/          # VS Code 配置
├── docker-compose.yml
└── README.md
```
