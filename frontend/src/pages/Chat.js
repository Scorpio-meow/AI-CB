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
import {
  Send as SendIcon,
  Delete as DeleteIcon,
  Add as AddIcon
} from '@mui/icons-material';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

function Chat() {
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

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
        setCurrentConversation(response.data[0]);
        setMessages(response.data[0].messages || []);
      }
    } catch (error) {
      setError('載入對話失敗');
    }
  };

  const loadConversation = async (conversation) => {
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

    // 立即顯示用戶消息
    setMessages(prev => [...prev, userMessage]);
    setNewMessage('');
    setLoading(true);

    try {
      const response = await axios.post('/api/chat/send', {
        content: newMessage,
        conversation_id: currentConversation?.id
      });

      // 添加機器人回應
      setMessages(prev => [...prev, response.data.message]);

      // 如果是新對話，更新對話列表
      if (!currentConversation || response.data.conversation_id !== currentConversation.id) {
        await loadConversations();
        const newConv = conversations.find(c => c.id === response.data.conversation_id);
        if (newConv) {
          setCurrentConversation(newConv);
        }
      }

    } catch (error) {
      setError('發送消息失敗');
      // 移除失敗的用戶消息
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
      <Box sx={{ width: 300, borderRight: 1, borderColor: 'divider' }}>
        <Paper sx={{ height: '100%', borderRadius: 0 }}>
          <Box sx={{ p: 2 }}>
            <Button
              fullWidth
              variant="contained"
              startIcon={<AddIcon />}
              onClick={startNewConversation}
            >
              新對話
            </Button>
          </Box>
          
          <Divider />
          
          <List sx={{ height: 'calc(100% - 80px)', overflow: 'auto' }}>
            {conversations.map((conv) => (
              <ListItem
                key={conv.id}
                button
                selected={currentConversation?.id === conv.id}
                onClick={() => loadConversation(conv)}
                sx={{
                  borderLeft: currentConversation?.id === conv.id ? 3 : 0,
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

      {/* 主聊天區域 */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
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
      </Box>
    </Box>
  );
}

export default Chat;
