import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import LayoutShell from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ChatInterface from './pages/Chat/ChatInterface'

const router = createBrowserRouter(
  [
    { path: '/login', element: <Login /> },
    {
      element: <LayoutShell />,
      children: [
        { path: '/', element: <Navigate to="/dashboard" replace /> },
        { path: '/dashboard', element: <Dashboard /> },
        { path: '/chat', element: <ChatInterface /> },
      ],
    },
  ],
  {
    future: {
      v7_relativeSplatPath: true,
    },
  }
)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider>
      <RouterProvider
        router={router}
        future={{
          v7_startTransition: true,
        }}
      />
    </ConfigProvider>
  </React.StrictMode>
)
