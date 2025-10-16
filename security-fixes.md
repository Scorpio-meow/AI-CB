# 🛡️ ChatBot 專案資安審計報告

> **審計完成日期**: 2025年10月16日  
> **審計範圍**: 全專案深度資安檢查  
> **審計專家**: 高級資安顧問（30年滲透測試與防禦經驗）  

---

## 📊 專案基本資訊

* **專案名稱**: ChatBot 應用程式（增強型混合 RAG 系統）
* **目標使用者**: 內部員工、客戶服務人員
* **處理的資料類型**:
  - ✅ **個人身份資訊（PII）**: 是，用戶註冊信息（用戶名、郵箱）
  - ❌ **支付或財務資訊**: 否
  - ✅ **用戶上傳內容（UGC）**: 是，文檔上傳功能（PDF、TXT、DOCX）
* **技術棧**:
  - **前端**: React 18 + Material-UI + Axios
  - **後端**: FastAPI + SQLAlchemy + LangChain + FAISS
  - **資料庫**: SQLite（開發）/ PostgreSQL（生產）
* **部署環境**: 本地開發環境（localhost），支援 Docker 容器化
* **外部依賴與服務**:
  - **NPM 套件**: 42 個依賴，包含 axios、react、@mui/material 等
  - **Python 套件**: 47 個依賴，包含 fastapi、sqlalchemy、transformers 等
  - **外部 API**: LLM 服務（ngrok 隧道：`https://blowfish-absolute-absolutely.ngrok-free.app`）
  - **雲端服務**: 無直接雲端服務依賴

---

## 🚨 第一部分：新手常見的災難性錯誤檢查

### 威脅標題：**高風險 - 敏感 API 金鑰與密碼明文儲存於 .env 檔案中**
* **風險等級**: `高`
* **威脅描述**: `.env` 檔案包含完整的生產環境密鑰（ADMIN_API_KEY、JWT_SECRET_KEY、SECRET_KEY），雖然已加入 `.gitignore`，但仍存在意外洩漏的風險。
* **受影響的元件**: `backend/.env` 檔案第 22-24 行

#### 駭客攻擊劇本 (Hacker's Playbook):
> 我知道很多開發者會將真實的 .env 檔案「暫時」複製到其他地方備份，或是透過 Slack、Email 分享給同事。我只需要社交工程攻擊你們公司的任何一個員工，或是等待你們其中一個人不小心將 .env 內容貼到 GitHub Issue、Stack Overflow 上求助。一旦我拿到了這個 ADMIN_API_KEY（`jYWf1WwhUooRrY1HI1jTlaiOrp6oUrFwzBfybumXydexFpxskpfdT-FRDzsPS0UJxnzy5k5_wWKjxYA`），我就能以管理員身份訪問所有用戶資料、刪除任何文件、竊取所有對話記錄。

#### 修復原理 (Principle of the Fix):
> 為什麼不能把真實密鑰寫在 .env 裡？因為 .env 就像是你錢包裡的信用卡密碼備忘紙條。正確的做法是使用「環境變數注入」或「密鑰管理服務」，讓密鑰像銀行密碼一樣只存在你腦海裡（環境變數），而不是寫在紙條上（檔案）。

#### 修復建議與程式碼範例:
1. **立即更換所有密鑰**:
```bash
# 生成新的安全密鑰
python backend/scripts/generate_secure_keys.py
```

2. **使用範本檔案**:
```bash
# 創建範本檔案
cp backend/.env backend/.env.template
# 清空範本中的實際密鑰值
sed -i 's/ADMIN_API_KEY=.*/ADMIN_API_KEY=CHANGE_THIS_IN_PRODUCTION/g' backend/.env.template
```

3. **生產環境使用環境變數注入**:
```bash
# 正確的生產環境啟動方式
export ADMIN_API_KEY="$(openssl rand -base64 32)"
export JWT_SECRET_KEY="$(openssl rand -base64 32)"
python -m uvicorn main:app
```

---

### 威脅標題：**高風險 - ngrok 隧道服務在生產環境使用**
* **風險等級**: `高`
* **威脅描述**: LLM API 服務使用 ngrok 隧道（`https://blowfish-absolute-absolutely.ngrok-free.app`），這是一個公開的隧道服務，存在中間人攻擊和服務不穩定風險。
* **受影響的元件**: `backend/.env` 第 12 行

#### 駭客攻擊劇本 (Hacker's Playbook):
> 我發現你們的 AI 服務使用了 ngrok 隧道。ngrok 是一個很棒的開發工具，但它的免費版本會在隨機子域名下公開你的服務。我只需要暴力掃描 `*.ngrok-free.app` 的子域名，很快就能找到你們的 AI 端點。更糟糕的是，ngrok 的免費隧道會定期更換 URL，這意味著你們必須經常更新配置，增加了出錯的機會。我還可以註冊相似的子域名進行釣魚攻擊。

#### 修復建議與程式碼範例:
1. **生產環境使用專用域名**:
```env
# 修正前 (開發環境可用)
LLM_API_BASE=https://blowfish-absolute-absolutely.ngrok-free.app

# 修正後 (生產環境)
LLM_API_BASE=https://ai-api.yourdomain.com
```

2. **添加環境檢查**:
```python
# backend/app/core/security.py 中已有相關檢查
def validate_api_endpoint(url: str) -> str:
    if os.getenv("ENVIRONMENT") == "production" and "ngrok" in parsed.netloc:
        raise ValueError("Ngrok URLs are not allowed in production")
```

---

## 📋 第二部分：標準應用程式安全審計

### 威脅標題：**中風險 - JWT 算法降級風險**
* **風險等級**: `中`
* **威脅描述**: JWT 配置中存在從 RSA256 降級到 HS256 的邏輯，可能被攻擊者利用進行算法混淆攻擊。
* **受影響的元件**: `backend/app/core/jwt_auth.py` 第 22-33 行

