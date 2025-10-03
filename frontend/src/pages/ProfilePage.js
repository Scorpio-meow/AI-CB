/**
 * 用戶資料頁面
 */

import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Divider,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Person as PersonIcon,
  Lock as LockIcon,
  AdminPanelSettings as AdminIcon
} from '@mui/icons-material';
import authService from '../services/authService';

const ProfilePage = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // 修改密碼對話框
  const [passwordDialog, setPasswordDialog] = useState(false);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });

  useEffect(() => {
    loadUserProfile();
  }, []);

  const loadUserProfile = async () => {
    try {
      const userData = await authService.getCurrentUser();
      setUser(userData);
    } catch (err) {
      setError('載入用戶資料失敗');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (!passwordData.currentPassword || !passwordData.newPassword) {
      setError('請填寫所有密碼欄位');
      return;
    }

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setError('兩次密碼輸入不一致');
      return;
    }

    setUpdating(true);
    setError('');

    const result = await authService.changePassword(
      passwordData.currentPassword,
      passwordData.newPassword,
      passwordData.confirmPassword
    );

    setUpdating(false);

    if (result.success) {
      setSuccess('密碼修改成功');
      setPasswordDialog(false);
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
    } else {
      setError(result.error);
    }
  };

  const handleLogout = async () => {
    await authService.logout();
    window.location.href = '/login';
  };

  if (loading) {
    return (
      <Container>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (!user) {
    return (
      <Container>
        <Alert severity="error">無法載入用戶資料</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" gutterBottom>
            <PersonIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            用戶資料
          </Typography>
          <Typography variant="body2" color="text.secondary">
            管理您的帳號資訊和安全設定
          </Typography>
        </Box>

        {/* Messages */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}
        {success && (
          <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
            {success}
          </Alert>
        )}

        {/* Profile Card */}
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                基本資訊
              </Typography>
              {user.is_admin && (
                <Chip
                  icon={<AdminIcon />}
                  label="管理員"
                  color="primary"
                  size="small"
                />
              )}
            </Box>

            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary">
                用戶名
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {user.username}
              </Typography>
            </Box>

            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary">
                電子郵件
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {user.email}
              </Typography>
            </Box>

            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary">
                角色
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {user.role}
              </Typography>
            </Box>

            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary">
                帳號狀態
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {user.is_active ? (
                  <Chip label="已啟用" color="success" size="small" />
                ) : (
                  <Chip label="已停用" color="error" size="small" />
                )}
              </Typography>
            </Box>

            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary">
                註冊時間
              </Typography>
              <Typography variant="body1">
                {new Date(user.created_at).toLocaleString('zh-TW')}
              </Typography>
            </Box>

            {user.last_login && (
              <Box>
                <Typography variant="caption" color="text.secondary">
                  最後登入
                </Typography>
                <Typography variant="body1">
                  {new Date(user.last_login).toLocaleString('zh-TW')}
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>

        {/* Security Card */}
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              <LockIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              安全設定
            </Typography>

            <Divider sx={{ my: 2 }} />

            <Button
              variant="outlined"
              startIcon={<LockIcon />}
              onClick={() => setPasswordDialog(true)}
              fullWidth
            >
              修改密碼
            </Button>
          </CardContent>
        </Card>

        {/* Logout Button */}
        <Button
          variant="contained"
          color="error"
          fullWidth
          onClick={handleLogout}
          size="large"
        >
          登出
        </Button>

        {/* Change Password Dialog */}
        <Dialog
          open={passwordDialog}
          onClose={() => setPasswordDialog(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>修改密碼</DialogTitle>
          <DialogContent>
            <TextField
              fullWidth
              label="當前密碼"
              type="password"
              value={passwordData.currentPassword}
              onChange={(e) =>
                setPasswordData({ ...passwordData, currentPassword: e.target.value })
              }
              margin="normal"
            />
            <TextField
              fullWidth
              label="新密碼"
              type="password"
              value={passwordData.newPassword}
              onChange={(e) =>
                setPasswordData({ ...passwordData, newPassword: e.target.value })
              }
              margin="normal"
              helperText="至少 8 個字符,包含大小寫字母和數字"
            />
            <TextField
              fullWidth
              label="確認新密碼"
              type="password"
              value={passwordData.confirmPassword}
              onChange={(e) =>
                setPasswordData({ ...passwordData, confirmPassword: e.target.value })
              }
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPasswordDialog(false)}>取消</Button>
            <Button
              onClick={handleChangePassword}
              variant="contained"
              disabled={updating}
            >
              {updating ? <CircularProgress size={24} /> : '確認修改'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Container>
  );
};

export default ProfilePage;
