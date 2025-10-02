import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Chip,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  People as PeopleIcon,
  Chat as ChatIcon,
  Description as DocumentIcon,
  TrendingUp as TrendingUpIcon
} from '@mui/icons-material';
import api from '../services/api';

// 記憶體快取（3分鐘 TTL）
const cache = {
  statistics: { data: null, timestamp: 0 },
  users: { data: null, timestamp: 0 },
  documents: { data: null, timestamp: 0 }
};
const CACHE_TTL = 3 * 60 * 1000; // 3 分鐘

// 請求去重標記
let loadingPromise = null;

function AdminDashboard() {
  const [statistics, setStatistics] = useState(null);
  const [users, setUsers] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // 編輯用戶對話框
  const [editUserDialog, setEditUserDialog] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  
  // AbortController refs
  const abortControllerRef = useRef(null);
  const isMountedRef = useRef(true);
  
  useEffect(() => {
    isMountedRef.current = true;
    loadData();
    
    // Cleanup on unmount
    return () => {
      isMountedRef.current = false;
      // 不要在組件卸載時取消請求，讓請求自然完成
      // if (abortControllerRef.current) {
      //   abortControllerRef.current.abort();
      // }
    };
  }, []);

  const loadData = async (force = false) => {
    // 請求去重：如果已有進行中的請求，直接返回該 Promise
    if (loadingPromise && !force) {
      return loadingPromise;
    }

    // 檢查快取（僅在非強制刷新時）
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

    // 取消之前的請求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // 創建新的 AbortController
    abortControllerRef.current = new AbortController();
    const timeoutId = setTimeout(() => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    }, 45000); // 45 秒超時，給 DevTunnels 更多時間

    loadingPromise = (async () => {
      try {
        const [statsResponse, usersResponse, docsResponse] = await Promise.all([
          api.get('/admin/statistics', { signal: abortControllerRef.current.signal }),
          api.get('/admin/users', { signal: abortControllerRef.current.signal }),
          api.get('/documents', { signal: abortControllerRef.current.signal })
        ]);
        
        // 只有當組件還在時才更新狀態
        if (!isMountedRef.current) return;

        // 更新快取
        const timestamp = Date.now();
        cache.statistics = { data: statsResponse.data, timestamp };
        cache.users = { data: usersResponse.data, timestamp };
        cache.documents = { data: docsResponse.data, timestamp };

        setStatistics(statsResponse.data);
        setUsers(usersResponse.data);
        setDocuments(docsResponse.data);
      } catch (err) {
        if (!isMountedRef.current) return;

        // 只有真正的超時才顯示超時錯誤
        if (err.name === 'AbortError' || err.name === 'CanceledError') {
          // 不顯示錯誤，讓使用者可以重試
          if (process.env.NODE_ENV === 'development') console.debug('Admin data loading was cancelled', err);
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
  };

  const handleEditUser = (user) => {
    setEditingUser({ ...user });
    setEditUserDialog(true);
  };

  const handleSaveUser = async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000); // 45 秒超時

    try {
      await api.put(`/admin/users/${editingUser.id}`, {
        username: editingUser.username,
        email: editingUser.email,
        is_active: editingUser.is_active,
        is_admin: editingUser.is_admin
      }, { signal: controller.signal });
      
      setEditUserDialog(false);
      loadData(true); // 強制刷新
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
      const timeoutId = setTimeout(() => controller.abort(), 45000); // 45 秒超時

      try {
        await api.delete(`/admin/users/${userId}`, { signal: controller.signal });
        loadData(true); // 強制刷新
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
      const timeoutId = setTimeout(() => controller.abort(), 45000); // 45 秒超時

      try {
        await api.delete(`/documents/${docId}`, { signal: controller.signal });
        loadData(true); // 強制刷新
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
      <Box display="flex" justifyContent="center" alignItems="center" height="50vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        管理後台
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* 統計卡片 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <PeopleIcon color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography variant="h6">{statistics?.users?.total || 0}</Typography>
                  <Typography color="textSecondary">總用戶數</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <ChatIcon color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography variant="h6">{statistics?.conversations?.total || 0}</Typography>
                  <Typography color="textSecondary">總對話數</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <DocumentIcon color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography variant="h6">{statistics?.documents?.total || 0}</Typography>
                  <Typography color="textSecondary">文件數量</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <TrendingUpIcon color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography variant="h6">{statistics?.messages?.recent_7_days || 0}</Typography>
                  <Typography color="textSecondary">近7天消息</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 用戶管理 */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>用戶管理</Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>用戶名</TableCell>
                <TableCell>郵箱</TableCell>
                <TableCell>狀態</TableCell>
                <TableCell>權限</TableCell>
                <TableCell>註冊時間</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>{user.id}</TableCell>
                  <TableCell>{user.username}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <Chip 
                      label={user.is_active ? '活躍' : '停用'} 
                      color={user.is_active ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={user.is_admin ? '管理員' : '用戶'} 
                      color={user.is_admin ? 'primary' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {new Date(user.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Button 
                      size="small" 
                      onClick={() => handleEditUser(user)}
                      sx={{ mr: 1 }}
                    >
                      編輯
                    </Button>
                    <Button 
                      size="small" 
                      color="error"
                      onClick={() => handleDeleteUser(user.id)}
                    >
                      刪除
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 文件管理 */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>文件管理</Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>文件名</TableCell>
                <TableCell>類型</TableCell>
                <TableCell>狀態</TableCell>
                <TableCell>上傳時間</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {documents.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell>{doc.id}</TableCell>
                  <TableCell>{doc.filename}</TableCell>
                  <TableCell>{doc.file_type}</TableCell>
                  <TableCell>
                    <Chip 
                      label={doc.is_processed ? '已處理' : '處理中'} 
                      color={doc.is_processed ? 'success' : 'warning'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {new Date(doc.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Button 
                      size="small" 
                      color="error"
                      onClick={() => handleDeleteDocument(doc.id)}
                    >
                      刪除
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 編輯用戶對話框 */}
      <Dialog open={editUserDialog} onClose={() => setEditUserDialog(false)}>
        <DialogTitle>編輯用戶</DialogTitle>
        <DialogContent>
          {editingUser && (
            <Box sx={{ pt: 1 }}>
              <TextField
                fullWidth
                label="用戶名"
                value={editingUser.username}
                onChange={(e) => setEditingUser({...editingUser, username: e.target.value})}
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="郵箱"
                value={editingUser.email}
                onChange={(e) => setEditingUser({...editingUser, email: e.target.value})}
                sx={{ mb: 2 }}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={editingUser.is_active}
                    onChange={(e) => setEditingUser({...editingUser, is_active: e.target.checked})}
                  />
                }
                label="帳號活躍"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={editingUser.is_admin}
                    onChange={(e) => setEditingUser({...editingUser, is_admin: e.target.checked})}
                  />
                }
                label="管理員權限"
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditUserDialog(false)}>取消</Button>
          <Button onClick={handleSaveUser} variant="contained">保存</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default AdminDashboard;
