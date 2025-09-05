// src/contexts/AgentContext.js
import React, { createContext, useState, useEffect, useCallback, useContext } from 'react';
import * as customAgentService from '../services/customAgentService';

const AgentContext = createContext();

export const useAgents = () => useContext(AgentContext);

export const AgentProvider = ({ children }) => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAgents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await customAgentService.getAllAgentsWithDetails();
      setAgents(response.data);
    } catch (err) {
      setError('無法載入 Agents 列表。');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
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
