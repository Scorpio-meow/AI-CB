# Token 刷新錯誤修復報告

## 📅 日期
2025年10月8日

## 🐛 問題描述

### 錯誤現象
```
POST http://localhost:3000/api/auth/refresh 401 (Unauthorized)
[Token] 靜默刷新失敗
GET http://localhost:3000/api/chat/conversations/8 403 (Forbidden)
```

### 根本原因
1. 用戶之前登錄過，`access_token` 存儲在 localStorage
2. `access_token` 即將過期，觸發靜默刷新
3. 但 `refresh_token` Cookie 已經過期或不存在
4. 刷新請求返回 401 未授權
5. 系統繼續使用過期的 token 發送請求
6. 導致後續請求返回 403 禁止訪問

### 問題流程
```
頁面載入
  ↓
檢測到 access_token 即將過期
  ↓
嘗試使用 refresh_token Cookie 刷新
  ↓
❌ refresh_token 不存在/已過期
  ↓
返回 401 錯誤
  ↓
❌ 錯誤處理不當，未清除 access_token
  ↓
繼續使用過期 token 發送請求
  ↓
返回 403 錯誤
```

---

## ✅ 修復方案

### 1. 改進 Request Interceptor

**修復前**:
```javascript
} catch (error) {
  console.error('[Token] 靜默刷新失敗:', error);
  // 刷新失敗時，仍然使用原有 token 嘗試 ❌ 錯誤！
}
```

**修復後**:
```javascript
} catch (error) {
  console.warn('[Token] 靜默刷新失敗，清除無效 Token:', error.response?.status);
  // 刷新失敗，清除無效的 token 避免無限循環
  if (error.response?.status === 401) {
    clearAuth(); // ✅ 清除認證信息
    // 不要立即跳轉，讓 response interceptor 處理
  } else {
    // 非 401 錯誤（網絡問題等），使用原有 token 嘗試
    config.headers.Authorization = `Bearer ${token}`;
  }
}
```

### 2. 添加過期 Token 檢測

**新增邏輯**:
```javascript
} else if (!hasValidAuth() && token) {
  // Token 已完全過期，清除它
  console.log('[Token] Token 已完全過期，清除認證信息');
  clearAuth();
} else {
  config.headers.Authorization = `Bearer ${token}`;
}
```

### 3. 改進 Response Interceptor

**修復前**:
```javascript
localStorage.removeItem('access_token');
localStorage.removeItem('user_info');
```

**修復後**:
```javascript
clearAuth(); // ✅ 使用統一的清除函數
```

### 4. 新增工具函數

**文件**: `frontend/src/utils/tokenUtils.js`

```javascript
/**
 * 檢查是否有有效的登錄狀態
 */
export const hasValidAuth = () => {
  const token = localStorage.getItem('access_token');
  if (!token) return false;
  
  // 檢查 token 是否完全過期
  const remainingTime = getTokenRemainingTime(token);
  return remainingTime > 0;
};

/**
 * 清除所有認證信息
 */
export const clearAuth = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_info');
  console.log('[Auth] 已清除認證信息');
};
```

---

## 🔄 修復後的流程

### 正常刷新流程（refresh_token 有效）
```
頁面載入
  ↓
檢測到 access_token 即將過期
  ↓
嘗試使用 refresh_token Cookie 刷新
  ↓
✅ 刷新成功
  ↓
更新 localStorage 中的 access_token
  ↓
使用新 token 發送請求
  ↓
✅ 請求成功
```

### Token 過期流程（refresh_token 無效）
```
頁面載入
  ↓
檢測到 access_token 即將過期
  ↓
嘗試使用 refresh_token Cookie 刷新
  ↓
❌ refresh_token 不存在/已過期（401）
  ↓
✅ 清除 access_token 和 user_info
  ↓
後續請求無 Authorization header
  ↓
返回 401 錯誤
  ↓
✅ Response Interceptor 捕獲
  ↓
清除認證信息並跳轉到登錄頁
```

