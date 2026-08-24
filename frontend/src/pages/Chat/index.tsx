import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Box, Snackbar, Alert } from '@mui/material';
import api from '../../services/api';
import { useChat } from '../../hooks/useChat';
import { SnackbarState, ModelDetail } from './types';
import ChatSidebar from './ChatSidebar';
import ChatHeader from './ChatHeader';
import ChatMessageList from './ChatMessageList';
import ChatInputArea from './ChatInputArea';

export const ChatPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const [thinkOpenArr, setThinkOpenArr] = useState<Record<number | string, boolean>>({});
  const [newMessage, setNewMessage] = useState('');
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [, setModelDetails] = useState<ModelDetail[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [userSelectedModel, setUserSelectedModel] = useState(false);
  const [reasoningEffort, setReasoningEffort] = useState<string>('medium');
  const [modelsLoading, setModelsLoading] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<SnackbarState>({
    open: false,
    message: '',
    severity: 'info',
  });

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const messagesTopRef = useRef<HTMLDivElement | null>(null);

  const {
    loading,
    loadingMore,
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
    startNewConversation,
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

  const loadAvailableModels = useCallback(async (force = false) => {
    if (!force && (window as any).__tagsLoading) {
      return;
    }

    const normalizeModelList = (list: any[]): string[] => {
      const result: string[] = [];
      list.forEach((item) => {
        if (typeof item === 'string') {
          item.split(',').forEach((sub) => {
            const trimmed = sub.trim();
            if (trimmed && !result.includes(trimmed)) {
              result.push(trimmed);
            }
          });
        }
      });
      return result;
    };

    if (!force) {
      const cached = localStorage.getItem('cached_tags');
      const cacheTime = localStorage.getItem('cached_tags_time');
      if (cached && cacheTime) {
        const age = Date.now() - parseInt(cacheTime, 10);
        if (age < 5 * 60 * 1000) {
          try {
            const cachedData = JSON.parse(cached);
            const cachedModels = normalizeModelList(cachedData.models || []);
            const cachedDetails = cachedData.details || [];
            setAvailableModels(cachedModels);
            setModelDetails(cachedDetails);

            if (!selectedModelRef.current && cachedModels.length > 0) {
              const defaultModel = cachedData.default?.split(',')[0].trim() || cachedModels[0];
              setSelectedModel(defaultModel);
            }
            return;
          } catch (e) {
            console.error('Failed to parse cached models', e);
          }
        }
      }
    }

    (window as any).__tagsLoading = true;
    setModelsLoading(true);

    try {
      const res = await api.get('/chat/models');
      const models = normalizeModelList(res.data?.models || []);
      const details = res.data?.details || [];
      const rawDefault = res.data?.default || (models.length > 0 ? models[0] : 'gemma4:26b');
      const defaultModel = typeof rawDefault === 'string' ? rawDefault.split(',')[0].trim() : models[0];

      setAvailableModels(models);
      setModelDetails(details);

      try {
        localStorage.setItem('cached_tags', JSON.stringify({ ...res.data, models, default: defaultModel }));
        localStorage.setItem('cached_tags_time', Date.now().toString());
      } catch (e) {
        console.warn('Failed to save models to localStorage', e);
      }

      if (!userSelectedModelRef.current && !selectedModelRef.current) {
        setSelectedModel(defaultModel);
      } else if (selectedModelRef.current && !models.includes(selectedModelRef.current)) {
        setSelectedModel(defaultModel);
      }
    } catch (err) {
      console.warn('載入可用模型失敗，使用預設值', err);
      setAvailableModels(['gemma4:26b', 'gemma3:27b']);
      setModelDetails([]);
    } finally {
      (window as any).__tagsLoading = false;
      setModelsLoading(false);
    }
  }, []);

  const handleSelectModel = (model: string) => {
    setSelectedModel(model);
    setUserSelectedModel(true);
  };

  const handleToggleThinking = (id: number | string) => {
    setThinkOpenArr((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleCopyMessage = (text: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setSnackbar({
        open: true,
        message: '已複製內容至剪貼簿',
        severity: 'success',
      });
    }
  };

  const handleSend = async () => {
    if (!newMessage.trim()) return;

    const userMessage: any = {
      content: newMessage,
      is_user: true,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const toSend = newMessage;
    setNewMessage('');

    try {
      await sendChatMessage(toSend, selectedModel, reasoningEffort);
    } catch {
      setMessages((prev) => prev.slice(0, -1));
      setSnackbar({
        open: true,
        message: '發送訊息失敗，請稍後再試',
        severity: 'error',
      });
    }
  };

  const handleSelectConversation = async (id: number) => {
    await fetchConversation(id);
  };

  const handleDeleteConversation = async (id: number) => {
    const ok = await deleteConversation(id);
    if (ok) {
      setSnackbar({
        open: true,
        message: '對話已成功刪除',
        severity: 'info',
      });
    }
  };

  useEffect(() => {
    queueMicrotask(() => {
      loadAvailableModels();
      fetchConversations();
    });
  }, [loadAvailableModels, fetchConversations]);

  useEffect(() => {
    if (location.state?.conversationId) {
      queueMicrotask(() => {
        handleSelectConversation(location.state.conversationId);
      });
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location, navigate]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  return (
    <Box
      sx={{
        display: 'flex',
        height: 'calc(100vh - 110px)',
        width: '100%',
        backgroundColor: '#FFFFFF',
        borderRadius: 3,
        border: '1px solid #E2E8F0',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.04)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* 側邊欄（內部已自適應桌面常駐與移動端抽屜） */}
      <ChatSidebar
        open={mobileSidebarOpen}
        onClose={() => setMobileSidebarOpen(false)}
        conversations={conversations}
        currentConversation={currentConversation}
        onSelectConversation={handleSelectConversation}
        onNewConversation={startNewConversation}
        onDeleteConversation={handleDeleteConversation}
        loading={loading}
      />

      {/* 主要內容區 */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
        <ChatHeader
          availableModels={availableModels}
          selectedModel={selectedModel}
          onSelectModel={handleSelectModel}
          reasoningEffort={reasoningEffort}
          onSelectReasoningEffort={setReasoningEffort}
          modelsLoading={modelsLoading}
          onRefreshModels={() => loadAvailableModels(true)}
          currentConversation={currentConversation}
          onOpenSidebar={() => setMobileSidebarOpen(true)}
        />

        <ChatMessageList
          messages={messages}
          loading={loading}
          loadingMore={loadingMore}
          hasMoreMessages={hasMoreMessages}
          onLoadMore={loadMoreMessages}
          thinkOpenArr={thinkOpenArr}
          onToggleThinking={handleToggleThinking}
          onCopyMessage={handleCopyMessage}
          messagesEndRef={messagesEndRef}
          messagesTopRef={messagesTopRef}
        />

        <ChatInputArea
          value={newMessage}
          onChange={setNewMessage}
          onSend={handleSend}
          loading={loading}
        />
      </Box>

      {/* 提示通知 */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%', borderRadius: 2 }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ChatPage;
