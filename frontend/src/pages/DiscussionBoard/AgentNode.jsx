import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Paper, Typography, Box, Divider, CircularProgress, Link } from '@mui/material'; // 引入 CircularProgress
import { createMotionTransition, reduceMotionStyles } from '../../utils/motion';

function AgentNode({ data }) {
  const isBusy = data.status === 'thinking' || data.status === 'revising';

  return (
    <Paper
      elevation={3}
      sx={{
        padding: '14px 10px',
        margin: '17px 0px',
        borderRadius: '16px',
        border: data.isEntryPoint ? '3.5px solid #4CAF50' : '2px solid #000000ff',
        boxShadow: data.isEntryPoint
          ? '0 14px 30px rgba(76, 175, 80, 0.22)'
          : isBusy
            ? '0 14px 28px rgba(245, 158, 11, 0.18)'
            : '0 10px 24px rgba(15, 23, 42, 0.08)',
        width: 350,
        backgroundColor: isBusy ? '#fffbe6' : 'white',
        transform: isBusy ? 'translateY(-2px)' : 'translateY(0)',
        transition: createMotionTransition(['background-color', 'box-shadow', 'transform']),
        ...reduceMotionStyles,
      }}
    >
      <Handle type="target" position={Position.Top} style={{
        background: data.isEntryPoint ? ' #4CAF50' : '#000000ff', width: 16, height: 16,
        border: data.isEntryPoint ? '3.5px solid #4CAF50' : '2px solid #000000ff',
        boxShadow: data.isEntryPoint ? '0 0 10px rgba(76, 175, 80, 0.5)' : 'none'
      }} />

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
          backgroundColor: isBusy ? '#fff8db' : '#f8fafc',
          padding: '8px',
          border: '1px solid rgba(15, 23, 42, 0.12)',
          borderRadius: '12px',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          display: 'flex', // 使用 flex 來置中
          alignItems: 'center',
          justifyContent: 'center',
          transition: createMotionTransition(['background-color', 'border-color']),
          ...reduceMotionStyles,
        }}
      >
        {/* ================================================================= */}
        {/* === 新增：根據 data.status 顯示不同內容 ======================= */}
        {/* ================================================================= */}
        {data.status === 'thinking' || data.status === 'revising' ? (
          <Box sx={{ textAlign: 'center', color: 'grey.700' }}>
            <CircularProgress size={20} thickness={5} />
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
          ) : <span style={{ color: '#999' }}>等待回應...</span>
        )}
      </Box>

      <Handle type="source" position={Position.Bottom} style={{
        background: data.isEntryPoint ? ' #4CAF50' : '#000000ff', width: 16, height: 16,
        border: data.isEntryPoint ? '3.5px solid #4CAF50' : '2px solid #000000ff',
        boxShadow: data.isEntryPoint ? '0 0 10px rgba(76, 175, 80, 0.5)' : 'none'
      }} />
    </Paper>
  );
}

export default memo(AgentNode);