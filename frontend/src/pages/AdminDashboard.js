import React, { useState, useEffect } from 'react';
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
import axios from 'axios';

function AdminDashboard() {
  const [statistics, setStatistics] = useState(null);
  const [users, setUsers] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // 編輯用戶對話框
  const [editUserDialog, setEditUserDialog] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsResponse, usersResponse, docsResponse] = await Promise.all([
        axios.get('/api/admin/statistics'),
        axios.get('/api/admin/users'),
        axios.get('/api/documents/')
      ]);
      
      setStatistics(statsResponse.data);
  // normalize responses to arrays to avoid runtime map errors
  setUsers(Array.isArray(usersResponse.data) ? usersResponse.data : (usersResponse.data ? [usersResponse.data] : []));
  setDocuments(Array.isArray(docsResponse.data) ? docsResponse.data : (docsResponse.data ? [docsResponse.data] : []));
    } catch (err) {
      setError('載入數據失敗');
      console.error('Admin data loading error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEditUser = (user) => {
    setEditingUser({ ...user });
    setEditUserDialog(true);
  };

  const handleSaveUser = async () => {
    try {
      await axios.put(`/api/admin/users/${editingUser.id}`, {
        username: editingUser.username,
        email: editingUser.email,
        is_active: editingUser.is_active,
        is_admin: editingUser.is_admin
      });
      
      setEditUserDialog(false);
      loadData();
    } catch (err) {
      setError('更新用戶失敗');
      console.error('Update user error:', err);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (window.confirm('確定要刪除此用戶嗎？此操作不可逆！')) {
      try {
        await axios.delete(`/api/admin/users/${userId}`);
        loadData();
      } catch (err) {
        setError('刪除用戶失敗');
        console.error('Delete user error:', err);
      }
    }
  };

  const handleDeleteDocument = async (docId) => {
    if (window.confirm('確定要刪除此文件嗎？')) {
      try {
        await axios.delete(`/api/documents/${docId}`);
        loadData();
      } catch (err) {
        setError('刪除文件失敗');
        console.error('Delete document error:', err);
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
              {(Array.isArray(users) ? users : []).map((user) => (
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
              {(Array.isArray(documents) ? documents : []).map((doc) => (
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
