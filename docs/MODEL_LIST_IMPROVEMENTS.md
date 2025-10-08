# 模型列表更新功能改進說明

## 📅 更新日期
2025年10月8日

## 📋 改進概述

本次更新為 ChatBot 應用程式的模型列表功能添加了以下五個重要改進：

### 1. ✅ 手動刷新按鈕
- **位置**: 模型選擇器右側
- **功能**: 允許用戶立即更新模型列表，無需等待自動輪詢
- **特點**: 
  - 使用 Material-UI RefreshIcon
  - 顯示 Tooltip 提示文字
  - 載入時自動禁用
  - 成功刷新後顯示 Snackbar 通知

### 2. ✅ 載入狀態指示
- **位置**: 模型選擇器內部（右側）
- **功能**: 在獲取模型列表時顯示旋轉的載入指示器
- **實現**: 
  - 新增 `modelsLoading` 狀態
  - 使用 `CircularProgress` 組件
  - 載入期間禁用模型選擇器和刷新按鈕

### 3. ✅ 改進錯誤提示（Snackbar）
- **位置**: 頁面右下角
- **功能**: 以非侵入式方式顯示成功/錯誤訊息
- **特點**:
  - 自動 6 秒後消失
  - 支持三種嚴重性級別：success, warning, error
  - 可手動關閉
  - 不阻擋用戶操作

**訊息類型**:
- ✅ 成功: "已更新模型列表 (X 個模型)"
- ⚠️ 警告: "載入可用模型失敗，已改為使用預設模型"

### 4. ✅ 可配置輪詢間隔
- **配置方式**: 前端環境變數
- **變數名稱**: `REACT_APP_MODEL_POLL_INTERVAL_MS`
- **單位**: 毫秒
- **預設值**: 300000 (5分鐘)

**配置示例**:
```env
# 1 分鐘輪詢
REACT_APP_MODEL_POLL_INTERVAL_MS=60000

# 3 分鐘輪詢
REACT_APP_MODEL_POLL_INTERVAL_MS=180000

# 10 分鐘輪詢
REACT_APP_MODEL_POLL_INTERVAL_MS=600000
```

### 5. ✅ 模型詳細信息顯示
- **位置**: 模型選擇器下拉菜單
- **顯示內容**:
  - 模型名稱（主行）
  - 模型家族（family）
  - 參數大小（size/parameter_size）
  - 量化級別（quantization_level）

**示例顯示**:
```
qwen3:30b
qwen3moe • 30.5B • Q4_K_M

deepseek-r1:14b
qwen2 • 14.8B • Q4_K_M
```

---

## 🔧 技術實現細節

### 新增狀態管理
```javascript
const [modelDetails, setModelDetails] = useState([]);  // 模型詳細信息
const [modelsLoading, setModelsLoading] = useState(false);  // 載入狀態
const [snackbar, setSnackbar] = useState({ 
  open: false, 
  message: '', 
  severity: 'info' 
});  // Snackbar 狀態
```

### 數據流程改進
1. **API 請求**: `/api/external-tags` 或 `/api/tags`
2. **數據解析**: 提取模型名稱和詳細信息
3. **狀態更新**: `setAvailableModels()` + `setModelDetails()`
4. **緩存**: localStorage 存儲（包含詳細信息）
5. **UI 渲染**: MenuItem 顯示雙行內容

### 緩存策略優化
```javascript
// 緩存數據結構
{
  models: ['qwen3:30b', 'deepseek-r1:14b'],
  details: [
    { name: 'qwen3:30b', size: '30.5B', family: 'qwen3moe', ... },
    { name: 'deepseek-r1:14b', size: '14.8B', family: 'qwen2', ... }
  ],
  default: 'gpt-oss:20b'
}
```

---

## 🎨 UI/UX 改進

### 改進前
- ❌ 無法手動刷新
- ❌ 載入時無視覺反饋
- ❌ 錯誤訊息遮擋內容
- ❌ 輪詢間隔固定
- ❌ 僅顯示模型名稱

