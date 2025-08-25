import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Divider,
  CircularProgress,
  Alert,
  Chip
} from '@mui/material';

import { FaRobot } from "react-icons/fa";

import {
  Send as SendIcon,
  Delete as DeleteIcon,
  Add as AddIcon
} from '@mui/icons-material';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

// 導入我們剛剛建立的 DiscussionBoard 組件
import DiscussionBoard from './DiscussionBoard'; 

function Chat() {
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  // 新增一個 state 來控制視圖模式 ('chat' 或 'discussion')
  const [viewMode, setViewMode] = useState('chat');

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async () => {
    try {
      const response = await axios.get('/api/chat/conversations');
      setConversations(response.data);
      
      if (response.data.length > 0 && !currentConversation) {
        // 只有在 chat 模式下才自動選擇第一個對話
        if (viewMode === 'chat') {
            setCurrentConversation(response.data[0]);
            setMessages(response.data[0].messages || []);
        }
      }
    } catch (error) {
      setError('載入對話失敗');
    }
  };

  const loadConversation = async (conversation) => {
    // 點擊對話列表時，自動切換回 chat 模式
    setViewMode('chat'); 
    try {
      const response = await axios.get(`/api/chat/conversations/${conversation.id}`);
      setCurrentConversation(response.data);
      setMessages(response.data.messages || []);
    } catch (error) {
      setError('載入對話詳情失敗');
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;

    const userMessage = {
      content: newMessage,
      is_user: true,
      created_at: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setNewMessage('');
    setLoading(true);

    try {
      const response = await axios.post('/api/chat/send', {
        content: newMessage,
        conversation_id: currentConversation?.id
      });
      
      setMessages(prev => [...prev, response.data.message]);

      if (!currentConversation || response.data.conversation_id !== currentConversation.id) {
        await loadConversations();
        const newConv = conversations.find(c => c.id === response.data.conversation_id);
        if (newConv) {
          setCurrentConversation(newConv);
        }
      }

    } catch (error) {
      setError('發送消息失敗');
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const deleteConversation = async (conversationId) => {
    try {
      await axios.delete(`/api/chat/conversations/${conversationId}`);
      await loadConversations();
      
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setMessages([]);
      }
    } catch (error) {
      setError('刪除對話失敗');
    }
  };

  const startNewConversation = () => {
    setCurrentConversation(null);
    setMessages([]);
    // 點擊新對話時，切換到 chat 模式
    setViewMode('chat');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex' }}>
      {/* 側邊欄 - 對話列表 */}
      {/* 我們將側邊欄稍微修改，使其在 discussion 模式下仍然可見，但行為不同 */}
      <Box sx={{ width: 300, borderRight: 1, borderColor: 'divider', display: 'flex', flexDirection: 'column' }}>
        <Paper sx={{ height: '100%', borderRadius: 0 }}>
          <Box sx={{ p: 2, display:"flex", columnGap:1}}>
            <Button
              fullWidth
              variant={viewMode === 'chat' ? 'contained' : 'outlined'}
              startIcon={<AddIcon />}
              onClick={startNewConversation} // 這個按鈕會切換到 chat 模式
            >
              新對話
            </Button>

            <Button
              fullWidth
              variant={viewMode === 'discussion' ? 'contained' : 'outlined'}
              startIcon={<FaRobot />}
              onClick={() => setViewMode('discussion')} // 這個按鈕切換到 discussion 模式
            >
              AI討論
            </Button>
          </Box>
          
          <Divider />
          
          {/* 對話列表只在 chat 模式下有意義，所以我們保持原樣 */}
          <List sx={{ height: 'calc(100% - 80px)', overflow: 'auto' }}>
            {conversations.map((conv) => (
              <ListItem
                key={conv.id}
                button
                selected={currentConversation?.id === conv.id && viewMode === 'chat'} // 只有在 chat 模式下才高亮
                onClick={() => loadConversation(conv)} // 點擊後會切換到 chat 模式
                sx={{
                  borderLeft: currentConversation?.id === conv.id && viewMode === 'chat' ? 3 : 0,
                  borderColor: 'primary.main'
                }}
              >
                <ListItemText
                  primary={conv.title}
                  secondary={new Date(conv.updated_at).toLocaleDateString()}
                  primaryTypographyProps={{
                    noWrap: true,
                    fontSize: '0.9rem'
                  }}
                />
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteConversation(conv.id);
                  }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </ListItem>
            ))}
          </List>
        </Paper>
      </Box>

      {/* 主區域：根據 viewMode 條件渲染 Chat UI 或 DiscussionBoard */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {viewMode === 'chat' ? (
          <>
            {/* 聊天標題 */}
            <Paper sx={{ p: 2, borderRadius: 0 }} elevation={1}>
              <Typography variant="h6">
                {currentConversation?.title || '新對話'}
              </Typography>
            </Paper>

            {/* 錯誤提示 */}
            {error && (
              <Alert severity="error" onClose={() => setError('')}>
                {error}
              </Alert>
            )}

            {/* 消息列表 */}
            <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
                {/* 如果沒有訊息，顯示歡迎畫面或提示 */}
                 {messages.length === 0 && !currentConversation && (
                    <Box sx={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'grey.500'}}>
                        <Typography variant='h5'>請從左側選擇或開始一個新對話</Typography>
                    </Box>
                 )}
              {messages.map((message, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    justifyContent: message.is_user ? 'flex-end' : 'flex-start',
                    mb: 2
                  }}
                >
                  <Paper
                    sx={{
                      p: 2,
                      maxWidth: '70%',
                      backgroundColor: message.is_user ? 'primary.main' : 'grey.100',
                      color: message.is_user ? 'white' : 'text.primary'
                    }}
                  >
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                    
                    {!message.is_user && message.context_used && (
                      <Box sx={{ mt: 1 }}>
                        <Chip 
                          label="使用了知識庫" 
                          size="small" 
                          variant="outlined" 
                          sx={{ fontSize: '0.7rem' }}
                        />
                      </Box>
                    )}
                  </Paper>
                </Box>
              ))}
              
              {loading && (
                <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
                  <Paper sx={{ p: 2, backgroundColor: 'grey.100' }}>
                    <CircularProgress size={20} />
                    <Typography variant="body2" sx={{ ml: 1, display: 'inline' }}>
                      正在思考...
                    </Typography>
                  </Paper>
                </Box>
              )}
              
              <div ref={messagesEndRef} />
            </Box>

            {/* 輸入區域 */}
            <Paper sx={{ p: 2, borderRadius: 0 }} elevation={1}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  multiline
                  maxRows={4}
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="輸入你的問題..."
                  disabled={loading}
                />
                <Button
                  variant="contained"
                  onClick={sendMessage}
                  disabled={loading || !newMessage.trim()}
                  sx={{ minWidth: 60 }}
                >
                  <SendIcon />
                </Button>
              </Box>
            </Paper>
          </>
        ) : (
          // 如果 viewMode 是 'discussion'，則渲染 DiscussionBoard
          <DiscussionBoard />
        )}
      </Box>
    </Box>
  );
}

export default Chat;