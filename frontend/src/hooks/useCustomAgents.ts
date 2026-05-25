import { useState, useCallback } from 'react';
import * as customAgentService from '../services/customAgentService';
import { CustomAgent } from '../services/customAgentService';

export function useCustomAgents() {
  const [agents, setAgents] = useState<CustomAgent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = useCallback(async (force: boolean = false): Promise<CustomAgent[]> => {
    setLoading(true);
    setError(null);
    try {
      const response = await customAgentService.getAllAgentsWithDetails(force);
      const data = response?.data || response || [];
      setAgents(data);
      return data;
    } catch (err: any) {
      if (err?.name === 'AbortError' || err?.name === 'CanceledError' || err?.message === 'canceled') {
        return [];
      }
      const errorMsg = err.message || '無法載入自訂 Agent 列表';
      setError(errorMsg);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const createAgent = useCallback(async (agentData: Partial<CustomAgent>): Promise<CustomAgent | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await customAgentService.createCustomAgent(agentData);
      const newAgent = response?.data || response;
      if (newAgent) {
        setAgents(prev => [...prev, newAgent]);
      }
      return newAgent;
    } catch (err: any) {
      setError(err.message || '創建自訂 Agent 失敗');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateAgent = useCallback(async (id: number, agentData: Partial<CustomAgent>): Promise<CustomAgent | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await customAgentService.updateCustomAgent(id, agentData);
      const updatedAgent = response?.data || response;
      if (updatedAgent) {
        setAgents(prev => prev.map(a => a.id === id ? updatedAgent : a));
      }
      return updatedAgent;
    } catch (err: any) {
      setError(err.message || '更新自訂 Agent 失敗');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteAgent = useCallback(async (id: number): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await customAgentService.deleteCustomAgent(id);
      setAgents(prev => prev.filter(a => a.id !== id));
      return true;
    } catch (err: any) {
      setError(err.message || '刪除自訂 Agent 失敗');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    agents,
    setAgents,
    loading,
    error,
    fetchAgents,
    createAgent,
    updateAgent,
    deleteAgent,
  };
}
export default useCustomAgents;
