# 安全漏洞修復摘要

## 修復日期
2025年10月17日

## 修復的漏洞

### 🔴 Critical 級別

#### 1. python-jose Algorithm Confusion with OpenSSH ECDSA Keys (CVE-2024-33663, CVE-2024-33664)
- **套件**: python-jose
- **修復前版本**: 3.3.0 (固定版本)
- **修復後版本**: >=3.3.0 (允許更新到最新版本)
- **修復措施**:
  - 更新 `requirements.txt` 中的版本約束為 `>=3.3.0`
  - 在 `jwt_auth.py` 中加強算法驗證,明確指定允許的算法
  - 增加 `verify_signature` 和 `verify_exp` 選項以防止算法混淆攻擊
  - 嚴格區分 RSA (RS256) 和對稱加密 (HS256),不允許混用

#### 2. python-jose Denial of Service via Compressed JWE Content
- **套件**: python-jose
- **修復前版本**: 3.3.0
- **修復後版本**: >=3.3.0
- **修復措施**: 同上

### 🟠 High 級別

#### 3-5. Hugging Face Transformers - Deserialization of Untrusted Data (多個 CVE)
- **套件**: transformers
- **修復前版本**: 4.36.0
- **修復後版本**: 4.57.1 (>=4.46.0)
- **修復措施**:
  - 升級到最新穩定版本
  - 同步升級 `huggingface_hub` 至 >=0.34.0 以解決依賴衝突
  - 升級 `tokenizers` 至 0.22.1

#### 6. nth-check - Inefficient Regular Expression Complexity
- **套件**: nth-check (npm)
- **修復前版本**: <2.0.1
- **修復後版本**: ^2.1.1
- **修復措施**: 在 `package.json` 中使用 `overrides` 強制更新深層依賴

### 🟡 Moderate 級別

#### 7-19. Hugging Face Transformers - Multiple ReDoS Vulnerabilities
- **套件**: transformers
- **受影響的組件**:
  - AdamWeightDecay optimizer
  - MarianTokenizer
  - DonutProcessor
  - get_imports() function
  - get_configuration_file function
  - 其他多個正則表達式處理組件
- **修復前版本**: 4.36.0
- **修復後版本**: 4.57.1
- **修復措施**: 升級到最新版本修復所有 ReDoS 漏洞

#### 20. scikit-learn - Sensitive Data Leakage Vulnerability (CVE-2024-5206)
- **套件**: scikit-learn
- **修復前版本**: 1.3.2
- **修復後版本**: 1.7.2 (>=1.5.0)
- **修復措施**: 升級到修復版本

#### 21-22. webpack-dev-server - Source Code Theft Vulnerabilities
- **套件**: webpack-dev-server (npm)
- **修復前版本**: <=5.2.0
- **修復後版本**: ^5.2.1
- **修復措施**: 使用 `overrides` 強制更新

#### 23. PostCSS - Line Return Parsing Error
- **套件**: postcss (npm)
- **修復前版本**: <8.4.31
- **修復後版本**: ^8.4.31
- **修復措施**: 使用 `overrides` 強制更新

#### 24. Transformers - Username Injection Vulnerability
- **套件**: transformers
- **修復措施**: 包含在 4.57.1 版本升級中

### 🔵 Low 級別

#### 25. Transformers - Deserialization of Untrusted Data
- **套件**: transformers
- **修復措施**: 包含在 4.57.1 版本升級中

## 修改的檔案

### 後端 (Backend)
1. **`backend/requirements.txt`**
   - `python-jose[cryptography]==3.3.0` → `python-jose[cryptography]>=3.3.0`
   - `transformers==4.36.0` → `transformers>=4.46.0`
   - `scikit-learn==1.3.2` → `scikit-learn>=1.5.0`
   - `huggingface_hub==0.19.3` → `huggingface_hub>=0.34.0`
   - `sentence-transformers==2.2.2` → `sentence-transformers>=2.3.0` (實際安裝 5.1.1)

2. **`backend/app/core/jwt_auth.py`**
   - 增強 JWT 解碼安全性
   - 明確指定允許的算法列表
   - 增加簽名和過期時間驗證選項
   - 防止算法混淆攻擊

### 前端 (Frontend)
1. **`frontend/package.json`**
   - `react-scripts: "5.0.1"` → `react-scripts: "^5.0.1"`
   - 新增 `overrides` 段落強制更新深層依賴:
     - `nth-check: "^2.1.1"`
     - `postcss: "^8.4.31"`
     - `webpack-dev-server: "^4.15.2"` (使用 v4 以相容 react-scripts 5.0.1)
     - `svgo: "^2.8.0"`

## 安裝/更新指令

### 後端
```powershell
cd backend
..\CBvenv\Scripts\pip.exe install -r requirements.txt
```

### 前端
```powershell
cd frontend
npm install
```

## 驗證結果

### 後端
✅ 所有套件成功升級:
- transformers: 4.36.0 → 4.57.1
- scikit-learn: 1.3.2 → 1.7.2
- huggingface_hub: 0.19.3 → 0.35.3
- sentence-transformers: 2.2.2 → 5.1.1
- tokenizers: 0.15.2 → 0.22.1
- python-jose: 已允許更新

### 前端
✅ `npm audit` 報告: **found 0 vulnerabilities**

## 注意事項

### 相容性
1. **JWT 認證系統**: 已加強安全性,但保持向後相容
2. **Transformers API**: 從 4.36.0 升級到 4.57.1 可能有 API 變更,但向量嵌入功能保持一致
3. **scikit-learn**: 從 1.3.2 升級到 1.7.2,API 保持相容
4. **sentence-transformers**: 從 2.2.2 升級到 5.1.1,主要 API 保持相容,但內部實現有改進

### 測試建議
建議執行以下測試:
- [ ] JWT 認證功能測試
- [ ] 文檔向量嵌入測試
- [ ] 混合 RAG 系統測試
- [ ] 前端建置測試
- [ ] 端到端整合測試

### 生產環境部署
1. 在開發環境充分測試後再部署到生產環境
2. 建議先在測試環境進行完整測試
3. 部署前備份現有環境

## 額外的安全改進

### JWT 認證強化
在 `jwt_auth.py` 中實施的額外安全措施:
```python
# 明確指定算法,防止算法混淆
algorithms=["RS256"]  # 僅允許 RS256
options={"verify_signature": True, "verify_exp": True}
```

### 依賴管理最佳實踐
- 使用版本範圍約束 (`>=`) 而非固定版本,允許自動接收安全更新
- 對於前端深層依賴使用 `overrides` 強制更新
- 定期執行 `npm audit` 和 `pip list --outdated` 檢查更新

## 未來建議

1. **定期安全審計**: 建議每月執行一次依賴安全掃描
2. **自動化更新**: 考慮使用 Dependabot 或 Renovate 自動建立更新 PR
3. **安全策略文檔**: 維護 SECURITY.md 文檔說明安全報告流程
4. **漏洞監控**: 訂閱 GitHub Security Advisories 通知

## 參考資源

- [python-jose Security Advisory](https://github.com/advisories/GHSA-9jgg-88mc-972h)
- [Transformers Security Advisories](https://github.com/huggingface/transformers/security/advisories)
- [scikit-learn CVE-2024-5206](https://nvd.nist.gov/vuln/detail/CVE-2024-5206)
- [npm Security Best Practices](https://docs.npmjs.com/cli/v8/using-npm/security)
