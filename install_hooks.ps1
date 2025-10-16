# Install Pre-Commit Hook
# 安裝 Git Pre-Commit Hook 進行本地安全檢查

Write-Host "🔧 安裝 Pre-Commit Hook..." -ForegroundColor Yellow

# 檢查是否為 Git 倉庫
if (-not (Test-Path ".git")) {
    Write-Host "❌ 錯誤: 當前目錄不是 Git 倉庫！" -ForegroundColor Red
    exit 1
}

# 建立 hooks 目錄
$hooksDir = ".git\hooks"
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
}

# 複製 pre-commit hook
$sourceHook = ".github\hooks\pre-commit"
$targetHook = ".git\hooks\pre-commit"

if (-not (Test-Path $sourceHook)) {
    Write-Host "❌ 錯誤: 找不到 $sourceHook" -ForegroundColor Red
    exit 1
}

Copy-Item -Path $sourceHook -Destination $targetHook -Force
Write-Host "✅ Pre-commit hook 已安裝到 $targetHook" -ForegroundColor Green

# Windows 上不需要 chmod，但要確保 Python 可執行
Write-Host ""
Write-Host "📝 使用說明:" -ForegroundColor Cyan
Write-Host "   - 每次 git commit 時會自動執行安全檢查" -ForegroundColor White
Write-Host "   - 檢查項目: 敏感文件、硬編碼密鑰、console.log、SQL注入" -ForegroundColor White
Write-Host "   - 如需跳過檢查: git commit --no-verify" -ForegroundColor White
Write-Host ""

# 測試 hook
Write-Host "🧪 測試 hook..." -ForegroundColor Yellow
python $sourceHook

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Pre-commit hook 安裝成功！" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "⚠️  Hook 已安裝，但測試失敗" -ForegroundColor Yellow
    Write-Host "   請確認 Python 3 已正確安裝" -ForegroundColor Yellow
}
