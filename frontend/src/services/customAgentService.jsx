import api from './api';

const basePath = '/custom_agents';

// 超時控制輔助函數
const withTimeout = async (apiCall, timeoutMs = 45000) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const result = await apiCall(controller.signal);
    clearTimeout(timeoutId);
    return result;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
};

// 獲取所有自訂 Agent (僅自訂)
export const getCustomAgents = () => {
  return withTimeout((signal) => api.get(`${basePath}/`, { signal }));
};

// Simple in-memory cache + in-flight dedupe for getAllAgentsWithDetails
let _agentsCache = null;
let _agentsCacheTs = 0;
let _agentsInFlight = null; // stores Promise while request is ongoing
const AGENTS_TTL_MS = 2 * 60 * 1000; // 2 minutes

export const getAllAgentsWithDetails = async (force = false) => {
  const now = Date.now();

  if (!force && _agentsCache && (now - _agentsCacheTs) < AGENTS_TTL_MS) {
    return { data: _agentsCache };
  }

  if (!force && _agentsInFlight) {
    // return the in-flight promise to dedupe requests
    return _agentsInFlight;
  }

  _agentsInFlight = withTimeout(
    (signal) => api.get(`${basePath}/all_with_details`, { signal }),
    45000 // 45 秒超時
  ).then((res) => {
    try {
      _agentsCache = res.data;
      _agentsCacheTs = Date.now();
    } catch (e) {
      // ignore cache save errors
      console.warn('Failed to cache agents', e);
    }
    _agentsInFlight = null;
    return res;
  }).catch((err) => {
    _agentsInFlight = null;
    throw err;
  });

  return _agentsInFlight;
};

// 根據 ID 獲取單一自訂 Agent
export const getCustomAgent = (id) => {
  return withTimeout((signal) => api.get(`${basePath}/${id}`, { signal }));
};

// 創建新的自訂 Agent
export const createCustomAgent = (agentData) => {
  return withTimeout((signal) => api.post(`${basePath}/`, agentData, { signal }));
};

// 更新指定的自訂 Agent
export const updateCustomAgent = (id, agentData) => {
  return withTimeout((signal) => api.put(`${basePath}/${id}`, agentData, { signal }));
};

// 刪除指定的自訂 Agent
export const deleteCustomAgent = (id) => {
  return withTimeout((signal) => api.delete(`${basePath}/${id}`, { signal }));
};