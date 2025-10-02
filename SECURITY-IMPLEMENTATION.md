# 🔧 安全修復實施指南

## 📋 修復摘要

所有主要的安全問題已經修復完成！以下是詳細的修復內容和後續步驟。

---

## ✅ 已完成的修復

### 1. 環境變數與敏感資訊保護 ✅

**修復內容**:
- ✅ 更新 `.gitignore` 確保 `.env` 檔案永不被提交
- ✅ 創建 `.env.example` 範本檔案供參考
- ✅ 添加全面的 `.gitignore` 規則（包括數據庫、上傳檔案、日誌等）

**操作步驟**:
1. **重要**: 從 Git 歷史中移除已提交的 `.env` 檔案：
```powershell
# 如果 .env 已經被提交到 Git，請執行以下命令清理歷史
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch backend/.env frontend/.env" --prune-empty --tag-name-filter cat -- --all
git push origin --force --all
```

2. 複製範本並設定環境變數：
```powershell
# 複製範本檔案
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env

# 編輯 backend\.env 並設定必要的值
```

3. 生成安全的 API Key：
```powershell
# 在 Python 環境中執行
python -c "import secrets; print('ADMIN_API_KEY=' + secrets.token_urlsafe(32))"
```

將生成的 API Key 添加到 `backend/.env` 檔案中。

---

### 2. 管理員 API 認證保護 ✅

**修復內容**:
- ✅ 創建 `app/core/security.py` 模組
- ✅ 實施 API Key 認證機制
- ✅ 保護所有管理員端點（`/api/admin/*`）
- ✅ 添加安全標頭中間件
- ✅ 實施速率限制防止 API 濫用

**使用方式**:
所有管理員 API 請求現在都需要在 Header 中包含 API Key：

```javascript
// 前端範例
const response = await fetch('http://localhost:8001/api/admin/users', {
  headers: {
    'X-API-Key': 'your_admin_api_key_here'
  }
});
```

```python
# Python 範例
import requests

headers = {'X-API-Key': 'your_admin_api_key_here'}
response = requests.get('http://localhost:8001/api/admin/users', headers=headers)
```

---

### 3. 檔案上傳安全強化 ✅

**修復內容**:
- ✅ 添加檔案頭部驗證（Magic Number 檢查）
- ✅ 實施檔名清理和驗證（防止路徑遍歷攻擊）
- ✅ 降低檔案大小限制從 50MB 到 10MB
- ✅ 添加單次上傳檔案數量限制（最多 10 個）
- ✅ 實施檔案雜湊計算（用於重複檢測）
- ✅ 加強錯誤處理和安全日誌記錄

**安全措施**:
- 白名單副檔名驗證 (`.txt`, `.pdf`, `.docx`)
- 檔案頭部與 MIME 類型交叉驗證
- 防止路徑遍歷攻擊的檔名清理
- 檔案大小限制和流式處理

---

### 4. CORS 設定優化 ✅

**修復內容**:
- ✅ 移除生產環境的 ALLOWED_ORIGIN_REGEX
- ✅ 明確定義允許的來源列表
- ✅ 添加環境檢測邏輯

**設定**:
```env
# 開發環境
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# 生產環境（請替換為實際域名）
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

---

### 5. 速率限制實施 ✅

**修復內容**:
- ✅ 創建 `RateLimitMiddleware`
- ✅ 預設每分鐘 60 次請求限制
- ✅ 可通過環境變數配置

**設定**:
```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

---

### 6. 依賴套件升級 ✅

**修復內容**:
- ✅ 替換 `PyPDF2==3.0.1` 為 `pypdf>=3.17.0`（修復安全漏洞）
- ✅ 升級 `requests==2.31.0` 到 `requests>=2.32.0`
- ✅ 添加 `python-multipart>=0.0.6`
- ✅ 更新所有檔案處理代碼使用新的 `pypdf` API

**安裝更新的套件**:
```powershell
cd backend
..\CBvenv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

### 7. 安全日誌和監控 ✅

**修復內容**:
- ✅ 創建 `app/core/security_logging.py` 模組
- ✅ 實施結構化安全事件日誌
- ✅ 自動創建 `logs/security.log` 檔案
- ✅ 記錄以下事件：
  - 未授權訪問嘗試
  - 檔案上傳操作
  - 管理員操作
  - 速率限制觸發
  - 可疑活動
  - 數據操作（存取/修改/刪除）

**日誌位置**:
- 安全日誌: `backend/logs/security.log`
- 應用日誌: 通過 uvicorn 輸出

---

## 🚀 啟動修復後的應用程式

### 步驟 1: 安裝更新的套件

```powershell
# 啟動虛擬環境
cd C:\Users\MITAC\Documents\AI-CB
.\CBvenv\Scripts\Activate.ps1

