# 後端啟動腳本
Write-Host "正在啟動 ChatBot 後端服務..." -ForegroundColor Green

# 進入後端目錄
Set-Location "backend"

# 激活虛擬環境
if (Test-Path "CBvenv\Scripts\Activate.ps1") {
    & "CBvenv\Scripts\Activate.ps1"
    Write-Host "已激活虛擬環境" -ForegroundColor Yellow
} else {
    Write-Host "找不到虛擬環境，請先設置Python環境" -ForegroundColor Red
    exit 1
}

# 檢查環境變數文件
if (-not (Test-Path ".env")) {
    Write-Host "未找到 .env 文件，正在創建..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "請編輯 .env 文件並填入實際配置" -ForegroundColor Red
    exit 1
}

# 啟動服務
Write-Host "正在啟動 FastAPI 服務器..." -ForegroundColor Green
& "python" "-m" "uvicorn" "main:app" "--reload" "--host" "0.0.0.0" "--port" "8000"
