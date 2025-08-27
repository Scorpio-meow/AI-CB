// src/components/DiscussionBoard/Sidebar.js

import React from 'react';
import { Box, Typography, List, ListItem, ListItemText } from '@mui/material';

const agentTypes = [
  { type: 'pm', label: '產品經理 (PM)', profession: 'PM', description: '負責產品規劃與需求。' },
  { type: 'engineer', label: '工程師 (RD)', profession: 'RD', description: '負責技術實現與開發。' },
  { type: 'ba', label: '業務 (BD)', profession: 'BD', description: '負責市場與商務拓展。' },
];

const Sidebar = () => {
  const onDragStart = (event, nodeType, label, profession) => {
    // 將 profession 也存入拖曳資料中
    event.dataTransfer.setData('application/reactflow', JSON.stringify({ nodeType, label, profession }));
    event.dataTransfer.effectAllowed = 'move';
  };
  
  return (
    <Box sx={{ width: 250, borderRight: 1, borderColor: 'divider', p: 1, backgroundColor: '#f9f9f9' }}>
        <Typography variant="h6" sx={{p:1}}>AI 角色</Typography>
      <List>
        {agentTypes.map((agent) => (
          <ListItem 
            key={agent.type} 
            onDragStart={(event) => onDragStart(event, agent.type, agent.label, agent.profession)} 
            draggable
            sx={{ cursor: 'grab', backgroundColor: 'white', border: '1px solid #ddd', borderRadius: 2, mb: 1, '&:hover': { backgroundColor: 'grey.100', borderColor: 'primary.main' } }}
          >
            <ListItemText primary={agent.label} secondary={agent.description} />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default Sidebar;