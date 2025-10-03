# 安全增強功能 - 快速啟動指南

本指南幫助您快速配置和啟動新增的安全增強功能。

---

## 📦 安裝依賴

### 1. 後端依賴

```bash
cd backend

# 激活虛擬環境
.\CBvenv\Scripts\Activate.ps1

# 安裝新增的依賴
pip install cryptography redis aioredis

# 或直接安裝所有依賴
pip install -r requirements.txt
```

### 2. 前端依賴

```bash
cd frontend

# 安裝 jwt-decode（Token 解析）
npm install jwt-decode

# 或使用 yarn
yarn add jwt-decode
```

---

## 🔧 環境配置

### 1. 後端配置 (.env)

在 `backend/.env` 中添加或修改以下配置：

```bash
# JWT 算法（使用 RSA）
JWT_ALGORITHM=RS256

# Redis 配置（Token 黑名單）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# CORS（允許前端訪問）
CORS_ORIGINS=http://localhost:3000
```

### 2. 前端配置

確保 `frontend/.env` 或 `frontend/package.json` 中配置了正確的 API URL：

```json
// package.json
{
  "proxy": "http://localhost:8000"
}
```

或

```bash
# .env
REACT_APP_API_BASE=http://localhost:8000/api
```

---

## 🚀 啟動服務

### 1. 啟動 Redis（可選）

Token 黑名單功能需要 Redis。如果不啟動 Redis，系統仍可正常運行，但登出時無法撤銷 Token。

#### 使用 Docker（推薦）

```bash
docker run -d -p 6379:6379 --name chatbot-redis redis:alpine
```

#### 使用 WSL（Windows）

```bash
# 在 WSL 中
sudo service redis-server start
```

#### 驗證 Redis

```bash
# 測試連接
redis-cli ping
# 應返回: PONG
```

### 2. 啟動後端

```bash
cd backend

# 激活虛擬環境
.\CBvenv\Scripts\Activate.ps1

# 啟動開發服務器
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**首次啟動時會自動：**
- ✅ 生成 RSA 金鑰對（保存在 `backend/keys/`）
- ✅ 嘗試連接 Redis（如可用）

**預期輸出：**
```
🔐 生成 RSA 金鑰對 (2048 bits)...
✅ RSA 金鑰對已生成:
   私鑰: backend/keys/jwt_private.pem
   公鑰: backend/keys/jwt_public.pem
✅ 使用 RSA 非對稱加密進行 JWT 簽名
✅ Redis 連接成功: localhost:6379
✅ Token 黑名單功能已啟用
```

如果 Redis 未啟動：
```
⚠️  Redis 連接失敗: ...
⚠️  Token 黑名單功能將不可用，但系統仍可正常運行
```

### 3. 啟動前端

```bash
cd frontend

# 啟動開發服務器
npm start
```

---

## ✅ 驗證功能

### 1. 手動測試

1. **註冊/登入**
   - 打開瀏覽器訪問 http://localhost:3000
   - 註冊或登入一個賬號
   - 打開瀏覽器開發者工具 → Application → Cookies
   - 確認看到 `refresh_token` Cookie（HttpOnly ✓）

2. **Token 刷新**
   - 保持登入狀態
   - 打開瀏覽器控制台
   - 等待 5 分鐘左右（或修改刷新閾值測試）
   - 應該看到 `[Token] Token 即將過期，觸發靜默刷新...`
   - 刷新成功後不需要重新登入

3. **Token 撤銷**
   - 點擊登出
   - 嘗試訪問需要認證的頁面
   - 應該被重定向到登入頁

4. **離線處理**
   - 打開瀏覽器開發者工具 → Network
   - 勾選 "Offline" 模擬離線
   - 應該看到 "您目前處於離線狀態" 提示
   - 取消 "Offline" 應該看到 "網絡已恢復" 提示

### 2. 自動測試腳本

```bash
cd backend

# 運行測試腳本
python scripts/test_security_enhancements.py
```

**預期輸出：**
```
🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐
安全增強功能測試
🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐

============================================================
  測試 1: RSA 非對稱加密
============================================================
✅ RSA 金鑰對已生成
✅ 私鑰格式正確 (PKCS#8)
✅ 公鑰格式正確

============================================================
  測試 2: 用戶註冊
============================================================
✅ 註冊成功
✅ Refresh Token 已存儲在 HttpOnly Cookie

...（其他測試）

============================================================
  測試完成
============================================================
```

---

## 🔍 故障排除

### 問題 1: Redis 連接失敗

**解決方案：**
1. 確認 Redis 已啟動：`redis-cli ping`
2. 檢查端口是否被占用：`netstat -an | findstr 6379`
3. 修改 `.env` 中的 `REDIS_HOST` 和 `REDIS_PORT`
4. 如果不需要 Token 黑名單，可以忽略此警告

### 問題 2: RSA 金鑰載入失敗

**解決方案：**
```bash
# 手動生成金鑰
cd backend
python -c "from app.core.rsa_keys import rsa_manager; rsa_manager.generate_keys()"
```

### 問題 3: Cookie 未設置

**解決方案：**
1. 確認後端配置了正確的 CORS：
   ```python
   # main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,  # 重要！
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. 確認前端配置了 `withCredentials`:
   ```javascript
   // api.js
   const api = axios.create({
       baseURL: API_BASE_URL,
       withCredentials: true,  // 重要！
   });
   ```

### 問題 4: 前端無法解析 Token

**解決方案：**
```bash
# 安裝 jwt-decode
cd frontend
npm install jwt-decode

# 或
yarn add jwt-decode
```

---

## 📚 相關文檔

- 📖 [完整安全增強文檔](./SECURITY_ENHANCEMENTS.md)
- 🔐 [JWT 認證指南](./JWT_Authentication_Guide.md)
- 🛡️ [安全最佳實踐](../Security-Guidelines_Traditional-Chinese.md)

---

## 🎉 完成！

您的 ChatBot 應用程式現在已啟用以下安全增強功能：

✅ **RSA 非對稱加密** - 更安全的 JWT 簽名  
✅ **Token 黑名單** - 可撤銷的 Token  
✅ **HttpOnly Cookie** - 防 XSS 攻擊  
✅ **靜默刷新** - 無感知的 Token 更新  
✅ **離線處理** - 網絡狀態監控

祝使用愉快！🚀
