import api from './api';

const basePath = '/custom_agents';

// 獲取所有自訂 Agent (僅自訂)
export const getCustomAgents = () => {
  return api.get(`${basePath}/`);
};

// 獲取所有 Agent (包含預設)
export const getAllAgentsWithDetails = () => {
  return api.get(`${basePath}/all_with_details`);
};

// 根據 ID 獲取單一自訂 Agent
export const getCustomAgent = (id) => {
  return api.get(`${basePath}/${id}`);
};

// 創建新的自訂 Agent
export const createCustomAgent = (agentData) => {
  return api.post(`${basePath}/`, agentData);
};

// 更新指定的自訂 Agent
export const updateCustomAgent = (id, agentData) => {
  return api.put(`${basePath}/${id}`, agentData);
};

// 刪除指定的自訂 Agent
export const deleteCustomAgent = (id) => {
  return api.delete(`${basePath}/${id}`);
};