import { Suspense, lazy } from 'react';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Layout from './components/Layout';
import { PrivateRoute, AdminRoute, PublicRoute } from './components/PrivateRoute';

const Chat = lazy(() => import('./pages/Chat'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const Documents = lazy(() => import('./pages/Documents'));
const CustomAgents = lazy(() => import('./pages/CustomAgents'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));

function withSuspense(element) {
  return <Suspense fallback={null}>{element}</Suspense>;
}

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
    element: <PublicRoute element={withSuspense(<LoginPage />)} />,
  },
  {
    path: '/register',
    element: <PublicRoute element={withSuspense(<RegisterPage />)} />,
  },
  // 受保護路由 (需要登入)
  {
    path: '/',
    element: <Layout />, // Layout 包裹所有頁面
    children: [
      { index: true, element: <Navigate to="/chat" replace /> },
      { 
        path: 'chat', 
        element: <PrivateRoute element={withSuspense(<Chat />)} /> 
      },
      { 
        path: 'documents', 
        element: <AdminRoute element={withSuspense(<Documents />)} /> 
      },
      { 
        path: 'custom-agents', 
        element: <PrivateRoute element={withSuspense(<CustomAgents />)} /> 
      },
      { 
        path: 'profile', 
        element: <PrivateRoute element={withSuspense(<ProfilePage />)} /> 
      },
      { 
        path: 'admin', 
        element: <AdminRoute element={withSuspense(<AdminDashboard />)} /> 
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
