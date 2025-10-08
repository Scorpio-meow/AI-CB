# Token 刷新錯誤 - 快速修復指南

## 🐛 問題
如果您看到以下錯誤：
```
POST /api/auth/refresh 401 (Unauthorized)
[Token] 靜默刷新失敗
GET /api/chat/conversations/8 403 (Forbidden)
```

## ✅ 解決方案

### 方法 1: 清除瀏覽器數據（推薦）

1. **打開開發者工具**: 按 `F12`
2. **打開控制台**: 點擊 "Console" 標籤
3. **清除 Storage**: 
   ```javascript
   localStorage.clear();
   console.log('✅ 已清除 localStorage');
   ```
4. **刷新頁面**: 按 `F5` 或 `Ctrl+R`
5. **重新登錄**: 訪問 `/login` 頁面

### 方法 2: 手動清除（如果方法1無效）

1. **打開 Application 標籤**（開發者工具）
2. **展開 Local Storage** → 點擊您的網站
3. **刪除以下項目**:
   - `access_token`
   - `user_info`
   - `cached_tags`
   - `cached_tags_time`
4. **展開 Cookies** → 點擊您的網站
5. **刪除以下 Cookie**:
   - `refresh_token`（如果存在）
6. **刷新頁面並重新登錄**

### 方法 3: 使用快捷腳本

**在控制台中執行**:
```javascript
// 清除所有認證數據
localStorage.removeItem('access_token');
localStorage.removeItem('user_info');
console.log('✅ 已清除認證信息');

// 跳轉到登錄頁
window.location.href = '/login';
```

---

## 🔍 為什麼會出現這個問題？

### 原因
- 您之前登錄過，`access_token` 存儲在瀏覽器中
- `access_token` 即將過期，系統嘗試自動刷新
- 但 `refresh_token` Cookie 已經過期
- 舊版本代碼沒有正確處理這種情況

### 已修復
- ✅ 現在系統會自動清除過期的 token
- ✅ 自動跳轉到登錄頁面
- ✅ 不會再出現 403 錯誤

---

## 📝 後續使用建議

### 1. 正常登錄流程
```
訪問 /login → 輸入賬號密碼 → 登錄成功 → 開始使用
```

### 2. Token 自動刷新
- `access_token` 有效期: 30 分鐘
- 系統會在到期前 5 分鐘自動刷新
- **您無需手動操作**

### 3. 長時間未使用
- 如果超過 7 天未使用，需要重新登錄
- 這是正常的安全機制

---

## ⚠️ 常見問題

### Q: 清除後還是有問題？
**A**: 嘗試硬刷新：`Ctrl + Shift + R`（Windows）或 `Cmd + Shift + R`（Mac）

### Q: 為什麼要清除 localStorage？
**A**: 舊的 `access_token` 已過期但未被清除，導致系統誤判認證狀態。

### Q: 會丟失數據嗎？
**A**: 不會。對話記錄等數據存儲在服務器，只是需要重新登錄。

### Q: 以後還會遇到這個問題嗎？
**A**: 不會。修復後的代碼會自動處理這種情況。

---

## 🚀 立即修復

**複製並在控制台執行**:
```javascript
// 一鍵清除並跳轉登錄
localStorage.clear();
window.location.href = '/login';
```

---

**更新時間**: 2025年10月8日  
**狀態**: ✅ 已修復  
**建議**: 清除緩存後重新登錄
