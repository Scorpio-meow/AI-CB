import { Suspense, lazy } from 'react';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import { PrivateRoute, AdminRoute, PublicRoute } from './components/PrivateRoute';
const Chat = lazy(() => import('./pages/Chat'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const Documents = lazy(() => import('./pages/Documents'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
function withSuspense(element) {
  return <Suspense fallback={null}>{element}</Suspense>;
}
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
    <RouterProvider
      router={router}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    />
  );
}
export default App;