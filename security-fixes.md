# 🔒 ChatBot 專案資安審計報告

**審計日期**: 2025年10月2日  
**審計範圍**: 全專案架構與程式碼安全性分析  
**審計師**: Senior Security Architect (30年經驗)

---

## 📋 專案基本資訊

- **專案名稱**: ChatBot 應用程式 (AI-CB)
- **簡介**: 具備使用者介面和後台管理介面的 ChatBot 應用程式，使用增強型混合 RAG（檢索增強生成）技術
- **目標使用者**: 一般用戶和系統管理員
- **處理的資料類型**:
  - ✅ 是否處理個人身份資訊（PII）: 是（用戶對話記錄、上傳文件）
  - ❌ 是否處理支付或財務資訊: 否
  - ✅ 是否有用戶上傳內容（UGC）: 是（TXT, PDF, DOCX 文件）
- **技術棧**:
  - **前端**: React 18 + Material-UI + React Router + Axios
  - **後端**: FastAPI + SQLAlchemy + LangChain + Ollama/GitHub Models
  - **資料庫**: SQLite (開發) / PostgreSQL (生產)
- **部署環境**: 本地開發環境 (localhost)，支援 Docker 容器化部署
- **外部依賴與服務**:
  - **NPM 套件**: 26個直接依賴（React生態系統）
  - **Python 套件**: 20+個關鍵依賴（AI/ML相關）
  - **外部 API**: 自定義 LLM API (`https://f20dfbce5e43.ngrok-free.app`)
  - **雲端服務**: Ngrok 隧道服務

---

## 🚨 第一部分：新手災難性錯誤檢查

### 威脅標題：高風險 - Ngrok API Base URL 暴露於環境設定檔

* **風險等級：** `高`
* **威脅描述：** 在 `.env` 檔案中發現硬編碼的 Ngrok 隧道 URL (`https://f20dfbce5e43.ngrok-free.app`)，該 URL 直接暴露了後端 LLM 服務的入口點。
* **受影響的元件：** `backend/.env` 第3行 `LLM_API_BASE=https://f20dfbce5e43.ngrok-free.app`

