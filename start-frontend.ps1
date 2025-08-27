# 前端啟動腳本
Write-Host "正在啟動 ChatBot 前端服務..." -ForegroundColor Green

# 確保在正確的目錄
if (-not (Test-Path "frontend")) {
    Write-Host "錯誤：請在 ChatBot 專案根目錄運行此腳本" -ForegroundColor Red
    Read-Host "按任意鍵退出"
    exit 1
}

# 進入前端目錄
Set-Location "frontend"
Write-Host "已進入前端目錄：$(Get-Location)" -ForegroundColor Yellow

# 檢查 Node.js 是否已安裝
try {
    $nodeVersion = & node --version 2>$null
    Write-Host "✓ Node.js 版本：$nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "錯誤：未找到 Node.js" -ForegroundColor Red
    Write-Host "請先安裝 Node.js：https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "按任意鍵退出"
    exit 1
}

# 檢查 npm 是否可用
try {
    $npmVersion = & npm --version 2>$null
    Write-Host "✓ npm 版本：$npmVersion" -ForegroundColor Green
} catch {
    Write-Host "錯誤：npm 不可用" -ForegroundColor Red
    Read-Host "按任意鍵退出"
    exit 1
}

# 檢查是否已安裝依賴
if (-not (Test-Path "node_modules")) {
    Write-Host "正在安裝前端依賴..." -ForegroundColor Yellow
    Write-Host "這可能需要幾分鐘時間..." -ForegroundColor Yellow
    try {
        & npm install
        Write-Host "✓ 前端依賴安裝完成" -ForegroundColor Green
    } catch {
        Write-Host "錯誤：無法安裝依賴" -ForegroundColor Red
        Write-Host "請檢查網絡連接並重試" -ForegroundColor Yellow
        Read-Host "按任意鍵退出"
        exit 1
    }
} else {
    Write-Host "✓ 前端依賴已安裝" -ForegroundColor Green
}

# 檢查環境配置
if (-not (Test-Path ".env")) {
    Write-Host "正在創建前端環境配置..." -ForegroundColor Yellow
    "REACT_APP_API_URL=http://127.0.0.1:8001" | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✓ 已創建 .env 文件" -ForegroundColor Green
}

# 啟動開發服務器
Write-Host ""
Write-Host "正在啟動 React 開發服務器..." -ForegroundColor Green
Write-Host "前端地址：http://localhost:3000" -ForegroundColor Cyan
Write-Host "後端 API：http://127.0.0.1:8001" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服務" -ForegroundColor Yellow
Write-Host ""

try {
    & npm start
} catch {
    Write-Host ""
    Write-Host "錯誤：無法啟動前端服務" -ForegroundColor Red
    Write-Host "請檢查：" -ForegroundColor Yellow
    Write-Host "1. Node.js 和 npm 是否正確安裝" -ForegroundColor Yellow
    Write-Host "2. 依賴是否已安裝（npm install）" -ForegroundColor Yellow
    Write-Host "3. 端口 3000 是否被占用" -ForegroundColor Yellow
    Read-Host "按任意鍵退出"
}
