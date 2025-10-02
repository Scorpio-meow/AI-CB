import axios from 'axios';

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
      console.warn('[api] Dropping explicit port from DevTunnels URL to avoid double port issues.', parsed.href);
      parsed.port = '';
    }

    const normalizedPath = ensureTrailingApi(parsed.pathname || '/api');
    parsed.pathname = normalizedPath;
    return parsed.toString().replace(/\/+$/, '');
  } catch (error) {
    console.warn('[api] Failed to parse API base URL, falling back to string normalization.', error);
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
});

// ==================== JWT 認證攔截器 ====================

// Request Interceptor - 自動添加 Access Token
api.interceptors.request.use(
  (config) => {
    // 從 localStorage 獲取 token
    const token = localStorage.getItem('access_token');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor - 自動刷新 Token
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

      try {
        // 獲取 refresh token
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (!refreshToken) {
          throw new Error('無刷新令牌');
        }

        // 刷新 access token
        const response = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token: new_refresh_token } = response.data;

        // 保存新的 tokens
        localStorage.setItem('access_token', access_token);
        if (new_refresh_token) {
          localStorage.setItem('refresh_token', new_refresh_token);
        }

        // 更新原始請求的 Authorization header
        originalRequest.headers.Authorization = `Bearer ${access_token}`;

        // 重試原始請求
        return api(originalRequest);
      } catch (refreshError) {
        // 刷新失敗,清除認證信息並跳轉到登入頁
        console.error('Token 刷新失敗:', refreshError);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_info');
        
        // 跳轉到登入頁
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
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
    const response = await api.get('/documents');
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
