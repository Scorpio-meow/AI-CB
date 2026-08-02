
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
import { useAuth } from '../hooks/useAuth';
const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loading, error: authError } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState('');
  const from = location.state?.from?.pathname || '/';
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    if (localError) setLocalError('');
  };
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.username || !formData.password) {
      setLocalError('請輸入用戶名和密碼');
      return;
    }
    setLocalError('');
    const result = await login(formData.username, formData.password);
    if (result.success) {
      navigate(from, { replace: true });
    }
  };
  const error = localError || authError;
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
            { }
            <Box sx={{ textAlign: 'center', mb: 3 }}>
              <LoginIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h4" component="h1" gutterBottom>
                ChatBot 登入
              </Typography>
              <Typography variant="body2" color="text.secondary">
                使用您的帳號登入系統
              </Typography>
            </Box>
            { }
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
            { }
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
            { }
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
        { }
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