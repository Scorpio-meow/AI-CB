import axios from 'axios';
import { shouldRefreshToken, hasValidAuth, clearAuth } from '../utils/tokenUtils';
import { devLog, devWarn } from '../utils/secureLogger';

// Normalize API URL from REACT_APP_API_BASE (preferred) or REACT_APP_API_URL (fallback)
// Prefer explicit REACT_APP_API_BASE or REACT_APP_API_URL, otherwise use same-origin relative path '/api'
const RAW_API_URL = process.env.REACT_APP_API_BASE || process.env.REACT_APP_API_URL || '/api';

const ensureTrailingApi = (urlString) => {
  const trimmed = urlString.replace(/\/+$/, '');
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`;
};

const normalizeAbsoluteUrl = (rawUrl) => {
  try {
    const parsed = new URL(rawUrl);

    // Drop explicit DevTunnels port – the subdomain already encodes the port, adding ":xxxx" breaks TLS routing
    if (parsed.hostname.includes('devtunnels.ms') && parsed.port) {
      devWarn('[api] Dropping explicit port from DevTunnels URL to avoid double port issues.', parsed.href);
      parsed.port = '';
    }

    const normalizedPath = ensureTrailingApi(parsed.pathname || '/api');
    parsed.pathname = normalizedPath;
    return parsed.toString().replace(/\/+$/, '');
  } catch (error) {
    devWarn('[api] Failed to parse API base URL, falling back to string normalization.', error);
    return ensureTrailingApi(rawUrl);
  }
};

const API_BASE_URL = RAW_API_URL.startsWith('http://') || RAW_API_URL.startsWith('https://')
  ? normalizeAbsoluteUrl(RAW_API_URL)
  : ensureTrailingApi(RAW_API_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // 啟用 Cookie 支援
});

// ==================== JWT 認證攔截器 ====================

// Token refresh lock - prevents multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshSubscribers = [];

const onAccessTokenRefreshed = (accessToken) => {
  refreshSubscribers.forEach((callback) => callback(accessToken));
  refreshSubscribers = [];
};

const addRefreshSubscriber = (callback) => {
  refreshSubscribers.push(callback);
};

// Request Interceptor - 自動添加 Access Token 和靜默刷新
api.interceptors.request.use(
  async (config) => {
    // 從 localStorage 獲取 token
    const token = localStorage.getItem('access_token');
    
    if (token) {
      // 檢查是否需要刷新 Token（提前 5 分鐘刷新）
      if (shouldRefreshToken(token, 300) && !isRefreshing) {
        devLog('[Token] Token 即將過期，觸發靜默刷新...');
        
        try {
          isRefreshing = true;
          
          // 刷新 Token（使用 Cookie 中的 refresh_token）
          const response = await axios.post(
            `${API_BASE_URL}/auth/refresh`,
            {},
            { withCredentials: true }
          );

          const { access_token } = response.data;

          // 保存新的 access token
          localStorage.setItem('access_token', access_token);

          // 通知所有等待的請求
          onAccessTokenRefreshed(access_token);

          // 更新當前請求的 token
          config.headers.Authorization = `Bearer ${access_token}`;
          
          devLog('[Token] 靜默刷新成功');
        } catch (error) {
          devWarn('[Token] 靜默刷新失敗，清除無效 Token:', error.response?.status);
          // 刷新失敗，清除無效的 token 避免無限循環
          if (error.response?.status === 401) {
            clearAuth();
            // 不要立即跳轉，讓 response interceptor 處理
          } else {
            // 非 401 錯誤（網絡問題等），使用原有 token 嘗試
            config.headers.Authorization = `Bearer ${token}`;
          }
        } finally {
          isRefreshing = false;
        }
      } else if (!hasValidAuth() && token) {
        // Token 已完全過期，清除它
        console.log('[Token] Token 已完全過期，清除認證信息');
        clearAuth();
      } else {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor - 自動刷新 Token (with refresh lock)
api.interceptors.response.use(
  (response) => {
    // 請求成功,直接返回
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // 如果是 401 錯誤且還沒有重試過
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // If already refreshing, wait for the new token
      if (isRefreshing) {
        return new Promise((resolve) => {
          addRefreshSubscriber((accessToken) => {
            originalRequest.headers.Authorization = `Bearer ${accessToken}`;
            resolve(api(originalRequest));
          });
        });
      }

      isRefreshing = true;

      try {
        // 刷新 access token（使用 Cookie 中的 refresh_token）
        const response = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );

        const { access_token } = response.data;

        // 保存新的 access token
        localStorage.setItem('access_token', access_token);

        // Notify all waiting requests with new token
        isRefreshing = false;
        onAccessTokenRefreshed(access_token);

        // 更新原始請求的 Authorization header
        originalRequest.headers.Authorization = `Bearer ${access_token}`;

        // 重試原始請求
        return api(originalRequest);
      } catch (refreshError) {
        // 刷新失敗,清除認證信息並跳轉到登入頁
        isRefreshing = false;
        refreshSubscribers = [];
        
        console.warn('[Token] Token 刷新失敗，清除認證信息:', refreshError.response?.status);
        clearAuth();
        
        // 只有在非登錄頁面才跳轉，避免無限循環
        const currentPath = window.location.pathname;
        if (currentPath !== '/login' && currentPath !== '/register') {
          console.log('[Token] 跳轉到登錄頁面');
          // 使用 setTimeout 避免在請求攔截器中直接跳轉
          setTimeout(() => {
            window.location.href = '/login';
          }, 100);
        }
        
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export const chatService = {
  async sendMessage(content, conversationId = null, model_name = null) {
    const response = await api.post('/chat/send', { 
      content, 
      conversation_id: conversationId,
      model_name
    });
    return response.data;
  },

  async getConversations() {
    const response = await api.get('/chat/conversations');
    return response.data;
  },

  async getConversation(conversationId) {
    const response = await api.get(`/chat/conversations/${conversationId}`);
    return response.data;
  },

  async deleteConversation(conversationId) {
    const response = await api.delete(`/chat/conversations/${conversationId}`);
    return response.data;
  }
};

export const documentService = {
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async uploadDocuments(files) {
    const formData = new FormData();
    files.forEach((f) => formData.append('file', f));

    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getDocuments() {
    const response = await api.get('/documents/');  // 修正：加上 trailing slash 避免 307 redirect
    return response.data;
  },

  async deleteDocument(documentId) {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  }
};

export const adminService = {
  async getUsers() {
    const response = await api.get('/admin/users');
    return response.data;
  },

  async getStatistics() {
    const response = await api.get('/admin/statistics');
    return response.data;
  },

  async updateUser(userId, userData) {
    const response = await api.put(`/admin/users/${userId}`, userData);
    return response.data;
  },

  async deleteUser(userId) {
    const response = await api.delete(`/admin/users/${userId}`);
    return response.data;
  }
};

export default api;
