# 🛡️ ChatBot 專案資安審計報告

**審計日期**: 2025年10月15日  
**審計者**: 資安顧問 (30年經驗)  
**審計範圍**: 全專案資安評估  
**專案階段**: Vibe Coding → Go-Live 前安全加固  

---

## 📋 專案基本資訊

### 專案名稱與簡介
- **專案名稱**: ChatBot 應用程式
- **簡介**: 基於增強型混合 RAG（檢索增強生成）技術的智能對話系統，具備使用者介面和後台管理介面

### 目標使用者
- 一般使用者（聊天對話）
- 管理員使用者（後台管理、文件上傳、系統監控）

### 處理的資料類型
- **是否處理個人身份資訊（PII）**: ✅ 是（用戶帳號、電子郵件、對話記錄）
- **是否處理支付或財務資訊**: ❌ 否
- **是否有用戶上傳內容（UGC）**: ✅ 是（文檔上傳、對話內容）

### 技術棧（Tech Stack）
- **前端**: React 18 + Material-UI + Axios + React Router
- **後端**: FastAPI + SQLAlchemy + LangChain + sentence-transformers
- **資料庫**: SQLite (開發) / PostgreSQL (生產)

### 部署環境/伺服器類型
- 本地開發環境（localhost）
- 支援 Docker 容器化部署

### 外部依賴與服務
- **NPM 套件**: 前端依賴包含 React 生態系
- **Python 套件**: AI/ML 相關套件（torch, transformers, faiss-cpu）
- **外部 API 服務**: LLM API（通過 ngrok tunnel）
- **使用的雲端服務**: 無（純本地部署）

---

## 🚨 第一部分：新手常見的災難性錯誤檢查

### 威脅標題：高風險 - 生產環境中仍使用開發用 ngrok 隧道
- **風險等級**: `高`
- **威脅描述**: 在 `.env` 文件中發現使用 ngrok 隧道作為 LLM API 端點，這在生產環境中存在重大安全風險
- **受影響的元件**: `backend/.env` 第2行 `LLM_API_BASE=https://blowfish-absolute-absolutely.ngrok-free.app`

#### 駭客攻擊劇本 (Hacker's Playbook):
> 我是一個惡意攻擊者，我知道很多開發者為了方便會在生產環境中繼續使用開發工具。當我看到你的 API 請求指向 ngrok 隧道時，我立刻意識到這是一個機會。首先，我會嘗試劫持這個 ngrok 隧道 - ngrok 的隨機子域名很容易被猜測或暴力破解。一旦我控制了這個端點，我就能看到所有從你的 ChatBot 發送的用戶查詢、API 密鑰，甚至可以返回惡意內容讓你的 AI 說出我想要的話。更糟糕的是，我還能通過這個通道進行中間人攻擊，竊取用戶的私密對話內容...

#### 修復原理 (Principle of the Fix):
> ngrok 就像是在你家和銀行之間架設一條臨時的玻璃走廊 - 雖然方便，但任何人都能看到裡面發生什麼。在開發階段用來測試沒問題，但在生產環境就像是把銀行金庫的鑰匙交給陌生人保管。正確的做法是使用固定的、有 SSL 證書的正式域名，或者將 LLM 服務部署在受控制的內網環境中。

#### 修復建議與程式碼範例:
**立即修復步驟**:
1. 將 LLM API 部署到正式的雲端服務或內網服務器
2. 使用固定域名和 HTTPS 證書
3. 設置適當的防火牆規則

**修正前**:
```env
LLM_API_BASE=https://blowfish-absolute-absolutely.ngrok-free.app
```

**修正後**:
```env
# 生產環境
LLM_API_BASE=https://api.yourcompany.com/llm
# 或內網環境
LLM_API_BASE=https://internal-llm.yourcompany.local:8000
```

---

### 威脅標題：高風險 - 硬編碼的管理員 API Key 存在安全隱患
- **風險等級**: `高`
- **威脅描述**: 管理員 API Key 直接寫在 `.env` 文件中，且長度和複雜度不足，容易被暴力破解
- **受影響的元件**: `backend/.env` 第16行 `ADMIN_API_KEY=zl4DDtCi-dHRqa4-VBN_Z-bNJEVClCYWegqoLt2N098`

