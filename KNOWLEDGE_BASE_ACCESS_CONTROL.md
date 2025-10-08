# 知識庫管理權限限制說明

## 修改日期
2025年10月8日

## 問題修復記錄
### 2025年10月8日 - 修復管理員儀表板 403 錯誤
**問題**：管理員儀表板嘗試載入文檔列表時出現 403 錯誤
**原因**：AdminDashboard.js 使用 `/api/documents/` 而非 `/api/admin/documents`
**解決方案**：將 AdminDashboard.js 中的 API 調用改為 `/admin/documents`

## 修改目的
確保只有管理員（`is_admin=True`）可以訪問知識庫管理功能，普通用戶（`role=user`）無法上傳、查看或刪除知識庫文件。

## 修改內容

### 1. 後端 API 權限加固
**檔案**: `backend/app/api/documents.py`

#### 修改項目：
1. **導入管理員驗證函數**
   ```python
   from app.core.jwt_auth import get_current_admin_user
   ```

2. **所有端點添加管理員權限檢查**
   - `POST /api/documents/upload` - 上傳文件（需要管理員權限）
   - `GET /api/documents/` - 獲取文件列表（需要管理員權限）
   - `DELETE /api/documents/{document_id}` - 刪除文件（需要管理員權限）

#### 修改細節：
```python
# 上傳文件
@router.post("/upload")
async def upload_document(
    file: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    current_user: dict = Depends(get_current_admin_user)  # ✅ 新增
):
    """上傳文件到知識庫（需要管理員權限）"""

# 獲取文件列表
@router.get("/")
async def get_documents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)  # ✅ 新增
):
    """獲取文件列表（需要管理員權限）"""

# 刪除文件
@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)  # ✅ 新增
):
    """刪除文件（需要管理員權限）"""
```

### 2. 前端導航欄權限控制
**檔案**: `frontend/src/components/Layout.js`

#### 修改項目：
只為管理員顯示"知識庫"按鈕

```javascript
{user?.is_admin && (
  <Button 
    color="inherit" 
    startIcon={<Description />}
    onClick={() => navigate('/documents')}
  >
    知識庫
  </Button>
)}
```

**效果**：
- ✅ 管理員：可以看到並點擊"知識庫"按鈕
- ❌ 普通用戶：完全看不到"知識庫"按鈕

### 3. 前端路由權限保護
**檔案**: `frontend/src/App.js`

#### 修改項目：
將 documents 路由從 `PrivateRoute` 改為 `AdminRoute`

```javascript
{ 
  path: 'documents', 
  element: <AdminRoute element={<Documents />} />  // ✅ 改為 AdminRoute
},
```

**效果**：
- ✅ 管理員：可以訪問 `/documents` 路由
- ❌ 普通用戶：訪問 `/documents` 會被重定向到聊天頁面

## 安全保護層級

### 三層防護機制：
1. **後端 API 層**：所有知識庫相關 API 都需要管理員 JWT Token
2. **前端路由層**：`AdminRoute` 組件阻止非管理員訪問頁面
3. **前端 UI 層**：普通用戶看不到知識庫入口按鈕

## 測試建議

### 管理員測試：
1. 登入管理員帳號
2. 檢查導航欄是否顯示"知識庫"按鈕
3. 點擊進入知識庫管理頁面
4. 測試上傳、查看、刪除文件功能

### 普通用戶測試：
1. 登入普通用戶帳號
2. 確認導航欄**沒有**"知識庫"按鈕
3. 嘗試直接訪問 `http://localhost:3000/documents`
   - 應該被重定向到聊天頁面
4. 嘗試直接調用 API（使用 Postman 或瀏覽器開發者工具）
   ```bash
   GET /api/documents/
   POST /api/documents/upload
   DELETE /api/documents/{id}
   ```
   - 所有請求應返回 `403 Forbidden` 或類似權限錯誤

## 相關檔案
- `backend/app/api/documents.py` - 知識庫 API 端點（僅管理員可訪問）
- `backend/app/api/admin.py` - 管理員 API 端點（包含 `/admin/documents`）
- `backend/app/core/jwt_auth.py` - JWT 驗證與權限檢查
- `frontend/src/components/Layout.js` - 導航欄組件
- `frontend/src/components/PrivateRoute.js` - 路由保護組件
- `frontend/src/App.js` - 路由配置
- `frontend/src/pages/AdminDashboard.js` - 管理員儀表板（使用 `/admin/documents`）
- `frontend/src/pages/Documents.js` - 知識庫管理頁面（使用 `/documents`）

## 注意事項
1. 確保 `get_current_admin_user` 函數正確驗證用戶的 `is_admin` 標記
2. 如果未來添加新的知識庫相關端點，記得添加 `Depends(get_current_admin_user)`
3. 前端的權限控制主要用於 UX，真正的安全防護在後端 API
4. **重要**：管理員儀表板應使用 `/admin/documents`，知識庫管理頁面使用 `/documents`
   - `/admin/documents` - 簡單的列表查詢（用於儀表板統計）
   - `/documents` - 完整的 CRUD 操作（用於知識庫管理頁面）

## 回滾方案
如需恢復普通用戶訪問權限，修改：
1. 移除 `documents.py` 中的 `current_user: dict = Depends(get_current_admin_user)` 參數
2. 移除 `Layout.js` 中知識庫按鈕的 `user?.is_admin &&` 條件
3. 將 `App.js` 中的 `AdminRoute` 改回 `PrivateRoute`
