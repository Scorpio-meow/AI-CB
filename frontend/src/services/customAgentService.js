import axios from 'axios';

// Support REACT_APP_API_URL that may include or omit the `/api` prefix.
// Examples supported:
// - REACT_APP_API_URL=http://localhost:8001
// - REACT_APP_API_URL=http://localhost:8001/api
const RAW_API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';
const API_URL_NO_TRAIL = RAW_API_URL.replace(/\/+$/, ''); // remove trailing slashes
const API_BASE = API_URL_NO_TRAIL.endsWith('/api') ? API_URL_NO_TRAIL : `${API_URL_NO_TRAIL}/api`;

const apiClient = axios.create({
  baseURL: `${API_BASE}/custom_agents`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 獲取所有自訂 Agent (僅自訂)
export const getCustomAgents = () => {
  return apiClient.get('/');
};

// 獲取所有 Agent (包含預設)
export const getAllAgentsWithDetails = () => {
  return apiClient.get('/all_with_details');
};

// 根據 ID 獲取單一自訂 Agent
export const getCustomAgent = (id) => {
  return apiClient.get(`/${id}`);
};

// 創建新的自訂 Agent
export const createCustomAgent = (agentData) => {
  return apiClient.post('/', agentData);
};

// 更新指定的自訂 Agent
export const updateCustomAgent = (id, agentData) => {
  return apiClient.put(`/${id}`, agentData);
};

// 刪除指定的自訂 Agent
export const deleteCustomAgent = (id) => {
  return apiClient.delete(`/${id}`);
};