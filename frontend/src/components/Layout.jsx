import { useState } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Avatar, Menu, MenuItem, MenuDivider, Icon } from './ui';
import styles from './Layout.module.css';
function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleMenuClose = () => {
    setAnchorEl(null);
  };
  const handleProfile = () => {
    handleMenuClose();
    navigate('/profile');
  };
  const handleLogout = async () => {
    handleMenuClose();
    await logout();
    navigate('/login');
  };
  return (
    <div className={styles.wrapper}>
      <header className={styles.appBar}>
        <div className={styles.toolbar}>
          <div className={styles.brand}>
            ChatBot 系統
          </div>
          <div className={styles.navGroup}>
            <button
              type="button"
              className={`${styles.navButton} ${location.pathname.startsWith('/chat') ? styles.navButtonActive : ''}`}
              onClick={() => navigate('/chat')}
            >
              <Icon name="chat" size={18} />
              <span>聊天</span>
            </button>
            <button
              type="button"
              className={`${styles.navButton} ${location.pathname.startsWith('/tools') ? styles.navButtonActive : ''}`}
              onClick={() => navigate('/tools')}
            >
              <Icon name="tools" size={18} />
              <span>AI 工具</span>
            </button>
            {user?.is_admin && (
              <button
                type="button"
                className={`${styles.navButton} ${location.pathname.startsWith('/documents') ? styles.navButtonActive : ''}`}
                onClick={() => navigate('/documents')}
              >
                <Icon name="description" size={18} />
                <span>知識庫</span>
              </button>
            )}
            {user?.is_admin && (
              <button
                type="button"
                className={`${styles.navButton} ${location.pathname.startsWith('/admin') ? styles.navButtonActive : ''}`}
                onClick={() => navigate('/admin')}
              >
                <Icon name="admin" size={18} />
                <span>管理後台</span>
              </button>
            )}
            <button
              type="button"
              onClick={handleMenuOpen}
              className={styles.userAvatarBtn}
              aria-label="帳號選單"
            >
              <Avatar size={34} style={{ backgroundColor: 'var(--color-primary-light)', color: 'var(--color-primary-text)' }}>
                {user?.username?.[0]?.toUpperCase() || <Icon name="account-circle" size={20} />}
              </Avatar>
            </button>
          </div>
        </div>
      </header>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleMenuClose}
        placement="bottom-end"
      >
        <div className={styles.userMenuHeader}>
          {user?.username}
        </div>
        <MenuItem
          icon={<Icon name="person" size={16} />}
          onClick={handleProfile}
        >
          個人資料
        </MenuItem>
        <MenuDivider />
        <MenuItem
          icon={<Icon name="logout" size={16} />}
          danger
          onClick={handleLogout}
        >
          登出
        </MenuItem>
      </Menu>
      <main className={styles.mainContent}>
        <Outlet />
      </main>
    </div>
  );
}
export default Layout;