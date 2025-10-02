# JWT 認證系統完整指南

## 📋 目錄

1. [系統概述](#系統概述)
2. [快速開始](#快速開始)
3. [API 端點](#api-端點)
4. [認證流程](#認證流程)
5. [安全性特性](#安全性特性)
6. [前端整合](#前端整合)
7. [故障排除](#故障排除)

---

## 系統概述

ChatBot 應用程式現已實施完整的 JWT (JSON Web Token) 認證系統,提供:

- ✅ **用戶註冊和登入**: 安全的帳號創建和身份驗證
- ✅ **JWT Token**: Access Token (30分鐘) + Refresh Token (7天)
- ✅ **角色權限**: 區分普通用戶和管理員
- ✅ **密碼安全**: BCrypt 加密,強密碼驗證
- ✅ **令牌刷新**: 自動續期機制
- ✅ **安全日誌**: 詳細的認證事件記錄

### 技術棧

- **JWT**: python-jose (JOSE/JWT 實現)
- **密碼加密**: passlib + bcrypt
- **Token 傳輸**: HTTP Bearer Authentication
- **會話管理**: 無狀態 JWT (不需要 Redis)

---

## 快速開始

### 1. 安裝依賴

```bash
cd backend
pip install -r requirements.txt
```

新增的依賴:
- `python-jose[cryptography]==3.3.0` - JWT 處理
- `passlib[bcrypt]==1.7.4` - 密碼加密

### 2. 配置環境變數

在 `backend/.env` 中確認以下配置:

```env
# JWT 配置
JWT_SECRET_KEY=8x5KpN2wqM_YzjTvRh9LcEu6DfXb3GsQaW1PnJmHkV7iYt0oZr4Ue-8x5KpN2wqM_YzjTvRh9LcEu6DfXb3GsQaW1PnJmHkV7
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

⚠️ **重要**: 生產環境務必更換為自己的 SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3. 運行數據庫遷移

```bash
cd backend
python scripts/migrate_to_jwt.py
```

這會為 User 表添加 `role` 和 `last_login` 欄位。

### 4. 創建管理員帳號

**方式 A: 互動模式 (推薦)**
```bash
python scripts/create_admin.py -i
```

**方式 B: 命令行模式**
```bash
python scripts/create_admin.py --username admin --email admin@example.com --password Admin123456
```

### 5. 啟動服務

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

---

## API 端點

所有認證端點都在 `/api/auth` 路徑下。

### 📝 用戶註冊

**POST** `/api/auth/register`

**請求體:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123"
}
```

**響應** (201 Created):
```json
{
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "role": "user",
    "is_active": true,
    "is_admin": false,
    "created_at": "2024-01-01T00:00:00",
    "last_login": null
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "message": "註冊成功"
}
```

**密碼要求:**
- 至少 8 個字符
- 包含大寫字母
- 包含小寫字母
- 包含數字

---

### 🔐 用戶登入

**POST** `/api/auth/login`

**請求體:**
```json
{
  "username": "john_doe",
  "password": "SecurePass123"
}
```

**響應** (200 OK):
```json
{
  "user": { /* ... */ },
  "tokens": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "message": "登入成功"
}
```

---

### 🔄 刷新令牌

**POST** `/api/auth/refresh`

**請求體:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**響應** (200 OK):
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### 👤 獲取當前用戶資料

**GET** `/api/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**響應** (200 OK):
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T00:00:00",
  "last_login": "2024-01-15T10:30:00"
}
```

---

### ✏️ 更新用戶資料

**PUT** `/api/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**請求體:**
```json
{
  "email": "newemail@example.com",
  "current_password": "OldPass123",
  "new_password": "NewSecurePass456"
}
```

**響應** (200 OK):
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "newemail@example.com",
  /* ... */
}
```

---

### 🔒 修改密碼

**POST** `/api/auth/change-password`

**Headers:**
```
Authorization: Bearer <access_token>
```

**請求體:**
```json
{
  "current_password": "OldPass123",
  "new_password": "NewSecurePass456",
  "confirm_password": "NewSecurePass456"
}
```

**響應** (200 OK):
```json
{
  "message": "密碼修改成功",
  "success": true
}
```

---

### 🚪 登出

**POST** `/api/auth/logout`

**Headers:**
```
Authorization: Bearer <access_token>
```

**響應** (200 OK):
```json
{
  "message": "登出成功",
  "success": true
}
```

⚠️ **注意**: JWT 是無狀態的,實際的令牌撤銷需要在客戶端完成 (刪除存儲的 token)。

---

### ✅ 驗證令牌

**GET** `/api/auth/validate`

**Headers:**
```
Authorization: Bearer <access_token>
```

**響應** (200 OK):
```json
{
  "message": "Token 有效,用戶: john_doe",
  "success": true
}
```

---

## 認證流程

### 完整認證流程圖

```
┌─────────┐                 ┌─────────┐
│         │   1. Register   │         │
│ Client  │────────────────>│ Backend │
│         │   2. Login      │         │
└─────────┘<────────────────└─────────┘
     │                           │
     │   3. Store Tokens         │
     │   (localStorage)          │
     ▼                           │
┌─────────┐                     │
│         │   4. API Request    │
│ Client  │────────────────────>│
│         │   + Access Token    │
└─────────┘                     │
     │                           │
     │   5. Access Token Expired│
     ▼                           │
┌─────────┐                     │
│         │   6. Refresh Token  │
│ Client  │────────────────────>│
│         │   7. New Tokens     │
└─────────┘<────────────────────┘
     │
     │   8. Continue with new token
     ▼
```

### 詳細步驟

#### 1. 註冊 / 登入
```javascript
const response = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});

const { user, tokens } = await response.json();
```

#### 2. 存儲 Tokens
```javascript
localStorage.setItem('access_token', tokens.access_token);
localStorage.setItem('refresh_token', tokens.refresh_token);
```

#### 3. 使用 Access Token 發送請求
```javascript
const response = await fetch('/api/admin/users', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});
```

#### 4. Access Token 過期時自動刷新
```javascript
async function refreshAccessToken() {
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      refresh_token: localStorage.getItem('refresh_token')
    })
  });
  
  const { access_token, refresh_token } = await response.json();
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('refresh_token', refresh_token);
}
```

---

## 安全性特性

### 1. 密碼加密
- 使用 **BCrypt** 算法加密密碼
- 自動生成 Salt
- 不可逆加密

### 2. 強密碼策略
- 最少 8 字符
- 必須包含大寫字母
- 必須包含小寫字母
- 必須包含數字

### 3. JWT 令牌安全
- **短期 Access Token**: 30 分鐘過期
- **長期 Refresh Token**: 7 天過期
- HMAC-SHA256 簽名
- 包含用戶身份和角色信息

### 4. 安全日誌
所有認證事件都會記錄到 `logs/security.log`:
- 用戶註冊
- 登入成功/失敗
- 密碼修改
- 令牌刷新

### 5. 角色權限控制
- **普通用戶**: 訪問聊天、文檔上傳
- **管理員**: 完整系統管理權限

---

## 前端整合

### React + Axios 範例

#### 1. 創建 Axios 實例

```javascript
// src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8001'
});

// Request Interceptor - 自動添加 Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response Interceptor - 自動刷新 Token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post('/api/auth/refresh', {
          refresh_token: refreshToken
        });

        const { access_token, refresh_token } = response.data;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh 失敗,跳轉到登入頁
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

#### 2. 認證服務

```javascript
// src/services/authService.js
import api from './api';

export const authService = {
  async register(username, email, password) {
    const response = await api.post('/api/auth/register', {
      username,
      email,
      password
    });
    
    const { user, tokens } = response.data;
    this.saveTokens(tokens);
    return user;
  },

  async login(username, password) {
    const response = await api.post('/api/auth/login', {
      username,
      password
    });
    
    const { user, tokens } = response.data;
    this.saveTokens(tokens);
    return user;
  },

  async logout() {
    try {
      await api.post('/api/auth/logout');
    } finally {
      this.clearTokens();
    }
  },

  async getCurrentUser() {
    const response = await api.get('/api/auth/me');
    return response.data;
  },

  saveTokens(tokens) {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
  },

  clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  isAuthenticated() {
    return !!localStorage.getItem('access_token');
  }
};
```

#### 3. 受保護的路由

```javascript
// src/components/PrivateRoute.js
import React from 'react';
import { Navigate } from 'react-router-dom';
import { authService } from '../services/authService';

export const PrivateRoute = ({ children }) => {
  return authService.isAuthenticated() ? children : <Navigate to="/login" />;
};
```

---

## 故障排除

### 問題 1: "無效的認證令牌"

**原因**: Access Token 已過期或無效

**解決方案**:
1. 檢查 Token 是否正確存儲
2. 確保在請求頭中正確添加 `Authorization: Bearer <token>`
3. 使用 Refresh Token 刷新 Access Token

### 問題 2: "需要管理員權限"

**原因**: 當前用戶不是管理員

**解決方案**:
```bash
# 創建管理員帳號
python scripts/create_admin.py -i
```

### 問題 3: 密碼強度不足

**錯誤**: "密碼必須包含至少一個大寫字母"

**解決方案**: 確保密碼符合以下要求:
- ✅ 至少 8 字符
- ✅ 包含大寫字母 (A-Z)
- ✅ 包含小寫字母 (a-z)
- ✅ 包含數字 (0-9)

### 問題 4: Token 解碼失敗

**錯誤**: "無效的認證令牌: Signature verification failed"

**原因**: JWT_SECRET_KEY 不匹配

**解決方案**:
1. 確認 `.env` 中的 `JWT_SECRET_KEY` 正確
2. 重新登入獲取新的 Token

---

## 最佳實踐

### 1. Token 存儲
✅ **推薦**: localStorage (SPA 應用)
❌ **不推薦**: Cookie (需要額外的 CSRF 保護)

### 2. Token 刷新策略
- Access Token 過期前 5 分鐘自動刷新
- 使用 Axios Interceptor 自動處理

### 3. 安全建議
- ✅ 生產環境務必使用 HTTPS
- ✅ 定期更換 JWT_SECRET_KEY
- ✅ 實施速率限制防止暴力破解
- ✅ 記錄所有認證事件

### 4. 密碼管理
- ✅ 強制用戶使用強密碼
- ✅ 定期提示用戶修改密碼
- ✅ 提供密碼重置功能 (可選)

---

## API 測試範例

### cURL 測試

```bash
# 1. 註冊
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"Test123456"}'

# 2. 登入
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test123456"}'

# 3. 獲取當前用戶 (需要 Token)
curl -X GET http://localhost:8001/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 4. 訪問管理員 API (需要管理員權限)
curl -X GET http://localhost:8001/api/admin/users \
  -H "Authorization: Bearer YOUR_ADMIN_ACCESS_TOKEN"
```

---

## 總結

✅ **已實施的功能**:
- JWT 認證系統
- 用戶註冊和登入
- 令牌自動刷新
- 角色權限控制
- 密碼安全加密
- 安全事件日誌

🎯 **下一步**:
1. 更新前端應用以使用 JWT 認證
2. 測試所有認證流程
3. 部署到生產環境

📚 **相關文檔**:
- [FastAPI 文檔](https://fastapi.tiangolo.com/)
- [JWT 官方網站](https://jwt.io/)
- [Python-JOSE 文檔](https://python-jose.readthedocs.io/)

---

**文檔版本**: 1.0  
**最後更新**: 2025-01-02