#### 修復建議與程式碼範例:
```python
# 修正前：允許降級
except Exception as e:
    USE_RSA = False
    ALGORITHM = "HS256"  # 危險的降級

# 修正後：拒絕啟動
except Exception as e:
    logger.error(f"RSA 金鑰載入失敗: {e}")
    raise RuntimeError("生產環境必須使用 RSA 金鑰") from e
```

---

### 威脅標題：**中風險 - CORS 開發模式配置過寬鬆**
* **風險等級**: `中`
* **威脅描述**: CORS 配置在開發環境中允許正則表達式匹配任意 DevTunnels 子域，存在跨域攻擊風險。
* **受影響的元件**: `backend/main.py` 第 73-74 行

#### 修復建議與程式碼範例:
```python
# 修正前：過於寬鬆
ALLOWED_ORIGIN_REGEX = r"https://[a-zA-Z0-9-]+\.asse\.devtunnels\.ms"

# 修正後：精確匹配
ALLOWED_ORIGINS = [
    "https://specific-subdomain.devtunnels.ms",  # 指定的開發隧道
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]
```

---

### 威脅標題：**中風險 - 文件上傳目錄權限過寬**
* **風險等級**: `中`
* **威脅描述**: Windows 系統下的上傳目錄具有完全控制權限，可能被利用上傳惡意文件。
* **受影響的元件**: `backend/data/uploads/` 目錄權限設置

#### 修復建議與程式碼範例:
```powershell
# 修正前：過寬權限
# MITAC:(I)(OI)(CI)(F)  # 完全控制

# 修正後：最小權限
icacls "backend\data\uploads" /grant "IIS_IUSRS:(OI)(CI)(M)"
icacls "backend\data\uploads" /remove "Users"
```

---

### 威脅標題：**低風險 - 前端 Console 日誌洩漏調試資訊**
* **風險等級**: `低`
* **威脅描述**: 前端代碼包含大量 console.log 語句，在生產環境可能洩漏敏感調試資訊。
* **受影響的元件**: 多個前端 JavaScript 檔案

#### 修復建議與程式碼範例:
```javascript
// 添加生產環境日誌過濾
const isDevelopment = process.env.NODE_ENV === 'development';

// 修正前
console.log('[Token] Token 即將過期...');

// 修正後
if (isDevelopment) {
  console.log('[Token] Token 即將過期...');
}
```

---

### 威脅標題：**低風險 - Access Token 存儲在 localStorage**
* **風險等級**: `低`
* **威脅描述**: Access Token 存儲在瀏覽器 localStorage 中，容易受到 XSS 攻擊。
* **受影響的元件**: `frontend/src/services/authService.js`

#### 修復建議與程式碼範例:
```javascript
// 建議：移至 HttpOnly Cookie 或 Secure Storage
// 由於 Access Token 有效期短（30分鐘），風險可控
// 但建議添加額外保護
const secureStorage = {
  setItem: (key, value) => {
    // 使用加密存儲或 Cookie
    document.cookie = `${key}=${value}; Secure; SameSite=Strict; HttpOnly`;
  }
};
```

---

## ✅ 發現的安全亮點

1. **優秀的 .gitignore 配置**: 正確排除了 `.env`、`*.pem` 等敏感檔案
2. **強密碼驗證**: 實施了密碼強度檢查（8字符、大小寫、數字）
3. **檔名安全驗證**: 實施了路徑遍歷攻擊防護
4. **参數化查詢**: 使用 SQLAlchemy ORM，有效防止 SQL 注入
5. **安全標頭中間件**: 添加了 X-Content-Type-Options、X-Frame-Options 等安全標頭
6. **速率限制**: 實施了 API 速率限制（60次/分鐘）
7. **JWT Token 黑名單**: 支援 Token 撤銷機制
8. **檔案類型白名單**: 僅允許 .txt、.pdf、.docx 檔案上傳

---

## 🎯 優先修復建議

### 🔴 立即修復 (24小時內)
1. 更換所有硬編碼的 API 密鑰
2. 設置生產環境專用的 LLM API 端點
3. 加固文件上傳目錄權限

### 🟡 短期修復 (1週內)
1. 移除 JWT 算法降級邏輯
2. 精確化 CORS 配置
3. 清理前端調試日誌

### 🟢 長期優化 (1個月內)
1. 實施密鑰管理服務
2. 添加 API 訪問審計日誌
3. 設置自動化安全掃描

---

## 🛠️ 自動化安全掃描腳本

由於我發現了一些潛在的安全模式，建議執行以下自動化掃描：

```python
# 建議執行的安全掃描腳本
python backend/scripts/security_scanner.py  # 已存在
python backend/scripts/run_security_checks.py  # 已存在
```

這些腳本將幫助您：
- 掃描硬編碼密碼和 API 金鑰
- 檢查 SQL 注入漏洞模式
- 驗證文件權限設置
- 分析依賴庫安全漏洞

---

## 📞 緊急回應計劃

若發現安全漏洞被利用，請立即：

1. **隔離受影響系統**
2. **更換所有認證密鑰**
3. **檢查訪問日誌**: `backend/logs/security.log`
4. **通知所有用戶更改密碼**
5. **實施臨時 IP 封鎖**: 使用內建的入侵檢測系統

---

**審計結論**: 該專案在安全設計上展現了良好的基礎，但需要立即處理密鑰管理和生產環境配置問題。整體安全級別為 **中等偏上**，經過建議修復後可達到 **高安全級別**。

---
*此報告由資安專家基於 OWASP Top 10 (2021) 標準進行評估*
