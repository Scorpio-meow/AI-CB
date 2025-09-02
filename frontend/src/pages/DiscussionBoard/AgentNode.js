import React from 'react';
import { Handle, Position } from 'reactflow';
import { Paper, Typography, Box, Divider, CircularProgress, Link } from '@mui/material'; // 引入 CircularProgress

function AgentNode({ data }) {
  return (
    <Paper 
      elevation={3} 
      sx={{ 
        padding: '14px 10px', 
        margin: '17px 0px', 
        borderRadius: '8px', 
        border: data.isEntryPoint ? '3.5px solid #4CAF50' : '2px solid #000000ff',
        boxShadow: data.isEntryPoint ? '0 0 10px rgba(76, 175, 80, 0.5)' : 'none',
        width: 350,
        backgroundColor: data.status === 'thinking' || data.status === 'revising' ? '#fffbe6' : 'white',
        transition: 'background-color 0.3s ease',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ 
       background: data.isEntryPoint ? ' #4CAF50' : '#000000ff' ,width: 16,height: 16,
        border: data.isEntryPoint ? '3.5px solid #4CAF50' : '2px solid #000000ff',
        boxShadow: data.isEntryPoint ? '0 0 10px rgba(76, 175, 80, 0.5)' : 'none'}} />
      
      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', textAlign: 'center' }}>
        {data.label}
      </Typography>
      <Divider sx={{ my: 1 }} />
      
      <Box 
        sx={{
          minHeight: 50, // 設定最小高度，避免思考中狀態框太小
          maxHeight: 350,
          overflowY: 'auto',
          fontSize: '0.875rem',
          backgroundColor: '#f5f5f5',
          padding: '8px',
          border:"0.1px solid black",
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
           data.response ? (
            <Box sx={{ width: '100%' }}>
              <div>{data.response}</div>
              {data.downloadUrl && (
                <Box sx={{ mt: 1, textAlign: 'right' }}>
                  <Link href={data.downloadUrl} target="_blank" rel="noopener" underline="hover">
                    下載檔案{data.fileName ? `（${data.fileName}）` : ''}
                  </Link>
                </Box>
              )}
            </Box>
           ) : <span style={{color: '#999'}}>等待回應...</span>
        )}
      </Box>

      <Handle type="source" position={Position.Bottom} style={{ 
        background: data.isEntryPoint ? ' #4CAF50' : '#000000ff',width: 16,height: 16,
        border: data.isEntryPoint ? '3.5px solid #4CAF50' : '2px solid #000000ff',
        boxShadow: data.isEntryPoint ? '0 0 10px rgba(76, 175, 80, 0.5)' : 'none'}}/>
    </Paper>
  );
}

export default React.memo(AgentNode);