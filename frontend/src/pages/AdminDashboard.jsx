import { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import {
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  Chip,
  Alert,
  Spinner,
  Icon
} from '../components/ui';
import styles from './AdminDashboard.module.css';
const cache = {
  statistics: { data: null, timestamp: 0 },
  users: { data: null, timestamp: 0 },
  documents: { data: null, timestamp: 0 }
};
const CACHE_TTL = 3 * 60 * 1000;
let loadingPromise = null;
function AdminDashboard() {
  const [statistics, setStatistics] = useState(null);
  const [users, setUsers] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editUserDialog, setEditUserDialog] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const abortControllerRef = useRef(null);
  const isMountedRef = useRef(true);
  const loadData = useCallback(async (force = false) => {
    if (loadingPromise && !force) {
      return loadingPromise;
    }
    const now = Date.now();
    if (!force) {
      const statsValid = cache.statistics.data && (now - cache.statistics.timestamp) < CACHE_TTL;
      const usersValid = cache.users.data && (now - cache.users.timestamp) < CACHE_TTL;
      const docsValid = cache.documents.data && (now - cache.documents.timestamp) < CACHE_TTL;
      if (statsValid && usersValid && docsValid) {
        setStatistics(cache.statistics.data);
        setUsers(cache.users.data);
        setDocuments(cache.documents.data);
        setLoading(false);
        return;
      }
    }
    setLoading(true);
    setError('');
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    const timeoutId = setTimeout(() => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    }, 45000);
    loadingPromise = (async () => {
      try {
        const [statsResponse, usersResponse, docsResponse] = await Promise.all([
          api.get('/admin/statistics', { signal: abortControllerRef.current.signal }),
          api.get('/admin/users', { signal: abortControllerRef.current.signal }),
          api.get('/admin/documents', { signal: abortControllerRef.current.signal })
        ]);
        if (!isMountedRef.current) return;
        const timestamp = Date.now();
        cache.statistics = { data: statsResponse.data, timestamp };
        cache.users = { data: usersResponse.data, timestamp };
        cache.documents = { data: docsResponse.data, timestamp };
        setStatistics(statsResponse.data);
        setUsers(usersResponse.data);
        setDocuments(docsResponse.data);
      } catch (err) {
        if (!isMountedRef.current) return;
        if (err.name === 'AbortError' || err.name === 'CanceledError') {
          if (import.meta.env.DEV) console.debug('Admin data loading was cancelled', err);
        } else {
          setError('載入數據失敗：' + (err.response?.data?.detail || err.message || '未知錯誤'));
        }
        console.error('Admin data loading error:', err);
      } finally {
        clearTimeout(timeoutId);
        setLoading(false);
        loadingPromise = null;
      }
    })();
    return loadingPromise;
  }, []);
  useEffect(() => {
    isMountedRef.current = true;
    queueMicrotask(() => {
      loadData();
    });
    return () => {
      isMountedRef.current = false;
    };
  }, [loadData]);
  const handleEditUser = (user) => {
    setEditingUser({ ...user });
    setEditUserDialog(true);
  };
  const handleSaveUser = async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);
    try {
      await api.put(`/admin/users/${editingUser.id}`, {
        username: editingUser.username,
        email: editingUser.email,
        is_active: editingUser.is_active,
        is_admin: editingUser.is_admin
      }, { signal: controller.signal });
      setEditUserDialog(false);
      loadData(true);
    } catch (err) {
      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        setError('更新用戶超時，請稍後再試');
      } else {
        setError('更新用戶失敗：' + (err.response?.data?.detail || err.message));
      }
      console.error('Update user error:', err);
    } finally {
      clearTimeout(timeoutId);
    }
  };
  const handleDeleteUser = async (userId) => {
    if (window.confirm('確定要刪除此用戶嗎？此操作不可逆！')) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 45000);
      try {
        await api.delete(`/admin/users/${userId}`, { signal: controller.signal });
        loadData(true);
      } catch (err) {
        if (err.name === 'AbortError' || err.name === 'CanceledError') {
          setError('刪除用戶超時，請稍後再試');
        } else {
          setError('刪除用戶失敗：' + (err.response?.data?.detail || err.message));
        }
        console.error('Delete user error:', err);
      } finally {
        clearTimeout(timeoutId);
      }
    }
  };
  const handleDeleteDocument = async (docId) => {
    if (window.confirm('確定要刪除此文件嗎？')) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 45000);
      try {
        await api.delete(`/documents/${docId}`, { signal: controller.signal });
        loadData(true);
      } catch (err) {
        if (err.name === 'AbortError' || err.name === 'CanceledError') {
          setError('刪除文件超時，請稍後再試');
        } else {
          setError('刪除文件失敗：' + (err.response?.data?.detail || err.message));
        }
        console.error('Delete document error:', err);
      } finally {
        clearTimeout(timeoutId);
      }
    }
  };
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <Spinner size={36} color="var(--color-primary)" />
      </div>
    );
  }
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>管理後台</h1>
      {error && (
        <Alert severity="error" style={{ marginBottom: '16px' }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {/* 統計卡片 */}
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statIcon}>
            <Icon name="people" size={24} />
          </div>
          <div>
            <div className={styles.statValue}>{statistics?.users?.total || 0}</div>
            <div className={styles.statLabel}>總用戶數</div>
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statIcon}>
            <Icon name="chat" size={24} />
          </div>
          <div>
            <div className={styles.statValue}>{statistics?.conversations?.total || 0}</div>
            <div className={styles.statLabel}>總對話數</div>
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statIcon}>
            <Icon name="description" size={24} />
          </div>
          <div>
            <div className={styles.statValue}>{statistics?.documents?.total || 0}</div>
            <div className={styles.statLabel}>文件數量</div>
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statIcon}>
            <Icon name="speed" size={24} />
          </div>
          <div>
            <div className={styles.statValue}>{statistics?.messages?.recent_7_days || 0}</div>
            <div className={styles.statLabel}>近7天消息</div>
          </div>
        </div>
      </div>
      {/* 用戶管理表格 */}
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>用戶管理</h2>
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>ID</th>
                <th>用戶名</th>
                <th>郵箱</th>
                <th>狀態</th>
                <th>權限</th>
                <th>註冊時間</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.id}</td>
                  <td>{user.username}</td>
                  <td>{user.email}</td>
                  <td>
                    <Chip
                      label={user.is_active ? '活躍' : '停用'}
                      color={user.is_active ? 'success' : 'error'}
                      size="sm"
                    />
                  </td>
                  <td>
                    <Chip
                      label={user.is_admin ? '管理員' : '用戶'}
                      color={user.is_admin ? 'primary' : 'default'}
                      size="sm"
                    />
                  </td>
                  <td>
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <div className={styles.tableActions}>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleEditUser(user)}
                      >
                        編輯
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => handleDeleteUser(user.id)}
                      >
                        刪除
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {/* 文件管理表格 */}
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>文件管理</h2>
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>ID</th>
                <th>文件名</th>
                <th>類型</th>
                <th>狀態</th>
                <th>上傳時間</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.id}</td>
                  <td>{doc.filename}</td>
                  <td>{doc.file_type}</td>
                  <td>
                    <Chip
                      label={doc.is_processed ? '已處理' : '處理中'}
                      color={doc.is_processed ? 'success' : 'warning'}
                      size="sm"
                    />
                  </td>
                  <td>
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleDeleteDocument(doc.id)}
                    >
                      刪除
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {/* 編輯用戶 Dialog */}
      <Dialog
        open={editUserDialog}
        onClose={() => setEditUserDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>編輯用戶</DialogTitle>
        <DialogContent>
          {editingUser && (
            <div className={styles.editUserForm}>
              <TextField
                fullWidth
                label="用戶名"
                value={editingUser.username}
                onChange={(e) => setEditingUser({ ...editingUser, username: e.target.value })}
              />
              <TextField
                fullWidth
                label="郵箱"
                value={editingUser.email}
                onChange={(e) => setEditingUser({ ...editingUser, email: e.target.value })}
              />
              <Switch
                checked={editingUser.is_active}
                onChange={(e) => setEditingUser({ ...editingUser, is_active: e.target.checked })}
                label="帳號活躍"
              />
              <Switch
                checked={editingUser.is_admin}
                onChange={(e) => setEditingUser({ ...editingUser, is_admin: e.target.checked })}
                label="管理員權限"
              />
            </div>
          )}
        </DialogContent>
        <DialogActions>
          <Button variant="secondary" onClick={() => setEditUserDialog(false)}>
            取消
          </Button>
          <Button variant="primary" onClick={handleSaveUser}>
            保存
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}
export default AdminDashboard;