# 安裝更新的套件
cd backend
pip install -r requirements.txt
```

### 步驟 2: 設定環境變數

```powershell
# 確保 backend/.env 已正確配置
# 特別檢查以下項目：
# - ADMIN_API_KEY （必須設定一個強隨機值）
# - MODEL_NAME
# - LLM_API_BASE
# - ALLOWED_ORIGINS
```

### 步驟 3: 啟動後端服務

```powershell
cd C:\Users\MITAC\Documents\AI-CB\backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

啟動時會看到類似以下輸出：
```
⚠️  WARNING: ADMIN_API_KEY not set in environment!
⚠️  Using temporary API key: <隨機生成的 Key>
⚠️  Please set ADMIN_API_KEY in your .env file!
```

**請立即保存這個臨時 Key** 或在 `.env` 中設定您自己的 Key。

### 步驟 4: 啟動前端服務

```powershell
cd C:\Users\MITAC\Documents\AI-CB\frontend
npm start
```

### 步驟 5: 驗證修復

1. **測試一般 API** (不需要認證):
```powershell
curl http://localhost:8001/health
```

2. **測試管理員 API** (需要 API Key):
```powershell
# 應該返回 401 Unauthorized
curl http://localhost:8001/api/admin/users

# 使用 API Key 應該成功
curl http://localhost:8001/api/admin/users -H "X-API-Key: your_api_key_here"
```

3. **測試檔案上傳安全性**:
- 嘗試上傳大於 10MB 的檔案（應該被拒絕）
- 嘗試上傳不支援的格式（應該被拒絕）
- 檢查 `logs/security.log` 確認事件被記錄

---

## 🔒 安全檢查清單

在部署到生產環境之前，請確認以下項目：

- [ ] 所有 `.env` 檔案已添加到 `.gitignore`
- [ ] Git 歷史中沒有敏感資訊
- [ ] `ADMIN_API_KEY` 已設定為強隨機字串（至少 32 字符）
- [ ] `ALLOWED_ORIGINS` 只包含生產環境的域名
- [ ] `MAX_FILE_SIZE_MB` 設定適當
- [ ] 速率限制已啟用並設定合理的值
- [ ] 已安裝所有更新的依賴套件
- [ ] 安全日誌正常工作
- [ ] 檔案上傳功能經過測試
- [ ] 管理員 API 需要正確的認證

---

## 📝 後續建議

### 短期（1週內）

1. **實施完整的認證系統**:
   - 添加 JWT 認證
   - 實施用戶註冊/登入功能
   - 密碼雜湊（bcrypt/argon2）

2. **前端整合**:
   - 更新前端以包含 X-API-Key header
   - 添加管理員登入頁面
   - 實施 API Key 管理界面

3. **測試**:
   - 進行滲透測試
   - 負載測試
   - 檔案上傳測試（各種格式和大小）

### 中期（1個月內）

1. **進階安全功能**:
   - 實施 CSRF 保護
   - 添加 Content Security Policy (CSP)
   - 實施 Session 管理

2. **監控和告警**:
   - 設定自動告警（異常登入、大量失敗請求等）
   - 整合日誌分析工具
   - 實施健康檢查端點

3. **合規性**:
   - 資料隱私政策
   - 用戶數據加密
   - 審計日誌保留政策

---

## 🆘 故障排除

### 問題: 後端啟動失敗

**原因**: 缺少必要的環境變數

**解決方案**:
```powershell
# 檢查 .env 檔案
cat backend\.env

# 確保至少包含以下變數:
# MODEL_NAME
# LLM_API_BASE
```

### 問題: 管理員 API 返回 401

**原因**: 缺少或錯誤的 API Key

**解決方案**:
1. 檢查後端啟動日誌中的臨時 API Key
2. 或在 `.env` 中設定 `ADMIN_API_KEY`
3. 確保請求 Header 中包含 `X-API-Key`

### 問題: 檔案上傳失敗

**原因**: 多種可能

**解決方案**:
1. 檢查檔案大小（<10MB）
2. 檢查檔案格式（只允許 .txt, .pdf, .docx）
3. 查看 `logs/security.log` 了解詳細錯誤
4. 確保 `data/uploads/` 目錄存在且可寫

### 問題: 速率限制誤觸發

**原因**: 開發時請求過於頻繁

**解決方案**:
在 `backend/.env` 中調整限制：
```env
RATE_LIMIT_ENABLED=false  # 開發環境可暫時禁用
# 或增加限制
RATE_LIMIT_PER_MINUTE=120
```

---

## 📞 需要幫助？

如果您在實施過程中遇到任何問題，請：

1. 檢查 `logs/security.log` 查看詳細錯誤
2. 查看後端控制台輸出
3. 檢查瀏覽器控制台錯誤
4. 參考 `security-fixes.md` 了解原始審計報告

---

**最後提醒**: 在生產環境部署之前，請務必：
- 進行完整的安全測試
- 使用 HTTPS
- 設定防火牆規則
- 定期備份數據
- 監控安全日誌

祝部署順利！🎉
