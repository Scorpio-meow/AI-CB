import React from 'react';
import { Box, Typography, IconButton, Collapse, Paper } from '@mui/material';
import { ExpandMore, ExpandLess, LightbulbOutlined } from '@mui/icons-material';
import { ThinkBlockProps } from './types';

export const ThinkBlock: React.FC<ThinkBlockProps> = ({
  thinkContent,
  isOpen,
  onToggle,
}) => {
  if (!thinkContent) return null;

  return (
    <Paper
      elevation={0}
      sx={{
        my: 1.5,
        border: '1px solid',
        borderColor: 'rgba(37, 99, 235, 0.18)',
        borderRadius: 2,
        backgroundColor: 'rgba(239, 246, 255, 0.65)',
        overflow: 'hidden',
        transition: 'all 0.2s ease-in-out',
      }}
    >
      <Box
        onClick={onToggle}
        role="button"
        tabIndex={0}
        aria-expanded={isOpen}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          py: 1,
          cursor: 'pointer',
          userSelect: 'none',
          '&:hover': {
            backgroundColor: 'rgba(219, 234, 254, 0.5)',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <LightbulbOutlined sx={{ fontSize: 18, color: '#2563EB' }} />
          <Typography variant="body2" sx={{ fontWeight: 600, color: '#1E40AF' }}>
            思考與推論過程
          </Typography>
        </Box>
        <IconButton size="small" aria-label={isOpen ? '收合思考過程' : '展開思考過程'}>
          {isOpen ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
        </IconButton>
      </Box>

      <Collapse in={isOpen} timeout="auto" unmountOnExit>
        <Box
          sx={{
            px: 2,
            py: 1.5,
            borderTop: '1px solid',
            borderColor: 'rgba(37, 99, 235, 0.12)',
            backgroundColor: 'rgba(255, 255, 255, 0.85)',
          }}
        >
          <Typography
            variant="body2"
            sx={{
              whiteSpace: 'pre-wrap',
              color: '#334155',
              fontFamily: 'monospace',
              fontSize: '0.825rem',
              lineHeight: 1.6,
            }}
          >
            {thinkContent}
          </Typography>
        </Box>
      </Collapse>
    </Paper>
  );
};

export default ThinkBlock;