**駭客攻擊劇本 (Hacker's Playbook):**
> 「太棒了！我在你的 GitHub 專案中看到了 `.env` 檔案，裡面有一個完整的 Ngrok URL。這意味著我現在知道你的 LLM 服務在哪裡運行。我可以直接對這個 URL 發送大量請求，消耗你的 API 配額，或者嘗試找出這個服務的其他端點。更糟的是，如果這個 Ngrok 隧道沒有適當的認證保護，我甚至可能直接存取你的內部服務。我現在就開始用我的 botnet 對你的服務發動 DDoS 攻擊...」

**修復原理 (Principle of the Fix):**
> 「為什麼不能把 Ngrok URL 寫在 `.env` 裡？想像一下，`.env` 檔案就像是你家門口的『歡迎墊』，上面寫著家裡的WiFi密碼。任何路過的人都能看到。正確的做法是，把這些敏感的連線資訊存放在『家裡的保險箱』（伺服器環境變數）裡，只有你自己知道密碼。更好的做法是使用『動態門牌號碼』（環境特定的設定），讓開發環境、測試環境和生產環境都有不同的地址，這樣即使開發環境的地址被洩露，生產環境依然是安全的。」

* **修復建議與程式碼範例：**
  1. **立即行動**: 從 Git 歷史記錄中移除 `.env` 檔案
  2. **加強 .gitignore**: 確保所有環境檔案都被排除
  3. **使用環境特定的設定檔**:
  
```bash
# 修正前 (危險)
LLM_API_BASE=https://f20dfbce5e43.ngrok-free.app

# 修正後 (安全)
# .env.example (可提交到 Git)
LLM_API_BASE=your_llm_service_url_here

# .env.local (不提交到 Git)
LLM_API_BASE=https://your-actual-production-url.com
```

```python
# 在程式碼中添加驗證
import os
from urllib.parse import urlparse

def validate_api_base(url):
    parsed = urlparse(url)
    if 'ngrok' in parsed.netloc and os.getenv('ENVIRONMENT') == 'production':
        raise ValueError("Ngrok URLs not allowed in production")
    return url

LLM_API_BASE = validate_api_base(os.environ.get("LLM_API_BASE"))
```

---

### 威脅標題：高風險 - 完全移除身份驗證系統造成無授權存取

* **風險等級：** `高`
* **威脅描述：** 整個系統已完全移除用戶註冊/登入及 JWT 認證功能，所有 API 端點都處於開放狀態，任何人都可以無限制存取管理功能。
* **受影響的元件：** 
  - `backend/app/core/user_context.py` - 預設用戶 ID 為 1
  - `backend/app/api/admin.py` - 管理員 API 無認證保護
  - `backend/app/api/chat.py` - 聊天 API 無認證保護

**駭客攻擊劇本 (Hacker's Playbook):**
> 「這太不可思議了！我發現這個 ChatBot 應用程式根本沒有任何登入機制。我直接訪問 `/api/admin/users` 就能看到所有用戶列表，訪問 `/api/admin/conversations` 就能看到所有私密對話記錄。我甚至可以呼叫 `/api/admin/vector-store/clear` 直接清空整個知識庫！更誇張的是，我可以上傳惡意文件到知識庫，然後讓所有用戶在對話中接收到我注入的惡意內容。這簡直是一個沒有門鎖的銀行金庫！」

**修復原理 (Principle of the Fix):**
> 「為什麼一定要有身份驗證？想像你開了一家咖啡店，但是沒有任何方式區分『顧客』和『員工』，結果每個進來的人都能隨意操作收銀機、查看帳本、甚至改變咖啡配方。身份驗證就像是『員工識別證』和『顧客會員卡』，讓系統知道誰可以做什麼。管理員 API 就像是『員工專用區域』，應該只有戴著『管理員識別證』的人才能進入。沒有身份驗證的系統，就等於把所有門都大開，歡迎任何人隨意進出。」

* **修復建議與程式碼範例：**
  1. **立即實施基本認證保護**:

```python
# 緊急臨時措施 - 添加簡單的 API Key 認證
from fastapi import HTTPException, Header
import secrets

# 生成一個強隨機 API Key
ADMIN_API_KEY = secrets.token_urlsafe(32)
print(f"管理員 API Key: {ADMIN_API_KEY}")  # 安全地記錄下來

async def verify_admin_key(x_api_key: str = Header(None)):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return True

# 在所有管理員路由上添加依賴
@router.get("/admin/users", dependencies=[Depends(verify_admin_key)])
async def get_users(...):
    pass
```

  2. **實施完整的 JWT 認證系統**:

```python
# 完整的 JWT 實現
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username
```

---

### 威脅標題：中風險 - 不安全的檔案上傳處理

* **風險等級：** `中`
* **威脅描述：** 檔案上傳功能缺乏充分的安全驗證，僅依賴 MIME 類型檢查，且檔案直接存儲在 Web 可存取的目錄中。
* **受影響的元件：** 
  - `backend/app/api/documents.py` - 檔案上傳邏輯
  - `backend/app/services/document_processor.py` - 檔案處理邏輯

**駭客攻擊劇本 (Hacker's Playbook):**
> 「我注意到這個系統允許上傳 PDF 和 DOCX 文件。雖然你檢查了 MIME 類型，但我可以輕易偽造這些。我會建立一個看起來像正常 PDF 的檔案，但實際上包含惡意的 JavaScript 程式碼，或者利用 PyPDF2 或 python-docx 庫的已知漏洞。更簡單的方法是，我會上傳一個超大的檔案（比如接近 50MB 的限制），然後同時上傳多個這樣的檔案，讓你的伺服器記憶體爆炸。如果你的檔案存儲在 Web 可存取的位置，我甚至可能直接通過 URL 存取其他用戶的敏感文件。」

**修復原理 (Principle of the Fix):**
> 「檔案上傳就像是讓陌生人把包裹放到你家裡。你不能只看包裹外面的標籤就相信內容是安全的，因為標籤很容易偽造。正確的做法是：1) 像機場安檢一樣徹底檢查內容（檔案頭部驗證），2) 把包裹放在隔離的倉庫（獨立存儲目錄），3) 在打開包裹前先用防護措施（沙盒環境），4) 限制包裹的大小和數量（速率限制），5) 絕對不要讓任何人隨意進入你的倉庫（禁止直接 Web 存取）。」

* **修復建議與程式碼範例：**

