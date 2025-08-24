# 前端啟動腳本
Write-Host "正在啟動 ChatBot 前端服務..." -ForegroundColor Green

# 進入前端目錄
Set-Location "frontend"

# 檢查是否已安裝依賴
if (-not (Test-Path "node_modules")) {
    Write-Host "正在安裝前端依賴..." -ForegroundColor Yellow
    npm install
}

# 啟動開發服務器
Write-Host "正在啟動 React 開發服務器..." -ForegroundColor Green
npm start
