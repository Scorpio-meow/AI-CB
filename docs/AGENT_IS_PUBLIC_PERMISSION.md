# Agent 公開/私人狀態修改權限

## 🔒 權限規則

### is_public 欄位特殊限制

**只有 Agent 的創建者可以修改 `is_public` 狀態**

這是一個特殊的權限規則，確保即使是管理員也無法改變 Agent 的公開/私人狀態。

---

## 📋 詳細權限表

| 操作 | 創建者 | 管理員 | 其他用戶 |
|------|--------|--------|----------|
| **修改 is_public** | ✅ 允許 | ❌ 禁止 | ❌ 禁止 |
| **修改其他欄位** (name, role, system_prompt 等) | ✅ 允許 | ✅ 允許 | ❌ 禁止 |
| **刪除 Agent** | ✅ 允許 | ✅ 允許 | ❌ 禁止 |
| **查看公開 Agent** | ✅ 允許 | ✅ 允許 | ✅ 允許 |
| **查看私人 Agent** | ✅ 允許（自己的） | ❌ 禁止 | ❌ 禁止 |

---

## 💻 實現細節

### 後端檢查邏輯 (`backend/app/api/custom_agent.py`)

```python
@router.put("/{agent_id}", response_model=CustomAgent)
def update_custom_agent(
    agent_id: int,
    agent: CustomAgentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    db_agent = crud_custom_agent.get_custom_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    user_id = current_user.get("user_id")
    is_admin = current_user.get("is_admin", False)
    
    # 🔒 特殊規則：只有創建者可以修改 is_public 狀態
    if agent.is_public is not None and agent.is_public != db_agent.is_public:
        if db_agent.created_by != user_id:
            raise HTTPException(
                status_code=403, 
                detail="Access denied: Only the creator can change the public/private status"
            )
    
    # 一般更新權限：創建者或管理員
    if db_agent.created_by != user_id and not is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: You can only update your own agents"
        )
    
    db_agent = crud_custom_agent.update_custom_agent(db, agent_id=agent_id, agent_update=agent)
    return db_agent
```

### 檢查流程

1. **檢查 Agent 是否存在**
   - 如果不存在 → 返回 404

2. **檢查 is_public 修改權限** (優先級最高)
   - 如果請求要修改 `is_public`
   - 且請求者不是創建者
   - → 返回 403，錯誤訊息：`"Only the creator can change the public/private status"`

3. **檢查一般更新權限**
   - 如果請求者既不是創建者也不是管理員
   - → 返回 403，錯誤訊息：`"You can only update your own agents"`

4. **執行更新**
   - 所有權限檢查通過 → 執行更新

---

## 🧪 測試用例

### 測試腳本

使用以下腳本驗證權限規則：

```bash
cd backend
python scripts/test_is_public_permission.py
```

### 測試場景

#### ✅ 場景 1: 創建者修改 is_public
```python
# 創建者創建公開 Agent
POST /api/custom_agents/
{
  "name": "測試Agent",
  "is_public": true
}

# 創建者修改為私人
PUT /api/custom_agents/{id}
{
  "is_public": false
}
# 預期結果: ✅ 成功 (200)
```

#### ❌ 場景 2: 管理員修改他人的 is_public
```python
# 管理員嘗試修改
PUT /api/custom_agents/{id}
{
  "is_public": true
}
# 預期結果: ❌ 失敗 (403)
# 錯誤訊息: "Only the creator can change the public/private status"
```

#### ✅ 場景 3: 管理員修改其他欄位
```python
# 管理員修改名稱
PUT /api/custom_agents/{id}
{
  "name": "新名稱"
}
# 預期結果: ✅ 成功 (200)
```

#### ❌ 場景 4: 其他用戶修改任何欄位
```python
# 其他用戶嘗試修改
PUT /api/custom_agents/{id}
{
  "name": "新名稱"
}
# 預期結果: ❌ 失敗 (403)
# 錯誤訊息: "You can only update your own agents"
```

---

## 🎯 前端處理建議

### 禁用 is_public 切換開關

根據當前用戶是否為創建者，動態禁用切換開關：

```javascript
// CustomAgents.js
<FormControlLabel
  control={
    <Switch
      checked={formData.is_public}
      onChange={(e) => setFormData({...formData, is_public: e.target.checked})}
      disabled={editingAgent && editingAgent.created_by !== currentUser.user_id}
      //        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      //        只有創建者可以切換
    />
  }
  label={formData.is_public ? "公開 Agent" : "私人 Agent"}
/>
```

### 顯示提示訊息

當管理員嘗試修改時，顯示友好提示：

```javascript
{editingAgent && editingAgent.created_by !== currentUser.user_id && (
  <Alert severity="info">
    注意：您可以修改此 Agent 的其他欄位，但只有創建者可以修改公開/私人狀態
  </Alert>
)}
```

---

## 🔍 錯誤處理

### 後端錯誤響應

```json
{
  "detail": "Access denied: Only the creator can change the public/private status"
}
```

### 前端錯誤處理

```javascript
try {
  await updateCustomAgent(editingAgent.id, formData);
} catch (error) {
  if (error.response?.status === 403) {
    if (error.response.data.detail.includes("public/private status")) {
      setError("只有創建者可以修改公開/私人狀態");
    } else {
      setError("您沒有權限修改此 Agent");
    }
  }
}
```

---

## 📊 權限檢查順序

```
請求更新 Agent
    |
    ├─> 檢查 Agent 是否存在
    |       └─> 不存在 → 404
    |
    ├─> 檢查是否嘗試修改 is_public
    |   |
    |   ├─> 是，且不是創建者
    |   |       └─> 403 (Only creator can change public/private status)
    |   |
    |   └─> 否，或是創建者
    |           └─> 繼續
    |
    ├─> 檢查一般更新權限
    |   |
    |   ├─> 不是創建者且不是管理員
    |   |       └─> 403 (You can only update your own agents)
    |   |
    |   └─> 是創建者或管理員
    |           └─> 繼續
    |
    └─> 執行更新
            └─> 200 (成功)
```

---

## 🎉 優勢

### 1. 數據隱私保護
- 創建者完全控制 Agent 的可見性
- 防止管理員意外或惡意公開私人 Agent

### 2. 責任明確
- 只有創建者對 Agent 的可見性負責
- 避免權限糾紛

### 3. 靈活管理
- 管理員仍可修改其他欄位（修正錯誤、優化提示詞等）
- 不影響正常管理工作

### 4. 審計追蹤
- 可見性變更只能由創建者執行
- 易於追蹤和審計

---

## 📝 總結

**核心原則**: `is_public` 是 Agent 創建者的**專屬權限**

- ✅ 創建者：完全控制
- ⚠️ 管理員：可管理其他欄位，但不能改變可見性
- ❌ 其他用戶：無權修改

這種設計確保了 Agent 隱私設置的穩定性和可預測性，同時保持了管理靈活性。