```python
import magic
import hashlib
import tempfile
from pathlib import Path

class SecureDocumentProcessor:
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
    ALLOWED_MIME_TYPES = {
        'application/pdf': [b'%PDF'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [b'PK'],
        'text/plain': []
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB instead of 50MB
    
    @staticmethod
    def validate_file_security(file_path: str, content_type: str) -> bool:
        """多層次檔案驗證"""
        
        # 1. 檔案大小檢查
        if os.path.getsize(file_path) > SecureDocumentProcessor.MAX_FILE_SIZE:
            raise ValueError("檔案大小超過限制")
        
        # 2. 副檔名檢查
        ext = Path(file_path).suffix.lower()
        if ext not in SecureDocumentProcessor.ALLOWED_EXTENSIONS:
            raise ValueError(f"不允許的檔案副檔名: {ext}")
        
        # 3. MIME 類型檢查 (使用 python-magic)
        actual_mime = magic.from_file(file_path, mime=True)
        if actual_mime != content_type:
            raise ValueError(f"MIME 類型不符: 聲稱 {content_type}, 實際 {actual_mime}")
        
        # 4. 檔案頭部檢查
        with open(file_path, 'rb') as f:
            header = f.read(512)
            
        if content_type in SecureDocumentProcessor.ALLOWED_MIME_TYPES:
            magic_numbers = SecureDocumentProcessor.ALLOWED_MIME_TYPES[content_type]
            if magic_numbers and not any(header.startswith(magic) for magic in magic_numbers):
                raise ValueError("檔案頭部驗證失敗")
        
        return True
    
    @staticmethod
    def secure_file_storage(file_content: bytes, original_filename: str) -> str:
        """安全的檔案存儲"""
        
        # 使用內容雜湊作為檔名，防止路徑遍歷攻擊
        file_hash = hashlib.sha256(file_content).hexdigest()
        ext = Path(original_filename).suffix.lower()
        secure_filename = f"{file_hash}{ext}"
        
        # 存儲在 Web 根目錄外的安全位置
        secure_dir = Path("/app/secure_uploads")  # Web 無法存取的目錄
        secure_dir.mkdir(exist_ok=True)
        
        secure_path = secure_dir / secure_filename
        with open(secure_path, 'wb') as f:
            f.write(file_content)
        
        return str(secure_path)
```

---

## 📊 第二部分：OWASP Top 10 (2021) 審計結果

### A01: 權限控制失效 ✅ **已發現嚴重問題**
- **狀態**: 🔴 **嚴重** - 整個認證系統已被移除
- **影響**: 任何人都可以存取管理員功能、查看所有用戶資料
- **修復優先級**: **立即**

### A02: 加密機制失效 ⚠️ **需要改進**
- **狀態**: 🟡 **中等** - 敏感設定資訊以明文存儲
- **影響**: Ngrok URL、資料庫連線字串暴露
- **修復優先級**: **高**

### A03: 注入式攻擊 ✅ **狀況良好**
- **狀態**: 🟢 **安全** - 使用 SQLAlchemy ORM，未發現明顯的 SQL 注入風險
- **備註**: 所有資料庫操作都通過 ORM 進行

### A04: 不安全的設計 ⚠️ **需要改進**
- **狀態**: 🟡 **中等** - 系統設計缺乏基本的安全層級
- **影響**: 沒有存取控制分層、缺乏輸入驗證策略
- **修復優先級**: **中**

### A05: 安全設定錯誤 ✅ **已發現問題**
- **狀態**: 🔴 **嚴重** - CORS 設定過於寬鬆、環境設定暴露
- **影響**: 跨來源請求攻擊風險、敏感資訊洩露
- **修復優先級**: **高**

### A06: 危險或過時的元件 ⚠️ **需要檢查**
- **狀態**: 🟡 **中等** - 需要檢查依賴性漏洞
- **影響**: 潛在的已知 CVE 風險
- **修復優先級**: **中**

### A07: 身份認證和驗證機制失效 ✅ **已發現嚴重問題**
- **狀態**: 🔴 **嚴重** - 與 A01 相同，完全缺乏認證機制
- **修復優先級**: **立即**

### A08: 軟體和資料完整性失效 ✅ **狀況良好**
- **狀態**: 🟢 **安全** - 使用固定版本的依賴性
- **備註**: package.json 和 requirements.txt 都指定了版本

### A09: 安全記錄和監控失效 ⚠️ **需要改進**
- **狀態**: 🟡 **中等** - 缺乏全面的安全事件記錄
- **影響**: 難以偵測和回應安全事件
- **修復優先級**: **中**

### A10: 伺服器端請求偽造 (SSRF) ✅ **狀況良好**
- **狀態**: 🟢 **安全** - 沒有發現明顯的 SSRF 風險
- **備註**: 外部 API 呼叫都是固定端點

---

## 🔗 第三部分：依賴性與供應鏈安全

### Python 後端依賴分析

**高風險依賴**:
- `PyPDF2==3.0.1` - 已知有安全問題，建議升級到 `pypdf>=3.1.0`
- `requests==2.31.0` - 較舊版本，建議升級到最新版本

