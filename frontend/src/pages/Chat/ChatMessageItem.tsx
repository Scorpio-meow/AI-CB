import React, { useMemo } from 'react';
import { Box, Paper, Typography, IconButton, Tooltip, Avatar } from '@mui/material';
import { ContentCopy, Person, SmartToyOutlined } from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DOMPurify from 'dompurify';
import { ChatMessageItemProps } from './types';
import ThinkBlock from './ThinkBlock';
import SourceBadges from './SourceBadges';
import ResearchTraceBlock from './ResearchTraceBlock';

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  isThinkingOpen,
  onToggleThinking,
  onCopyMessage,
}) => {
  const isUser = message.is_user;

  // 解析思考區塊與主要內容
  const { thinkContent, mainContent } = useMemo(() => {
    const rawContent = message.content || '';
    const thinkMatch = rawContent.match(/<think>([\s\S]*?)<\/think>/);
    if (thinkMatch) {
      return {
        thinkContent: thinkMatch[1].trim(),
        mainContent: rawContent.replace(/<think>[\s\S]*?<\/think>/, '').trim(),
      };
    }
    return {
      thinkContent: '',
      mainContent: rawContent,
    };
  }, [message.content]);

  const sanitizedContent = useMemo(() => {
    return DOMPurify.sanitize(mainContent);
  }, [mainContent]);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
        gap: 1.5,
        mb: 2.5,
        width: '100%',
      }}
    >
      <Avatar
        sx={{
          width: 36,
          height: 36,
          bgcolor: isUser ? '#2563EB' : '#EEF2F6',
          color: isUser ? '#FFFFFF' : '#2563EB',
          boxShadow: '0 2px 4px rgba(0,0,0,0.06)',
          border: isUser ? 'none' : '1px solid #E2E8F0',
        }}
      >
        {isUser ? <Person fontSize="small" /> : <SmartToyOutlined fontSize="small" />}
      </Avatar>

      <Box
        sx={{
          maxWidth: { xs: '85%', sm: '78%', md: '72%' },
          display: 'flex',
          flexDirection: 'column',
          alignItems: isUser ? 'flex-end' : 'flex-start',
        }}
      >
        <Paper
          elevation={isUser ? 2 : 1}
          sx={{
            p: 2,
            borderRadius: isUser ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
            backgroundColor: isUser ? '#2563EB' : '#FFFFFF',
            color: isUser ? '#FFFFFF' : '#1E293B',
            border: isUser ? 'none' : '1px solid #E2E8F0',
            boxShadow: isUser
              ? '0 4px 12px rgba(37, 99, 235, 0.2)'
              : '0 2px 8px rgba(0, 0, 0, 0.04)',
            overflowWrap: 'break-word',
            wordBreak: 'break-word',
          }}
        >
          {/* AI 自主研究歷程折疊卡片 */}
          {!isUser && message.research_trace && message.research_trace.length > 0 && (
            <ResearchTraceBlock trace={message.research_trace} />
          )}

          {/* 思考區塊 */}
          {!isUser && thinkContent && (
            <ThinkBlock
              thinkContent={thinkContent}
              isOpen={isThinkingOpen}
              onToggle={onToggleThinking}
            />
          )}

          {isUser ? (
            <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
              {mainContent}
            </Typography>
          ) : (
            <Box
              sx={{
                '& p': { m: 0, mb: 1, '&:last-child': { mb: 0 }, lineHeight: 1.65 },
                '& pre': {
                  backgroundColor: '#0F172A',
                  color: '#F8FAFC',
                  p: 1.5,
                  borderRadius: 1.5,
                  overflowX: 'auto',
                  my: 1,
                },
                '& code': {
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  backgroundColor: 'rgba(0, 0, 0, 0.05)',
                  px: 0.6,
                  py: 0.2,
                  borderRadius: 0.8,
                },
                '& pre code': {
                  backgroundColor: 'transparent',
                  p: 0,
                },
                '& ul, & ol': { pl: 2.5, my: 0.8 },
                '& table': {
                  borderCollapse: 'collapse',
                  width: '100%',
                  my: 1.5,
                },
                '& th, & td': {
                  border: '1px solid #CBD5E1',
                  p: 1,
                  fontSize: '0.875rem',
                },
                '& th': {
                  backgroundColor: '#F1F5F9',
                },
              }}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{sanitizedContent}</ReactMarkdown>
            </Box>
          )}

          {!isUser && (
            <SourceBadges
              sources={message.sources || (message.context_used as any)}
              sourcesDetail={message.sources_detail}
            />
          )}
        </Paper>

        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 0.5,
            mt: 0.5,
            px: 0.5,
          }}
        >
          {message.created_at && (
            <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.7rem' }}>
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Typography>
          )}

          <Tooltip title="複製訊息內容">
            <IconButton
              size="small"
              onClick={() => onCopyMessage(mainContent)}
              sx={{
                p: 0.4,
                color: '#94A3B8',
                '&:hover': { color: '#2563EB' },
              }}
            >
              <ContentCopy sx={{ fontSize: 14 }} />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>
    </Box>
  );
};

export default ChatMessageItem;
