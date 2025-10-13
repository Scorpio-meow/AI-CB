# ✅ 效能優化實施檢查清單

## 📋 部署前檢查

### 後端準備
- [x] ✅ 資料庫連接池配置已更新 (`app/models/database.py`)
- [x] ✅ 資料庫查詢優化已實施 (`app/services/chat_service.py`, `app/api/admin.py`)
- [x] ✅ 快取系統已建立 (`app/core/cache.py`)
- [x] ✅ 快取裝飾器已應用 (`app/api/admin.py`)
- [x] ✅ 效能配置檔案已創建 (`.env.performance`)
- [x] ✅ 效能測試腳本已建立 (`scripts/performance_test.py`)
- [ ] 待完成: 複製 `.env.performance` 到 `.env` 並調整參數

### 文檔準備
- [x] ✅ 完整優化報告 (`PERFORMANCE_OPTIMIZATION.md`)
- [x] ✅ 快速參考指南 (`PERFORMANCE_QUICK_REF.md`)
- [x] ✅ 前端優化指南 (`docs/FRONTEND_PERFORMANCE.md`)

---

## 🚀 部署步驟

### 步驟 1: 備份現有配置
```powershell
cd backend
cp .env .env.backup
cp chatbot.db chatbot.db.backup
```

### 步驟 2: 更新環境變數
```powershell
# 複製效能配置模板
cp .env.performance .env

# 編輯並根據需求調整
notepad .env
```

**必需配置項**:
```env
# 確保這些已設置
DATABASE_URL=sqlite:///./chatbot.db  # 或 PostgreSQL URL
MODEL_NAME=your-model-name
LLM_API_BASE=your-api-base
DB_POOL_SIZE=20
CACHE_ENABLED=true
```

### 步驟 3: 驗證依賴
```powershell
.\CBvenv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 步驟 4: 測試配置
```powershell
# 測試資料庫連接
python -c "from app.models.database import engine; print(engine.pool.size())"

# 測試快取系統
python -c "from app.core.cache import get_cache; cache = get_cache(); cache.set('test', 'ok'); print(cache.get('test'))"
```

### 步驟 5: 重啟服務
```powershell
# 方法 1: 使用 VS Code 任務
# Ctrl+Shift+P -> "Tasks: Run Task" -> "啟動完整系統"

# 方法 2: 手動啟動
cd backend
..\CBvenv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 步驟 6: 驗證部署
```powershell
# 檢查健康狀態
curl http://localhost:8001/health

# 執行效能測試
python scripts/performance_test.py
```

---

## 🧪 測試驗證

### 功能測試
- [ ] 用戶登入/登出正常
- [ ] 對話列表載入正常
- [ ] 發送訊息正常
- [ ] 文檔上傳正常
- [ ] 管理後台統計正常

### 效能測試
- [ ] `/health` 響應時間 < 50ms
- [ ] `/api/chat/conversations` 響應時間 < 200ms
- [ ] `/api/admin/statistics` 響應時間 < 300ms
- [ ] 快取命中率 > 50% (第二次請求)
- [ ] 並發 20 用戶無錯誤

### 日誌檢查
```powershell
# 檢查啟動日誌
Get-Content logs/app.log -Tail 50

# 檢查快取日誌 (使用分析工具)
.\analyze_logs.ps1 -Action cache-stats

# 檢查錯誤
.\analyze_logs.ps1 -Action errors
```

---

## 📊 效能基準

### 目標指標
| 端點 | 目標時間 | 檢查 |
|------|---------|------|
| GET /health | < 50ms | [ ] |
| GET /api/chat/models | < 100ms | [ ] |
| GET /api/chat/conversations | < 200ms | [ ] |
| POST /api/chat/send | < 2000ms | [ ] |
| GET /api/admin/statistics | < 300ms | [ ] |
| GET /api/documents/ | < 500ms | [ ] |

### 資料庫效能
- [ ] 連接池使用率 < 50%
- [ ] 平均查詢時間 < 100ms
- [ ] N+1 查詢已消除

### 快取效能
- [ ] 快取命中率 > 60%
- [ ] 快取響應時間 < 5ms
- [ ] 記憶體使用穩定

---

## 🔄 回滾計畫

### 如果出現問題

#### 快速回滾
```powershell
# 恢復舊配置
cd backend
cp .env.backup .env

# 重啟服務
# 使用 VS Code 任務重新啟動
```

#### 資料庫回滾
```powershell
# 如果資料庫出問題
cd backend
cp chatbot.db.backup chatbot.db
```

#### 完全回滾到優化前版本
```powershell
# 使用 git 回滾
git stash
git checkout <previous-commit>

# 重啟服務
```

---

## 📈 監控計畫

### 每日檢查 (第 1 週)
- [ ] 檢查錯誤日誌
- [ ] 驗證快取命中率
- [ ] 監控響應時間
- [ ] 檢查資料庫連接池

### 每週檢查 (第 1 月)
- [ ] 執行完整效能測試
- [ ] 分析慢查詢日誌
- [ ] 檢查記憶體使用
- [ ] 用戶反饋收集

### 效能告警閾值
```env
# 設定告警
ALERT_RESPONSE_TIME_MS=1000
ALERT_ERROR_RATE=0.05
ALERT_CACHE_HIT_RATE=0.4
ALERT_DB_POOL_USAGE=0.8
```

---

## 🎯 後續優化

### 短期 (1-2 週)
- [ ] 添加 Redis 快取替代記憶體快取
- [ ] 實施前端虛擬滾動
- [ ] 添加資料庫索引

### 中期 (1-2 月)
- [ ] 實施 APM 監控
- [ ] 優化 RAG 向量檢索
- [ ] 資料庫分區策略

### 長期 (3-6 月)
- [ ] 微服務拆分
- [ ] 向量資料庫升級
- [ ] CDN 部署

---

## 📞 支援

### 遇到問題？

1. **檢查日誌**: `logs/app.log`, `logs/security.log`
2. **執行測試**: `python scripts/performance_test.py`
3. **查看文檔**: `PERFORMANCE_OPTIMIZATION.md`
4. **效能分析**: 啟用 `SQLALCHEMY_ECHO=true` 查看 SQL 查詢

### 常見問題

**Q: 快取不生效？**
A: 檢查 `CACHE_ENABLED=true` 並重啟服務

**Q: 資料庫連接池滿了？**
A: 增加 `DB_POOL_SIZE` 和 `DB_MAX_OVERFLOW`

**Q: 響應時間還是慢？**
A: 檢查是否有慢查詢，啟用 SQL 日誌分析

---

## ✅ 完成確認

當所有檢查項目都完成後:

- [ ] 所有功能測試通過
- [ ] 所有效能測試達標
- [ ] 日誌無嚴重錯誤
- [ ] 用戶反饋正面
- [ ] 監控指標穩定

**簽署**: _____________  
**日期**: _____________  
**版本**: 1.0

---

**文檔版本**: 1.0  
**建立日期**: 2025年10月13日  
**維護者**: Development Team
