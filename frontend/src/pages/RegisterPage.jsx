import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { TextField, Button, Alert, IconButton, Icon } from '../components/ui';
import styles from './Auth.module.css';
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
      <div className={styles.container}>
        <div className={styles.card} style={{ textAlign: 'center' }}>
          <div style={{ color: 'var(--color-success)', marginBottom: '16px' }}>
            <Icon name="check-circle" size={64} />
          </div>
          <h2 className={styles.title}>註冊成功!</h2>
          <p className={styles.subtitle}>正在跳轉到首頁...</p>
        </div>
      </div>
    );
  }
  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.headerIcon}>
            <Icon name="person-add" size={48} />
          </div>
          <h1 className={styles.title}>創建新帳號</h1>
          <p className={styles.subtitle}>填寫以下資料完成註冊</p>
        </div>
        {error && (
          <Alert severity="error" style={{ marginBottom: '16px' }}>
            {error}
          </Alert>
        )}
        <form onSubmit={handleSubmit} className={styles.form}>
          <TextField
            fullWidth
            label="用戶名"
            name="username"
            value={formData.username}
            onChange={handleChange}
            disabled={loading}
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
          />
          <TextField
            fullWidth
            label="密碼"
            name="password"
            type={showPassword ? 'text' : 'password'}
            value={formData.password}
            onChange={handleChange}
            disabled={loading}
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
          <TextField
            fullWidth
            label="確認密碼"
            name="confirmPassword"
            type={showPassword ? 'text' : 'password'}
            value={formData.confirmPassword}
            onChange={handleChange}
            disabled={loading}
          />
          {formData.password && (
            <div style={{ marginTop: '8px', padding: '8px', backgroundColor: 'var(--bg-surface-secondary)', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', fontWeight: 600, marginBottom: '6px' }}>
                密碼要求:
              </div>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <li style={{ display: 'flex', alignItems: 'center', gap: '6px', color: passwordRequirements.length ? 'var(--color-success)' : 'var(--color-error)' }}>
                  <Icon name={passwordRequirements.length ? 'check' : 'close'} size={14} />
                  <span>至少 8 個字符</span>
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '6px', color: passwordRequirements.uppercase ? 'var(--color-success)' : 'var(--color-error)' }}>
                  <Icon name={passwordRequirements.uppercase ? 'check' : 'close'} size={14} />
                  <span>包含大寫字母</span>
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '6px', color: passwordRequirements.lowercase ? 'var(--color-success)' : 'var(--color-error)' }}>
                  <Icon name={passwordRequirements.lowercase ? 'check' : 'close'} size={14} />
                  <span>包含小寫字母</span>
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '6px', color: passwordRequirements.number ? 'var(--color-success)' : 'var(--color-error)' }}>
                  <Icon name={passwordRequirements.number ? 'check' : 'close'} size={14} />
                  <span>包含數字</span>
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '6px', color: passwordRequirements.match ? 'var(--color-success)' : 'var(--color-error)' }}>
                  <Icon name={passwordRequirements.match ? 'check' : 'close'} size={14} />
                  <span>兩次密碼輸入一致</span>
                </li>
              </ul>
            </div>
          )}
          <Button
            fullWidth
            type="submit"
            variant="primary"
            size="lg"
            disabled={loading || !isPasswordValid}
            loading={loading}
            className={styles.submitBtn}
          >
            註冊
          </Button>
        </form>
        <div className={styles.footer}>
          已有帳號?
          <Link to="/login" className={styles.link}>
            立即登入
          </Link>
        </div>
      </div>
      <p className={styles.copyright}>
        ChatBot © 2025 - Powered by JWT Authentication
      </p>
    </div>
  );
};
export default RegisterPage;