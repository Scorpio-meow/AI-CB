import React, { useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import * as customAgentService from '../services/customAgentService';
import { CustomAgent } from '../services/customAgentService';
import { hasValidAuth } from '../utils/tokenUtils';
import { AgentContext } from './agentContextInstance';
interface AgentProviderProps {
  children: ReactNode;
}
export const AgentProvider = ({ children }: AgentProviderProps) => {
  const [agents, setAgents] = useState<CustomAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);
  const fetchAgents = useCallback(async (force: boolean = false): Promise<CustomAgent[]> => {
    if (!hasValidAuth()) {
      if (import.meta.env.DEV) {
        console.debug('AgentContext: 沒有有效認證，跳過獲取 agents');
      }
      if (isMountedRef.current) {
        setLoading(false);
        setAgents([]);
      }
      return [];
    }
    try {
      if (isMountedRef.current) {
        setLoading(true);
        setError(null);
      }
      const response = await customAgentService.getAllAgentsWithDetails(force);
      if (!isMountedRef.current) return [];
      
      const data = response?.data || response || [];
      setAgents(data);
      return data;
    } catch (err: any) {
      if (err?.name === 'AbortError' || err?.name === 'CanceledError' || err?.message === 'canceled') {
        if (import.meta.env.DEV) console.debug('fetchAgents was cancelled', err);
        return [];
      }
      if (err?.response?.status === 403) {
        if (import.meta.env.DEV) {
          console.debug('AgentContext: 403 Forbidden - token 可能過期或無效');
        }
        if (isMountedRef.current) {
          setAgents([]);
        }
        return [];
      }
      if (isMountedRef.current) {
        setError('無法載入 Agents 列表。');
      }
      console.error(err);
      return [];
    } finally {
      if (isMountedRef.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    isMountedRef.current = true;
    const loadAgents = async () => {
      await fetchAgents();
    };
    loadAgents();
    return () => {
      isMountedRef.current = false;
    };
  }, [fetchAgents]);
  const addAgent = (agent: CustomAgent) => {
    setAgents(prev => [...prev, agent]);
  };
  const updateAgent = (updatedAgent: CustomAgent) => {
    setAgents(prev => prev.map(agent => (agent.id === updatedAgent.id ? updatedAgent : agent)));
  };
  const removeAgent = (agentId: number) => {
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
