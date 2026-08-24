import React from 'react';
import {
  Box,
  Typography,
  Select,
  MenuItem,
  FormControl,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Refresh as RefreshIcon,
  LayersOutlined,
  PsychologyOutlined,
} from '@mui/icons-material';
import { ChatHeaderProps } from './types';

const REASONING_EFFORT_OPTIONS = [
  { value: 'none', label: '無推理 (None / 快速)', shortLabel: '無 (None)' },
  { value: 'low', label: '輕度推理 (Low / 平衡)', shortLabel: '輕度 (Low)' },
  { value: 'medium', label: '標準推理 (Medium / 預設)', shortLabel: '標準 (Medium)' },
  { value: 'high', label: '深度推理 (High / 嚴密)', shortLabel: '深度 (High)' },
  { value: 'xhigh', label: '極致推理 (X-High / 長程)', shortLabel: '極致 (X-High)' },
];

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  availableModels,
  selectedModel,
  onSelectModel,
  reasoningEffort,
  onSelectReasoningEffort,
  modelsLoading,
  onRefreshModels,
  currentConversation,
  onOpenSidebar,
}) => {
  return (
    <Box
      sx={{
        px: { xs: 1.5, sm: 2.5 },
        py: 1.2,
        borderBottom: '1px solid #E2E8F0',
        backgroundColor: '#FFFFFF',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 1.5,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {onOpenSidebar && (
          <IconButton
            size="small"
            onClick={onOpenSidebar}
            sx={{ display: { xs: 'flex', md: 'none' }, color: '#475569' }}
            aria-label="開啟對話清單"
          >
            <MenuIcon />
          </IconButton>
        )}

        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#1E293B' }}>
            {currentConversation?.title || '新對話'}
          </Typography>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
        {/* 模型選擇器 */}
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <Select
            value={availableModels.includes(selectedModel) ? selectedModel : (availableModels[0] || '')}
            onChange={(e) => onSelectModel(e.target.value)}
            displayEmpty
            disabled={modelsLoading}
            sx={{
              borderRadius: 2,
              fontSize: '0.85rem',
              backgroundColor: '#F8FAFC',
              '& .MuiSelect-select': {
                py: 0.8,
              },
            }}
          >
            {availableModels.length === 0 && (
              <MenuItem value="" disabled>
                載入模型中...
              </MenuItem>
            )}
            {availableModels.map((model) => (
              <MenuItem key={model} value={model} sx={{ fontSize: '0.85rem' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <LayersOutlined sx={{ fontSize: 16, color: '#2563EB' }} />
                  {model}
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* 推理程度選擇器 */}
        <Tooltip title="設定模型思考與推理深度 (Reasoning Effort)">
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <Select
              value={reasoningEffort}
              onChange={(e) => onSelectReasoningEffort(e.target.value)}
              sx={{
                borderRadius: 2,
                fontSize: '0.85rem',
                backgroundColor: '#F8FAFC',
                '& .MuiSelect-select': {
                  py: 0.8,
                },
              }}
            >
              {REASONING_EFFORT_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value} sx={{ fontSize: '0.85rem' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <PsychologyOutlined sx={{ fontSize: 16, color: '#7C3AED' }} />
                    {opt.shortLabel}
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Tooltip>

        <Tooltip title="重新整理可用模型清單">
          <span>
            <IconButton
              size="small"
              onClick={onRefreshModels}
              disabled={modelsLoading}
              sx={{ color: '#64748B', '&:hover': { color: '#2563EB' } }}
              aria-label="重新整理模型"
            >
              {modelsLoading ? <CircularProgress size={18} /> : <RefreshIcon fontSize="small" />}
            </IconButton>
          </span>
        </Tooltip>
      </Box>
    </Box>
  );
};

export default ChatHeader;
