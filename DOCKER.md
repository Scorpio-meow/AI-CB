# Docker 部署指南

## 概述

本項目提供了完整的 Docker 容器化解決方案，支援開發、測試和生產環境的部署。

## 文件結構

```
├── backend/
│   ├── Dockerfile              # 後端生產環境 Docker 文件
│   ├── .dockerignore          # 後端 Docker 忽略文件
│   └── healthcheck.py         # 健康檢查腳本
├── frontend/
│   ├── Dockerfile             # 前端生產環境 Docker 文件
│   ├── Dockerfile.dev         # 前端開發環境 Docker 文件
│   ├── nginx.conf            # Nginx 配置文件
│   └── .dockerignore         # 前端 Docker 忽略文件
├── docker-compose.yml         # 基本 Docker Compose 配置
├── docker-compose.dev.yml     # 開發環境配置
├── docker-compose.prod.yml    # 生產環境配置
└── docker-start.ps1          # Docker 管理腳本
```

## 快速開始

### 1. 開發環境

使用開發環境配置啟動，支援熱重載：

```powershell
# 啟動開發環境
.\docker-start.ps1 -Action up -Dev -Build

# 查看日誌
.\docker-start.ps1 -Action logs -Dev
```

### 2. 生產環境

```powershell
# 構建並啟動生產環境
.\docker-start.ps1 -Action up -Build

# 使用生產配置
docker-compose -f docker-compose.prod.yml up -d --build
```

## Docker Compose 配置

### 開發環境 (docker-compose.dev.yml)

- **特點**：支援熱重載、掛載源碼目錄
- **後端**：`http://localhost:8001`
- **前端**：`http://localhost:3000`
- **數據持久化**：本地目錄掛載

### 生產環境 (docker-compose.prod.yml)

- **特點**：優化性能、資源限制、健康檢查
- **前端**：`http://localhost:80`
- **後端**：`http://localhost:8001`
- **包含**：Redis 快取、資源限制、自動重啟

## 常用命令

### 管理腳本使用

```powershell
# 啟動服務
.\docker-start.ps1 -Action up [-Dev] [-Build]

# 停止服務
.\docker-start.ps1 -Action down

# 查看狀態
.\docker-start.ps1 -Action status

# 查看日誌
.\docker-start.ps1 -Action logs

# 重啟服務
.\docker-start.ps1 -Action restart

# 清理資源
.\docker-start.ps1 -Action clean
```

### 直接使用 Docker Compose

```bash
# 開發環境
docker-compose -f docker-compose.dev.yml up -d --build
docker-compose -f docker-compose.dev.yml down

# 生產環境
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml down

# 查看日誌
docker-compose logs -f [service-name]

# 進入容器
docker exec -it chatbot-backend-dev bash
docker exec -it chatbot-frontend-dev sh
```

## 健康檢查

所有容器都配置了健康檢查：

```bash
# 查看容器健康狀態
docker ps

# 查看詳細健康檢查日誌
docker inspect chatbot-backend-prod | grep -A 10 Health
```

## 數據持久化

### 開發環境
- 後端數據：`./backend/data` → `/app/data`
- 數據庫：`./backend/chatbot.db` → `/app/chatbot.db`

### 生產環境
- 使用 Docker 卷進行數據持久化
- 卷名稱：`chatbot-data`、`chatbot-db`、`redis-data`

## 網路配置

所有服務運行在 `chatbot-network` 網路中：
- 服務間通信使用容器名稱
- 前端通過 Nginx 代理連接後端

## 性能優化

### 生產環境優化
- **多階段構建**：減少鏡像大小
- **Nginx 壓縮**：啟用 Gzip 壓縮
- **靜態資源快取**：設置長期快取
- **資源限制**：防止資源耗盡

### 監控和日誌
- **健康檢查**：自動重啟不健康的容器
- **日誌管理**：使用 `docker logs` 查看應用日誌
- **資源監控**：`docker stats` 查看資源使用

## 故障排除

### 常見問題

1. **端口衝突**
   ```bash
   # 檢查端口使用
   netstat -ano | findstr :8001
   netstat -ano | findstr :3000
   ```

2. **數據卷權限問題**
   ```bash
   # Windows 上確保 Docker 有正確的文件夾權限
   # 在 Docker Desktop 設置中配置文件共享
   ```

3. **內存不足**
   ```bash
   # 調整 Docker Desktop 內存限制
   # 或修改 docker-compose.prod.yml 中的資源限制
   ```

4. **網路連接問題**
   ```bash
   # 重新創建網路
   docker network rm chatbot-network
   docker-compose up -d
   ```

### 調試命令

```bash
# 進入後端容器調試
docker exec -it chatbot-backend bash
python healthcheck.py

# 查看前端構建日誌
docker-compose logs frontend

# 檢查數據卷
docker volume ls
docker volume inspect chatbot-data
```

## 安全考慮

### 生產環境建議
1. **環境變數**：使用 `.env` 文件管理敏感配置
2. **網路隔離**：使用自定義網路
3. **資源限制**：設置合理的 CPU 和內存限制
4. **定期更新**：保持基底鏡像和依賴的最新版本
5. **日誌管理**：配置日誌輪轉和外部日誌收集

### 數據備份
```bash
# 備份數據卷
docker run --rm -v chatbot-data:/data -v $(pwd):/backup alpine tar czf /backup/chatbot-data-backup.tar.gz -C /data .

# 恢復數據卷
docker run --rm -v chatbot-data:/data -v $(pwd):/backup alpine tar xzf /backup/chatbot-data-backup.tar.gz -C /data
```

## 擴展部署

### 使用 Docker Swarm
```bash
# 初始化 Swarm
docker swarm init

# 部署服務
docker stack deploy -c docker-compose.prod.yml chatbot
```

### 使用 Kubernetes
可以基於現有的 Docker 配置生成 Kubernetes YAML 文件進行部署。
