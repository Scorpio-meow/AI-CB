# 🔄 LLM API 遷移快速參考

## 修改摘要 (2025-10-08)

### ✅ 已完成
- [x] RAG 系統 (`contextual_rag.py`)
- [x] 工作流系統 (`workflow.py`)
- [x] 測試腳本創建
- [x] 遷移文檔撰寫

### 📝 核心變更

#### 1️⃣ API 端點
```diff
- /api/generate  (舊)
+ /api/chat      (新)
```

#### 2️⃣ 請求格式
```diff
- {"model": "...", "prompt": "單一字串"}
+ {"model": "...", "messages": [{"role": "...", "content": "..."}]}
```

#### 3️⃣ 響應格式
```diff
- {"response": "..."}
+ {"message": {"role": "assistant", "content": "..."}}
```

---

## 🎯 RAG 系統變更

### `build_context_prompt()`
```python
# 舊: 返回單一字串
def build_context_prompt(...) -> str:
    return "完整的 prompt 字串..."

# 新: 返回 user_prompt + history
def build_context_prompt(...) -> Tuple[str, List[Dict]]:
    return user_prompt, conversation_history
```

### `call_llm_api()`
```python
# 新增參數
async def call_llm_api(
    prompt: str,
    model_name: str = None,
    conversation_history: List[Dict[str, str]] = None  # 新增
) -> str:
    messages = [
        {"role": "system", "content": "系統提示"},
        *conversation_history,  # 最近3輪
        {"role": "user", "content": prompt}
    ]
```

---

## 🔄 Workflow 系統變更

### `execute_llm_call()`
```python
# 舊格式
full_prompt = f"System: {system}\n\n{task}"
payload = {"prompt": full_prompt}

# 新格式
messages = [
    {"role": "system", "content": system_prompt},
    *history_messages,  # 最近5輪
    {"role": "user", "content": task_description}
]
payload = {"messages": messages}
```

### 角色映射
```python
# Workflow 角色 → LLM 角色
"User"         → "user"
"編輯專家"      → "assistant" (帶 [編輯專家] 前綴)
"品質檢查"      → "assistant" (帶 [品質檢查] 前綴)
```

---

## 🧪 測試命令

### 快速測試
```bash
# 1. 確保後端運行在 port 8001
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001

# 2. 新終端運行測試
python test_chat_migration.py
```

### 手動測試 API
```bash
# 測試 RAG 單輪
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "什麼是特休?", "user_id": 1}'

# 測試 RAG 多輪 (使用返回的 conversation_id)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "那到期怎麼辦?", "user_id": 1, "conversation_id": 123}'
```

---

## 📊 對話歷史限制

| 系統 | 保留輪數 | 訊息數量 | 備註 |
|------|---------|---------|------|
| RAG | 3輪 | 6條 | user + assistant 各3條 |
| Workflow | 5輪 | 動態 | 依據 master_history |

---

## ⚠️ 重要注意

### 1. 向後兼容
- ✅ API 返回格式不變
- ✅ 記憶體結構不變
- ⚠️ 僅內部 LLM 調用格式改變

### 2. 依賴需求
- ✅ Ollama 標準版本已支援
- ⚠️ 自訂 LLM 服務需實現 `/api/chat`

### 3. 錯誤處理
- ✅ 保持原有異常處理邏輯
- ✅ Timeout/ConnectionError 不變

---

## 🚀 啟動服務

### 後端
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 前端
```bash
cd frontend
npm start
```

### 訪問地址
- 前端: http://localhost:3000
- 後端 API: http://localhost:8001
- API 文檔: http://localhost:8001/docs

---

## 📚 相關文檔

- 詳細遷移文檔: `docs/LLM_API_CHAT_MIGRATION.md`
- RAG 系統文檔: `docs/RAG_系統說明書.md`
- 安全指南: `docs/SECURITY_QUICKSTART.md`

---

## ✅ 驗證清單

運行測試後勾選:

- [ ] LLM API 直接調用正常
- [ ] RAG 單輪對話成功
- [ ] RAG 多輪對話有上下文
- [ ] Workflow 執行不報錯
- [ ] 日誌輸出正常
- [ ] 錯誤處理正確

---

**最後更新**: 2025-10-08  
**修改者**: GitHub Copilot  
**狀態**: ✅ 已完成,待測試
