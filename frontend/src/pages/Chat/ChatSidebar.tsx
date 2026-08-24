import React from 'react';
import {
  Box,
  Typography,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  IconButton,
  Tooltip,
  Drawer,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ChatOutlined,
} from '@mui/icons-material';
import { ChatSidebarProps } from './types';

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  open,
  onClose,
  conversations,
  currentConversation,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  loading,
}) => {
  const sidebarContent = (
    <Box
      sx={{
        width: 280,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#F8FAFC',
        borderRight: '1px solid #E2E8F0',
      }}
    >
      <Box sx={{ p: 2 }}>
        <Button
          fullWidth
          variant="contained"
          startIcon={<AddIcon />}
          onClick={onNewConversation}
          sx={{
            borderRadius: 2.5,
            py: 1,
            textTransform: 'none',
            fontWeight: 600,
            boxShadow: '0 2px 6px rgba(37, 99, 235, 0.25)',
          }}
        >
          開啟新對話
        </Button>
      </Box>

      <Divider sx={{ borderColor: '#E2E8F0' }} />

      <Box sx={{ flexGrow: 1, overflowY: 'auto', px: 1, py: 1 }}>
        <Typography
          variant="caption"
          sx={{ px: 1.5, py: 0.5, display: 'block', fontWeight: 600, color: '#94A3B8' }}
        >
          歷史對話記錄
        </Typography>

        {loading && conversations.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={24} sx={{ color: '#2563EB' }} />
          </Box>
        ) : conversations.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4, px: 2 }}>
            <Typography variant="body2" sx={{ color: '#94A3B8' }}>
              尚無歷史對話
            </Typography>
          </Box>
        ) : (
          <List sx={{ p: 0 }}>
            {conversations.map((conv, idx) => {
              const isSelected = currentConversation?.id === conv.id;
              return (
                <ListItem
                  key={conv.id ? `conv-${conv.id}` : `conv-${idx}`}
                  disablePadding
                  secondaryAction={
                    <Tooltip title="刪除此對話">
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteConversation(conv.id);
                        }}
                        sx={{
                          color: '#94A3B8',
                          '&:hover': { color: '#EF4444' },
                        }}
                        aria-label="刪除對話"
                      >
                        <DeleteIcon sx={{ fontSize: 18 }} />
                      </IconButton>
                    </Tooltip>
                  }
                  sx={{ mb: 0.5 }}
                >
                  <ListItemButton
                    selected={isSelected}
                    onClick={() => {
                      onSelectConversation(conv.id);
                      if (onClose) onClose();
                    }}
                    sx={{
                      borderRadius: 2,
                      py: 1,
                      px: 1.5,
                      '&.Mui-selected': {
                        backgroundColor: '#EFF6FF',
                        color: '#2563EB',
                        fontWeight: 600,
                        '&:hover': {
                          backgroundColor: '#DBEAFE',
                        },
                      },
                      '&:hover': {
                        backgroundColor: '#F1F5F9',
                      },
                    }}
                  >
                    <ChatOutlined
                      sx={{
                        fontSize: 18,
                        mr: 1.2,
                        color: isSelected ? '#2563EB' : '#64748B',
                        flexShrink: 0,
                      }}
                    />
                    <ListItemText
                      primary={
                        <Typography
                          noWrap
                          sx={{
                            fontSize: '0.875rem',
                            fontWeight: isSelected ? 600 : 400,
                            color: isSelected ? '#2563EB' : '#334155',
                          }}
                        >
                          {conv.title || '對話'}
                        </Typography>
                      }
                    />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        )}
      </Box>
    </Box>
  );

  return (
    <>
      {/* 桌面端常駐側邊欄 */}
      <Box
        sx={{
          display: { xs: 'none', md: 'block' },
          height: '100%',
          flexShrink: 0,
        }}
      >
        {sidebarContent}
      </Box>

      {/* 移動端抽屜式側邊欄 */}
      <Drawer
        anchor="left"
        open={open}
        onClose={onClose}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: 280,
          },
        }}
      >
        {sidebarContent}
      </Drawer>
    </>
  );
};

export default ChatSidebar;
