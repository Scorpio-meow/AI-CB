// src/pages/DiscussionBoard/Sidebar.js

import React from 'react';
import { Box, Paper, Typography, List, ListItem, ListItemText, ListItemIcon } from '@mui/material';
import { DragIndicator } from '@mui/icons-material';

// 定義可用的 AI 角色
const agentRoles = [
  { name: '專案經理', profession: 'PM' },
  { name: '軟體工程師', profession: 'RD' },
  { name: '業務分析師', profession: 'BD' },
];

const Sidebar = () => {
  const onDragStart = (event, nodeType, label, profession) => {
    const data = JSON.stringify({ nodeType, label, profession });
    event.dataTransfer.setData('application/reactflow', data);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Paper sx={{ width: 250, height: '100%', p: 2, borderRight: 1, borderColor: 'divider' }} elevation={2}>
      <Typography variant="h6" gutterBottom>
        AI 角色列表
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        請將角色拖拽到右側畫布中
      </Typography>
      <List>
        {agentRoles.map((role) => (
          <ListItem 
            key={role.profession} 
            draggable
            onDragStart={(event) => onDragStart(event, 'agent', role.name, role.profession)}
            sx={{ 
              cursor: 'grab', 
              border: '1px solid #ddd', 
              borderRadius: '8px', 
              mb: 1.5, 
              backgroundColor: '#f9f9f9',
              '&:hover': {
                backgroundColor: '#f0f0f0',
                boxShadow: '0 2px 5px rgba(0,0,0,0.1)'
              }
            }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <DragIndicator />
            </ListItemIcon>
            <ListItemText primary={role.name} secondary={`職業: ${role.profession}`} />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};

export default Sidebar;
