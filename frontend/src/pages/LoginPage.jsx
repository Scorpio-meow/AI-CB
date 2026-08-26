import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { TextField, Button, Alert, IconButton, Icon } from '../components/ui';
import styles from './Auth.module.css';
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
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.headerIcon}>
            <Icon name="login" size={48} />
          </div>
          <h1 className={styles.title}>ChatBot 登入</h1>
          <p className={styles.subtitle}>使用您的帳號登入系統</p>
        </div>
        {error && (
          <Alert severity="error" style={{ marginBottom: '16px' }}>
            {error}
          </Alert>
        )}
        <form onSubmit={handleSubmit} className={styles.form}>
          <TextField
            fullWidth
            label="用戶名或電子郵件"
            name="username"
            value={formData.username}
            onChange={handleChange}
            disabled={loading}
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
            autoComplete="current-password"
            endAdornment={
              <IconButton
                size="sm"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? '隱藏密碼' : '顯示密碼'}
              >
                <Icon name={showPassword ? 'visibility-off' : 'visibility'} size={18} />
              </IconButton>
            }
          />
          <Button
            fullWidth
            type="submit"
            variant="primary"
            size="lg"
            disabled={loading}
            loading={loading}
            className={styles.submitBtn}
          >
            登入
          </Button>
        </form>
        <div className={styles.footer}>
          還沒有帳號?
          <Link to="/register" className={styles.link}>
            立即註冊
          </Link>
        </div>
      </div>
      <p className={styles.copyright}>
        ChatBot © 2025 - Powered by JWT Authentication
      </p>
    </div>
  );
};
export default LoginPage;