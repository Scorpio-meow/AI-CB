# 前端與後端 API 交互全面審查報告

生成日期：2025年10月3日

---

## 📋 目錄
1. [配置檢查](#配置檢查)
2. [認證系統](#認證系統)
3. [聊天系統](#聊天系統)
4. [文檔管理](#文檔管理)
5. [管理後台](#管理後台)
6. [自訂Agent](#自訂agent)
7. [Tags系統](#tags系統)
8. [Timeout與錯誤處理](#timeout與錯誤處理)
9. [問題與建議](#問題與建議)

---

## 🔧 配置檢查

### 前端配置 (`frontend/.env`)
```properties
✅ REACT_APP_API_BASE=https://1848b1fg-8001.asse.devtunnels.ms
✅ HTTPS=true
✅ WDS_SOCKET_HOST=1848b1fg-3000.asse.devtunnels.ms
✅ WDS_SOCKET_PORT=443
```

### 後端配置 (`backend/.env`)
```properties
✅ ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
✅ ALLOWED_ORIGIN_REGEX=https://[a-zA-Z0-9-]+\.asse\.devtunnels\.ms
✅ ENVIRONMENT=development (新增)
✅ PORT=8001
```

### API Base URL 計算 (`api.js`)
```javascript
RAW_API_URL = "https://1848b1fg-8001.asse.devtunnels.ms"
normalizeAbsoluteUrl():
  - 移除 DevTunnels 的明確 port (避免雙重 port 問題)
  - 確保路徑以 /api 結尾
結果: "https://1848b1fg-8001.asse.devtunnels.ms/api"
```

### CORS 配置 (`main.py`)
```python
allow_origins = [
  "http://localhost:3000",
  "http://127.0.0.1:3000"
]
allow_origin_regex = "https://[a-zA-Z0-9-]+\.asse\.devtunnels\.ms"
  (僅在 ENVIRONMENT != "production" 時啟用)

✅ 配置正確：前端 DevTunnels URL 符合 regex
```

**狀態：✅ 配置一致且正確**

---

## 🔐 認證系統

### 前端端點 (`authService.js`)
| 方法 | 端點 | Timeout | 用途 |
|------|------|---------|------|
| POST | `/auth/register` | 45s | 用戶註冊 |
| POST | `/auth/login` | 45s | 用戶登入 |
| POST | `/auth/logout` | 45s | 用戶登出 |
| POST | `/auth/refresh` | 45s | 刷新 access token |
| GET | `/auth/me` | **90s** | 獲取當前用戶資料 |
| PUT | `/auth/me` | 45s | 更新用戶資料 |
| POST | `/auth/change-password` | 45s | 修改密碼 |
| GET | `/auth/validate` | 45s | 驗證 token |

### 後端端點 (`auth.py`)
| 方法 | 路徑 | 依賴注入 | 返回值 |
|------|------|----------|--------|
| POST | `/api/auth/register` | - | user, tokens |
| POST | `/api/auth/login` | - | user, tokens |
| POST | `/api/auth/logout` | get_current_user_id | message |
| POST | `/api/auth/refresh` | - | access_token, refresh_token |
| GET | `/api/auth/me` | get_current_user_id | user |
| PUT | `/api/auth/me` | get_current_user_id | user |
| POST | `/api/auth/change-password` | get_current_user_id | message |
| GET | `/api/auth/validate` | get_current_user_id | valid:true |

**狀態：✅ 前後端端點完全匹配**

### Token 管理
- **存儲位置：** localStorage
  - `access_token`: JWT access token (30分鐘過期)
  - `refresh_token`: JWT refresh token (7天過期)
  - `user_info`: 用戶資料快取

- **Request Interceptor：** 自動添加 `Authorization: Bearer <token>`

- **Response Interceptor：** 
  - ✅ **Refresh Lock 機制已實施**（避免並行 refresh）
  - 401 錯誤 → 自動 refresh token → 重試原請求
  - Refresh 失敗 → 清除認證資料 → 跳轉登入頁

### ⚠️ 發現問題
1. **getCurrentUser timeout 增加到 90s**：
   - ✅ 已修復：給 DevTunnels + token refresh 充足時間
   - ⚠️ 但仍可能在 token 過期時卡住

2. **Layout.js loadUser 錯誤處理**：
   - ✅ 已簡化：移除冗餘 AbortController
   - ✅ 靜默處理 timeout 錯誤

---

## 💬 聊天系統

### 前端端點 (`api.js` + `Chat.js`)
| 方法 | 端點 | Timeout | 使用位置 |
|------|------|---------|----------|
| POST | `/chat/send` | - | Chat.js: handleSendMessage |
| GET | `/chat/conversations` | 45s | Chat.js: loadConversations |
| GET | `/chat/conversations/{id}` | 45s | Chat.js: loadConversation |
| GET | `/chat/conversations/{id}/messages` | 45s | Chat.js: loadConversation (分頁) |
| DELETE | `/chat/conversations/{id}` | - | Chat.js: handleDeleteConversation |
| POST | `/chat/conversations` | - | Chat.js: startNewConversation |

### 後端端點 (`chat.py`)
| 方法 | 路徑 | 查詢參數 | 返回值 |
|------|------|----------|--------|
| POST | `/api/chat/send` | - | message, conversation, assistant_message |
| GET | `/api/chat/conversations` | - | List[Conversation] |
| GET | `/api/chat/conversations/{id}` | - | Conversation |
| GET | `/api/chat/conversations/{id}/messages` | limit, offset | List[Message] (分頁) |
| DELETE | `/api/chat/conversations/{id}` | - | message |
| POST | `/api/chat/conversations` | - | Conversation |

**狀態：✅ 前後端端點完全匹配**

### 分頁實現
```javascript
// 前端 (Chat.js:213)
GET /chat/conversations/{id}/messages?limit=100&offset=0

// 後端 (chat.py:115)
async def get_conversation_messages_endpoint(
    conversation_id: int,
    limit: int = 100,
    offset: int = 0,
    ...
)
```

**✅ 分頁邏輯正確**

### ⚠️ 發現問題
1. **loadMoreMessages 實現**：
   - ✅ 有 IntersectionObserver 自動載入
   - ✅ 有手動「載入更多」按鈕
   - ⚠️ offset 計算依賴 `messages.length`，如果有刪除可能不準

---

## 📄 文檔管理

### 前端端點 (`api.js` + `Documents.js`)
| 方法 | 端點 | Timeout | 特殊處理 |
|------|------|---------|----------|
| POST | `/documents/upload` | - | multipart/form-data |
| GET | `/documents` | **120s** | 快取 3min |
| DELETE | `/documents/{id}` | - | - |

### 後端端點 (`documents.py`)
| 方法 | 路徑 | 功能 | 注意事項 |
|------|------|------|----------|
| POST | `/api/documents/upload` | 單檔或多檔上傳 | 流式寫入 |
| POST | `/api/documents/bulk_delete` | 批次刪除 | 並行處理 |
| GET | `/api/documents/` | 獲取文件列表 | **注意 trailing slash** |
| DELETE | `/api/documents/{id}` | 刪除單個文件 | - |

**狀態：⚠️ 發現潛在問題**

### ⚠️ 發現問題

1. **Trailing Slash 不一致：**
   ```javascript
   // 前端 (api.js:205)
   api.get('/documents')  // 沒有 trailing slash
   
   // 後端 (documents.py:305)
   @router.get("/")  // prefix="/api/documents" → /api/documents/
   ```
   
   **結果：**
   - 前端請求 `GET /api/documents`
   - 後端重定向 `307 → /api/documents/`
   - 增加一次往返延遲 (~1s)

   **修復建議：** 前端改為 `api.get('/documents/')`

2. **Documents timeout 120s：**
   - ✅ 已增加到 120s
   - ⚠️ 但實際查詢空表應該 < 1s
   - 問題是 **token refresh 時卡在隊列中**

3. **批次刪除端點：**
   - ✅ 後端有 `POST /api/documents/bulk_delete`
   - ❓ 前端 Documents.js 是否有使用？需要檢查

---

## 🛡️ 管理後台

### 前端端點 (`api.js` + `AdminDashboard.js`)
| 方法 | 端點 | Timeout | 快取 |
|------|------|---------|------|
| GET | `/admin/users` | 45s | 3min |
| GET | `/admin/statistics` | 45s | 3min |
| PUT | `/admin/users/{id}` | - | - |
| DELETE | `/admin/users/{id}` | - | - |

### 後端端點 (`admin.py`)
| 方法 | 路徑 | 權限檢查 | 功能 |
|------|------|----------|------|
| GET | `/api/admin/users` | is_admin | 獲取所有用戶 |
| GET | `/api/admin/statistics` | is_admin | 系統統計 |
| PUT | `/api/admin/users/{id}` | is_admin | 更新用戶 |
| DELETE | `/api/admin/users/{id}` | is_admin | 刪除用戶 |

**狀態：✅ 前後端端點完全匹配**

### ✅ 優化已實施
- ✅ 記憶體快取 3 分鐘
- ✅ isMountedRef guards
- ✅ 45s timeout with AbortController
- ✅ Dev-only debug logs

---

## 🤖 自訂Agent

### 前端端點 (`customAgentService.js`)
| 方法 | 端點 | Timeout | 快取/去重 |
|------|------|---------|-----------|
| GET | `/custom_agents/` | 45s | - |
| GET | `/custom_agents/all_with_details` | 45s | 記憶體快取 2min + 去重 |
| GET | `/custom_agents/{id}` | 45s | - |
| POST | `/custom_agents/` | 45s | - |
| PUT | `/custom_agents/{id}` | 45s | - |
| DELETE | `/custom_agents/{id}` | 45s | - |

### 後端端點 (`custom_agent.py`)
| 方法 | 路徑 | 功能 | 關聯查詢 |
|------|------|------|----------|
| GET | `/api/custom_agents/` | 獲取用戶的 agents | - |
| GET | `/api/custom_agents/all_with_details` | 包含統計資料 | JOIN tags, conversations |
| GET | `/api/custom_agents/{id}` | 單個 agent 詳情 | - |
| POST | `/api/custom_agents/` | 建立 agent | - |
| PUT | `/api/custom_agents/{id}` | 更新 agent | - |
| DELETE | `/api/custom_agents/{id}` | 刪除 agent | CASCADE 刪除 |

**狀態：✅ 前後端端點完全匹配**

### ✅ 優化已實施
- ✅ `all_with_details` 記憶體快取 2 分鐘
- ✅ in-flight 去重（`_agentsInFlight` Promise 共享）
- ✅ 45s timeout with withTimeout wrapper
- ✅ AgentContext 移到受保護路由（不在登入前載入）

---

## 🏷️ Tags系統

### 前端端點 (`Chat.js`)
| 方法 | 端點 | Timeout | 快取 |
|------|------|---------|------|
| GET | `/tags` | - | localStorage 5min |
| GET | `/external-tags` | - | - |

### 後端端點 (`tags.py`)
| 方法 | 路徑 | 功能 |
|------|------|------|
| GET | `/api/tags` | 獲取所有 tags |
| GET | `/api/external-tags` | 獲取外部 tags |

**狀態：✅ 前後端端點完全匹配**

### ✅ 優化已實施
- ✅ localStorage 快取 5 分鐘
- ✅ window.__tagsLoading 去重
- ✅ Dev-only debug logs

---

## ⏱️ Timeout 與錯誤處理

### Timeout 設定總覽

| 位置 | 方法 | Timeout | 原因 |
|------|------|---------|------|
| authService | register, login, logout, refresh, updateProfile, changePassword, validate | 45s | 一般操作 |
| authService | **getCurrentUser** | **90s** | DevTunnels + token refresh |
| customAgentService | 所有方法 | 45s | 包含快取去重 |
| Chat.js | loadConversation | 45s | AbortController |
| Chat.js | loadConversations | 45s | AbortController |
| Documents.js | loadDocuments | **120s** | Token refresh + CORS preflight |
| AdminDashboard.js | loadData | 45s | AbortController |

### AbortController 使用

| 檔案 | 位置 | 狀態 |
|------|------|------|
| Layout.js | loadUser | ❌ **已移除**（與 authService 衝突） |
| Chat.js | loadConversation | ✅ 正確 |
| Chat.js | loadConversations | ✅ 正確 |
| Chat.js | loadMoreMessages | ✅ 正確 |
| Documents.js | loadDocuments | ✅ 正確 |
| Documents.js | uploadSingle | ✅ 正確 (per-file) |
| AdminDashboard.js | loadData | ✅ 正確 |

### isMountedRef Guards

| 檔案 | 狀態 |
|------|------|
| Layout.js | ✅ 已實施 |
| Chat.js | ✅ 已實施 |
| Documents.js | ✅ 已實施 |
| AdminDashboard.js | ✅ 已實施 |
| AgentContext.js | ✅ 已實施 |

### 錯誤處理策略

| 類型 | 處理方式 |
|------|----------|
| **Timeout 錯誤** | Dev-only debug log, 不顯示紅色 error |
| **AbortError / CanceledError** | 靜默處理 (dev-only debug) |
| **401 Unauthorized** | api.js refresh interceptor 自動處理 |
| **其他錯誤** | console.error + 用戶友好提示 |

---

## 🚨 問題與建議

### 🔴 高優先級問題

1. **Documents 端點 Trailing Slash 不一致**
   - **現象：** 307 Redirect 增加 1s 延遲
   - **位置：** `api.js:205` vs `documents.py:305`
   - **修復：** 前端改為 `api.get('/documents/')`

2. **getCurrentUser 在 token 過期時卡住**
   - **現象：** 等待 refresh queue 導致 45-90s timeout
   - **位置：** `Layout.js:59` 調用 `authService.getCurrentUser()`
   - **影響：** 每次進入受保護路由都可能卡住
   - **建議：** 
     - 考慮在 Layout mount 前主動檢查 token 是否快過期
     - 或實施 token 預刷新機制

3. **Messages 載入時 offset 計算不準確**
   - **現象：** 依賴 `messages.length`，刪除後會錯位
   - **位置：** `Chat.js` loadMoreMessages
   - **建議：** 改用 cursor-based pagination

### 🟡 中優先級問題

4. **Refresh Lock 可能死鎖**
   - **現象：** 如果 refresh 請求本身超時，所有等待的請求都會卡住
   - **位置：** `api.js` refresh interceptor
   - **建議：** 加入 refresh lock timeout 和錯誤重置邏輯

5. **Documents loadDocuments 快取可能過時**
   - **現象：** 上傳/刪除後快取未失效
   - **位置：** `Documents.js`
   - **建議：** 上傳/刪除後強制刷新 `loadDocuments(true)`

6. **批次刪除端點未使用**
   - **現象：** 後端有 `POST /api/documents/bulk_delete` 但前端未使用
   - **建議：** 實施批次選擇和刪除功能

### 🟢 低優先級改進

7. **統一 Timeout 配置**
   - **建議：** 將所有 timeout 值移到環境變數或配置檔案

8. **API 響應快取策略**
   - **建議：** 考慮使用 React Query 或 SWR 統一管理快取和重新驗證

9. **錯誤訊息國際化**
   - **建議：** 將所有錯誤訊息提取到語言檔案

---

## ✅ 總結

### 已驗證正確的部分
- ✅ **CORS 配置**：DevTunnels regex 正確啟用
- ✅ **Token Refresh Lock**：避免並行 refresh 競爭
- ✅ **isMountedRef Guards**：所有關鍵組件已實施
- ✅ **Console 噪音消除**：dev-only debug logs
- ✅ **AgentProvider 架構**：移到受保護路由
- ✅ **分頁系統**：messages 端點支援 limit/offset

### 需要修復的問題
1. 🔴 **Documents trailing slash** (簡單修復)
2. 🔴 **getCurrentUser token 過期卡住** (需要架構改進)
3. 🟡 **Refresh lock 死鎖風險** (需要超時重置邏輯)
4. 🟡 **Documents 快取失效** (需要事件驅動刷新)

### 建議下一步
1. 修復 Documents trailing slash
2. 測試完整工作流程（Login → Chat → Documents → Admin）
3. 監控 Network tab 確認無 timeout/cancel
4. 實施 token 預刷新機制
5. 考慮引入 React Query 統一管理 API 狀態

---

**報告結束**
生成時間：2025-10-03
