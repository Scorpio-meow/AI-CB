// src/pages/DiscussionBoard/Sidebar.js

import React from 'react';
import { Box, Paper, Typography, List, ListItem, ListItemText, ListItemIcon, CircularProgress, Alert } from '@mui/material';
import { DragIndicator } from '@mui/icons-material';
import { useAgents } from '../../contexts/AgentContext';

const Sidebar = () => {
  const { agents, loading, error } = useAgents();

  const onDragStart = (event, nodeType, label, profession) => {
    const data = JSON.stringify({ nodeType, label, profession });
    event.dataTransfer.setData('application/reactflow', data);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Paper sx={{ width: 250, height: '100%', p: 2, borderRight: 1, borderColor: 'divider', display: 'flex', flexDirection: 'column' }} elevation={2}>
      <Typography variant="h6" gutterBottom>
        AI 角色列表
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        請將角色拖拽到右側畫布中
      </Typography>
      
      {loading ? (
        <CircularProgress />
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : (
        <Box sx={{ flex: 1, overflowY: 'auto', pr: 1 }}>
          <List sx={{ p: 0 }}>
            {agents.map((agent) => (
              <ListItem 
                key={agent.id} 
                draggable
                onDragStart={(event) => onDragStart(event, 'agent', agent.name, agent.role)}
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
                <ListItemText primary={agent.name} secondary={`角色: ${agent.role}`} />
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Paper>
  );
};

export default Sidebar;