import api from './api';
const basePath = '/custom_agents';
export interface CustomAgent {
  id: number;
  name: string;
  role: string;
  expertise: string;
  prompt: string;
  tools?: any;
  is_public: boolean;
  created_by?: number;
}
const withTimeout = async <T>(
  apiCall: (signal: AbortSignal) => Promise<T>,
  timeoutMs: number = 45000
): Promise<T> => {
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
export const getCustomAgents = (): Promise<any> => {
  return withTimeout((signal) => api.get<CustomAgent[]>(`${basePath}/`, { signal }));
};
let _agentsCache: CustomAgent[] | null = null;
let _agentsCacheTs = 0;
let _agentsInFlight: Promise<any> | null = null;
const AGENTS_TTL_MS = 2 * 60 * 1000;
export const getAllAgentsWithDetails = async (force: boolean = false): Promise<any> => {
  const now = Date.now();
  if (!force && _agentsCache && (now - _agentsCacheTs) < AGENTS_TTL_MS) {
    return { data: _agentsCache };
  }
  if (!force && _agentsInFlight) {
    return _agentsInFlight;
  }
  _agentsInFlight = withTimeout(
    (signal) => api.get<CustomAgent[]>(`${basePath}/all_with_details`, { signal }),
    45000
  ).then((res) => {
    try {
      _agentsCache = res.data;
      _agentsCacheTs = Date.now();
    } catch (e) {
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
export const getCustomAgent = (id: number): Promise<any> => {
  return withTimeout((signal) => api.get<CustomAgent>(`${basePath}/${id}`, { signal }));
};
export const createCustomAgent = (agentData: Partial<CustomAgent>): Promise<any> => {
  return withTimeout((signal) => api.post<CustomAgent>(`${basePath}/`, agentData, { signal }));
};
export const updateCustomAgent = (id: number, agentData: Partial<CustomAgent>): Promise<any> => {
  return withTimeout((signal) => api.put<CustomAgent>(`${basePath}/${id}`, agentData, { signal }));
};
export const deleteCustomAgent = (id: number): Promise<any> => {
  return withTimeout((signal) => api.delete<any>(`${basePath}/${id}`, { signal }));
};
