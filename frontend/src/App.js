import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AgentProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Navigate to="/chat" />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/custom-agents" element={<CustomAgents />} />
            </Routes>
          </Layout>
        </Router>
      </AgentProvider>
    </ThemeProvider>
  );
}

export default App;