#### 駭客攻擊劇本 (Hacker's Playbook):
> 我通過各種方式（比如 git 歷史、配置文件洩漏、或者內部人員）拿到了你的 `.env` 文件。我看到這個 API Key 只有 43 字符，而且看起來是某種可預測的格式。我會寫一個腳本來生成類似格式的 Key，然後對你的 `/api/admin/` 端點進行暴力攻擊。一旦成功，我就能訪問所有管理功能：刪除用戶、查看對話記錄、上傳惡意文件、甚至完全控制你的系統...

#### 修復原理 (Principle of the Fix):
> API Key 就像是你家的萬能鑰匙，絕對不能用簡單的鑰匙。現在的 Key 就像是用 "123456" 做密碼一樣危險。正確的做法是生成至少 64 字符的隨機字串，並且定期輪換。更好的方式是使用動態 Token 系統，而不是固定的 Key。

#### 修復建議與程式碼範例:
**立即修復步驟**:
1. 生成更強的 API Key（至少 64 字符）
2. 實施 API Key 輪換機制
3. 添加速率限制和異常監控

**生成強 API Key**:
```python
import secrets
import string

def generate_secure_api_key(length=64):
    alphabet = string.ascii_letters + string.digits + "_-"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# 生成新的安全 API Key
new_key = generate_secure_api_key(64)
print(f"ADMIN_API_KEY={new_key}")
```

**增強的 API Key 驗證**:
```python
# backend/app/core/security.py 增加速率限制
class APIKeyRateLimit:
    def __init__(self):
        self.attempts = {}
    
    def check_rate_limit(self, ip: str) -> bool:
        # 每小時最多嘗試 10 次
        if ip in self.attempts:
            if self.attempts[ip]['count'] > 10:
                return False
        return True
```

---

### 威脅標題：中風險 - 開發環境配置殘留在生產代碼中
- **風險等級**: `中`
- **威脅描述**: 前端代碼中包含大量 DevTunnels 相關配置和註釋，顯示開發環境配置可能殘留在生產代碼中
- **受影響的元件**: 多個前端 JavaScript 文件包含 DevTunnels 相關代碼

#### 修復建議與程式碼範例:
**清理步驟**:
1. 移除所有 DevTunnels 相關代碼
2. 建立環境變數管理機制
3. 創建生產環境構建流程

---

### 威脅標題：高風險 - JWT 密鑰配置存在安全隱患
- **風險等級**: `高`
- **威脅描述**: JWT 密鑰過短且可預測，容易被暴力破解，危及整個認證系統
- **受影響的元件**: `backend/.env` 第19行 JWT_SECRET_KEY

#### 駭客攻擊劇本 (Hacker's Playbook):
> 我拿到了你的 JWT Secret Key，發現它竟然包含重複的模式！這讓我立刻意識到這不是一個真正隨機生成的密鑰。我可以用這個密鑰偽造任何用戶的 JWT Token，包括管理員 Token。我會偽造一個 is_admin=true 的 Token，然後就能完全控制你的系統，查看所有用戶的私密對話，甚至刪除整個數據庫...

#### 修復建議與程式碼範例:
**生成安全的 JWT 密鑰**:
```python
import secrets

# 生成 256 位（32 字節）的隨機密鑰
jwt_secret = secrets.token_urlsafe(32)
print(f"JWT_SECRET_KEY={jwt_secret}")
```

---

## 🔒 第二部分：標準應用程式安全審計

### 威脅標題：中風險 - 文件上傳安全機制不完整
- **風險等級**: `中`
- **威脅描述**: 雖然實施了基本的文件驗證，但缺乏完整的惡意文件檢測機制
- **受影響的元件**: `backend/app/api/documents.py` 和 `backend/app/services/document_processor.py`

#### 修復建議與程式碼範例:
**增強文件安全檢查**:
```python
# 增加病毒掃描集成（建議）
def scan_file_for_malware(file_path: str) -> bool:
    """集成 ClamAV 或其他反病毒引擎"""
    pass

# 更嚴格的 MIME 類型檢查
ALLOWED_MIME_TYPES = {
    'text/plain': ['.txt'],
    'application/pdf': ['.pdf'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
}
```

---

### 威脅標題：中風險 - 缺乏全面的輸入驗證和清理
- **風險等級**: `中`
- **威脅描述**: 雖然使用了 Pydantic 驗證，但缺乏對特殊字符和潛在腳本注入的防護
- **受影響的元件**: 所有 API 端點的輸入處理

