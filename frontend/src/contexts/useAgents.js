import { useContext } from 'react';
import { AgentContext } from './agentContextInstance';

export const useAgents = () => useContext(AgentContext);