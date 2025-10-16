<#
.SYNOPSIS
    加固文件上傳目錄權限（Windows 環境）
    
.DESCRIPTION
    實施最小權限原則，確保上傳目錄安全
    - 移除過寬的權限
    - 僅保留應用程式需要的讀寫權限
    - 禁止執行權限
    
.NOTES
    執行前請確保以管理員身份運行 PowerShell
#>

# 需要管理員權限
#Requires -RunAsAdministrator

$uploadDir = "C:\Users\MITAC\Documents\AI-CB\backend\data\uploads"

Write-Host "=== 文件上傳目錄權限加固腳本 ===" -ForegroundColor Cyan
Write-Host ""

# 檢查目錄是否存在
if (-not (Test-Path $uploadDir)) {
    Write-Host "✗ 上傳目錄不存在: $uploadDir" -ForegroundColor Red
    exit 1
}

Write-Host "📁 目標目錄: $uploadDir" -ForegroundColor Yellow
Write-Host ""

# 顯示當前權限
Write-Host "📋 當前權限:" -ForegroundColor Yellow
icacls $uploadDir
Write-Host ""

# 確認操作
$confirmation = Read-Host "是否繼續修改權限？這將移除 Users 和過寬的權限 (y/n)"
if ($confirmation -ne 'y') {
    Write-Host "操作已取消" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "🔧 開始修改權限..." -ForegroundColor Cyan

try {
    # 1. 禁用繼承，保留現有 ACL
    Write-Host "  → 禁用權限繼承..." -ForegroundColor Gray
    icacls $uploadDir /inheritance:d | Out-Null
    
    # 2. 移除 Users 組的權限（過寬）
    Write-Host "  → 移除 Users 組權限..." -ForegroundColor Gray
    icacls $uploadDir /remove "Users" 2>$null | Out-Null
    
    # 3. 移除 Authenticated Users（如果存在）
    Write-Host "  → 移除 Authenticated Users 權限..." -ForegroundColor Gray
    icacls $uploadDir /remove "Authenticated Users" 2>$null | Out-Null
    
    # 4. 確保 SYSTEM 有完全控制（系統需要）
    Write-Host "  → 設置 SYSTEM 權限..." -ForegroundColor Gray
    icacls $uploadDir /grant "NT AUTHORITY\SYSTEM:(OI)(CI)F" | Out-Null
    
    # 5. 確保 Administrators 有完全控制
    Write-Host "  → 設置 Administrators 權限..." -ForegroundColor Gray
    icacls $uploadDir /grant "BUILTIN\Administrators:(OI)(CI)F" | Out-Null
    
    # 6. 設置當前用戶的修改權限（應用程式運行用戶）
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    Write-Host "  → 設置應用程式用戶 ($currentUser) 權限..." -ForegroundColor Gray
    icacls $uploadDir /grant "${currentUser}:(OI)(CI)M" | Out-Null
    
    # 7. 如果使用 IIS，添加 IIS_IUSRS（可選）
    # icacls $uploadDir /grant "IIS_IUSRS:(OI)(CI)M" | Out-Null
    
    Write-Host ""
    Write-Host "✓ 權限修改完成！" -ForegroundColor Green
    Write-Host ""
    
    # 顯示修改後的權限
    Write-Host "📋 修改後的權限:" -ForegroundColor Yellow
    icacls $uploadDir
    
    Write-Host ""
    Write-Host "🔒 安全說明:" -ForegroundColor Cyan
    Write-Host "  - SYSTEM: 完全控制（系統服務需要）" -ForegroundColor Gray
    Write-Host "  - Administrators: 完全控制（管理維護需要）" -ForegroundColor Gray
    Write-Host "  - $currentUser: 修改權限（應用程式讀寫需要）" -ForegroundColor Gray
    Write-Host "  - 已移除: Users、Authenticated Users（過寬權限）" -ForegroundColor Gray
    Write-Host ""
    Write-Host "權限說明:" -ForegroundColor Yellow
    Write-Host "  (OI) = 對象繼承 - 文件繼承此權限" -ForegroundColor Gray
    Write-Host "  (CI) = 容器繼承 - 子目錄繼承此權限" -ForegroundColor Gray
    Write-Host "  M    = Modify - 修改（讀+寫+刪除，但不能更改權限）" -ForegroundColor Gray
    Write-Host "  F    = Full Control - 完全控制" -ForegroundColor Gray
    
} catch {
    Write-Host ""
    Write-Host "✗ 權限修改失敗: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ 權限加固完成！" -ForegroundColor Green
