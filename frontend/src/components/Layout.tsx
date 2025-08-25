import React from 'react'
import { Layout, Menu } from 'antd'
import { Link, Outlet, useLocation } from 'react-router-dom'

const { Header, Sider, Content } = Layout

export default function LayoutShell() {
  const { pathname } = useLocation()
  const selectedKeys = [pathname.startsWith('/chat') ? '/chat' : pathname]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth="0">
        <div style={{ color: '#fff', padding: '16px', fontWeight: 600 }}>HR ChatBot</div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={selectedKeys}
          items={[
            {
              key: '/dashboard',
              label: <Link to="/dashboard">Dashboard</Link>,
            },
            {
              key: '/chat',
              label: <Link to="/chat">Chat</Link>,
            },
          ]}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff' }}>Welcome</Header>
        <Content style={{ margin: '16px' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
