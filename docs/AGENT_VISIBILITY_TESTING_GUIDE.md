# Agent 公開/私人功能測試指南

## 🧪 快速測試步驟

### 前置條件
- ✅ 後端運行在 http://localhost:8001
- ✅ 前端運行在 http://localhost:3000
- ✅ 數據庫遷移已完成
- ✅ 至少有 2 個測試用戶帳號

---

## 📋 測試用例

### 測試 1: 創建公開 Agent

**步驟**:
1. 訪問 http://localhost:3000
2. 登入為用戶 A
3. 點擊左側菜單「Agent 管理」
4. 點擊右上角「新增 Agent」按鈕
5. 填寫表單：
   - 名稱: `公共助手`
   - 角色: `Public Assistant`
   - 專業領域: `一般性協助`
   - 系統提示: `你是一個公共助手`
   - 工具: `File, Search`
   - **確保「公開 Agent」開關為開啟** ✅
6. 點擊「儲存」

**預期結果**:
- ✅ Agent 創建成功
- ✅ 列表中顯示綠色「公開」標籤
- ✅ 圖標顯示為 🌍

---

### 測試 2: 創建私人 Agent

**步驟**:
1. 繼續以用戶 A 登入
2. 點擊「新增 Agent」
3. 填寫表單：
   - 名稱: `我的私人助手`
   - 角色: `Private Assistant`
   - 專業領域: `私人事務處理`
   - 系統提示: `你是我的私人助手`
   - 工具: `File`
   - **關閉「公開 Agent」開關** ❌ → 變為 🔒 私人
4. 點擊「儲存」

**預期結果**:
- ✅ Agent 創建成功
- ✅ 列表中顯示灰色「私人」標籤
- ✅ 圖標顯示為 🔒

---

### 測試 3: 跨用戶可見性

**步驟**:
1. 登出用戶 A
2. 登入為用戶 B
3. 訪問「Agent 管理」頁面
4. 查看 Agent 列表

**預期結果**:
- ✅ 看到「公共助手」（用戶 A 的公開 Agent）
- ❌ **看不到**「我的私人助手」（用戶 A 的私人 Agent）

---

### 測試 4: 編輯權限控制

**步驟**:
1. 繼續以用戶 B 登入
2. 嘗試編輯「公共助手」（用戶 A 創建的）
3. 點擊「編輯」按鈕
4. 修改任何內容並點擊「儲存」

**預期結果**:
- ❌ 應顯示錯誤: `"Access denied: You can only update your own agents"`
- ❌ 編輯失敗（403 錯誤）

---

### 測試 5: 刪除權限控制

**步驟**:
1. 繼續以用戶 B 登入
2. 嘗試刪除「公共助手」
3. 點擊「刪除」按鈕
4. 確認刪除

**預期結果**:
- ❌ 應顯示錯誤: `"Access denied: You can only delete your own agents"`
- ❌ 刪除失敗（403 錯誤）

---

### 測試 6: 修改可見性

**步驟**:
1. 登出用戶 B
2. 重新登入為用戶 A
3. 編輯「公共助手」
4. **關閉「公開 Agent」開關** → 變為私人
5. 點擊「儲存」
6. 登出並以用戶 B 登入
7. 查看 Agent 列表

**預期結果**:
- ✅ 用戶 A 成功將 Agent 改為私人
- ❌ 用戶 B 現在看不到「公共助手」了

---

### 測試 7: 管理員特權

**步驟**:
1. 登入為管理員帳號
2. 訪問「Agent 管理」頁面
3. 查看所有 Agent
4. 嘗試編輯任何用戶的 Agent
5. 嘗試刪除任何用戶的 Agent

**預期結果**:
- ✅ 管理員可以看到所有 Agent（公開 + 所有私人）
- ✅ 管理員可以編輯任何 Agent
- ✅ 管理員可以刪除任何 Agent

---

## 🎨 UI 驗證清單

### 表單檢查
- [ ] 新增/編輯對話框包含公開/私人開關
- [ ] 開關顯示清晰的圖標（🌍 / 🔒）
- [ ] 開關說明文字正確
- [ ] 默認狀態為「公開」

### 列表檢查
- [ ] 表格包含「可見性」列
- [ ] 公開 Agent 顯示綠色「公開」Chip
- [ ] 私人 Agent 顯示灰色「私人」Chip
- [ ] Chip 包含對應圖標

### 錯誤處理
- [ ] 權限錯誤顯示友好的錯誤消息
- [ ] 不會出現未處理的異常
- [ ] 控制台無錯誤輸出

---

## 🐛 常見問題排查

### 問題 1: 看不到新增的欄位

**可能原因**: 數據庫遷移未執行

**解決方法**:
```bash
cd backend
python scripts/migrate_add_agent_visibility.py
```

### 問題 2: 所有 API 返回 401

**可能原因**: JWT Token 過期或無效

**解決方法**:
1. 登出並重新登入
2. 清除瀏覽器緩存
3. 檢查後端是否正常運行

### 問題 3: 前端顯示異常

**可能原因**: 前端未重新編譯

**解決方法**:
```bash
cd frontend
npm start
```

### 問題 4: 創建 Agent 時沒有 created_by

**可能原因**: 未傳遞 user_id

**解決方法**: 檢查 API 端點是否正確使用 `get_current_active_user`

---

## 📊 測試結果記錄

### 測試記錄表

| 測試項目 | 狀態 | 備註 |
|---------|------|------|
| 創建公開 Agent | ⬜ | |
| 創建私人 Agent | ⬜ | |
| 跨用戶可見性 | ⬜ | |
| 編輯權限控制 | ⬜ | |
| 刪除權限控制 | ⬜ | |
| 修改可見性 | ⬜ | |
| 管理員特權 | ⬜ | |

填寫說明:
- ✅ 通過
- ❌ 失敗
- ⚠️ 部分通過
- ⬜ 未測試

---

## 🔍 API 測試（可選）

### 使用 curl 測試

#### 1. 登入獲取 Token
```bash
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password"}'
```

#### 2. 創建公開 Agent
```bash
curl -X POST http://localhost:8001/api/custom_agents/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "測試 Agent",
    "role": "Test Agent",
    "expertise": "測試專用",
    "prompt": "你是測試助手",
    "tools": ["File"],
    "is_public": true
  }'
```

#### 3. 創建私人 Agent
```bash
curl -X POST http://localhost:8001/api/custom_agents/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "私人 Agent",
    "role": "Private Agent",
    "expertise": "私人專用",
    "prompt": "你是私人助手",
    "tools": ["File"],
    "is_public": false
  }'
```

#### 4. 獲取 Agent 列表
```bash
curl -X GET http://localhost:8001/api/custom_agents/all_with_details \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## ✅ 測試完成確認

所有測試通過後，請確認：

- [ ] 所有 7 個測試用例都通過
- [ ] UI 顯示正常
- [ ] 無控制台錯誤
- [ ] 權限控制正確
- [ ] 跨用戶可見性正確
- [ ] 管理員特權正常

**測試完成日期**: _______________  
**測試人員**: _______________  
**測試結果**: _______________

---

**文檔版本**: 1.0  
**最後更新**: 2025年10月8日  
**狀態**: Ready for Testing
