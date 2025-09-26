import axios from 'axios';

// Normalize API URL from REACT_APP_API_BASE (preferred) or REACT_APP_API_URL (fallback)
const RAW_API_URL = process.env.REACT_APP_API_BASE || process.env.REACT_APP_API_URL || 'http://localhost:8001/api';
const API_URL_NO_TRAIL = RAW_API_URL.replace(/\/+$/, '');
const API_BASE_URL = API_URL_NO_TRAIL.endsWith('/api') ? API_URL_NO_TRAIL : `${API_URL_NO_TRAIL}/api`;

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
