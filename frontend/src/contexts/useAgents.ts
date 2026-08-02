import { useContext } from 'react';
import { AgentContext, AgentContextType } from './agentContextInstance';
export const useAgents = (): AgentContextType => {
  const context = useContext(AgentContext);
  if (context === undefined) {
    throw new Error('useAgents must be used within an AgentProvider');
  }
  return context;
};
export default useAgents;
