import React from 'react';
import { Handle, Position } from 'reactflow';
import { Paper, Typography, Box, Divider, CircularProgress } from '@mui/material'; // 引入 CircularProgress

function AgentNode({ data }) {
  return (
    <Paper 
      elevation={3} 
      sx={{ 
        padding: '10px 15px', 
        borderRadius: '8px', 
        border: data.isEntryPoint ? '2px solid #4CAF50' : '1px solid #bbb',
        boxShadow: data.isEntryPoint ? '0 0 10px rgba(76, 175, 80, 0.5)' : 'none',
        width: 250,
        backgroundColor: data.status === 'thinking' || data.status === 'revising' ? '#fffbe6' : 'white',
        transition: 'background-color 0.3s ease',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#555' }} />
      
      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', textAlign: 'center' }}>
        {data.label}
      </Typography>
      <Divider sx={{ my: 1 }} />
      
      <Box 
        sx={{
          minHeight: 50, // 設定最小高度，避免思考中狀態框太小
          maxHeight: 150,
          overflowY: 'auto',
          fontSize: '0.875rem',
          backgroundColor: '#f5f5f5',
          padding: '8px',
          borderRadius: '4px',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          display: 'flex', // 使用 flex 來置中
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        {/* ================================================================= */}
        {/* === 新增：根據 data.status 顯示不同內容 ======================= */}
        {/* ================================================================= */}
        {data.status === 'thinking' || data.status === 'revising' ? (
          <Box sx={{ textAlign: 'center', color: 'grey.600' }}>
            <CircularProgress size={20} />
            <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
              {data.status === 'revising' ? '重新思考中...' : '思考中...'}
            </Typography>
          </Box>
        ) : (
           data.response ? data.response : <span style={{color: '#999'}}>等待回應...</span>
        )}
      </Box>

      <Handle type="source" position={Position.Bottom} style={{ background: '#555' }} />
    </Paper>
  );
}

export default React.memo(AgentNode);