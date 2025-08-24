# ChatBot 完整啟動腳本
Write-Host "正在啟動 ChatBot 完整系統..." -ForegroundColor Green

# 檢查是否在正確的目錄
if (-not (Test-Path "backend") -or -not (Test-Path "frontend")) {
    Write-Host "請在 ChatBot 專案根目錄運行此腳本" -ForegroundColor Red
    exit 1
}

# 啟動後端（在新的 PowerShell 窗口中）
Write-Host "正在啟動後端服務..." -ForegroundColor Yellow
Start-Process PowerShell -ArgumentList "-NoExit", "-Command", "& '.\start-backend.ps1'"

# 等待幾秒讓後端啟動
Start-Sleep -Seconds 5

# 啟動前端（在新的 PowerShell 窗口中）
Write-Host "正在啟動前端服務..." -ForegroundColor Yellow
Start-Process PowerShell -ArgumentList "-NoExit", "-Command", "& '.\start-frontend.ps1'"

Write-Host "系統啟動完成！" -ForegroundColor Green
Write-Host "後端服務: http://localhost:8000" -ForegroundColor Cyan
Write-Host "前端服務: http://localhost:3000" -ForegroundColor Cyan
Write-Host "API 文檔: http://localhost:8000/docs" -ForegroundColor Cyan
