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
import { Send as SendIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import DiscussionBoard from './DiscussionBoard';

function Chat() {
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);
  const [viewMode, setViewMode] = useState('chat');
  const discussionBoardRef = useRef(null);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (viewMode === 'chat') {
      scrollToBottom();
    }
  }, [messages, viewMode]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async () => {
    try {
      const response = await axios.get('/api/chat/conversations');
      setConversations(response.data);
      if (response.data.length > 0 && !currentConversation) {
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
    setViewMode('chat');
    try {
      const response = await axios.get(`/api/chat/conversations/${conversation.id}`);
      setCurrentConversation(response.data);
      setMessages(response.data.messages || []);
    } catch (error) {
      setError('載入對話詳情失敗');
    }
  };

  const sendChatMessage = async () => {
    if (!newMessage.trim() || viewMode !== 'chat') return;

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

  const handleStartWorkflow = () => {
    if (discussionBoardRef.current) {
      discussionBoardRef.current.startWorkflow();
    }
  };

  const handleSendMessage = () => {
    if (viewMode === 'discussion') {
      handleStartWorkflow();
    } else {
      sendChatMessage();
    }
  };

  const handleWorkflowComplete = (result) => {
    const systemMessage = {
      content: `**工作流執行完畢**\n\n---\n\n${result}`,
      is_user: false,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, systemMessage]);
    setViewMode('chat'); // Switch back to chat view to see the result
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
    setViewMode('chat');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex' }}>
      {/* 側邊欄 - 這部分不變 */}
      <Box sx={{ width: 300, borderRight: 1, borderColor: 'divider', display: 'flex', flexDirection: 'column' }}>
        <Paper sx={{ height: '100%', borderRadius: 0 }}>
          <Box sx={{ p: 2, display: "flex", columnGap: 1 }}>
            <Button
              fullWidth
              variant={viewMode === 'chat' ? 'contained' : 'outlined'}
              startIcon={<AddIcon />}
              onClick={startNewConversation}
            >
              新對話
            </Button>
            <Button
              fullWidth
              variant={viewMode === 'discussion' ? 'contained' : 'outlined'}
              startIcon={<FaRobot />}
              onClick={() => setViewMode('discussion')}
            >
              AI討論
            </Button>
          </Box>
          <Divider />
          <List sx={{ height: 'calc(100% - 80px)', overflow: 'auto' }}>
            {conversations.map((conv) => (
              <ListItem
                key={conv.id}
                button
                selected={currentConversation?.id === conv.id && viewMode === 'chat'}
                onClick={() => loadConversation(conv)}
                sx={{
                  borderLeft: currentConversation?.id === conv.id && viewMode === 'chat' ? 3 : 0,
                  borderColor: 'primary.main'
                }}
              >
                <ListItemText
                  primary={conv.title}
                  secondary={new Date(conv.updated_at).toLocaleDateString()}
                  primaryTypographyProps={{ noWrap: true, fontSize: '0.9rem' }}
                />
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </ListItem>
            ))}
          </List>
        </Paper>
      </Box>

      {/* 主區域 */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        
        {/* 主要內容區域 (會變動) */}
        <Box sx={{ flex: 1, overflow: 'hidden' }}>
            {viewMode === 'chat' ? (
            <>
                <Paper sx={{ p: 2, borderRadius: 0 }} elevation={1}>
                    <Typography variant="h6">{currentConversation?.title || '新對話'}</Typography>
                </Paper>
                {error && (<Alert severity="error" onClose={() => setError('')}>{error}</Alert>)}
                <Box sx={{ height: 'calc(100% - 68px)', overflow: 'auto', p: 2 }}>
                    {messages.map((message, index) => (
                        <Box key={index} sx={{ display: 'flex', justifyContent: message.is_user ? 'flex-end' : 'flex-start', mb: 2 }}>
                            <Paper sx={{ p: 2, maxWidth: '70%', backgroundColor: message.is_user ? 'primary.main' : 'grey.100', color: message.is_user ? 'white' : 'text.primary' }}>
                                <ReactMarkdown>{message.content}</ReactMarkdown>
                                {!message.is_user && message.context_used && (
                                <Box sx={{ mt: 1 }}><Chip label="使用了知識庫" size="small" variant="outlined" sx={{ fontSize: '0.7rem' }}/></Box>
                                )}
                            </Paper>
                        </Box>
                    ))}
                    {loading && (
                        <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
                            <Paper sx={{ p: 2, backgroundColor: 'grey.100' }}>
                                <CircularProgress size={20} />
                                <Typography variant="body2" sx={{ ml: 1, display: 'inline' }}>正在思考...</Typography>
                            </Paper>
                        </Box>
                    )}
                    <div ref={messagesEndRef} />
                </Box>
            </>
            ) : (
                <DiscussionBoard 
                    ref={discussionBoardRef}
                    initialPrompt={newMessage} 
                    onWorkflowComplete={handleWorkflowComplete}
                />
            )}
        </Box>

        {/* 輸入區域 (固定在底部) */}
        <Paper sx={{ p: 2, borderRadius: 0, borderTop: 1, borderColor: 'divider' }} elevation={2}>
            <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
                fullWidth
                multiline
                maxRows={4}
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={loading}
                placeholder={
                    viewMode === 'discussion' 
                      ? '在此輸入工作流的初始指令...' 
                      : '輸入你的問題...'
                }
            />
            <Button
                variant="contained"
                onClick={handleSendMessage}
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