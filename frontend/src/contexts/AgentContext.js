// src/contexts/AgentContext.js
import React, { createContext, useState, useEffect, useCallback, useContext, useRef } from 'react';
import * as customAgentService from '../services/customAgentService';
import { hasValidAuth } from '../utils/tokenUtils';

const AgentContext = createContext();

export const useAgents = () => useContext(AgentContext);

export const AgentProvider = ({ children }) => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isMountedRef = useRef(true);

  const fetchAgents = useCallback(async () => {
    // 檢查是否有有效的認證 token
    if (!hasValidAuth()) {
      if (process.env.NODE_ENV === 'development') {
        console.debug('AgentContext: 沒有有效認證，跳過獲取 agents');
      }
      if (isMountedRef.current) {
        setLoading(false);
        setAgents([]);
      }
      return;
    }

    try {
      if (isMountedRef.current) {
        setLoading(true);
        setError(null);
      }
      const response = await customAgentService.getAllAgentsWithDetails();
      if (!isMountedRef.current) return; // component unmounted, ignore
      if (response && response.data) setAgents(response.data);
    } catch (err) {
      // Ignore cancellation errors (Abort/Canceled)
      if (err?.name === 'AbortError' || err?.name === 'CanceledError' || err?.message === 'canceled') {
        if (process.env.NODE_ENV === 'development') console.debug('fetchAgents was cancelled', err);
        return;
      }
      
      // 403 錯誤表示未授權，可能是 token 過期或無效
      if (err?.response?.status === 403) {
        if (process.env.NODE_ENV === 'development') {
          console.debug('AgentContext: 403 Forbidden - token 可能過期或無效');
        }
        // 清空 agents 列表，但不顯示錯誤給用戶（token 刷新會自動處理）
        if (isMountedRef.current) {
          setAgents([]);
        }
        return;
      }
      
      if (isMountedRef.current) {
        setError('無法載入 Agents 列表。');
      }
      console.error(err);
    } finally {
      if (isMountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    fetchAgents();
    return () => {
      isMountedRef.current = false;
    };
  }, [fetchAgents]);

  const addAgent = (agent) => {
    setAgents(prev => [...prev, agent]);
  };

  const updateAgent = (updatedAgent) => {
    setAgents(prev => prev.map(agent => (agent.id === updatedAgent.id ? updatedAgent : agent)));
  };

  const removeAgent = (agentId) => {
    setAgents(prev => prev.filter(agent => agent.id !== agentId));
  };

  const value = {
    agents,
    loading,
    error,
    fetchAgents,
    addAgent,
    updateAgent,
    removeAgent
  };

  return (
    <AgentContext.Provider value={value}>
      {children}
    </AgentContext.Provider>
  );
};
