// src/contexts/AgentContext.js
import React, { createContext, useState, useEffect, useCallback, useContext, useRef } from 'react';
import * as customAgentService from '../services/customAgentService';

const AgentContext = createContext();

export const useAgents = () => useContext(AgentContext);

export const AgentProvider = ({ children }) => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isMountedRef = useRef(true);

  const fetchAgents = useCallback(async () => {
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
