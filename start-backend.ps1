# 後端啟動腳本
Write-Host "正在啟動 ChatBot 後端服務..." -ForegroundColor Green

# 確保在正確的目錄
if (-not (Test-Path "backend")) {
    Write-Host "錯誤：請在 ChatBot 專案根目錄運行此腳本" -ForegroundColor Red
    Read-Host "按任意鍵退出"
    exit 1
}

# 進入後端目錄
Set-Location "backend"
Write-Host "已進入後端目錄：$(Get-Location)" -ForegroundColor Yellow

# 檢查並激活虛擬環境
if (Test-Path "CBvenv\Scripts\Activate.ps1") {
    Write-Host "正在激活虛擬環境..." -ForegroundColor Yellow
    & "CBvenv\Scripts\Activate.ps1"
    Write-Host "✓ 已激活虛擬環境" -ForegroundColor Green
} else {
    Write-Host "錯誤：找不到虛擬環境 CBvenv\Scripts\Activate.ps1" -ForegroundColor Red
    Write-Host "請先設置 Python 虛擬環境：" -ForegroundColor Yellow
    Write-Host "  python -m venv CBvenv" -ForegroundColor Cyan
    Write-Host "  CBvenv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Cyan
    Read-Host "按任意鍵退出"
    exit 1
}

# 檢查環境變數文件
if (-not (Test-Path ".env")) {
    Write-Host "警告：未找到 .env 文件" -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Write-Host "正在創建 .env 文件..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "✓ 已創建 .env 文件" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  重要：請編輯 .env 文件並填入實際配置" -ForegroundColor Red
        Write-Host "   必填項目：" -ForegroundColor Yellow
        Write-Host "   - GITHUB_TOKEN 或 OPENAI_API_KEY" -ForegroundColor Yellow
        Write-Host "   - SECRET_KEY" -ForegroundColor Yellow
        Write-Host ""
        $continue = Read-Host "是否繼續啟動服務？(y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            exit 1
        }
    } else {
        Write-Host "錯誤：找不到 .env.example 文件" -ForegroundColor Red
        Read-Host "按任意鍵退出"
        exit 1
    }
}

# 檢查依賴
Write-Host "正在檢查 Python 依賴..." -ForegroundColor Yellow
try {
    & python -c "import fastapi, sqlalchemy, faiss; print('✓ 核心依賴已安裝')" 2>$null
    Write-Host "✓ 核心依賴檢查通過" -ForegroundColor Green
} catch {
    Write-Host "警告：某些依賴可能未安裝" -ForegroundColor Yellow
    Write-Host "請運行：pip install -r requirements.txt" -ForegroundColor Cyan
}

# 啟動服務
Write-Host ""
Write-Host "正在啟動 FastAPI 服務器..." -ForegroundColor Green
Write-Host "服務地址：http://127.0.0.1:8001" -ForegroundColor Cyan
Write-Host "API 文檔：http://127.0.0.1:8001/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服務" -ForegroundColor Yellow
Write-Host ""

try {
    & python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
} catch {
    Write-Host ""
    Write-Host "錯誤：無法啟動服務" -ForegroundColor Red
    Write-Host "請檢查：" -ForegroundColor Yellow
    Write-Host "1. Python 虛擬環境是否正確激活" -ForegroundColor Yellow
    Write-Host "2. 依賴是否已安裝（pip install -r requirements.txt）" -ForegroundColor Yellow
    Write-Host "3. 環境變數是否已配置" -ForegroundColor Yellow
    Read-Host "按任意鍵退出"
}
