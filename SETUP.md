# 快速設置指南

## 環境配置

### 1. 後端設置
```bash
cd backend
# 複製環境變數文件
copy .env.example .env
```

編輯 `.env` 文件，配置以下必要項目：
- `OPENAI_API_KEY`: 您的 OpenAI API 密鑰
- `SECRET_KEY`: JWT 加密密鑰（建議使用隨機字符串）
- `DATABASE_URL`: 數據庫連接字符串

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
export SECRET_KEY=your_secret_key_here

# 啟動服務
docker-compose up -d
```

### 3. 訪問應用程式
- 前端界面: http://localhost:3000
- 後端 API: http://localhost:8000
- API 文檔: http://localhost:8000/docs

### 4. 默認管理員帳號
首次運行時，請通過註冊頁面創建帳號，然後在數據庫中手動將該用戶的 `is_admin` 字段設為 `true`。

## 常見問題

### Q: 無法連接到 OpenAI API
A: 請確認 `OPENAI_API_KEY` 已正確設置在 `.env` 文件中。

### Q: 前端無法連接到後端
A: 檢查後端服務是否正常運行在 http://localhost:8000

### Q: 數據庫連接失敗
A: 確認 PostgreSQL 服務正在運行，或使用 SQLite（默認配置）。

## 開發說明

- 後端使用 FastAPI，支持自動 API 文檔生成
- 前端使用 React + Material-UI，響應式設計
- RAG 系統支持文件上傳和智能問答
- 支持多用戶對話和管理員後台

更多詳細信息請查看 `README.md` 文件。
