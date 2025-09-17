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
  SupportAgent
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
              startIcon={<SupportAgent />}
              onClick={() => navigate('/custom-agents')}
            >
              自訂Agent
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
        <Outlet />
      </Box>
    </Box>
  );
}

export default Layout;
