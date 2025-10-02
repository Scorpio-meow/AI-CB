# 🚀 快速啟動指南 - 安全版本

## ⚡ 5 分鐘快速啟動

### 1️⃣ 設定環境變數 (2 分鐘)

```powershell
# 複製範本
Copy-Item backend\.env.example backend\.env

# 生成 API Key
python -c "import secrets; print(secrets.token_urlsafe(32))"
# 將輸出的值設定為 backend\.env 中的 ADMIN_API_KEY
```

### 2️⃣ 安裝套件 (2 分鐘)

```powershell
# 啟動虛擬環境
.\CBvenv\Scripts\Activate.ps1

# 安裝更新的套件
cd backend
pip install -r requirements.txt
```

### 3️⃣ 啟動服務 (1 分鐘)

**終端 1 - 後端**:
```powershell
cd C:\Users\MITAC\Documents\AI-CB\backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

**終端 2 - 前端**:
```powershell
cd C:\Users\MITAC\Documents\AI-CB\frontend
npm start
```

---

## 🔑 重要變更

### ⚠️ 管理員 API 現在需要認證！

所有 `/api/admin/*` 端點現在都需要 API Key：

```javascript
// 在請求中添加 Header
headers: {
  'X-API-Key': 'your_admin_api_key_from_env_file'
}
```

### 📁 檔案上傳限制變更

- ✅ 最大檔案大小: **10MB** (之前是 50MB)
- ✅ 單次最多上傳: **10個檔案**
- ✅ 允許的格式: `.txt`, `.pdf`, `.docx`
- ✅ 新增安全驗證: 檔案頭部檢查

### 🛡️ 新增的安全功能

1. **速率限制**: 每分鐘 60 次請求
2. **安全標頭**: 自動添加安全 HTTP Headers
3. **安全日誌**: 所有重要操作都會被記錄到 `logs/security.log`
4. **檔案驗證**: 防止惡意檔案上傳

---

## 📝 臨時 API Key

如果 `.env` 中沒有設定 `ADMIN_API_KEY`，系統會生成一個臨時 Key。

**在後端啟動時查看控制台輸出**:
```
⚠️  WARNING: ADMIN_API_KEY not set in environment!
⚠️  Using temporary API key: Abc123XYZ_temporary_key_here
⚠️  Please set ADMIN_API_KEY in your .env file!
```

**立即將此 Key 保存到 `backend/.env`**:
```env
ADMIN_API_KEY=Abc123XYZ_temporary_key_here
```

---

## ✅ 驗證修復是否成功

### 測試 1: 一般 API (不需認證)
```powershell
curl http://localhost:8001/health
# 預期: {"status":"healthy"}
```

### 測試 2: 受保護的管理員 API
```powershell
# 沒有 API Key - 應該失敗
curl http://localhost:8001/api/admin/users
# 預期: 401 Unauthorized

# 有 API Key - 應該成功
curl http://localhost:8001/api/admin/users -H "X-API-Key: your_key_here"
# 預期: 返回用戶列表
```

### 測試 3: 檔案上傳安全性
在前端上傳檔案，檢查 `logs/security.log` 確認事件被記錄。

---

## 🐛 常見問題

### Q: 後端啟動失敗，提示 "MODEL_NAME is required"

**A**: 確保 `backend/.env` 中設定了以下變數:
```env
MODEL_NAME=gpt-oss:20b
LLM_API_BASE=https://your-llm-endpoint.com
```

### Q: 管理員功能無法使用

**A**: 檢查是否在請求中添加了 `X-API-Key` header。

### Q: 檔案上傳失敗

**A**: 
1. 檢查檔案大小 (<10MB)
2. 檢查檔案格式 (.txt/.pdf/.docx)
3. 查看 `logs/security.log`

---

## 📚 完整文檔

- 📋 **安全審計報告**: `security-fixes.md`
- 🔧 **詳細實施指南**: `SECURITY-IMPLEMENTATION.md`
- 📖 **專案說明**: `README.md`

---

## 🎉 完成！

您的應用程式現在已經具備了基本的安全防護。

**下一步**: 查看 `SECURITY-IMPLEMENTATION.md` 了解更多安全建議和進階配置。
