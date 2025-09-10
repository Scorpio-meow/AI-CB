# Docker 啟動腳本
# 用於快速啟動和管理 Docker 容器

param(
    [string]$Action = "up",
    [switch]$Dev,
    [switch]$Build,
    [switch]$Clean
)

Write-Host "ChatBot Docker 管理腳本" -ForegroundColor Green
Write-Host "==============================" -ForegroundColor Green

# 設置 Docker Compose 檔案
$composeFile = if ($Dev) { "docker-compose.dev.yml" } else { "docker-compose.yml" }
$env = if ($Dev) { "開發" } else { "生產" }

Write-Host "使用 $env 環境配置: $composeFile" -ForegroundColor Yellow

switch ($Action.ToLower()) {
    "up" {
        Write-Host "啟動容器..." -ForegroundColor Blue
        if ($Build) {
            docker-compose -f $composeFile up --build -d
        } else {
            docker-compose -f $composeFile up -d
        }
    }
    "down" {
        Write-Host "停止容器..." -ForegroundColor Blue
        docker-compose -f $composeFile down
    }
    "build" {
        Write-Host "構建鏡像..." -ForegroundColor Blue
        docker-compose -f $composeFile build
    }
    "logs" {
        Write-Host "查看日誌..." -ForegroundColor Blue
        docker-compose -f $composeFile logs -f
    }
    "status" {
        Write-Host "容器狀態..." -ForegroundColor Blue
        docker-compose -f $composeFile ps
    }
    "restart" {
        Write-Host "重啟容器..." -ForegroundColor Blue
        docker-compose -f $composeFile restart
    }
    "clean" {
        Write-Host "清理 Docker 資源..." -ForegroundColor Red
        docker-compose -f $composeFile down -v --rmi all
        docker system prune -f
    }
    default {
        Write-Host "使用方法:" -ForegroundColor Cyan
        Write-Host "  .\docker-start.ps1 -Action up [-Dev] [-Build]     # 啟動容器" -ForegroundColor White
        Write-Host "  .\docker-start.ps1 -Action down                   # 停止容器" -ForegroundColor White
        Write-Host "  .\docker-start.ps1 -Action build                  # 構建鏡像" -ForegroundColor White
        Write-Host "  .\docker-start.ps1 -Action logs                   # 查看日誌" -ForegroundColor White
        Write-Host "  .\docker-start.ps1 -Action status                 # 查看狀態" -ForegroundColor White
        Write-Host "  .\docker-start.ps1 -Action restart                # 重啟容器" -ForegroundColor White
        Write-Host "  .\docker-start.ps1 -Action clean                  # 清理資源" -ForegroundColor White
        Write-Host "" -ForegroundColor White
        Write-Host "參數:" -ForegroundColor Cyan
        Write-Host "  -Dev      使用開發環境配置" -ForegroundColor White
        Write-Host "  -Build    強制重新構建鏡像" -ForegroundColor White
        exit
    }
}

if ($Clean) {
    Write-Host "執行深度清理..." -ForegroundColor Red
    docker system prune -af --volumes
}

Write-Host "操作完成！" -ForegroundColor Green
