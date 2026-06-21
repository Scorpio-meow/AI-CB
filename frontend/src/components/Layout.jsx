import { useState } from 'react';
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
import { useAuth } from '../hooks/useAuth';
import { AgentProvider } from '../contexts/AgentContext';
import { createMotionTransition, reduceMotionStyles } from '../utils/motion';

function Layout() {
  const navigate = useNavigate();
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
    <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'grey.50' }}>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          top: 0,
          px: { xs: 1, sm: 2 },
          pt: 1,
          background: 'transparent',
          backdropFilter: 'blur(14px)',
          WebkitBackdropFilter: 'blur(14px)',
          transition: createMotionTransition(['background-color', 'box-shadow', 'transform']),
          ...reduceMotionStyles,
        }}
      >
        <Toolbar
          sx={{
            minHeight: 72,
            px: { xs: 1.5, sm: 2 },
            borderRadius: 3,
            border: '1px solid',
            borderColor: 'rgba(255,255,255,0.55)',
            bgcolor: 'rgba(37, 99, 235, 0.92)',
            boxShadow: '0 12px 30px rgba(37, 99, 235, 0.18)',
          }}
        >
          <Typography
            variant="h6"
            component="div"
            sx={{
              flexGrow: 1,
              fontWeight: 700,
              letterSpacing: 0.2,
            }}
          >
            ChatBot 系統
          </Typography>

          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              flexWrap: 'wrap',
              justifyContent: 'flex-end',
            }}
          >
            <Button
              color="inherit"
              startIcon={<Chat />}
              onClick={() => navigate('/chat')}
              sx={{
                minHeight: 44,
                borderRadius: 999,
                px: 1.75,
                transition: createMotionTransition(['background-color', 'box-shadow', 'transform']),
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.14)',
                  boxShadow: '0 8px 18px rgba(15, 23, 42, 0.16)',
                  transform: 'translateY(-1px)',
                },
                '&:focus-visible': {
                  outline: '2px solid rgba(255,255,255,0.95)',
                  outlineOffset: 2,
                },
                ...reduceMotionStyles,
              }}
            >
              聊天
            </Button>

            {user?.is_admin && (
              <Button
                color="inherit"
                startIcon={<Description />}
                onClick={() => navigate('/documents')}
                sx={{
                  minHeight: 44,
                  borderRadius: 999,
                  px: 1.75,
                  transition: createMotionTransition(['background-color', 'box-shadow', 'transform']),
                  '&:hover': {
                    bgcolor: 'rgba(255,255,255,0.14)',
                    boxShadow: '0 8px 18px rgba(15, 23, 42, 0.16)',
                    transform: 'translateY(-1px)',
                  },
                  '&:focus-visible': {
                    outline: '2px solid rgba(255,255,255,0.95)',
                    outlineOffset: 2,
                  },
                  ...reduceMotionStyles,
                }}
              >
                知識庫
              </Button>
            )}

            <Button
              color="inherit"
              startIcon={<SupportAgent />}
              onClick={() => navigate('/custom-agents')}
              sx={{
                minHeight: 44,
                borderRadius: 999,
                px: 1.75,
                transition: createMotionTransition(['background-color', 'box-shadow', 'transform']),
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.14)',
                  boxShadow: '0 8px 18px rgba(15, 23, 42, 0.16)',
                  transform: 'translateY(-1px)',
                },
                '&:focus-visible': {
                  outline: '2px solid rgba(255,255,255,0.95)',
                  outlineOffset: 2,
                },
                ...reduceMotionStyles,
              }}
            >
              自訂Agent
            </Button>

            {user?.is_admin && (
              <Button
                color="inherit"
                startIcon={<AdminPanelSettings />}
                onClick={() => navigate('/admin')}
                sx={{
                  minHeight: 44,
                  borderRadius: 999,
                  px: 1.75,
                  transition: createMotionTransition(['background-color', 'box-shadow', 'transform']),
                  '&:hover': {
                    bgcolor: 'rgba(255,255,255,0.14)',
                    boxShadow: '0 8px 18px rgba(15, 23, 42, 0.16)',
                    transform: 'translateY(-1px)',
                  },
                  '&:focus-visible': {
                    outline: '2px solid rgba(255,255,255,0.95)',
                    outlineOffset: 2,
                  },
                  ...reduceMotionStyles,
                }}
              >
                管理後台
              </Button>
            )}

            {/* User Menu */}
            <IconButton
              onClick={handleMenuOpen}
              size="small"
              sx={{
                ml: 1,
                minWidth: 44,
                minHeight: 44,
                transition: createMotionTransition(['background-color', 'transform', 'box-shadow']),
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.14)',
                  transform: 'translateY(-1px)',
                  boxShadow: '0 8px 18px rgba(15, 23, 42, 0.16)',
                },
                '&:focus-visible': {
                  outline: '2px solid rgba(255,255,255,0.95)',
                  outlineOffset: 2,
                },
                ...reduceMotionStyles,
              }}
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
        slotProps={{
          paper: {
            elevation: 0,
            sx: {
              mt: 1,
              minWidth: 220,
              borderRadius: 3,
              border: '1px solid',
              borderColor: 'divider',
              boxShadow: '0 18px 40px rgba(15, 23, 42, 0.14)',
              overflow: 'visible',
            },
          },
        }}
      >
        <MenuItem disabled>
          <Typography variant="body2" sx={{
            color: "text.secondary"
          }}>
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
      <Box component="main" sx={{ px: { xs: 2, sm: 3 }, pb: 3, mt: 2 }}>
        <AgentProvider>
          <Outlet />
        </AgentProvider>
      </Box>
    </Box>
  );
}

export default Layout;