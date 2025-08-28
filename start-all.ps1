# ChatBot 完整啟動腳本
Write-Host "正在啟動 ChatBot 完整系統..." -ForegroundColor Green

# 檢查是否在正確的目錄
if (-not (Test-Path "backend") -or -not (Test-Path "frontend")) {
    Write-Host "錯誤：請在 ChatBot 專案根目錄運行此腳本" -ForegroundColor Red
    Write-Host "當前目錄：$(Get-Location)" -ForegroundColor Yellow
    Write-Host "預期結構：應包含 backend/ 和 frontend/ 目錄" -ForegroundColor Yellow
    Read-Host "按任意鍵退出"
    exit 1
}

# 檢查虛擬環境
if (-not (Test-Path "backend\CBvenv\Scripts\Activate.ps1")) {
    Write-Host "錯誤：找不到虛擬環境 backend\CBvenv\" -ForegroundColor Red
    Write-Host "請先設置 Python 虛擬環境" -ForegroundColor Yellow
    Read-Host "按任意鍵退出"
    exit 1
}

# 檢查環境配置
if (-not (Test-Path "backend\.env")) {
    Write-Host "警告：未找到 backend\.env 文件" -ForegroundColor Yellow
    Write-Host "將複製 .env.example 作為模板" -ForegroundColor Yellow
    if (Test-Path "backend\.env.example") {
        Copy-Item "backend\.env.example" "backend\.env"
        Write-Host "請編輯 backend\.env 文件並填入實際配置後重新運行" -ForegroundColor Red
        Read-Host "按任意鍵退出"
        exit 1
    }
}

Write-Host "正在啟動後端服務..." -ForegroundColor Yellow
Start-Process PowerShell -ArgumentList "-NoExit", "-Command", "Set-Location '$PWD'; .\start-backend.ps1"

# 等待後端啟動
Write-Host "等待後端服務啟動..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

Write-Host "正在啟動前端服務..." -ForegroundColor Yellow
Start-Process PowerShell -ArgumentList "-NoExit", "-Command", "Set-Location '$PWD'; .\start-frontend.ps1"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "ChatBot 系統啟動完成！" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host "後端服務: http://127.0.0.1:8001" -ForegroundColor Cyan
Write-Host "前端服務: http://localhost:3000" -ForegroundColor Cyan
Write-Host "API 文檔: http://127.0.0.1:8001/docs" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Green

Read-Host "按任意鍵退出"
