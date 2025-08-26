import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box
} from '@mui/material';
import {
  AdminPanelSettings,
  Chat,
  Description,
  AccountTree
} from '@mui/icons-material';
import { useNavigate, Outlet } from 'react-router-dom';

function Layout({ children }) {
  const navigate = useNavigate();

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
              startIcon={<AccountTree />}
              onClick={() => navigate('/chat')}
            >
              工作流
            </Button>
            
            <Button 
              color="inherit" 
              startIcon={<AdminPanelSettings />}
              onClick={() => navigate('/admin')}
            >
              管理後台
            </Button>
          </Box>
        </Toolbar>
      </AppBar>
      
      <Box component="main" sx={{ mt: 2 }}>
        {/* If used as a router layout, render nested routes via Outlet; fall back to children for direct usage */}
        {children ? children : <Outlet />}
      </Box>
    </Box>
  );
}

export default Layout;
