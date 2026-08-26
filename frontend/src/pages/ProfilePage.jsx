import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import {
  TextField,
  Button,
  Alert,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Spinner,
  Icon
} from '../components/ui';
import styles from './ProfilePage.module.css';
const ProfilePage = () => {
  const { user, loading, logout, changePassword } = useAuth();
  const [localLoading, setLocalLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [passwordDialog, setPasswordDialog] = useState(false);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const handleChangePassword = async () => {
    if (!passwordData.currentPassword || !passwordData.newPassword) {
      setError('請填寫所有密碼欄位');
      return;
    }
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setError('兩次密碼輸入不一致');
      return;
    }
    setLocalLoading(true);
    setError('');
    const result = await changePassword(
      passwordData.currentPassword,
      passwordData.newPassword,
      passwordData.confirmPassword
    );
    setLocalLoading(false);
    if (result.success) {
      setSuccess('密碼修改成功');
      setPasswordDialog(false);
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
    } else {
      setError(result.error || '修改密碼失敗');
    }
  };
  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };
  if (loading) {
    return (
      <div className={styles.container} style={{ display: 'flex', justifyContent: 'center', padding: '64px 0' }}>
        <Spinner size={36} color="var(--color-primary)" />
      </div>
    );
  }
  if (!user) {
    return (
      <div className={styles.container}>
        <Alert severity="error">無法載入用戶資料</Alert>
      </div>
    );
  }
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>
          <Icon name="person" size={28} />
          <span>用戶資料</span>
        </h1>
        <p className={styles.subtitle}>管理您的帳號資訊和安全設定</p>
      </div>
      {error && (
        <Alert severity="error" style={{ marginBottom: '16px' }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" style={{ marginBottom: '16px' }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <h2 className={styles.cardTitle}>基本資訊</h2>
          {user.is_admin && (
            <Chip
              icon={<Icon name="admin" size={14} />}
              label="管理員"
              color="primary"
              size="sm"
            />
          )}
        </div>
        <div className={styles.infoGrid}>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>用戶名</span>
            <span className={styles.infoValue}>{user.username}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>電子郵件</span>
            <span className={styles.infoValue}>{user.email}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>角色</span>
            <span className={styles.infoValue}>{user.role}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>帳號狀態</span>
            <div>
              {user.is_active ? (
                <Chip label="已啟用" color="success" size="sm" />
              ) : (
                <Chip label="已停用" color="error" size="sm" />
              )}
            </div>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>註冊時間</span>
            <span className={styles.infoValue}>
              {new Date(user.created_at).toLocaleString('zh-TW')}
            </span>
          </div>
          {user.last_login && (
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>最後登入</span>
              <span className={styles.infoValue}>
                {new Date(user.last_login).toLocaleString('zh-TW')}
              </span>
            </div>
          )}
        </div>
      </div>
      <div className={styles.card}>
        <h2 className={styles.cardTitle} style={{ marginBottom: '16px' }}>
          <Icon name="lock" size={20} />
          <span>安全設定</span>
        </h2>
        <Button
          variant="outline"
          startIcon={<Icon name="lock" size={16} />}
          onClick={() => setPasswordDialog(true)}
          fullWidth
        >
          修改密碼
        </Button>
      </div>
      <Button
        variant="danger"
        fullWidth
        onClick={handleLogout}
        size="lg"
      >
        登出
      </Button>
      <Dialog
        open={passwordDialog}
        onClose={() => setPasswordDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>修改密碼</DialogTitle>
        <DialogContent>
          <div className={styles.dialogForm}>
            <TextField
              fullWidth
              label="當前密碼"
              type="password"
              value={passwordData.currentPassword}
              onChange={(e) =>
                setPasswordData({ ...passwordData, currentPassword: e.target.value })
              }
            />
            <TextField
              fullWidth
              label="新密碼"
              type="password"
              value={passwordData.newPassword}
              onChange={(e) =>
                setPasswordData({ ...passwordData, newPassword: e.target.value })
              }
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
            />
          </div>
        </DialogContent>
        <DialogActions>
          <Button variant="secondary" onClick={() => setPasswordDialog(false)}>
            取消
          </Button>
          <Button
            variant="primary"
            onClick={handleChangePassword}
            disabled={localLoading}
            loading={localLoading}
          >
            確認修改
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};
export default ProfilePage;