import { useState, useEffect, useRef, useCallback } from 'react';
import DOMPurify from 'dompurify';
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
  InputLabel,
  Snackbar,
  Tooltip
} from '@mui/material';
import { FaRobot } from "react-icons/fa";
import { ExpandMore, ExpandLess, LightbulbOutlined } from '@mui/icons-material';
import { Send as SendIcon, Delete as DeleteIcon, Add as AddIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import api from '../services/api';
import ReactMarkdown from 'react-markdown';
import DiscussionBoard from './DiscussionBoard/DiscussionBoard';
import remarkGfm from 'remark-gfm';
import { useChat } from '../hooks/useChat';

function Chat() {
  const [thinkOpenArr, setThinkOpenArr] = useState({});
  const location = useLocation();
  const navigate = useNavigate();
  const [newMessage, setNewMessage] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [modelDetails, setModelDetails] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [userSelectedModel, setUserSelectedModel] = useState(false);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const messagesEndRef = useRef(null);
  const [viewMode, setViewMode] = useState('chat');
  const discussionBoardRef = useRef(null);
  const messagesTopRef = useRef(null);

  // 使用對話自訂 Hook
  const {
    loading,
    loadingMore,
    error,
    setError,
    conversations,
    currentConversation,
    messages,
    setMessages,
    hasMoreMessages,
    fetchConversations,
    fetchConversation,
    loadMoreMessages,
    sendChatMessage,
    deleteConversation,
    startNewConversation
  } = useChat();

  const selectedModelRef = useRef(selectedModel);
  const userSelectedModelRef = useRef(userSelectedModel);

  useEffect(() => {
    selectedModelRef.current = selectedModel;
  }, [selectedModel]);

  useEffect(() => {
    userSelectedModelRef.current = userSelectedModel;
  }, [userSelectedModel]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // 載入可用模型
  const loadAvailableModels = useCallback(async (force = false) => {
    if (!force && window.__tagsLoading) {
      return;
    }

    if (!force) {
      const cached = localStorage.getItem('cached_tags');
      const cacheTime = localStorage.getItem('cached_tags_time');
      if (cached && cacheTime) {
        const age = Date.now() - parseInt(cacheTime, 10);
        if (age < 5 * 60 * 1000) {
          try {
            const cachedData = JSON.parse(cached);
            const cachedModels = cachedData.models || [];
            const cachedDetails = cachedData.details || [];

            setAvailableModels(cachedModels);
            setModelDetails(cachedDetails);

            const currentSelectedModel = selectedModelRef.current;
            if (!currentSelectedModel && cachedData.default) {
              setSelectedModel(cachedData.default);
            } else if (!currentSelectedModel && cachedModels.length > 0) {
              setSelectedModel(cachedModels[0]);
            }
            return;
          } catch (e) {
            console.warn('解析緩存失敗', e);
          }
        }
      }
    }

    window.__tagsLoading = true;
    setModelsLoading(true);
    try {
      const externalTagsUrl = import.meta.env.VITE_TAGS_URL;
      const backendProxyWhenExternal = externalTagsUrl ? '/api/external-tags' : null;
      let payload;

      if (backendProxyWhenExternal) {
        try {
          const response = await api.get('/external-tags');
          payload = response.data;
          if (!payload) payload = null;
        } catch (e) {
          try {
            const response = await api.get('/tags');
            payload = response.data;
          } catch (innerErr) {
            payload = null;
          }
        }
      } else {
        const response = await api.get('/tags');
        payload = response.data;
      }

      let models = [];
      let details = [];
      let defaultModel = null;

      const normalizeModels = (items) => {
        if (!Array.isArray(items)) return { models: [], details: [] };
        const modelsList = [];
        const detailsList = [];

        items.forEach((item) => {
          let modelName = '';
          let modelDetail = null;

          if (typeof item === 'string') {
            modelName = item.trim();
          } else if (item && typeof item === 'object') {
            modelName = item.name || item.model || item.value || item.id || item.label;
            if (modelName && typeof modelName === 'string') {
              modelName = modelName.trim();
              modelDetail = {
                name: modelName,
                size: item.size || item.details?.parameter_size || null,
                family: item.details?.family || item.family || null,
                quantization: item.details?.quantization_level || null,
                format: item.details?.format || null
              };
            }
          }

          if (modelName) {
            modelsList.push(modelName);
            detailsList.push(modelDetail);
          }
        });

        return { models: modelsList, details: detailsList };
      };

      if (Array.isArray(payload)) {
        const result = normalizeModels(payload);
        models = result.models;
        details = result.details;
      } else if (payload && Array.isArray(payload.models)) {
        const result = normalizeModels(payload.models);
        models = result.models;
        details = result.details;
        defaultModel = payload.default || null;
      } else if (payload && Array.isArray(payload.tags)) {
        const result = normalizeModels(payload.tags);
        models = result.models;
        details = result.details;
        defaultModel = payload.default || null;
      } else if (payload && Array.isArray(payload.data)) {
        const result = normalizeModels(payload.data);
        models = result.models;
        details = result.details;
      } else if (payload && Array.isArray(payload.items)) {
        const result = normalizeModels(payload.items);
        models = result.models;
        details = result.details;
      }

      if (!models || models.length === 0) {
        models = ['gemma4:26b', 'gemma3:27b'];
        details = [];
      }

      setAvailableModels(models);
      setModelDetails(details);

      try {
        localStorage.setItem('cached_tags', JSON.stringify({ models, details, default: defaultModel }));
        localStorage.setItem('cached_tags_time', Date.now().toString());
      } catch (e) {
        console.warn('緩存 tags 失敗', e);
      }

      const currentSelectedModel = selectedModelRef.current;
      const currentUserSelectedModel = userSelectedModelRef.current;

      if (currentUserSelectedModel && currentSelectedModel && models.includes(currentSelectedModel)) {
        // keep user selection
      } else if (currentSelectedModel && models.includes(currentSelectedModel)) {
        // keep current
      } else {
        const newModel = defaultModel || models[0];
        setSelectedModel(newModel);
      }

      if (force) {
        setSnackbar({ open: true, message: `已更新模型列表 (${models.length} 個模型)`, severity: 'success' });
      }
    } catch (error) {
      console.warn('載入可用模型失敗，將使用預設模型。', error);
      setSnackbar({ open: true, message: '載入可用模型失敗，已改為使用預設模型', severity: 'warning' });
      setAvailableModels(['gemma4:26b', 'gemma3:27b']);
      setModelDetails([]);
      const currentSelectedModel = selectedModelRef.current;
      const currentUserSelectedModel = userSelectedModelRef.current;
      if (!currentUserSelectedModel || !currentSelectedModel) {
        setSelectedModel('gemma4:26b');
      }
    } finally {
      window.__tagsLoading = false;
      setModelsLoading(false);
    }
  }, []);

  const loadConversation = useCallback(async (conversation) => {
    setViewMode('chat');
    await fetchConversation(conversation.id);
  }, [fetchConversation]);

  const loadConversations = useCallback(async () => {
    return await fetchConversations();
  }, [fetchConversations]);

  useEffect(() => {
    queueMicrotask(() => {
      loadAvailableModels();
    });
  }, [loadAvailableModels]);

  useEffect(() => {
    const defaultInterval = 5 * 60 * 1000;
    const configuredInterval = import.meta.env.VITE_MODEL_POLL_INTERVAL_MS
      ? parseInt(import.meta.env.VITE_MODEL_POLL_INTERVAL_MS, 10)
      : defaultInterval;
    const intervalMs = isNaN(configuredInterval) ? defaultInterval : configuredInterval;

    const id = setInterval(() => {
      loadAvailableModels(false);
    }, intervalMs);
    return () => clearInterval(id);
  }, [loadAvailableModels]);

  useEffect(() => {
    queueMicrotask(() => {
      loadConversations();
    });
  }, [loadConversations]);

  useEffect(() => {
    if (location.state?.conversationId) {
      queueMicrotask(() => {
        loadConversation({ id: location.state.conversationId });
      });
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location, navigate, loadConversation]);

  useEffect(() => {
    if (viewMode === 'chat') {
      scrollToBottom();
    }
  }, [messages, viewMode, scrollToBottom]);

  // IntersectionObserver for auto-loading more messages when scrolling to top
  useEffect(() => {
    const element = messagesTopRef.current;
    if (!element || !hasMoreMessages || loadingMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && hasMoreMessages && !loadingMore) {
          loadMoreMessages();
        }
      },
      {
        root: null,
        rootMargin: '100px',
        threshold: 0.1
      }
    );

    observer.observe(element);

    return () => {
      if (element) {
        observer.unobserve(element);
      }
      observer.disconnect();
    };
  }, [hasMoreMessages, loadingMore, loadMoreMessages]);

  const sendChatMessageCallback = useCallback(async () => {
    if (!newMessage.trim() || viewMode !== 'chat') return;

    const userMessage = {
      content: newMessage,
      is_user: true,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMessage]);
    const messageToSend = newMessage;
    setNewMessage('');

    try {
      await sendChatMessage(messageToSend, selectedModel);
    } catch {
      setMessages((prev) => prev.slice(0, -1));
    }
  }, [newMessage, viewMode, sendChatMessage, selectedModel, setMessages]);

  const deleteConversationCallback = useCallback(async (conversationId) => {
    await deleteConversation(conversationId);
  }, [deleteConversation]);

  // Simple preprocessing
  const preprocessContent = (content) => {
    if (!content || typeof content !== 'string') return '';
    const withBreaks = content.replace(/<br\s*\/?/gi, '\n\n');
    try {
      return DOMPurify.sanitize(withBreaks, { ALLOWED_TAGS: [], ALLOWED_ATTR: {} });
    } catch (err) {
      console.warn('DOMPurify failed to sanitize content', err);
      let stripped = withBreaks;
      let previous;
      do {
        previous = stripped;
        stripped = stripped.replace(/<[^>]+>/g, '');
      } while (stripped !== previous);
      return stripped;
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
      sendChatMessageCallback();
    }
  };

  const handleWorkflowComplete = useCallback(async (conversationId) => {
    setViewMode('chat');
    if (conversationId) {
      await loadConversations();
      await loadConversation({ id: conversationId });
    }
  }, [loadConversation, loadConversations]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex' }}>
      {/* 側邊欄 */}
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
                sx={{
                  borderLeft: currentConversation?.id === conv.id && viewMode === 'chat' ? 3 : 0,
                  borderColor: 'primary.main',
                  display: 'flex',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  bgcolor: currentConversation?.id === conv.id && viewMode === 'chat' ? 'action.selected' : 'transparent',
                  '&:hover': { bgcolor: 'action.hover' }
                }}
                onClick={() => loadConversation(conv)}
              >
                <ListItemText
                  primary={conv.title}
                  secondary={new Date(conv.updated_at).toLocaleDateString()}
                  primaryTypographyProps={{ noWrap: true, fontSize: '0.9rem' }}
                />
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); deleteConversationCallback(conv.id); }}
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
        {/* 主要內容區域 */}
        <Box sx={{ flex: 1, overflow: 'hidden' }}>
          {viewMode === 'chat' ? (
            <>
              <Paper sx={{ p: 2, borderRadius: 0 }} elevation={1}>
                <Typography variant="h6">{currentConversation?.title || '新對話'}</Typography>
              </Paper>
              {error && (<Alert severity="error" onClose={() => setError('')}>{error}</Alert>)}
              <Box sx={{ height: 'calc(100% - 68px)', overflow: 'auto', p: 2 }}>
                {hasMoreMessages && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={loadMoreMessages}
                      disabled={loadingMore}
                      startIcon={loadingMore ? <CircularProgress size={16} /> : null}
                    >
                      {loadingMore ? '載入中...' : '載入更多訊息'}
                    </Button>
                  </Box>
                )}
                <div ref={messagesTopRef} style={{ height: '1px' }} />

                {messages.map((message, index) => {
                  let thinkContent = null;
                  let mainContent = message.content;
                  const thinkMatch = typeof mainContent === 'string' ? mainContent.match(/<think>([\s\S]*?)<\/think>/i) : null;
                  if (thinkMatch) {
                    thinkContent = thinkMatch[1].trim();
                    mainContent = mainContent.replace(thinkMatch[0], '').trim();
                  }
                  const thinkOpen = !!thinkOpenArr[index];
                  const handleToggleThink = () => setThinkOpenArr(prev => ({ ...prev, [index]: !prev[index] }));
                  return (
                    <Box key={index} sx={{ display: 'flex', justifyContent: message.is_user ? 'flex-end' : 'flex-start', mb: 2 }}>
                      <Paper sx={{ p: 2, maxWidth: '70%', backgroundColor: message.is_user ? 'primary.main' : 'grey.100', color: message.is_user ? 'white' : 'text.primary' }}>
                        {thinkContent && (
                          <Box sx={{ mb: 1, p: 1.5, backgroundColor: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }} onClick={handleToggleThink}>
                              <LightbulbOutlined sx={{ color: '#ad8b00', mr: 1 }} fontSize="small" />
                              <Typography variant="body2" sx={{ color: '#ad8b00', fontWeight: 500, flex: 1 }}>AI思考</Typography>
                              {thinkOpen ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
                            </Box>
                            {thinkOpen && (
                              <Box sx={{ mt: 1 }}>
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{thinkContent}</ReactMarkdown>
                              </Box>
                            )}
                          </Box>
                        )}
                        {mainContent && (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{preprocessContent(mainContent)}</ReactMarkdown>
                        )}
                        {!message.is_user && message.context_used && (
                          <Box sx={{ mt: 1 }}><Chip label="使用了知識庫" size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} /></Box>
                        )}
                      </Paper>
                    </Box>
                  );
                })}
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

        {/* 輸入區域 */}
        <Paper sx={{ p: 2, borderRadius: 0, borderTop: 1, borderColor: 'divider' }} elevation={2}>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
            {viewMode === 'chat' && (
              <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'flex-end' }}>
                <FormControl sx={{ minWidth: 180 }}>
                  <InputLabel size="small">模型</InputLabel>
                  <Select
                    size="small"
                    value={selectedModel || ''}
                    onChange={(e) => {
                      const newModel = e.target.value;
                      setSelectedModel(newModel);
                      setUserSelectedModel(true);
                    }}
                    label="模型"
                    disabled={loading || modelsLoading}
                  >
                    {availableModels.map((model, index) => {
                      const detail = modelDetails[index];
                      return (
                        <MenuItem key={model} value={model}>
                          <Box>
                            <Typography variant="body2">{model}</Typography>
                            {detail && (detail.size || detail.family) && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                {detail.family && `${detail.family}`}
                                {detail.size && ` • ${detail.size}`}
                                {detail.quantization && ` • ${detail.quantization}`}
                              </Typography>
                            )}
                          </Box>
                        </MenuItem>
                      );
                    })}
                  </Select>
                </FormControl>
                <Tooltip title="刷新模型列表">
                  <IconButton
                    size="small"
                    onClick={() => loadAvailableModels(true)}
                    disabled={modelsLoading}
                    sx={{ mb: 0.5 }}
                  >
                    <RefreshIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
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
              disabled={loading}
            >
              <SendIcon />
            </Button>
          </Box>
        </Paper>
      </Box>

      {/* Snackbar 通知 */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default Chat;