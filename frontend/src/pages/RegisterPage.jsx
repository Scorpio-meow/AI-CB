
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
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
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  PersonAdd as RegisterIcon,
  Check,
  Close
} from '@mui/icons-material';
import { useAuth } from '../hooks/useAuth';
const RegisterPage = () => {
  const navigate = useNavigate();
  const { register, loading, error: authError } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState('');
  const [success, setSuccess] = useState(false);
  const passwordRequirements = {
    length: formData.password.length >= 8,
    uppercase: /[A-Z]/.test(formData.password),
    lowercase: /[a-z]/.test(formData.password),
    number: /[0-9]/.test(formData.password),
    match: formData.password === formData.confirmPassword && formData.password.length > 0
  };
  const isPasswordValid = Object.values(passwordRequirements).every(req => req);
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    if (localError) setLocalError('');
  };
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.username || !formData.email || !formData.password) {
      setLocalError('請填寫所有必填欄位');
      return;
    }
    if (!isPasswordValid) {
      setLocalError('密碼不符合要求');
      return;
    }
    setLocalError('');
    const result = await register(
      formData.username,
      formData.email,
      formData.password
    );
    if (result.success) {
      setSuccess(true);
      setTimeout(() => {
        navigate('/', { replace: true });
      }, 2000);
    }
  };
  const error = localError || authError;
  if (success) {
    return (
      <Container maxWidth="sm">
        <Box
          sx={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <Card elevation={3}>
            <CardContent sx={{ p: 4, textAlign: 'center' }}>
              <Check sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
              <Typography variant="h5" gutterBottom>
                註冊成功!
              </Typography>
              <Typography variant="body1" color="text.secondary">
                正在跳轉到首頁...
              </Typography>
            </CardContent>
          </Card>
        </Box>
      </Container>
    );
  }
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
              <RegisterIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h4" component="h1" gutterBottom>
                創建新帳號
              </Typography>
              <Typography variant="body2" color="text.secondary">
                填寫以下資料完成註冊
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
                label="用戶名"
                name="username"
                value={formData.username}
                onChange={handleChange}
                disabled={loading}
                margin="normal"
                autoFocus
                helperText="3-50 個字符,只能包含字母、數字、下劃線和連字符"
              />
              <TextField
                fullWidth
                label="電子郵件"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                disabled={loading}
                margin="normal"
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
                slotProps={{
                  input: {
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
                  }
                }}
              />
              <TextField
                fullWidth
                label="確認密碼"
                name="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                value={formData.confirmPassword}
                onChange={handleChange}
                disabled={loading}
                margin="normal"
              />
              { }
              {formData.password && (
                <Box sx={{ mt: 2, mb: 1 }}>
                  <Typography variant="caption" color="text.secondary" gutterBottom>
                    密碼要求:
                  </Typography>
                  <List dense>
                    <ListItem disablePadding>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        {passwordRequirements.length ? (
                          <Check fontSize="small" color="success" />
                        ) : (
                          <Close fontSize="small" color="error" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={<Typography variant="caption">至少 8 個字符</Typography>}
                      />
                    </ListItem>
                    <ListItem disablePadding>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        {passwordRequirements.uppercase ? (
                          <Check fontSize="small" color="success" />
                        ) : (
                          <Close fontSize="small" color="error" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={<Typography variant="caption">包含大寫字母</Typography>}
                      />
                    </ListItem>
                    <ListItem disablePadding>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        {passwordRequirements.lowercase ? (
                          <Check fontSize="small" color="success" />
                        ) : (
                          <Close fontSize="small" color="error" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={<Typography variant="caption">包含小寫字母</Typography>}
                      />
                    </ListItem>
                    <ListItem disablePadding>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        {passwordRequirements.number ? (
                          <Check fontSize="small" color="success" />
                        ) : (
                          <Close fontSize="small" color="error" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={<Typography variant="caption">包含數字</Typography>}
                      />
                    </ListItem>
                    <ListItem disablePadding>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        {passwordRequirements.match ? (
                          <Check fontSize="small" color="success" />
                        ) : (
                          <Close fontSize="small" color="error" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={<Typography variant="caption">兩次密碼輸入一致</Typography>}
                      />
                    </ListItem>
                  </List>
                </Box>
              )}
              <Button
                fullWidth
                type="submit"
                variant="contained"
                size="large"
                disabled={loading || !isPasswordValid}
                sx={{ mt: 3, mb: 2 }}
              >
                {loading ? (
                  <>
                    <CircularProgress size={24} sx={{ mr: 1 }} />
                    註冊中...
                  </>
                ) : (
                  '註冊'
                )}
              </Button>
            </form>
            { }
            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                已有帳號?{' '}
                <Link to="/login" style={{ textDecoration: 'none' }}>
                  <Typography
                    component="span"
                    variant="body2"
                    color="primary"
                    sx={{ fontWeight: 'bold' }}
                  >
                    立即登入
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
export default RegisterPage;