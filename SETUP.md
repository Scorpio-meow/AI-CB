# 快速設置指南

## 環境配置

### 1. 後端設置
```bash
cd backend
# 複製環境變數文件
copy .env.example .env
```

編輯 `.env` 文件，配置以下必要項目：
- `GITHUB_TOKEN`: 您的 GitHub Personal Access Token（推薦）
- `MODEL_NAME`: GitHub Models 模型名稱（如 openai/gpt-4o-mini）
- 或 `OPENAI_API_KEY`: 您的 OpenAI API 密鑰
- `SECRET_KEY`: JWT 加密密鑰（建議使用隨機字符串）
- `DATABASE_URL`: 數據庫連接字符串（默認 SQLite）

### 2. 依賴安裝

確保已安裝必要套件：
```bash
# 進入虛擬環境
.\CBvenv\Scripts\Activate.ps1

# 安裝/更新依賴
pip install -r requirements.txt

# 驗證關鍵套件
python -c "import PyPDF2, docx, faiss; print('PDF/DOCX 處理套件已安裝')"
```

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
- 後端 API: http://127.0.0.1:8000
- API 文檔: http://127.0.0.1:8000/docs

### 4. 管理員設置
目前系統沒有啟用用戶認證系統，所有功能都是開放使用的。如需啟用認證功能，需要：
1. 在 `backend/main.py` 中添加 auth 路由
2. 配置前端的認證拦截器

### 5. 文檔上傳測試
系統支援以下文件格式：
- TXT 文件（支援多種編碼）
- PDF 文件（使用 PyPDF2）
- DOCX 文件（使用 python-docx）
- 最大文件大小：50MB

## 常見問題

### Q: 無法連接到 GitHub Models API
A: 請確認 `GITHUB_TOKEN` 已正確設置在 `.env` 文件中，並且 token 有必要權限。

### Q: 無法連接到 OpenAI API
A: 請確認 `OPENAI_API_KEY` 已正確設置在 `.env` 文件中。

### Q: 前端無法連接到後端
A: 檢查後端服務是否正常運行在 http://127.0.0.1:8000

### Q: 數據庫連接失敗
A: 確認 PostgreSQL 服務正在運行，或使用 SQLite（默認配置）。

### Q: PDF/DOCX 處理失敗
A: 確認已安裝 PyPDF2 和 python-docx：
```bash
pip install PyPDF2==3.0.1 python-docx==1.1.0
```

### Q: FAISS 索引問題
A: 可以重置 FAISS 索引：
```bash
python scripts/reset_faiss.py
```

## 開發說明

- 後端使用 FastAPI，支持自動 API 文檔生成
- 前端使用 React + Material-UI，響應式設計
- RAG 系統使用 FAISS IndexFlatIP 進行向量檢索
- 支援繁體中文優化的嵌入模型：paraphrase-multilingual-MiniLM-L12-v2
- 支持多用戶對話和管理員後台
- 文檔處理支援 TXT, PDF, DOCX 格式

## 工具腳本

- `scripts/reset_faiss.py` - 重置 FAISS 向量庫
- `start-all.ps1` - 啟動完整系統
- `start-backend.ps1` - 單獨啟動後端
- `start-frontend.ps1` - 單獨啟動前端

更多詳細信息請查看 `README.md` 文件。
