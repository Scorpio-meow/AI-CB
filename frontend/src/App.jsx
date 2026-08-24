import { Suspense, lazy } from 'react';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Layout from './components/Layout';
import { PrivateRoute, AdminRoute, PublicRoute } from './components/PrivateRoute';
import { MOTION_DURATION, MOTION_EASING } from './utils/motion';

const Chat = lazy(() => import('./pages/Chat'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const Documents = lazy(() => import('./pages/Documents'));
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
      main: '#2563EB',
    },
    secondary: {
      main: '#3B82F6',
    },
  },
  shape: {
    borderRadius: 14,
  },
  transitions: {
    duration: {
      shortest: MOTION_DURATION.short,
      shorter: MOTION_DURATION.short,
      short: MOTION_DURATION.medium,
      standard: MOTION_DURATION.medium,
      complex: MOTION_DURATION.long,
      enteringScreen: MOTION_DURATION.long,
      leavingScreen: MOTION_DURATION.short,
    },
    easing: {
      easeInOut: MOTION_EASING.standard,
      easeOut: MOTION_EASING.enter,
      easeIn: MOTION_EASING.exit,
      sharp: MOTION_EASING.standard,
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: {
          scrollBehavior: 'smooth',
          '@media (prefers-reduced-motion: reduce)': {
            scrollBehavior: 'auto',
          },
        },
        '*, *::before, *::after': {
          boxSizing: 'border-box',
        },
        '@media (prefers-reduced-motion: reduce)': {
          '*, *::before, *::after': {
            animationDuration: '0.01ms !important',
            animationIterationCount: '1 !important',
            transitionDuration: '0.01ms !important',
            scrollBehavior: 'auto !important',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
  },
});

const router = createBrowserRouter([
  {
    path: '/login',
    element: <PublicRoute element={withSuspense(<LoginPage />)} />,
  },
  {
    path: '/register',
    element: <PublicRoute element={withSuspense(<RegisterPage />)} />,
  },
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/chat" replace /> },
      {
        path: 'chat',
        element: <PrivateRoute element={withSuspense(<Chat />)} />,
      },
      {
        path: 'documents',
        element: <AdminRoute element={withSuspense(<Documents />)} />,
      },
      {
        path: 'profile',
        element: <PrivateRoute element={withSuspense(<ProfilePage />)} />,
      },
      {
        path: 'admin',
        element: <AdminRoute element={withSuspense(<AdminDashboard />)} />,
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