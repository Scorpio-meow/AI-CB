import React, { useRef, useEffect } from 'react';
import { Box, TextField, IconButton, Tooltip, Typography, CircularProgress } from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';
import { ChatInputAreaProps } from './types';

export const ChatInputArea: React.FC<ChatInputAreaProps> = ({
  value,
  onChange,
  onSend,
  loading,
  disabled = false,
}) => {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!loading && !disabled && value.trim()) {
        onSend();
      }
    }
  };

  useEffect(() => {
    if (!loading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [loading]);

  return (
    <Box
      sx={{
        p: { xs: 1.5, sm: 2 },
        borderTop: '1px solid #E2E8F0',
        backgroundColor: '#FFFFFF',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: 1,
          backgroundColor: '#F8FAFC',
          border: '1px solid #CBD5E1',
          borderRadius: 3,
          px: 1.5,
          py: 0.8,
          transition: 'all 0.2s ease',
          '&:focus-within': {
            borderColor: '#2563EB',
            backgroundColor: '#FFFFFF',
            boxShadow: '0 0 0 3px rgba(37, 99, 235, 0.12)',
          },
        }}
      >
        <TextField
          fullWidth
          multiline
          minRows={1}
          maxRows={6}
          placeholder="請輸入您的問題... (支援多行)"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading || disabled}
          inputRef={inputRef}
          variant="standard"
          slotProps={{
            input: {
              disableUnderline: true,
              sx: {
                fontSize: '0.925rem',
                lineHeight: 1.5,
                py: 0.5,
              },
            },
          }}
        />

        <Tooltip title="發送訊息 (Enter)">
          <span>
            <IconButton
              color="primary"
              onClick={onSend}
              disabled={loading || disabled || !value.trim()}
              sx={{
                backgroundColor: value.trim() && !loading ? '#2563EB' : 'transparent',
                color: value.trim() && !loading ? '#FFFFFF' : '#94A3B8',
                width: 36,
                height: 36,
                borderRadius: 2,
                '&:hover': {
                  backgroundColor: value.trim() && !loading ? '#1D4ED8' : 'rgba(0, 0, 0, 0.04)',
                },
                '&.Mui-disabled': {
                  backgroundColor: 'transparent',
                  color: '#CBD5E1',
                },
              }}
              aria-label="發送訊息"
            >
              {loading ? (
                <CircularProgress size={18} sx={{ color: '#2563EB' }} />
              ) : (
                <SendIcon sx={{ fontSize: 18 }} />
              )}
            </IconButton>
          </span>
        </Tooltip>
      </Box>

      <Typography
        variant="caption"
        sx={{
          display: 'block',
          mt: 0.6,
          px: 0.5,
          color: '#94A3B8',
          fontSize: '0.725rem',
          textAlign: 'right',
        }}
      >
        按 Enter 發送，Shift + Enter 換行
      </Typography>
    </Box>
  );
};

export default ChatInputArea;
