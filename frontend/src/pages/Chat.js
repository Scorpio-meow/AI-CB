import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
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
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import { FaRobot } from "react-icons/fa";
import { Send as SendIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import api from '../services/authService';
import ReactMarkdown from 'react-markdown';
import DiscussionBoard from './DiscussionBoard/DiscussionBoard';
import remarkGfm from 'remark-gfm';

function Chat() {
  const location = useLocation();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [userSelectedModel, setUserSelectedModel] = useState(false);
  const messagesEndRef = useRef(null);
  const [viewMode, setViewMode] = useState('chat');
  const discussionBoardRef = useRef(null);

  // Load available models (now fetched from /api/tags). Supports several response shapes.
  const loadAvailableModels = useCallback(async () => {
    try {
      // `api` baseURL already includes /api, so this requests /api/tags
      const response = await api.get('/tags');
      const payload = response.data;

      let models = [];
      let defaultModel = null;

      // Support payload as an array of strings
      if (Array.isArray(payload)) {
        models = payload;
      }

      // Support { models: [...], default: '...' }
      else if (payload && Array.isArray(payload.models)) {
        models = payload.models;
        defaultModel = payload.default || null;
      }

      // Support { tags: [...] } where tags may be strings or objects with name/value
      else if (payload && Array.isArray(payload.tags)) {
        models = payload.tags.map((t) => (typeof t === 'string' ? t : (t.name || t.value || ''))).filter(Boolean);
        defaultModel = payload.default || null;
      }

      // Support nested data arrays { data: [...] }
      else if (payload && Array.isArray(payload.data)) {
        models = payload.data;
      }

      // Final fallback
      if (!models || models.length === 0) {
        models = ['gpt-oss:20b', 'gemma3:27b'];
      }

      setAvailableModels(models);

      // If user explicitly selected a model, keep it (if still available).
      if (userSelectedModel && selectedModel) {
        if (models.includes(selectedModel)) {
          // keep user's choice
          setSelectedModel(selectedModel);
        } else {
          // user's chosen model no longer available -> fall back and clear flag
          setUserSelectedModel(false);
          setSelectedModel(defaultModel || models[0]);
        }
      } else {
        // No user selection yet, pick default or first
        setSelectedModel(defaultModel || models[0]);
      }
    } catch (error) {
      console.error('載入可用模型失敗:', error);
      // Set fallback models if API fails
      setAvailableModels(['gpt-oss:20b', 'gemma3:27b']);
      if (!userSelectedModel || !selectedModel) {
        setSelectedModel('gpt-oss:20b');
      }
    }
  }, [selectedModel, userSelectedModel]);

  // Define all functions before they are used in effects
  const loadConversation = useCallback(async (conversation) => {
    setViewMode('chat');
    try {
  const response = await api.get(`/chat/conversations/${conversation.id}`);
      setCurrentConversation(response.data);
      setMessages(response.data.messages || []);
    } catch (error) {
      setError('載入對話詳情失敗');
    }
  }, []); // State setters are stable

  const loadConversations = useCallback(async () => {
    try {
  const response = await api.get('/chat/conversations');
      setConversations(response.data);
      if (response.data.length > 0 && !currentConversation) {
        if (viewMode === 'chat') {
          // Automatically load the first conversation
          loadConversation(response.data[0]);
        }
      }
      // return fresh list to avoid callers using stale closure
      return response.data;
    } catch (error) {
      setError('載入對話失敗');
      return [];
    }
  }, [currentConversation, viewMode, loadConversation]);

  // Effects should be after function definitions
  useEffect(() => {
    loadAvailableModels();
  }, [loadAvailableModels]);

  // Poll for available models every 15 seconds to keep list up-to-date (即时更新)
  useEffect(() => {
    const intervalMs = 15000; // 15s
    const id = setInterval(() => {
      loadAvailableModels();
    }, intervalMs);
    return () => clearInterval(id);
  }, [loadAvailableModels]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    // Handle navigation from workflow page
    if (location.state?.conversationId) {
      loadConversation({ id: location.state.conversationId });
      // Clear state to prevent reloading on refresh
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location, navigate, loadConversation]);

  useEffect(() => {
    if (viewMode === 'chat') {
      scrollToBottom();
    }
  }, [messages, viewMode]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const sendChatMessage = useCallback(async () => {
    if (!newMessage.trim() || viewMode !== 'chat') return;

    const userMessage = {
      content: newMessage,
      is_user: true,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);
    const messageToSend = newMessage;
    setNewMessage('');
    setLoading(true);

    try {
  const response = await api.post('/chat/send', {
        content: messageToSend,
        conversation_id: currentConversation?.id,
        model_name: selectedModel
      });
      // 添加 GPT 回應到消息列表中，保留用戶消息
      setMessages(prev => [...prev, response.data.message]);
      // If server returned/created a different conversation id, refresh using fresh data
      if (!currentConversation || response.data.conversation_id !== currentConversation.id) {
        const updatedConvs = await loadConversations();
        const newConv = (updatedConvs || []).find(c => c.id === response.data.conversation_id) || response.data.conversation;
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
  }, [newMessage, viewMode, currentConversation, loadConversations, selectedModel]);

  const deleteConversation = useCallback(async (conversationId) => {
    try {
  await api.delete(`/chat/conversations/${conversationId}`);
      const newConversations = conversations.filter(c => c.id !== conversationId);
      setConversations(newConversations);
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setMessages([]);
      }
    } catch (error) {
      setError('刪除對話失敗');
    }
  }, [conversations, currentConversation]);

  // Simple preprocessing: convert HTML <br> tags to Markdown newlines
  const preprocessContent = (content) => {
    if (!content || typeof content !== 'string') return '';
    // replace common <br> variants with double newlines for markdown, then strip other tags
    return content.replace(/<br\s*\/?>/gi, '\n\n').replace(/<[^>]+>/g, '');
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

  const handleWorkflowComplete = useCallback((conversationId) => {
    if (conversationId) {
      loadConversation({ id: conversationId });
    }
    setViewMode('chat'); // Switch back to chat view
  }, [loadConversation]);

  const startNewConversation = () => {
    // Create a new conversation on the server, then load it
    setViewMode('chat');
    (async () => {
      try {
  const resp = await api.post('/chat/conversations');
        const newConv = resp.data;
        // refresh list and set current
        await loadConversations();
        setCurrentConversation(newConv);
        setMessages([]);
      } catch (e) {
        setError('建立新對話失敗');
      }
    })();
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
  <Box sx={{ width: 300, display: 'flex', flexDirection: 'column' }}>
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

  {/* 中間分隔線（垂直） */}
  <Divider orientation="vertical" flexItem />

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
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{preprocessContent(message.content)}</ReactMarkdown>
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
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
              {/* 模型選擇選單 */}
              {viewMode === 'chat' && (
                <FormControl sx={{ minWidth: 140 }}>
                  <InputLabel size="small">模型</InputLabel>
                  <Select
                    size="small"
                    value={selectedModel}
                    onChange={(e) => { setSelectedModel(e.target.value); setUserSelectedModel(true); }}
                    label="模型"
                    disabled={loading}
                  >
                    {availableModels.map((model) => (
                      <MenuItem key={model} value={model}>
                        {model}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}
              
              <TextField
                fullWidth
                multiline
                maxRows={4}
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyDown={handleKeyPress}
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