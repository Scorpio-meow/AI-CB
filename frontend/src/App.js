import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Chat from './pages/Chat';
import AdminDashboard from './pages/AdminDashboard';
import Documents from './pages/Documents';
import CustomAgents from './pages/CustomAgents';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import Layout from './components/Layout';
import { PrivateRoute, AdminRoute, PublicRoute } from './components/PrivateRoute';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});


const router = createBrowserRouter([
  // 公開路由 (未登入才能訪問)
  {
    path: '/login',
    element: <PublicRoute element={<LoginPage />} />,
  },
  {
    path: '/register',
    element: <PublicRoute element={<RegisterPage />} />,
  },
  // 受保護路由 (需要登入)
  {
    path: '/',
    element: <Layout />, // Layout 包裹所有頁面
    children: [
      { index: true, element: <Navigate to="/chat" replace /> },
      { 
        path: 'chat', 
        element: <PrivateRoute element={<Chat />} /> 
      },
      { 
        path: 'documents', 
        element: <PrivateRoute element={<Documents />} /> 
      },
      { 
        path: 'custom-agents', 
        element: <PrivateRoute element={<CustomAgents />} /> 
      },
      { 
        path: 'profile', 
        element: <PrivateRoute element={<ProfilePage />} /> 
      },
      { 
        path: 'admin', 
        element: <AdminRoute element={<AdminDashboard />} /> 
      },
    ],
  },
]);

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <RouterProvider
        router={router}
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      />
    </ThemeProvider>
  );
}

export default App;
