import { useState, useCallback, useRef } from 'react';
import api, { chatService, Conversation, Message } from '../services/api';
export function useChat() {
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [messagesOffset, setMessagesOffset] = useState(0);
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const loadConversationAbortRef = useRef<AbortController | null>(null);
  const loadConversationsAbortRef = useRef<AbortController | null>(null);
  const fetchConversations = useCallback(async (): Promise<Conversation[]> => {
    if (loadConversationsAbortRef.current) {
      loadConversationsAbortRef.current.abort();
    }
    const abortController = new AbortController();
    loadConversationsAbortRef.current = abortController;
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<Conversation[]>('/chat/conversations', {
        signal: abortController.signal
      });
      setConversations(response.data);
      return response.data;
    } catch (err: any) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') {
        return [];
      }
      const errorMsg = err.message || '無法獲取對話清單';
      setError(errorMsg);
      return [];
    } finally {
      setLoading(false);
      loadConversationsAbortRef.current = null;
    }
  }, []);
  const fetchConversation = useCallback(async (conversationId: number): Promise<Conversation | null> => {
    if (loadConversationAbortRef.current) {
      loadConversationAbortRef.current.abort();
    }
    const abortController = new AbortController();
    loadConversationAbortRef.current = abortController;
    setLoading(true);
    setError(null);
    try {
      const convResp = await api.get<Conversation>(`/chat/conversations/${conversationId}`, {
        signal: abortController.signal
      });
      setCurrentConversation(convResp.data);
      const msgsResp = await api.get<Message[]>(`/chat/conversations/${conversationId}/messages?limit=100&offset=0`, {
        signal: abortController.signal
      });
      const fetchedMessages = msgsResp.data || [];
      setMessages(fetchedMessages);
      setMessagesOffset(fetchedMessages.length);
      setHasMoreMessages(fetchedMessages.length === 100);
      return convResp.data;
    } catch (err: any) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') {
        return null;
      }
      const errorMsg = err.message || '無法獲取對話內容';
      setError(errorMsg);
      return null;
    } finally {
      setLoading(false);
      loadConversationAbortRef.current = null;
    }
  }, []);
  const loadMoreMessages = useCallback(async () => {
    if (!currentConversation || loadingMore || !hasMoreMessages) return;
    setLoadingMore(true);
    const abortController = new AbortController();
    try {
      const response = await api.get<Message[]>(
        `/chat/conversations/${currentConversation.id}/messages?limit=50&offset=${messagesOffset}`,
        { signal: abortController.signal }
      );
      const olderMessages = response.data || [];
      if (olderMessages.length > 0) {
        setMessages(prev => [...olderMessages, ...prev]);
        setMessagesOffset(prev => prev + olderMessages.length);
      }
      setHasMoreMessages(olderMessages.length === 50);
    } catch (err: any) {
      if (err.name !== 'CanceledError' && err.name !== 'AbortError') {
        setError(err.message || '無法載入更多訊息');
      }
    } finally {
      setLoadingMore(false);
    }
  }, [currentConversation, loadingMore, hasMoreMessages, messagesOffset]);
  const sendChatMessage = useCallback(async (
    content: string,
    selectedModel: string,
    reasoningEffort: string = 'medium',
    attachments?: import('../services/api').ChatAttachment[]
  ) => {
    if (!content.trim() && (!attachments || attachments.length === 0)) return;
    setLoading(true);
    setError(null);
    const userMsgId = Date.now();
    const userMessage: Message = {
      id: userMsgId,
      content,
      is_user: true,
      created_at: new Date().toISOString(),
      attachments: attachments || []
    };
    const botMsgId = userMsgId + 1;
    const botMessage: Message = {
      id: botMsgId,
      content: '',
      is_user: false,
      created_at: new Date().toISOString(),
      model_name: selectedModel,
      reasoning_effort: reasoningEffort,
      research_trace: [],
      sources: [],
      sources_detail: []
    };
    setMessages(prev => [...prev, userMessage, botMessage]);
    try {
      await chatService.sendMessageStream(
        content,
        currentConversation?.id || null,
        selectedModel,
        reasoningEffort,
        (ev) => {
          if (ev.event === 'step_start') {
            const stepData = ev.data;
            setMessages(prev => {
              const next = [...prev];
              const idx = next.findIndex(m => m.id === botMsgId);
              const targetIdx = idx !== -1 ? idx : next.length - 1;
              if (targetIdx >= 0 && !next[targetIdx].is_user) {
                const currentTrace = next[targetIdx].research_trace || [];
                const exists = currentTrace.some(s => s.step === stepData.step);
                if (!exists) {
                  next[targetIdx] = {
                    ...next[targetIdx],
                    research_trace: [...currentTrace, { ...stepData, status: 'running' }]
                  };
                }
              }
              return next;
            });
          } else if (ev.event === 'step_end') {
            const stepData = ev.data;
            setMessages(prev => {
              const next = [...prev];
              const idx = next.findIndex(m => m.id === botMsgId);
              const targetIdx = idx !== -1 ? idx : next.length - 1;
              if (targetIdx >= 0 && !next[targetIdx].is_user) {
                const currentTrace = next[targetIdx].research_trace || [];
                const updated = currentTrace.map(s => s.step === stepData.step ? { ...s, ...stepData } : s);
                if (!currentTrace.some(s => s.step === stepData.step)) {
                  updated.push(stepData);
                }
                next[targetIdx] = {
                  ...next[targetIdx],
                  research_trace: updated
                };
              }
              return next;
            });
          } else if (ev.event === 'token') {
            const token = ev.data?.content || '';
            setMessages(prev => {
              const next = [...prev];
              const idx = next.findIndex(m => m.id === botMsgId);
              const targetIdx = idx !== -1 ? idx : next.length - 1;
              if (targetIdx >= 0 && !next[targetIdx].is_user) {
                next[targetIdx] = {
                  ...next[targetIdx],
                  content: (next[targetIdx].content || '') + token
                };
              }
              return next;
            });
          } else if (ev.event === 'sources') {
            setMessages(prev => {
              const next = [...prev];
              const idx = next.findIndex(m => m.id === botMsgId);
              const targetIdx = idx !== -1 ? idx : next.length - 1;
              if (targetIdx >= 0 && !next[targetIdx].is_user) {
                next[targetIdx] = {
                  ...next[targetIdx],
                  sources: ev.data?.sources || [],
                  sources_detail: ev.data?.sources_detail || []
                };
              }
              return next;
            });
          } else if (ev.event === 'done') {
            const doneData = ev.data;
            setMessages(prev => {
              const next = [...prev];
              const idx = next.findIndex(m => m.id === botMsgId);
              const targetIdx = idx !== -1 ? idx : next.length - 1;
              if (targetIdx >= 0 && !next[targetIdx].is_user) {
                next[targetIdx] = {
                  ...next[targetIdx],
                  id: doneData.message_id || next[targetIdx].id,
                  content: doneData.answer || next[targetIdx].content,
                  sources: doneData.sources || next[targetIdx].sources,
                  sources_detail: doneData.sources_detail || next[targetIdx].sources_detail,
                  research_trace: doneData.research_trace || next[targetIdx].research_trace
                };
              }
              return next;
            });
            if (doneData.conversation_id && (!currentConversation || currentConversation.id !== doneData.conversation_id)) {
              fetchConversations().then(fresh => {
                const found = fresh.find(c => c.id === doneData.conversation_id);
                if (found) setCurrentConversation(found);
              });
            }
          } else if (ev.event === 'error') {
            setError(ev.data?.detail || '處理訊息時發生錯誤');
          }
        },
        undefined,
        attachments
      );
    } catch (err: any) {
      setError(err.message || '傳送訊息失敗');
      setMessages(prev => prev.filter(m => m.id !== botMsgId));
      throw err;
    } finally {
      setLoading(false);
    }
  }, [currentConversation, fetchConversations]);
  const deleteConversation = useCallback(async (conversationId: number): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await chatService.deleteConversation(conversationId);
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setMessages([]);
        setMessagesOffset(0);
        setHasMoreMessages(false);
      }
      return true;
    } catch (err: any) {
      setError(err.message || '刪除對話失敗');
      return false;
    } finally {
      setLoading(false);
    }
  }, [currentConversation]);
  const startNewConversation = useCallback(() => {
    setCurrentConversation(null);
    setMessages([]);
    setMessagesOffset(0);
    setHasMoreMessages(false);
  }, []);
  return {
    loading,
    loadingMore,
    error,
    setError,
    conversations,
    setConversations,
    currentConversation,
    setCurrentConversation,
    messages,
    setMessages,
    hasMoreMessages,
    fetchConversations,
    fetchConversation,
    loadMoreMessages,
    sendChatMessage,
    deleteConversation,
    startNewConversation
  };
}
export default useChat;
