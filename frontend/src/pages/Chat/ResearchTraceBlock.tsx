import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Collapse,
  IconButton,
  Chip,
  Divider,
} from '@mui/material';
import {
  TravelExplore,
  MenuBook,
  ArticleOutlined,
  ExpandMore,
  CheckCircleOutlined,
  ErrorOutlined,
  CodeOutlined,
} from '@mui/icons-material';
import { ResearchTraceBlockProps, ResearchTraceStep } from './types';

const getToolDisplayInfo = (toolName: string) => {
  switch (toolName) {
    case 'search_knowledge_base':
      return {
        label: '檢索內部知識庫',
        color: '#2563EB',
        bgColor: '#EFF6FF',
        icon: <MenuBook sx={{ fontSize: 16, color: '#2563EB' }} />,
      };
    case 'web_search':
      return {
        label: '外部聯網搜尋',
        color: '#0891B2',
        bgColor: '#ECFEFF',
        icon: <TravelExplore sx={{ fontSize: 16, color: '#0891B2' }} />,
      };
    case 'web_fetch':
      return {
        label: '深度閱讀網頁',
        color: '#7C3AED',
        bgColor: '#F5F3FF',
        icon: <ArticleOutlined sx={{ fontSize: 16, color: '#7C3AED' }} />,
      };
    default:
      return {
        label: toolName,
        color: '#64748B',
        bgColor: '#F1F5F9',
        icon: <CodeOutlined sx={{ fontSize: 16, color: '#64748B' }} />,
      };
  }
};

export const ResearchTraceBlock: React.FC<ResearchTraceBlockProps> = ({ trace }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!trace || trace.length === 0) return null;

  return (
    <Paper
      elevation={0}
      sx={{
        mb: 1.5,
        borderRadius: 2,
        border: '1px solid #E2E8F0',
        backgroundColor: '#F8FAFC',
        overflow: 'hidden',
        transition: 'all 0.2s ease',
      }}
    >
      {/* 標題欄 */}
      <Box
        onClick={() => setIsOpen(!isOpen)}
        sx={{
          py: 1,
          px: 1.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          userSelect: 'none',
          '&:hover': {
            backgroundColor: '#F1F5F9',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TravelExplore sx={{ fontSize: 18, color: '#2563EB' }} />
          <Typography
            variant="caption"
            sx={{ fontWeight: 600, color: '#334155', fontSize: '0.8rem' }}
          >
            AI 自主研究歷程 ({trace.length} 個步驟)
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8 }}>
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            {trace.map((step, idx) => {
              const info = getToolDisplayInfo(step.tool);
              return (
                <Chip
                  key={idx}
                  label={`S${step.step}`}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: '0.68rem',
                    fontWeight: 600,
                    color: info.color,
                    backgroundColor: info.bgColor,
                    border: `1px solid ${info.color}33`,
                  }}
                />
              );
            })}
          </Box>

          <IconButton
            size="small"
            sx={{
              transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s ease',
              p: 0.2,
              color: '#64748B',
            }}
          >
            <ExpandMore fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      {/* 展開之時間軸步驟清單 */}
      <Collapse in={isOpen}>
        <Divider sx={{ borderColor: '#E2E8F0' }} />
        <Box sx={{ p: 1.5, display: 'flex', flexDirection: 'column', gap: 1.2 }}>
          {trace.map((step: ResearchTraceStep, index: number) => {
            const toolInfo = getToolDisplayInfo(step.tool);
            const queryParam = step.arguments?.query || step.arguments?.url || '';

            return (
              <Box
                key={index}
                sx={{
                  p: 1.2,
                  borderRadius: 1.5,
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E2E8F0',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    mb: 0.8,
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8 }}>
                    {toolInfo.icon}
                    <Typography
                      variant="caption"
                      sx={{ fontWeight: 600, color: '#1E293B' }}
                    >
                      步驟 {step.step}：{toolInfo.label}
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    {step.duration_seconds !== undefined && (
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.7rem' }}>
                        {step.duration_seconds}s
                      </Typography>
                    )}
                    {step.status === 'error' ? (
                      <ErrorOutlined sx={{ fontSize: 14, color: '#EF4444' }} />
                    ) : (
                      <CheckCircleOutlined sx={{ fontSize: 14, color: '#10B981' }} />
                    )}
                  </Box>
                </Box>

                {queryParam && (
                  <Box sx={{ mb: 0.6 }}>
                    <Typography
                      variant="caption"
                      sx={{
                        color: '#475569',
                        backgroundColor: '#F8FAFC',
                        px: 0.8,
                        py: 0.3,
                        borderRadius: 1,
                        fontSize: '0.75rem',
                        display: 'inline-block',
                        wordBreak: 'break-all',
                        border: '1px solid #E2E8F0',
                      }}
                    >
                      關鍵字/目標: {queryParam}
                    </Typography>
                  </Box>
                )}

                {step.output_preview && (
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      color: '#64748B',
                      fontSize: '0.72rem',
                      lineHeight: 1.4,
                      backgroundColor: '#F8FAFC',
                      p: 0.8,
                      borderRadius: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'pre-wrap',
                      maxHeight: 80,
                      overflowY: 'auto',
                    }}
                  >
                    {step.output_preview}
                  </Typography>
                )}
              </Box>
            );
          })}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default ResearchTraceBlock;
