# Agent 公開/私人功能說明

## 📋 功能概述

此功能允許用戶在創建 Agent 時選擇該 Agent 是**公開**還是**私人**：

- **公開 Agent**：所有用戶都可以看到和使用
- **私人 Agent**：僅創建者自己可以看到和使用

## 🎯 主要特性

### 1. 數據庫層級
- ✅ 添加 `is_public` 欄位（Boolean，默認 True）
- ✅ 添加 `created_by` 欄位（ForeignKey 指向 users 表）
- ✅ 支持用戶所有權追蹤

### 2. API 層級
- ✅ **JWT 認證保護**：所有 Agent API 端點需要登入
- ✅ **權限控制**：
  - 創建 Agent 時自動設置 `created_by` 為當前用戶
  - 只有創建者可以編輯/刪除自己的私人 Agent
  - 管理員可以編輯/刪除任何 Agent
- ✅ **智能過濾**：
  - 獲取 Agent 列表時自動返回：公開 Agent + 用戶自己的私人 Agent
  - 私人 Agent 只對創建者可見

### 3. 前端層級
- ✅ **創建/編輯表單**：
  - 添加公開/私人切換開關（Switch）
  - 視覺化指示（🌍 公開 / 🔒 私人）
  - 默認為公開
- ✅ **Agent 列表**：
  - 顯示可見性狀態標籤（Chip）
  - 綠色「公開」/ 灰色「私人」

## 🔧 技術實現

### 後端文件修改

1. **`app/models/custom_agent.py`**
   ```python
   is_public = Column(Boolean, default=True, nullable=False)
   created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
   ```

2. **`app/schemas/custom_agent.py`**
   ```python
   is_public: bool = Field(True, description="是否為公開 Agent")
   created_by: Optional[int] = None
   ```

3. **`app/crud/crud_custom_agent.py`**
   - `create_custom_agent()` - 接受 `user_id` 參數
   - `get_custom_agents()` - 支持 `user_id` 過濾

4. **`app/api/custom_agent.py`**
   - 所有端點添加 JWT 認證 (`get_current_user`)
   - 創建時自動設置 `created_by`
   - 更新/刪除時檢查權限

### 前端文件修改

1. **`frontend/src/pages/CustomAgents.js`**
   - 添加 `is_public` 到表單狀態
   - 添加 Switch 組件切換公開/私人
   - 表格顯示可見性 Chip

### 數據庫遷移

**腳本**: `backend/scripts/migrate_add_agent_visibility.py`

運行方式：
```bash
cd backend
python scripts/migrate_add_agent_visibility.py
```

## 📖 使用指南

### 創建公開 Agent

1. 進入「Agent 管理」頁面
2. 點擊「新增 Agent」
3. 填寫 Agent 信息
4. 確保「公開 Agent」開關為**開啟**（默認）
5. 點擊「儲存」

**效果**：所有用戶都可以看到和使用此 Agent

### 創建私人 Agent

1. 進入「Agent 管理」頁面
2. 點擊「新增 Agent」
3. 填寫 Agent 信息
4. **關閉**「公開 Agent」開關（變為 🔒 私人）
5. 點擊「儲存」

**效果**：只有您自己可以看到和使用此 Agent

### 編輯 Agent 可見性

1. 在 Agent 列表中點擊「編輯」按鈕
2. 切換「公開 Agent」開關
3. 點擊「儲存」

**注意**：只能編輯自己創建的 Agent（或管理員權限）

### 刪除 Agent

- **普通用戶**：只能刪除自己創建的 Agent
- **管理員**：可以刪除任何 Agent

## 🔒 權限矩陣

| 操作 | 公開 Agent | 自己的私人 Agent | 他人的私人 Agent |
|------|-----------|----------------|----------------|
| **查看** | ✅ 所有人 | ✅ 創建者 | ❌ 不可見 |
| **使用** | ✅ 所有人 | ✅ 創建者 | ❌ 不可用 |
| **編輯** | ✅ 創建者<br>✅ 管理員 | ✅ 創建者<br>✅ 管理員 | ❌ 拒絕訪問 |
| **刪除** | ✅ 創建者<br>✅ 管理員 | ✅ 創建者<br>✅ 管理員 | ❌ 拒絕訪問 |

## 🧪 測試場景

### 場景 1：普通用戶創建私人 Agent
1. 登入為普通用戶 A
2. 創建私人 Agent "我的助手"
3. 登出並以用戶 B 登入
4. **預期**：用戶 B 看不到 "我的助手"

### 場景 2：將公開 Agent 改為私人
1. 用戶 A 創建公開 Agent "公共助手"
2. 其他用戶都可以看到
3. 用戶 A 將其改為私人
4. **預期**：其他用戶不再看到此 Agent

### 場景 3：權限拒絕
1. 用戶 A 創建私人 Agent
2. 用戶 B 嘗試編輯該 Agent
3. **預期**：返回 403 錯誤 "Access denied"

## 🚀 部署注意事項

1. **遷移數據庫**：
   ```bash
   cd backend
   python scripts/migrate_add_agent_visibility.py
   ```

2. **重啟服務**：
   - 停止後端服務
   - 重新啟動後端：`python -m uvicorn main:app --reload`
   - 前端會自動重新加載

3. **驗證遷移**：
   - 檢查現有 Agent 都變為公開（is_public=True）
   - 新創建的 Agent 有正確的 created_by 值

## 📝 API 端點變更

所有 `/api/custom_agents/*` 端點現在需要 JWT 認證：

```
GET    /api/custom_agents/all_with_details  - 獲取可見的所有 Agent（公開 + 自己的私人）
POST   /api/custom_agents/                  - 創建 Agent（自動設置 created_by）
GET    /api/custom_agents/                  - 獲取 Agent 列表（帶過濾）
GET    /api/custom_agents/{id}              - 獲取單個 Agent（權限檢查）
PUT    /api/custom_agents/{id}              - 更新 Agent（僅創建者/管理員）
DELETE /api/custom_agents/{id}              - 刪除 Agent（僅創建者/管理員）
```

## 🐛 已知限制

1. **向後兼容**：現有 Agent 的 `created_by` 為 NULL（遷移時無法確定創建者）
2. **管理員特權**：管理員可以管理所有 Agent，包括他人的私人 Agent

## 🔮 未來改進

- [ ] Agent 共享功能（與特定用戶共享私人 Agent）
- [ ] Agent 分組/標籤系統
- [ ] Agent 使用統計
- [ ] Agent 版本控制

---

**文檔版本**: 1.0  
**最後更新**: 2025年10月8日  
**作者**: AI-CB 開發團隊
