# DevTunnels 設定指南

## 問題診斷
當前錯誤：前端透過 DevTunnels 訪問後端時收到 504 Gateway Timeout 和 CORS 錯誤。

## 解決方案

### 1. 檢查 DevTunnels 是否正在運行

在 PowerShell 中執行：
```powershell
devtunnel list
```

你應該看到兩個 tunnel：
- `1848b1fg` port 3000 (前端)
- `1848b1fg` port 8001 (後端)

### 2. 啟動/重啟 DevTunnels

如果 DevTunnels 沒有運行，需要重新啟動：

#### 選項 A: 使用 VS Code DevTunnels 擴充功能
1. 在 VS Code 中按 `Ctrl+Shift+P`
2. 輸入 "DevTunnels: Create Tunnel"
3. 選擇 port 8001（後端）
4. 選擇 port 3000（前端）
5. 確保兩個隧道都設定為 **Public** 或 **Private with authentication disabled**

#### 選項 B: 使用命令列
```powershell
# 啟動後端隧道（port 8001）
devtunnel port create 8001 --protocol https

# 啟動前端隧道（port 3000）
devtunnel port create 3000 --protocol https

# 檢查狀態
devtunnel list
```

### 3. 確認 DevTunnels 的訪問設定

DevTunnels 必須允許匿名訪問或已正確配置認證。檢查：
```powershell
devtunnel show
```

確保輸出中包含：
- `Access: Public` 或適當的訪問設定
- 兩個 port 都已正確轉發

### 4. 測試 DevTunnels 連線

在瀏覽器中直接訪問：
- https://1848b1fg-8001.asse.devtunnels.ms/health

應該看到 `{"status":"healthy"}`

如果無法訪問，說明 DevTunnels 後端隧道沒有正確運行。

### 5. 更新前端環境變數（如果 DevTunnels URL 改變）

如果你的 DevTunnels URL 改變了，更新 `frontend/.env`：
```env
REACT_APP_API_BASE=https://<NEW_TUNNEL_ID>-8001.asse.devtunnels.ms
REACT_APP_WS_URL=wss://<NEW_TUNNEL_ID>-8001.asse.devtunnels.ms/api/workflow/ws
WDS_SOCKET_HOST=<NEW_TUNNEL_ID>-3000.asse.devtunnels.ms
```

然後重啟前端：
```powershell
# 在 frontend 目錄
npm start
```

### 6. 更新後端環境變數（如果需要）

如果 DevTunnels 前端 URL 改變了，更新 `backend/.env`：
```env
ALLOWED_ORIGIN_REGEX=https://[a-zA-Z0-9-]+\.asse\.devtunnels\.ms
```

後端的 `--reload` 模式會自動重新載入 `.env` 變更。

## 替代方案：使用本地開發（推薦用於開發階段）

如果 DevTunnels 設定複雜，可以暫時使用本地開發模式：

### 前端 `.env` 改為本地：
```env
# 註解掉 DevTunnels 設定
# REACT_APP_API_BASE=https://1848b1fg-8001.asse.devtunnels.ms
# REACT_APP_WS_URL=wss://1848b1fg-8001.asse.devtunnels.ms/api/workflow/ws

# 使用本地開發（透過 proxy）
# REACT_APP_API_BASE=/api  # 或直接不設定，使用 package.json 的 proxy
```

這樣前端會透過 `package.json` 的 `proxy: "http://localhost:8001"` 轉發請求。

然後訪問：
- 前端：http://localhost:3000
- 後端：http://localhost:8001

## 快速診斷命令

```powershell
# 檢查本地後端
curl http://localhost:8001/health

# 檢查 DevTunnels 後端
curl https://1848b1fg-8001.asse.devtunnels.ms/health

# 如果 DevTunnels 失敗但本地成功，說明 DevTunnels 配置有問題
```
