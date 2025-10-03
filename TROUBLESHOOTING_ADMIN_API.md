# 前端 API 請求失敗診斷指南

## 問題症狀
- Admin Dashboard 請求被取消 (CanceledError)
- CORS 預檢請求處於 pending 狀態
- 請求超時 (45秒)

## 已完成的修復

### ✅ 1. JWT 認證系統修復
- 修復了 RSA 密鑰算法不匹配問題
- 測試通過: `test_jwt_fix.py` ✅

### ✅ 2. CORS 配置更新
- 後端 `.env` 已添加前端 DevTunnels URL:
  ```
  ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://1848b1fg-3000.asse.devtunnels.ms
  ```
- 保留了 DevTunnels 正則表達式配置

## 診斷步驟

### 步驟 1: 檢查後端服務器狀態
在後端終端檢查是否看到:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
✅ 使用 RSA 非對稱加密進行 JWT 簽名
```

**如果沒有看到** → 重啟後端服務器:
```powershell
# 停止現有服務器 (Ctrl+C)
# 然後重新啟動
cd C:\Users\MITAC\Documents\AI-CB\backend
..\CBvenv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 步驟 2: 檢查 DevTunnels 轉發狀態
確認 DevTunnels 正在運行:
```powershell
devtunnel list
```

確認端口映射:
- 後端: `8001` → `https://1848b1fg-8001.asse.devtunnels.ms`
- 前端: `3000` → `https://1848b1fg-3000.asse.devtunnels.ms`

### 步驟 3: 檢查前端 localStorage
在瀏覽器開發者工具 (F12) 中:
1. 打開 **Application** 標籤
2. 選擇 **Local Storage** → `https://1848b1fg-3000.asse.devtunnels.ms`
3. 檢查是否有 `access_token`

**如果沒有 token**:
- 需要先登入: 訪問 `https://1848b1fg-3000.asse.devtunnels.ms/login`
- 使用管理員帳號登入: `yalkyao`

**如果有 token**:
- 複製 token 值
- 前往 https://jwt.io
- 貼上 token 檢查是否過期 (exp 欄位)

### 步驟 4: 檢查網絡請求
在瀏覽器開發者工具 (F12) 中:
1. 打開 **Network** 標籤
2. 刷新頁面
3. 查看失敗的請求:
   - `statistics`
   - `users`
   - `documents`

**檢查項目**:
- 請求 URL 是否正確 (應該是 `https://1848b1fg-8001.asse.devtunnels.ms/api/admin/...`)
- Request Headers 是否包含 `Authorization: Bearer <token>`
- Response 狀態碼是什麼 (401, 403, 500?)
- CORS 錯誤信息

### 步驟 5: 測試 CORS 預檢
在瀏覽器控制台 (F12 → Console) 執行:
```javascript
fetch('https://1848b1fg-8001.asse.devtunnels.ms/api/admin/statistics', {
  method: 'OPTIONS',
  headers: {
    'Origin': 'https://1848b1fg-3000.asse.devtunnels.ms',
    'Access-Control-Request-Method': 'GET',
    'Access-Control-Request-Headers': 'authorization'
  }
}).then(r => console.log('CORS OK:', r.status)).catch(e => console.error('CORS Error:', e))
```

**預期結果**: `CORS OK: 200` 或 `204`

## 常見問題解決

### 問題 1: Token 過期或無效
**症狀**: 401 Unauthorized
**解決**: 
1. 清除 localStorage
2. 重新登入

### 問題 2: CORS 預檢失敗
**症狀**: Preflight 請求卡在 pending
**解決**:
1. 確認後端 `.env` 的 `ALLOWED_ORIGINS` 包含前端 URL
2. 重啟後端服務器
3. 檢查後端日誌是否有 CORS 錯誤

### 問題 3: DevTunnels 連接失敗
**症狀**: ERR_CONNECTION_REFUSED
**解決**:
1. 檢查 DevTunnels 是否運行: `devtunnel list`
2. 重新啟動 DevTunnels
3. 更新前端 `.env` 中的 URL

### 問題 4: 管理員權限不足
**症狀**: 403 Forbidden
**解決**:
1. 檢查用戶是否為管理員: `python scripts/check_user.py`
2. 確認 JWT token 中包含 `is_admin: true`

## 快速測試命令

### 測試後端 API (使用 curl)
```powershell
# 測試登入
curl -X POST "https://1848b1fg-8001.asse.devtunnels.ms/api/auth/login" `
  -H "Content-Type: application/json" `
  -H "Origin: https://1848b1fg-3000.asse.devtunnels.ms" `
  -d '{\"username\":\"yalkyao\",\"password\":\"YOUR_PASSWORD\"}'

# 測試管理員端點 (替換 YOUR_TOKEN)
curl -X GET "https://1848b1fg-8001.asse.devtunnels.ms/api/admin/statistics" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -H "Origin: https://1848b1fg-3000.asse.devtunnels.ms"
```

### 測試 JWT 系統
```powershell
cd C:\Users\MITAC\Documents\AI-CB\backend
..\CBvenv\Scripts\python.exe test_jwt_fix.py
```

## 下一步

根據以上診斷步驟的結果:

1. **如果 CORS 預檢失敗** → 檢查後端 CORS 配置和 DevTunnels URL
2. **如果 Token 無效** → 重新登入獲取新 token
3. **如果請求超時** → 檢查 DevTunnels 連接和後端服務器狀態
4. **如果 403 錯誤** → 檢查用戶權限和 JWT payload

請執行以上診斷步驟,並將結果反饋給我,我會幫您進一步定位問題!