### 改進後
- ✅ 刷新按鈕 + Tooltip
- ✅ CircularProgress 指示器
- ✅ Snackbar 非侵入式通知
- ✅ 環境變數可配置
- ✅ 雙行顯示詳細信息

---

## 📦 相關文件修改

### 1. `frontend/src/pages/Chat.js`
**主要變更**:
- 新增 import: `Snackbar`, `Tooltip`, `RefreshIcon`
- 新增狀態: `modelDetails`, `modelsLoading`, `snackbar`
- 更新 `loadAvailableModels` 函數（支持詳細信息提取）
- 更新輪詢 useEffect（支持環境變數配置）
- 更新模型選擇器 UI（顯示詳細信息 + 刷新按鈕）
- 新增 Snackbar 組件

### 2. `frontend/.env`
**新增配置**:
```env
# === 模型列表輪詢配置 ===
# REACT_APP_MODEL_POLL_INTERVAL_MS=300000
```

### 3. `docs/MODEL_LIST_IMPROVEMENTS.md`
**新增文檔**: 本說明文件

---

## 🧪 測試建議

### 手動測試清單
- [ ] 刷新按鈕點擊測試
- [ ] 載入狀態顯示測試
- [ ] Snackbar 訊息顯示測試
- [ ] 模型詳細信息渲染測試
- [ ] 環境變數配置測試
- [ ] 緩存機制測試
- [ ] 錯誤處理測試

### 測試步驟
1. **刷新按鈕**:
   - 點擊刷新按鈕
   - 觀察載入指示器
   - 確認 Snackbar 訊息
   - 驗證模型列表更新

2. **載入狀態**:
   - 首次載入頁面
   - 觀察選擇器中的 CircularProgress
   - 確認載入期間按鈕禁用

3. **詳細信息**:
   - 打開模型下拉菜單
   - 確認雙行顯示
   - 驗證信息準確性

4. **環境配置**:
   - 修改 `.env` 中的 `REACT_APP_MODEL_POLL_INTERVAL_MS`
   - 重啟前端服務
   - 在控制台確認間隔日誌

---

## 🚀 後續優化建議

### 短期優化
- [ ] 添加模型圖標/標籤（基於家族或大小）
- [ ] 支持模型搜索/過濾功能
- [ ] 添加模型收藏功能
- [ ] 顯示模型上次更新時間

### 中期優化
- [ ] 模型性能指標顯示（速度、準確度等）
- [ ] 模型比較功能
- [ ] 歷史模型使用記錄
- [ ] 智能推薦模型（基於場景）

### 長期優化
- [ ] 模型管理後台（管理員）
- [ ] 自定義模型上傳
- [ ] 模型版本控制
- [ ] A/B 測試不同模型

---

## 📚 相關文檔

- [RAG 系統說明書](./RAG_系統說明書.md)
- [快速啟動指南](../QUICK-START.md)
- [本地開發設置](../LOCAL_DEVELOPMENT_SETUP.md)

---

## 👥 貢獻者

- **開發**: GitHub Copilot
- **需求**: 用戶反饋
- **測試**: 待補充

---

## 📝 變更日誌

### v1.1.0 (2025-10-08)
- ✨ 新增手動刷新按鈕
- ✨ 新增載入狀態指示
- ✨ 改進錯誤提示（Snackbar）
- ✨ 支持可配置輪詢間隔
- ✨ 顯示模型詳細信息

### v1.0.0 (原始版本)
- ✅ 基礎模型列表功能
- ✅ 自動輪詢（5分鐘）
- ✅ 緩存機制
- ✅ 容錯處理

---

## ⚠️ 注意事項

1. **緩存有效期**: 5分鐘，可能導致詳細信息短暫不同步
2. **API 依賴**: 需要後端 `/api/external-tags` 或 `/api/tags` 正常工作
3. **環境變數**: 修改後需重啟前端服務才能生效
4. **性能考量**: 詳細信息增加了數據傳輸量，但影響微乎其微

---

**文檔版本**: 1.0  
**最後更新**: 2025年10月8日  
**維護者**: GitHub Copilot