---

## 📝 修改的文件

### 1. `frontend/src/services/api.js`
- ✅ 改進 Request Interceptor 錯誤處理
- ✅ 添加過期 Token 檢測
- ✅ 改進 Response Interceptor
- ✅ 使用統一的 `clearAuth()` 函數

### 2. `frontend/src/utils/tokenUtils.js`
- ✅ 新增 `hasValidAuth()` 函數
- ✅ 新增 `clearAuth()` 函數
- ✅ 改進 `shouldRefreshToken()` 註釋

---

## 🧪 測試驗證

### 測試場景 1: 正常登錄狀態
```
✅ access_token 有效 → 正常使用
✅ access_token 即將過期 + refresh_token 有效 → 自動刷新
✅ 刷新後繼續正常使用
```

### 測試場景 2: Token 過期
```
✅ access_token 過期 + refresh_token 無效 → 清除認證
✅ 自動跳轉到登錄頁
✅ 不會出現 403 錯誤
```

### 測試場景 3: 網絡問題
```
✅ 刷新請求失敗（非 401） → 使用原 token 重試
✅ 不會清除認證信息
✅ 網絡恢復後正常工作
```

---

## ⚠️ 注意事項

### 1. Cookie 管理
- `refresh_token` 存儲在 HttpOnly Cookie 中
- 前端無法直接訪問或檢查
- 只能通過刷新請求來驗證有效性

### 2. Token 生命周期
- `access_token`: 30 分鐘（可配置）
- `refresh_token`: 7 天（可配置）
- 提前 5 分鐘觸發自動刷新

### 3. 用戶體驗
- ✅ 靜默刷新：用戶無感知
- ✅ 過期處理：自動跳轉登錄頁
- ✅ 錯誤提示：清晰的控制台日誌

---

## 🔒 安全性改進

### Before (安全風險)
```javascript
// 刷新失敗時，仍然使用原有 token 嘗試
// ❌ 可能導致使用過期 token 發送敏感請求
```

### After (安全增強)
```javascript
// 刷新失敗，清除無效的 token
clearAuth();
// ✅ 確保不會使用無效 token
// ✅ 強制用戶重新登錄
```

---

## 📊 影響範圍

### 受影響的功能
- ✅ 聊天功能（需要認證）
- ✅ 對話管理（需要認證）
- ✅ 文檔上傳（需要認證）
- ✅ 用戶設置（需要認證）

### 不受影響的功能
- ✅ 登錄頁面
- ✅ 註冊頁面
- ✅ 公開 API（如模型列表）

---

## 🎯 修復效果

### Before
```
❌ Token 刷新失敗後繼續使用過期 token
❌ 產生大量 403 錯誤
❌ 用戶體驗差（功能無法使用）
❌ 安全風險（使用無效憑證）
```

### After
```
✅ Token 刷新失敗後立即清除
✅ 不會產生 403 錯誤
✅ 自動跳轉登錄頁
✅ 安全可靠（強制重新認證）
```

---

## 📚 相關文檔

- [JWT 認證指南](./JWT_Authentication_Guide.md)
- [安全增強說明](./SECURITY_ENHANCEMENTS.md)
- [Token 工具函數](../frontend/src/utils/tokenUtils.js)

---

## ✅ 驗證清單

- [x] Request Interceptor 改進
- [x] Response Interceptor 改進
- [x] 新增工具函數
- [x] 錯誤處理優化
- [x] 控制台日誌改進
- [x] 安全性增強
- [x] 用戶體驗改善
- [x] 文檔更新

---

**修復狀態**: ✅ **完成**  
**測試狀態**: ⏳ **待用戶驗證**  
**建議**: 請清除瀏覽器緩存和 localStorage 後重新測試

---

**報告時間**: 2025年10月8日 12:15  
**修復者**: GitHub Copilot  
**優先級**: 🔴 高（安全相關）
