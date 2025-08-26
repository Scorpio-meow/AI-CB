import React from 'react';
import { createBrowserRouter, RouterProvider, createRoutesFromElements, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Chat from './pages/Chat';
import AdminDashboard from './pages/AdminDashboard';
import Documents from './pages/Documents';
import Layout from './components/Layout';

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

function App() {
  // Define routes for RouterProvider (v6 data routers)
  const routes = createRoutesFromElements(
    <Route element={<Layout />}>
      <Route path="/" element={<Navigate to="/chat" />} />
      <Route path="/dashboard" element={<Navigate to="/admin" replace />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="/documents" element={<Documents />} />
  {/* /workflow route intentionally removed to avoid direct access; Workflow component is not exposed as a top-level route */}
      <Route path="/admin" element={<AdminDashboard />} />
    </Route>
  );

  // enable future flags to opt-in v7 behavior and silence runtime warnings
  const router = createBrowserRouter(routes, {
    future: {
      v7_startTransition: true,
      v7_relativeSplatPath: true,
    },
  });

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <RouterProvider router={router} />
    </ThemeProvider>
  );
}

export default App;
