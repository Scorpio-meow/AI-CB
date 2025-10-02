# JWT 認證系統 - 快速開始指南

## 🚀 5 分鐘快速啟動

### 步驟 1: 安裝依賴 (已完成✅)

依賴已安裝:
- `python-jose[cryptography]==3.3.0`
- `passlib[bcrypt]==1.7.4`

### 步驟 2: 運行數據庫遷移

```powershell
cd C:\Users\MITAC\Documents\AI-CB\backend
..\CBvenv\Scripts\python.exe scripts/migrate_to_jwt.py
```

這會為 User 表添加 `role` 和 `last_login` 欄位。

### 步驟 3: 創建管理員帳號

**互動模式 (推薦)**:
```powershell
..\CBvenv\Scripts\python.exe scripts/create_admin.py -i
```

然後按提示輸入:
- 用戶名: `admin`
- 電子郵件: `admin@example.com`
- 密碼: `Admin123456` (記得改成強密碼!)

**或直接命令行**:
```powershell
..\CBvenv\Scripts\python.exe scripts/create_admin.py --username admin --email admin@example.com --password Admin123456
```

### 步驟 4: 啟動後端服務

停止當前服務(Ctrl+C),然後重新啟動:

```powershell
..\CBvenv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 步驟 5: 測試 JWT 認證

#### 5.1 註冊新用戶

```powershell
$body = @{
    username = "testuser"
    email = "test@example.com"
    password = "Test123456"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/auth/register" -Method Post -Body $body -ContentType "application/json"
```

#### 5.2 登入

```powershell
$body = @{
    username = "admin"
    password = "Admin123456"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8001/api/auth/login" -Method Post -Body $body -ContentType "application/json"

# 保存 Token
$token = $response.tokens.access_token
```

#### 5.3 訪問受保護的 API

```powershell
# 獲取當前用戶資料
$headers = @{ "Authorization" = "Bearer $token" }
Invoke-RestMethod -Uri "http://localhost:8001/api/auth/me" -Headers $headers

# 訪問管理員 API (需要管理員權限)
Invoke-RestMethod -Uri "http://localhost:8001/api/admin/users" -Headers $headers
```

---

## 📋 驗證清單

- [x] ✅ 依賴已安裝 (python-jose, passlib)
- [ ] ⏳ 數據庫已遷移 (migrate_to_jwt.py)
- [ ] ⏳ 管理員帳號已創建
- [ ] ⏳ 後端服務已重啟
- [ ] ⏳ JWT 認證測試通過

---

## 🎯 API 端點總覽

### 公開端點 (無需認證)
- `POST /api/auth/register` - 用戶註冊
- `POST /api/auth/login` - 用戶登入
- `POST /api/auth/refresh` - 刷新令牌

### 需要認證的端點
- `GET /api/auth/me` - 獲取當前用戶資料
- `PUT /api/auth/me` - 更新用戶資料
- `POST /api/auth/change-password` - 修改密碼
- `POST /api/auth/logout` - 登出
- `GET /api/auth/validate` - 驗證令牌

### 管理員專用端點 (需要 admin 角色)
- `GET /api/admin/users` - 獲取所有用戶
- `GET /api/admin/statistics` - 系統統計
- `GET /api/admin/conversations` - 所有對話
- `GET /api/admin/documents` - 所有文檔
- `GET /api/admin/vector-store/*` - 向量庫管理

---

## ⚠️ 重要提示

### Token 格式
所有需要認證的請求必須在 Header 中包含:
```
Authorization: Bearer <access_token>
```

### Token 過期時間
- **Access Token**: 30 分鐘
- **Refresh Token**: 7 天

### 密碼要求
- 至少 8 個字符
- 包含大寫字母 (A-Z)
- 包含小寫字母 (a-z)
- 包含數字 (0-9)

---

## 🔧 常見問題

### Q: "用戶名已被使用"
**A**: 嘗試使用不同的用戶名,或檢查數據庫中是否已存在該用戶。

### Q: "密碼強度不足"
**A**: 確保密碼符合要求 (至少8字符,包含大小寫字母和數字)。

### Q: "無效的認證令牌"
**A**: Token 可能已過期,使用 Refresh Token 刷新或重新登入。

### Q: "需要管理員權限"
**A**: 使用管理員帳號登入,或運行 `create_admin.py` 創建管理員。

---

## 📚 完整文檔

詳細文檔請參閱: `docs/JWT_Authentication_Guide.md`

---

**準備就緒後,執行步驟 2-4 即可啟用 JWT 認證系統!** 🎉
