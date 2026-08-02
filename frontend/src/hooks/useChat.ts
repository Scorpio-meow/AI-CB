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
  const sendChatMessage = useCallback(async (content: string, selectedModel: string) => {
    if (!content.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await chatService.sendMessage(content, currentConversation?.id || null, selectedModel);
      setMessages(prev => [...prev, response.message]);
      if (!currentConversation || response.conversation_id !== currentConversation.id) {
        const freshConvs = await fetchConversations();
        const found = freshConvs.find(c => c.id === response.conversation_id);
        if (found) {
          setCurrentConversation(found);
        }
      }
      return response;
    } catch (err: any) {
      setError(err.message || '傳送訊息失敗');
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
