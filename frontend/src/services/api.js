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

// No auth interceptors - auth has been removed from the backend.

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
