/**
 * 登入頁面
 */

import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  Container,
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  InputAdornment,
  IconButton
} from '@mui/material';
import { Visibility, VisibilityOff, Login as LoginIcon } from '@mui/icons-material';
import authService from '../services/authService';

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // 獲取登入前的路徑
  const from = location.state?.from?.pathname || '/';

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    // 清除錯誤提示
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // 驗證
    if (!formData.username || !formData.password) {
      setError('請輸入用戶名和密碼');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await authService.login(formData.username, formData.password);

      if (result.success) {
        // 登入成功,跳轉到原始路徑或首頁
        navigate(from, { replace: true });
      } else {
        setError(result.error || '登入失敗');
      }
    } catch {
      setError('登入失敗,請檢查網絡連接');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          py: 4
        }}
      >
        <Card elevation={3}>
          <CardContent sx={{ p: 4 }}>
            {/* Logo / Title */}
            <Box sx={{ textAlign: 'center', mb: 3 }}>
              <LoginIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h4" component="h1" gutterBottom>
                ChatBot 登入
              </Typography>
              <Typography variant="body2" color="text.secondary">
                使用您的帳號登入系統
              </Typography>
            </Box>

            {/* Error Alert */}
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="用戶名或電子郵件"
                name="username"
                value={formData.username}
                onChange={handleChange}
                disabled={loading}
                margin="normal"
                autoFocus
                autoComplete="username"
              />

              <TextField
                fullWidth
                label="密碼"
                name="password"
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={handleChange}
                disabled={loading}
                margin="normal"
                autoComplete="current-password"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  )
                }}
              />

              <Button
                fullWidth
                type="submit"
                variant="contained"
                size="large"
                disabled={loading}
                sx={{ mt: 3, mb: 2 }}
              >
                {loading ? (
                  <>
                    <CircularProgress size={24} sx={{ mr: 1 }} />
                    登入中...
                  </>
                ) : (
                  '登入'
                )}
              </Button>
            </form>

            {/* Links */}
            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                還沒有帳號?{' '}
                <Link to="/register" style={{ textDecoration: 'none' }}>
                  <Typography
                    component="span"
                    variant="body2"
                    color="primary"
                    sx={{ fontWeight: 'bold' }}
                  >
                    立即註冊
                  </Typography>
                </Link>
              </Typography>
            </Box>
          </CardContent>
        </Card>

        {/* Footer */}
        <Typography
          variant="body2"
          color="text.secondary"
          align="center"
          sx={{ mt: 3 }}
        >
          ChatBot © 2025 - Powered by JWT Authentication
        </Typography>
      </Box>
    </Container>
  );
};

export default LoginPage;