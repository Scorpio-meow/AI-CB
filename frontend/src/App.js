import React from 'react';
import { createBrowserRouter, RouterProvider, createRoutesFromElements, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Chat from './pages/Chat';
import AdminDashboard from './pages/AdminDashboard';
import Documents from './pages/Documents';
import Workflow from './pages/Workflow';
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
  const routes = createRoutesFromElements(
    <>
      <Route path="/" element={<Navigate to="/chat" />} />
  <Route path="/dashboard" element={<Navigate to="/admin" replace />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="/documents" element={<Documents />} />
      <Route path="/admin" element={<AdminDashboard />} />
    </>
  );

  // enable future flags to opt-in v7 behavior and silence runtime warnings
  const router = createBrowserRouter(routes, {
    future: {
      v7_startTransition: true,
      v7_relativeSplatPath: true
    }
  });

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <RouterProvider router={router}>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/chat" />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/workflow" element={<Workflow />} />
            <Route path="/admin" element={<AdminDashboard />} />
          </Routes>
        </Layout>
      </RouterProvider>
    </ThemeProvider>
  );
}

export default App;
