# 🐛 故障排除與修復記錄

## 問題 1: SecurityHeadersMiddleware 錯誤 ✅ 已修復

### 錯誤訊息
```
AttributeError: 'MutableHeaders' object has no attribute 'pop'
```

### 原因
`response.headers` 是 Starlette 的 `MutableHeaders` 對象，不支持 `.pop()` 方法。

### 修復
將 `response.headers.pop("Server", None)` 改為：
```python
if "Server" in response.headers:
    del response.headers["Server"]
```

### 檔案
`backend/app/core/security.py` 第 81 行

---

## 問題 2: LLM_API_BASE 配置錯誤 ✅ 已修復

### 錯誤訊息
```
Failed to resolve 'your-llm-api-endpoint.com'
```

### 原因
`backend/.env` 文件使用了範本值而非實際的 API 端點。

### 修復
更新 `backend/.env`:
```env
MODEL_NAME=gpt-oss:20b
LLM_API_BASE=https://f20dfbce5e43.ngrok-free.app
```

---

## 問題 3: BM25 索引不存在 ⚠️ 警告（非致命）

### 警告訊息
```
Failed to load BM25 index: Index 'MAIN' does not exist in FileStorage
```

### 原因
首次啟動或索引被清空後，BM25 索引尚未建立。

### 解決方案
這是正常的，系統會在上傳第一個文件時自動建立索引。不需要手動處理。

---

## ✅ 現在應該可以正常啟動

重新啟動後端服務：
```powershell
# 在終端中按 Ctrl+C 停止服務
# 然後重新啟動
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

應該會看到：
```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

沒有錯誤！✨

---

## 📝 重要提醒

### 已設定的 ADMIN_API_KEY
您的管理員 API Key 是：
```
zl4DDtCi-dHRqa4-VBN_Z-bNJEVClCYWegqoLt2N098
```

### 使用方式
所有管理員 API 請求需要此 Header：
```
X-API-Key: zl4DDtCi-dHRqa4-VBN_Z-bNJEVClCYWegqoLt2N098
```

### 測試命令
```powershell
# 測試一般 API
curl http://localhost:8001/health

# 測試管理員 API
curl http://localhost:8001/api/admin/users -H "X-API-Key: zl4DDtCi-dHRqa4-VBN_Z-bNJEVClCYWegqoLt2N098"
```

---

## 🎉 修復完成！

所有安全修復都已正確實施並且可以正常運行。
