import { createContext } from 'react';
import { CustomAgent } from '../services/customAgentService';

export interface AgentContextType {
  agents: CustomAgent[];
  loading: boolean;
  error: string | null;
  fetchAgents: (force?: boolean) => Promise<CustomAgent[]>;
  addAgent: (agent: CustomAgent) => void;
  updateAgent: (updatedAgent: CustomAgent) => void;
  removeAgent: (agentId: number) => void;
}

export const AgentContext = createContext<AgentContextType | undefined>(undefined);
