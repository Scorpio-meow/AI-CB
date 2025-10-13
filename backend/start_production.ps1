# ChatBot 生產環境啟動腳本 (Windows + RTX 4090 優化)
# 使用 Uvicorn 多 Worker 模式 (針對 i9-13900KF 24核心優化)

param(
    [int]$Workers = 32,
    [int]$Port = 8001,
    [string]$Host = "0.0.0.0"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   ChatBot 生產環境啟動 (GPU 加速模式)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "硬體配置: Intel i9-13900KF (24核心) + RTX 4090 (24GB)" -ForegroundColor Green
Write-Host "Workers: $Workers | Port: $Port | Host: $Host" -ForegroundColor Yellow
Write-Host ""

# 檢查虛擬環境
$venvPath = "C:\Users\MITAC\Documents\AI-CB\CBvenv"
if (-Not (Test-Path "$venvPath\Scripts\python.exe")) {
    Write-Host "❌ 虛擬環境不存在: $venvPath" -ForegroundColor Red
    exit 1
}

# 啟動虛擬環境
Write-Host "🔧 啟動虛擬環境..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"

# 檢查 CUDA 支援
Write-Host "🔍 檢查 GPU 狀態..." -ForegroundColor Yellow
$cudaCheck = & "$venvPath\Scripts\python.exe" -c "import torch; print('CUDA:', torch.cuda.is_available(), '| GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
Write-Host $cudaCheck -ForegroundColor Green

# 設定環境變數 (GPU 優化)
$env:GPU_BATCH_SIZE = "128"  # RTX 4090 24GB 最佳批次大小
$env:CUDA_VISIBLE_DEVICES = "0"  # 使用第一張 GPU

Write-Host ""
Write-Host "🚀 啟動 FastAPI (Uvicorn Multi-Worker)..." -ForegroundColor Cyan
Write-Host "⚡ 建議 Workers: 24 (保守) | 32 (推薦) | 49 (最大)" -ForegroundColor Gray
Write-Host ""

# 啟動 Uvicorn (多 Worker 模式)
Set-Location "C:\Users\MITAC\Documents\AI-CB\backend"
& "$venvPath\Scripts\python.exe" -m uvicorn main:app `
    --host $Host `
    --port $Port `
    --workers $Workers `
    --log-level info `
    --access-log

Write-Host ""
Write-Host "🛑 伺服器已停止" -ForegroundColor Red
