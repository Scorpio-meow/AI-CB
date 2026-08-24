import React from 'react';
import { Box, Typography, Button, CircularProgress, Paper, Chip } from '@mui/material';
import { SmartToyOutlined, QuestionAnswerOutlined } from '@mui/icons-material';
import { ChatMessageListProps } from './types';
import ChatMessageItem from './ChatMessageItem';

export const ChatMessageList: React.FC<ChatMessageListProps> = ({
  messages,
  loading,
  loadingMore,
  hasMoreMessages,
  onLoadMore,
  thinkOpenArr,
  onToggleThinking,
  onCopyMessage,
  messagesEndRef,
  messagesTopRef,
}) => {
  const isEmpty = messages.length === 0;

  return (
    <Box
      sx={{
        flexGrow: 1,
        overflowY: 'auto',
        p: { xs: 2, sm: 3 },
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div ref={messagesTopRef} />

      {hasMoreMessages && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 1.5 }}>
          <Button
            size="small"
            variant="outlined"
            onClick={onLoadMore}
            disabled={loadingMore}
            sx={{
              borderRadius: 2,
              textTransform: 'none',
              fontSize: '0.8rem',
              color: '#475569',
              borderColor: '#CBD5E1',
              '&:hover': {
                borderColor: '#94A3B8',
                backgroundColor: '#F8FAFC',
              },
            }}
          >
            {loadingMore ? <CircularProgress size={16} sx={{ mr: 1 }} /> : null}
            {loadingMore ? '正在載入更早訊息...' : '載入更早訊息'}
          </Button>
        </Box>
      )}

      {isEmpty && !loading ? (
        <Box
          sx={{
            flexGrow: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            py: 8,
          }}
        >
          <Paper
            elevation={0}
            sx={{
              p: 4,
              maxWidth: 480,
              borderRadius: 4,
              border: '1px dashed #CBD5E1',
              backgroundColor: 'rgba(248, 250, 252, 0.7)',
            }}
          >
            <SmartToyOutlined sx={{ fontSize: 48, color: '#2563EB', mb: 2 }} />
            <Typography variant="h6" sx={{ fontWeight: 600, color: '#1E293B', mb: 1 }}>
              歡迎使用內部知識庫對話
            </Typography>
            <Typography variant="body2" sx={{ color: '#64748B', mb: 3, lineHeight: 1.6 }}>
              我是通哥，您的知識助理。您可以詢問公司規章、人事差勤、專案流程或任何內部文檔相關問題。
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography variant="caption" sx={{ color: '#94A3B8', fontWeight: 600, textAlign: 'left' }}>
                常見問題提示：
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {['如何申請補休與加班？', '特休天數計算與遞延原則', '忘刷卡申請流程與期限', '留職停薪相關規定'].map((prompt, idx) => (
                  <Chip
                    key={idx}
                    icon={<QuestionAnswerOutlined sx={{ fontSize: 14 }} />}
                    label={prompt}
                    size="small"
                    variant="outlined"
                    onClick={() => onCopyMessage(prompt)}
                    sx={{
                      borderRadius: 1.5,
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      '&:hover': {
                        backgroundColor: '#EFF6FF',
                        borderColor: '#93C5FD',
                      },
                    }}
                  />
                ))}
              </Box>
            </Box>
          </Paper>
        </Box>
      ) : (
        messages.map((msg, index) => {
          const itemKey = `${msg.is_user ? 'user' : 'assistant'}-${msg.id ?? 'idx'}-${index}`;
          const thinkId = msg.id ?? index;
          return (
            <ChatMessageItem
              key={itemKey}
              message={msg}
              isThinkingOpen={Boolean(thinkOpenArr[thinkId])}
              onToggleThinking={() => onToggleThinking(thinkId)}
              onCopyMessage={onCopyMessage}
            />
          );
        })
      )}

      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
          <SmartToyOutlined sx={{ fontSize: 24, color: '#2563EB' }} />
          <Paper
            elevation={0}
            sx={{
              p: 2,
              borderRadius: '4px 16px 16px 16px',
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
            }}
          >
            <CircularProgress size={18} sx={{ color: '#2563EB' }} />
            <Typography variant="body2" sx={{ color: '#64748B' }}>
              正在檢索知識庫並生成回答...
            </Typography>
          </Paper>
        </Box>
      )}

      <div ref={messagesEndRef} />
    </Box>
  );
};

export default ChatMessageList;
