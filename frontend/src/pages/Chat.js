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

function Chat() {
  // <think> 展開狀態，key 為訊息 index
  const [thinkOpenArr, setThinkOpenArr] = useState({});
  const location = useLocation();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [modelDetails, setModelDetails] = useState([]); // 存儲完整的模型詳細信息
  const [selectedModel, setSelectedModel] = useState('');
  const [userSelectedModel, setUserSelectedModel] = useState(false);
  const [modelsLoading, setModelsLoading] = useState(false); // 模型列表載入狀態
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' }); // Snackbar 狀態
  const messagesEndRef = useRef(null);
  const [viewMode, setViewMode] = useState('chat');
  const discussionBoardRef = useRef(null);

  // 消息分頁狀態
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [messagesOffset, setMessagesOffset] = useState(0);
  const messagesTopRef = useRef(null);

  // AbortController refs for cancelling requests
  const loadConversationAbortRef = useRef(null);
  const loadConversationsAbortRef = useRef(null);
  
  // Refs for model selection to avoid dependency issues
  const selectedModelRef = useRef(selectedModel);
  const userSelectedModelRef = useRef(userSelectedModel);
  
  // Update refs when state changes
  useEffect(() => {
    selectedModelRef.current = selectedModel;
  }, [selectedModel]);
  
  useEffect(() => {
    userSelectedModelRef.current = userSelectedModel;
  }, [userSelectedModel]);

  // Load available models (now fetched from /api/tags). Supports several response shapes.
  const loadAvailableModels = useCallback(async (force = false) => {
    // 防止並發請求：如果正在請求中且非強制刷新，直接返回
    if (!force && window.__tagsLoading) {
      if (process.env.NODE_ENV === 'development') console.debug('Tags API 請求進行中，跳過重複請求');
      return;
    }

    // 檢查緩存（5分鐘內的緩存有效）
    if (!force) {
      const cached = localStorage.getItem('cached_tags');
      const cacheTime = localStorage.getItem('cached_tags_time');
      if (cached && cacheTime) {
        const age = Date.now() - parseInt(cacheTime, 10);
        if (age < 5 * 60 * 1000) { // 5 分鐘緩存
          if (process.env.NODE_ENV === 'development') console.debug('使用緩存的 tags 數據');
          try {
            const cachedData = JSON.parse(cached);
            const cachedModels = cachedData.models || [];
            const cachedDetails = cachedData.details || [];
            
            setAvailableModels(cachedModels);
            setModelDetails(cachedDetails);
            
            // 只在沒有選中模型時才設置默認值
            const currentSelectedModel = selectedModelRef.current;
            if (!currentSelectedModel && cachedData.default) {
              setSelectedModel(cachedData.default);
              console.log('[Models] 從緩存設置默認模型:', cachedData.default);
            } else if (!currentSelectedModel && cachedModels.length > 0) {
              setSelectedModel(cachedModels[0]);
              console.log('[Models] 從緩存設置第一個模型:', cachedModels[0]);
            }
            return;
          } catch (e) {
            console.warn('解析緩存失敗', e);
          }
        }
      }
    }

    window.__tagsLoading = true;
    setModelsLoading(true); // 開始載入
    try {
      const externalTagsUrl = process.env.REACT_APP_TAGS_URL;
      // If an external tags URL is configured, prefer querying our backend proxy to avoid
      // browser CORS issues. The backend exposes `/api/external-tags` which will fetch
      // the external URL server-side.
      const backendProxyWhenExternal = externalTagsUrl ? '/api/external-tags' : null;
      let payload;

      if (backendProxyWhenExternal) {
        // Use backend proxy to avoid browser CORS issues
        try {
          const response = await api.get('/external-tags');
          payload = response.data;
          // Some proxy implementations may return a wrapper object with `models`
          if (!payload) payload = null;
        } catch (e) {
          console.warn('Backend proxy /api/external-tags failed, falling back to /api/tags', e);
          try {
            const response = await api.get('/tags');
            payload = response.data;
          } catch (innerErr) {
            console.warn('Fallback /api/tags also failed:', innerErr);
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
              // 提取模型詳細信息
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
        models = ['gpt-oss:20b', 'gemma3:27b'];
        details = [];
      }

      setAvailableModels(models);
      setModelDetails(details);

      // 緩存結果
      try {
        localStorage.setItem('cached_tags', JSON.stringify({ models, details, default: defaultModel }));
        localStorage.setItem('cached_tags_time', Date.now().toString());
      } catch (e) {
        console.warn('緩存 tags 失敗', e);
      }

      // 設置選中的模型
      // 如果用戶已經手動選擇了模型，保持用戶的選擇（前提是模型仍在列表中）
      const currentSelectedModel = selectedModelRef.current;
      const currentUserSelectedModel = userSelectedModelRef.current;
      
      if (currentUserSelectedModel && currentSelectedModel && models.includes(currentSelectedModel)) {
        // 保持用戶選擇，不需要重新設置
        console.log('[Models] 保持用戶選擇的模型:', currentSelectedModel);
      } else if (currentSelectedModel && models.includes(currentSelectedModel)) {
        // 當前選擇的模型仍在列表中，保持選擇
        console.log('[Models] 保持當前模型:', currentSelectedModel);
      } else {
        // 設置新的默認模型
        const newModel = defaultModel || models[0];
        setSelectedModel(newModel);
        console.log('[Models] 設置默認模型:', newModel);
      }

      // 成功載入時顯示提示
      if (force) {
        setSnackbar({ open: true, message: `已更新模型列表 (${models.length} 個模型)`, severity: 'success' });
      }
    } catch (error) {
      // 最後保險處理：顯示友善提示、使用預設模型，但不把原始 fetch 錯誤暴露為未處理例外
      console.warn('載入可用模型失敗，將使用預設模型。', error);
      setSnackbar({ open: true, message: '載入可用模型失敗，已改為使用預設模型', severity: 'warning' });
      setAvailableModels(['gpt-oss:20b', 'gemma3:27b']);
      setModelDetails([]);
      const currentSelectedModel = selectedModelRef.current;
      const currentUserSelectedModel = userSelectedModelRef.current;
      if (!currentUserSelectedModel || !currentSelectedModel) {
        setSelectedModel('gpt-oss:20b');
      }
    } finally {
      window.__tagsLoading = false;
      setModelsLoading(false); // 結束載入
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  // 使用 ref 來訪問 selectedModel 和 userSelectedModel，避免無限循環

  // Define all functions before they are used in effects
  const loadConversation = useCallback(async (conversation) => {
    setViewMode('chat');

    // Cancel previous request if any
    if (loadConversationAbortRef.current) {
      loadConversationAbortRef.current.abort();
    }

    const abortController = new AbortController();
    loadConversationAbortRef.current = abortController;

    // 45 second timeout for DevTunnels
    const timeoutId = setTimeout(() => abortController.abort(), 45000);

    try {
      // Fetch conversation metadata
      const convResp = await api.get(`/chat/conversations/${conversation.id}`, {
        signal: abortController.signal
      });
      setCurrentConversation(convResp.data);

      // Fetch messages paginated to avoid loading huge payloads
      // Load the most recent 100 messages by default
      const msgsResp = await api.get(`/chat/conversations/${conversation.id}/messages?limit=100&offset=0`, {
        signal: abortController.signal
      });
      const fetchedMessages = msgsResp.data || [];
      setMessages(fetchedMessages);
      setMessagesOffset(fetchedMessages.length);

      // If we got exactly 100 messages, there might be more
      setHasMoreMessages(fetchedMessages.length === 100);

      clearTimeout(timeoutId);
    } catch (error) {
      if (error.name === 'CanceledError' || error.name === 'AbortError') {
        // 在開發環境顯示更詳細的取消日誌，生產環境避免噪音
        if (process.env.NODE_ENV === 'development') console.debug('loadConversation request cancelled', error);
      } else {
        console.error('載入對話失敗:', error);
        setError('載入對話詳情失敗，請稍後重試');
      }
      clearTimeout(timeoutId);
    } finally {
      loadConversationAbortRef.current = null;
    }
  }, []); // State setters are stable

  const loadConversations = useCallback(async () => {
    // Cancel previous request if any
    if (loadConversationsAbortRef.current) {
      loadConversationsAbortRef.current.abort();
    }

    const abortController = new AbortController();
    loadConversationsAbortRef.current = abortController;

    const timeoutId = setTimeout(() => abortController.abort(), 45000); // 45 秒超時

    try {
      const response = await api.get('/chat/conversations', {
        signal: abortController.signal
      });
      setConversations(response.data);
      clearTimeout(timeoutId);
      // return fresh list to avoid callers using stale closure
      return response.data;
    } catch (error) {
      if (error.name === 'CanceledError' || error.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') console.debug('loadConversations request cancelled', error);
      } else {
        console.error('載入對話失敗:', error);
        setError('載入對話失敗，請稍後重試');
      }
      clearTimeout(timeoutId);
      return [];
    } finally {
      loadConversationsAbortRef.current = null;
    }
  }, []);

  // Load more (older) messages for the current conversation
  const loadMoreMessages = useCallback(async () => {
    if (!currentConversation || loadingMore || !hasMoreMessages) {
      return;
    }

    setLoadingMore(true);

    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 45000); // 45 秒超時

    try {
      const response = await api.get(
        `/chat/conversations/${currentConversation.id}/messages?limit=50&offset=${messagesOffset}`,
        { signal: abortController.signal }
      );

      const olderMessages = response.data || [];

      if (olderMessages.length > 0) {
        // Prepend older messages to the beginning
        setMessages(prev => [...olderMessages, ...prev]);
        setMessagesOffset(prev => prev + olderMessages.length);
      }

      // If we got fewer than 50, we've reached the end
      setHasMoreMessages(olderMessages.length === 50);

      clearTimeout(timeoutId);
    } catch (error) {
      if (error.name === 'CanceledError' || error.name === 'AbortError') {
        if (process.env.NODE_ENV === 'development') console.debug('loadMoreMessages request cancelled', error);
      } else {
        console.error('載入更多消息失敗:', error);
        setError('載入更多消息失敗');
      }
      clearTimeout(timeoutId);
    } finally {
      setLoadingMore(false);
    }
  }, [currentConversation, loadingMore, hasMoreMessages, messagesOffset]);

  // Effects should be after function definitions
  useEffect(() => {
    loadAvailableModels();
  }, [loadAvailableModels]);

  // Poll for available models every 5 minutes to keep list up-to-date
  // 在 DevTunnels 環境下減少請求頻率以避免超時
  // 可通過 REACT_APP_MODEL_POLL_INTERVAL_MS 環境變數配置（單位：毫秒）
  useEffect(() => {
    const defaultInterval = 5 * 60 * 1000; // 5 分鐘預設值
    const configuredInterval = process.env.REACT_APP_MODEL_POLL_INTERVAL_MS
      ? parseInt(process.env.REACT_APP_MODEL_POLL_INTERVAL_MS, 10)
      : defaultInterval;
    const intervalMs = isNaN(configuredInterval) ? defaultInterval : configuredInterval;

    if (process.env.NODE_ENV === 'development') {
      console.debug(`模型列表輪詢間隔: ${intervalMs / 1000} 秒`);
    }

    const id = setInterval(() => {
      loadAvailableModels(false); // 使用緩存策略
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

  // IntersectionObserver for auto-loading more messages when scrolling to top
  useEffect(() => {
    const element = messagesTopRef.current;
    if (!element || !hasMoreMessages || loadingMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        // When the top marker becomes visible, load more messages
        if (entry.isIntersecting && hasMoreMessages && !loadingMore) {
          loadMoreMessages();
        }
      },
      {
        root: null, // viewport
        rootMargin: '100px', // trigger 100px before reaching the top
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
    // 只清空當前對話狀態，不在服務器創建新對話
    // 實際的對話會在使用者發送第一條訊息時自動創建
    setViewMode('chat');
    setCurrentConversation(null);
    setMessages([]);
    setMessagesOffset(0);
    setHasMoreMessages(false);
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
                {/* 載入更多按鈕 - 顯示在消息列表頂部 */}
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
                {/* IntersectionObserver 目標 - 用於自動載入 */}
                <div ref={messagesTopRef} style={{ height: '1px' }} />

                {messages.map((message, index) => {
                  // 解析 <think> ... </think> 區塊
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
                        {/* think 區塊 */}
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
                        {/* 主內容 */}
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

        {/* 輸入區域 (固定在底部) */}
        <Paper sx={{ p: 2, borderRadius: 0, borderTop: 1, borderColor: 'divider' }} elevation={2}>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
            {/* 模型選擇選單 */}
            {viewMode === 'chat' && (
              <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'flex-end' }}>
                <FormControl sx={{ minWidth: 180 }}>
                  <InputLabel size="small">模型</InputLabel>
                  <Select
                    size="small"
                    value={selectedModel || ''}
                    onChange={(e) => { 
                      const newModel = e.target.value;
                      console.log('[Models] 用戶選擇模型:', newModel);
                      setSelectedModel(newModel); 
                      setUserSelectedModel(true); 
                    }}
                    label="模型"
                    disabled={loading || modelsLoading}
                    endAdornment={
                      modelsLoading && (
                        <CircularProgress
                          size={16}
                          sx={{ position: 'absolute', right: 30, pointerEvents: 'none' }}
                        />
                      )
                    }
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