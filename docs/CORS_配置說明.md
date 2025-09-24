# CORS 配置分離說明

## 概述
現在已經將 CORS 配置分離為 `ALLOWED_ORIGINS` 和 `PUBLIC_ORIGINS`，以便更好地管理不同環境下的跨域訪問控制。

## 後端配置 (backend/.env)

### 環境變數
```properties
# 環境模式：development | production
NODE_ENV=development

# 私有/內部 origins (本地開發和內部服務)
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# 公共 origins (生產環境和外部訪問，如 DevTunnels)
PUBLIC_ORIGINS=https://pttqhds6-3000.asse.devtunnels.ms,https://pttqhds6-8001.asse.devtunnels.ms
```

### 後端邏輯 (main.py)
- **開發環境**：允許所有來源（包括 `*` 通配符）
- **生產環境**：僅允許明確指定的 origins
- **自動環境檢測**：基於 `NODE_ENV` 環境變數

## 前端配置 (frontend/.env)

### 環境變數
```properties
# 私有/內部 API 端點 (本地開發環境)
REACT_APP_ALLOWED_API_URLS=http://localhost:8001,http://127.0.0.1:8001

# 公共 API 端點 (生產環境和外部訪問)
REACT_APP_PUBLIC_API_URLS=https://pttqhds6-8001.asse.devtunnels.ms

# 完整的 API 端點列表 (向後兼容)
REACT_APP_API_URLS=http://localhost:8001,http://127.0.0.1:8001,https://pttqhds6-8001.asse.devtunnels.ms
```

### 前端邏輯 (api.js)
- **本地訪問**：優先使用 `ALLOWED_API_URLS`
- **DevTunnels 訪問**：優先使用 `PUBLIC_API_URLS`
- **其他環境**：混合使用，公共端點優先

## 優勢

### 1. 安全性
- 生產環境不使用通配符 `*`
- 明確區分內部和外部訪問端點
- 環境感知的 CORS 配置

### 2. 靈活性
- 支援多種部署環境
- 自動端點檢測和優先級排序
- 向後兼容現有配置

### 3. 可維護性
- 清晰的配置分離
- 詳細的日誌輸出
- 環境特定的行為

## 使用場景

### 開發環境
- 使用 `ALLOWED_ORIGINS` 進行本地開發
- 自動允許所有來源以便於調試

### DevTunnels 環境
- 使用 `PUBLIC_ORIGINS` 進行遠端訪問
- 自動檢測並優先使用遠端端點

### 生產環境
- 嚴格控制允許的 origins
- 僅使用明確配置的端點

## 測試方法

1. **本地開發**：訪問 `http://localhost:3000`
2. **DevTunnels**：訪問 `https://pttqhds6-3000.asse.devtunnels.ms`
3. **檢查控制台**：查看自動選擇的 API 端點日誌

## 注意事項

- 確保 DevTunnels URL 保持更新
- 生產環境中移除 `*` 通配符
- 定期檢查和更新 origins 列表