**建議行動**:
```bash
# 檢查漏洞
pip-audit --requirement requirements.txt

# 升級建議
PyPDF2==3.0.1 → pypdf>=3.17.0  # 更安全的分支
requests==2.31.0 → requests>=2.32.0
```

### Node.js 前端依賴分析

**潛在風險**:
- 需要定期執行 `npm audit` 檢查已知漏洞
- React 18.2.0 是穩定版本，但應關注安全更新

```bash
# 檢查前端漏洞
npm audit
npm audit fix
```

---

## 🔧 第四部分：業務邏輯與基礎設施安全

### 檔案系統安全
- **問題**: 上傳檔案存儲在 `data/uploads/` 可能被直接存取
- **建議**: 移至 Web 根目錄外，實施存取控制

### WebSocket 安全
- **問題**: WebSocket 連接缺乏認證驗證
- **風險**: 任何人都可以連接並發送訊息
- **建議**: 實施 WebSocket 認證機制

### 記憶體管理
- **問題**: RAG 系統的對話記憶體沒有大小限制
- **風險**: 可能導致記憶體洩露
- **建議**: 實施記憶體清理和大小限制

---

## 🚀 第五部分：立即行動計劃

### 緊急修復 (24小時內)

1. **移除敏感資訊**:
```bash
# 從 Git 歷史中移除 .env 檔案
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch backend/.env' \
  --prune-empty --tag-name-filter cat -- --all

# 強制推送更新
git push origin --force --all
```

2. **實施臨時認證**:
```python
# 添加到 main.py
TEMP_ADMIN_TOKEN = "CHANGE_THIS_IMMEDIATELY_" + secrets.token_urlsafe(16)
print(f"臨時管理員令牌: {TEMP_ADMIN_TOKEN}")

@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/admin"):
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != f"Bearer {TEMP_ADMIN_TOKEN}":
            return Response("Unauthorized", status_code=401)
    return await call_next(request)
```

### 短期修復 (1週內)

1. **實施完整認證系統** (JWT + bcrypt)
2. **加強檔案上傳安全性**
3. **設定適當的 CORS 政策**
4. **實施速率限制**

### 中期改進 (1個月內)

1. **安全程式碼審查流程**
2. **自動化安全測試**
3. **完整的日誌和監控系統**
4. **定期依賴性掃描**

---

## 📈 第六部分：安全成熟度評估

**目前安全等級**: 🔴 **高風險** (2/10)

**主要風險因子**:
- 完全缺乏認證機制
- 敏感資訊暴露
- 不安全的檔案處理
- 過於寬鬆的存取控制

**目標安全等級**: 🟢 **安全** (8/10)

**預計改進時程**: 2-4週（取決於資源投入）

---

## 💡 第七部分：給新手開發者的安全建議

### 🎯 黃金法則

1. **永遠不要提交秘密資訊到 Git**
   - 使用 `.env.example` 範本
   - 設定 pre-commit hooks 檢查敏感資訊

2. **預設拒絕，明確允許**
   - 所有 API 預設需要認證
   - 明確定義誰可以存取什麼資源

3. **多層防護**
   - 不要只依賴前端驗證
   - 後端必須驗證所有輸入
   - 實施深度防禦策略

4. **定期安全檢查**
   - 每週執行 `npm audit` 和 `pip-audit`
   - 設定自動化安全掃描
   - 關注安全公告和 CVE

### 🔧 實用工具推薦

```bash
# Python 安全工具
pip install bandit safety pip-audit
bandit -r backend/
safety check
pip-audit

# Node.js 安全工具
npm audit
npm install -g snyk
snyk test

# Git 安全工具
pip install detect-secrets
detect-secrets scan --all-files
```

---

## ✅ 總結與下一步

這個專案目前存在**嚴重的安全風險**，主要是由於移除了整個認證系統而導致的無授權存取問題。雖然這可能是為了開發便利而做的臨時決定，但絕對不能在任何可被外部存取的環境中運行。

**立即需要處理的問題**:
1. 🔴 **緊急**: 實施基本認證保護
2. 🔴 **緊急**: 移除敏感資訊暴露
3. 🟡 **重要**: 加強檔案上傳安全
4. 🟡 **重要**: 修復 CORS 設定

**積極方面**:
- 使用了現代化的技術棧
- 程式碼結構清晰
- 使用 ORM 避免了 SQL 注入
- 有基本的輸入驗證

只要按照本報告的建議進行修復，這個專案可以在短時間內達到可接受的安全等級。記住，**安全不是一次性的工作，而是持續的過程**。

---

**報告結束**  
*如需進一步的安全諮詢或協助實施修復措施，請隨時聯繫。*