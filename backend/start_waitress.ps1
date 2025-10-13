# Waitress 生產環境啟動腳本 (Windows 原生支援)
# 適用於需要穩定 Windows 服務的場景

param(
    [int]$Threads = 32,
    [int]$Port = 8001,
    [string]$Host = "0.0.0.0"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   ChatBot Waitress 生產環境啟動" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Threads: $Threads | Port: $Port | Host: $Host" -ForegroundColor Yellow
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

# 檢查 Waitress
$waitressCheck = & "$venvPath\Scripts\python.exe" -c "import waitress; print('Waitress version:', waitress.__version__)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Waitress 未安裝，正在安裝..." -ForegroundColor Yellow
    & "$venvPath\Scripts\pip.exe" install waitress
}
Write-Host $waitressCheck -ForegroundColor Green

# 設定環境變數
$env:GPU_BATCH_SIZE = "128"
$env:CUDA_VISIBLE_DEVICES = "0"

Write-Host ""
Write-Host "🚀 啟動 Waitress..." -ForegroundColor Cyan
Write-Host "⚠️ Waitress 使用執行緒而非進程，適合 Windows 環境" -ForegroundColor Gray
Write-Host ""

# 啟動 Waitress
Set-Location "C:\Users\MITAC\Documents\AI-CB\backend"
& "$venvPath\Scripts\waitress-serve.exe" `
    --host=$Host `
    --port=$Port `
    --threads=$Threads `
    --channel-timeout=300 `
    main:app

Write-Host ""
Write-Host "🛑 伺服器已停止" -ForegroundColor Red
