import { useState, useEffect, useRef } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Divider,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import {
  AdminPanelSettings,
  Chat,
  Description,
  SupportAgent,
  AccountCircle,
  Person,
  Logout
} from '@mui/icons-material';
import { useNavigate, Outlet } from 'react-router-dom';
import authService from '../services/authService';
import { AgentProvider } from '../contexts/AgentContext';

function Layout({ children }) {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    loadUser();
    
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const loadUser = async () => {
    if (!authService.isAuthenticated()) return;
    
    try {
      const userData = await authService.getCurrentUser();
      
      if (isMountedRef.current) {
        setUser(userData);
      }
    } catch (error) {
      // Silently handle errors during unmount or navigation
      // authService.getCurrentUser already logs errors and handles timeout
      if (isMountedRef.current && !error.isTimeout) {
        // Only log non-timeout errors when component is still mounted
        if (process.env.NODE_ENV === 'development') {
          console.debug('Layout.loadUser error (non-critical):', error.message);
        }
      }
    }
  };

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
    await authService.logout();
    navigate('/login');
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            ChatBot 系統
          </Typography>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button 
              color="inherit" 
              startIcon={<Chat />}
              onClick={() => navigate('/chat')}
            >
              聊天
            </Button>
            
            <Button 
              color="inherit" 
              startIcon={<Description />}
              onClick={() => navigate('/documents')}
            >
              知識庫
            </Button>

            <Button 
              color="inherit" 
              startIcon={<SupportAgent />}
              onClick={() => navigate('/custom-agents')}
            >
              自訂Agent
            </Button>

            {user?.is_admin && (
              <Button 
                color="inherit" 
                startIcon={<AdminPanelSettings />}
                onClick={() => navigate('/admin')}
              >
                管理後台
              </Button>
            )}

            {/* User Menu */}
            <IconButton
              onClick={handleMenuOpen}
              size="small"
              sx={{ ml: 2 }}
              aria-controls={open ? 'account-menu' : undefined}
              aria-haspopup="true"
              aria-expanded={open ? 'true' : undefined}
            >
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>
                {user?.username?.[0]?.toUpperCase() || <AccountCircle />}
              </Avatar>
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      {/* User Menu */}
      <Menu
        anchorEl={anchorEl}
        id="account-menu"
        open={open}
        onClose={handleMenuClose}
        onClick={handleMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <MenuItem disabled>
          <Typography variant="body2" color="text.secondary">
            {user?.username}
          </Typography>
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleProfile}>
          <ListItemIcon>
            <Person fontSize="small" />
          </ListItemIcon>
          <ListItemText>個人資料</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <Logout fontSize="small" />
          </ListItemIcon>
          <ListItemText>登出</ListItemText>
        </MenuItem>
      </Menu>
      
      <Box component="main" sx={{ mt: 2 }}>
        <AgentProvider>
          <Outlet />
        </AgentProvider>
      </Box>
    </Box>
  );
}

export default Layout;