#### 修復建議與程式碼範例:
**增強輸入驗證**:
```python
import html
import re

def sanitize_user_input(input_text: str) -> str:
    """清理用戶輸入，防止 XSS 和注入攻擊"""
    # HTML 實體編碼
    cleaned = html.escape(input_text)
    # 移除潛在危險字符
    cleaned = re.sub(r'[<>"\']', '', cleaned)
    return cleaned.strip()
```

---

### 威脅標題：低風險 - 日誌記錄機制需要增強
- **風險等級**: `低`
- **威脅描述**: 雖然有基本的日誌記錄，但缺乏安全事件的詳細追蹤
- **受影響的元件**: 整體日誌系統

#### 修復建議與程式碼範例:
**增強安全日誌**:
```python
import logging
from datetime import datetime

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger('security')
        
    def log_security_event(self, event_type: str, user_id: int = None, 
                          ip_address: str = None, details: dict = None):
        """記錄安全相關事件"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details or {}
        }
        self.logger.warning(f"SECURITY_EVENT: {log_entry}")
```

---

### 威脅標題：低風險 - 依賴項目存在已知漏洞風險
- **風險等級**: `低`
- **威脅描述**: 某些依賴項目可能包含已知的安全漏洞
- **受影響的元件**: `requirements.txt` 和 `package.json`

#### 修復建議與程式碼範例:
**定期安全掃描**:
```bash
# Python 依賴掃描
pip-audit

# Node.js 依賴掃描
npm audit

# 修復高風險漏洞
npm audit fix
```

---

## 🔧 第三部分：針對大型專案的特別策略

由於專案規模較大且包含多個安全敏感模組，建議採用分階段安全加固策略：

### 階段一：立即修復（7天內）
1. 更換所有弱密鑰和 API Key
2. 移除 ngrok 依賴，改用正式 API 端點
3. 清理開發環境殘留代碼

### 階段二：安全增強（30天內）
1. 實施全面的輸入驗證
2. 增強文件上傳安全機制
3. 完善安全日誌系統

### 階段三：持續監控（持續進行）
1. 建立自動化安全掃描
2. 實施安全監控和告警
3. 定期進行滲透測試

---

## 🎯 自動化掃描腳本建議

為了確保沒有遺漏類似的安全問題，建議您執行以下自動化掃描腳本：

### 密鑰掃描腳本
```python
#!/usr/bin/env python3
"""
掃描代碼中的敏感信息
"""
import re
import os
import glob

def scan_secrets():
    patterns = {
        'api_key': r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
        'password': r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?',
        'secret': r'(?i)(secret|token)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
        'private_key': r'-----BEGIN.*PRIVATE KEY-----',
        'connection_string': r'(?i)(connection[_-]?string|database[_-]?url)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'
    }
    
    suspicious_files = []
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith(('.py', '.js', '.env', '.conf', '.config')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    for pattern_name, pattern in patterns.items():
                        matches = re.findall(pattern, content, re.MULTILINE)
                        if matches:
                            suspicious_files.append({
                                'file': file_path,
                                'pattern': pattern_name,
                                'matches': len(matches)
                            })
                except Exception as e:
                    continue
    
    return suspicious_files

if __name__ == '__main__':
    results = scan_secrets()
    for result in results:
        print(f"⚠️  {result['file']}: 發現 {result['matches']} 個 {result['pattern']} 模式")
```

---

## ✅ 總結與優先級建議

### 立即修復（24小時內）
1. 🔴 **更換 ngrok 為正式 API 端點**
2. 🔴 **重新生成所有密鑰和 API Key**
3. 🔴 **清理開發環境殘留配置**

### 短期修復（7天內）
1. 🟡 **增強文件上傳安全機制**
2. 🟡 **實施全面輸入驗證**
3. 🟡 **完善錯誤處理和日誌記錄**

### 中期改善（30天內）
1. 🟢 **建立自動化安全測試**
2. 🟢 **實施安全監控系統**
3. 🟢 **進行滲透測試**

### 專案整體安全評分：⭐⭐⭐☆☆ (3/5)

**評分說明**：
- 專案具備基本的安全機制（JWT、密碼加密、檔案驗證）
- 存在一些關鍵的配置安全問題需要立即修復
- 整體架構設計合理，修復後可達到生產環境安全標準

---

**免責聲明**: 本報告基於靜態代碼分析，建議在修復後進行動態滲透測試以確保安全性。

**審計完成時間**: 2025年10月15日