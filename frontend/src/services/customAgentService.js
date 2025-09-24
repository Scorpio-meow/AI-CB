import { getApi } from './api.js';

// 使用統一的 API 管理器
const getApiClient = async () => {
  const api = await getApi();
  // 創建一個自訂 Agent 專用的客戶端
  return {
    get: (path) => api.get(`/custom_agents${path}`),
    post: (path, data) => api.post(`/custom_agents${path}`, data),
    put: (path, data) => api.put(`/custom_agents${path}`, data),
    delete: (path) => api.delete(`/custom_agents${path}`)
  };
};

// 獲取所有自訂 Agent (僅自訂)
export const getCustomAgents = async () => {
  const client = await getApiClient();
  return client.get('/');
};

// 獲取所有 Agent (包含預設)
export const getAllAgentsWithDetails = async () => {
  const client = await getApiClient();
  return client.get('/all_with_details');
};

// 根據 ID 獲取單一自訂 Agent
export const getCustomAgent = async (id) => {
  const client = await getApiClient();
  return client.get(`/${id}`);
};

// 創建新的自訂 Agent
export const createCustomAgent = async (agentData) => {
  const client = await getApiClient();
  return client.post('/', agentData);
};

// 更新指定的自訂 Agent
export const updateCustomAgent = async (id, agentData) => {
  const client = await getApiClient();
  return client.put(`/${id}`, agentData);
};

// 刪除指定的自訂 Agent
export const deleteCustomAgent = async (id) => {
  const client = await getApiClient();
  return client.delete(`/${id}`);
};