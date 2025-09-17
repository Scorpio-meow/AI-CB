import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Chat from './pages/Chat';
import AdminDashboard from './pages/AdminDashboard';
import Documents from './pages/Documents';
import CustomAgents from './pages/CustomAgents';
import Layout from './components/Layout';
import { AgentProvider } from './contexts/AgentContext';

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
  {
    path: '/',
    element: <Layout />, // Layout 包裹所有頁面
    children: [
      { index: true, element: <Navigate to="/chat" replace /> },
      { path: 'chat', element: <Chat /> },
      { path: 'documents', element: <Documents /> },
      { path: 'admin', element: <AdminDashboard /> },
      { path: 'custom-agents', element: <CustomAgents /> },
    ],
  },
]);

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AgentProvider>
        <RouterProvider
          router={router}
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
        />
      </AgentProvider>
    </ThemeProvider>
  );
}

export default App;
