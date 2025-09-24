import axios from 'axios';

// 支援多個 API 端點的配置
const API_URLS = process.env.REACT_APP_API_URLS 
  ? process.env.REACT_APP_API_URLS.split(',').map(url => url.trim())
  : ['http://localhost:8001'];

// 自動檢測可用的 API 端點
class ApiManager {
  constructor() {
    this.currentApiUrl = null;
    this.api = null;
    this.isInitialized = false;
    this.initPromise = null;
  }

  async initialize() {
    if (this.isInitialized) return this.api;
    if (this.initPromise) return this.initPromise;

    this.initPromise = this._findWorkingApi();
    await this.initPromise;
    this.isInitialized = true;
    return this.api;
  }

  async _findWorkingApi() {
    console.log('檢測可用的 API 端點...', API_URLS);
    
    // 檢測當前訪問環境
    const isLocalAccess = window.location.hostname === 'localhost' || 
                         window.location.hostname === '127.0.0.1';
    const isDevTunnels = window.location.hostname.includes('devtunnels.ms');
    
    let prioritizedUrls = [...API_URLS];
    
    if (isDevTunnels) {
      // 遠端 DevTunnels 訪問：優先使用遠端 API，排除本地端點
      console.log('🌐 檢測到 DevTunnels 遠端訪問，優先使用遠端 API');
      prioritizedUrls = API_URLS.filter(url => 
        !url.includes('localhost') && !url.includes('127.0.0.1')
      );
      // 如果沒有遠端端點，則使用所有端點
      if (prioritizedUrls.length === 0) {
        prioritizedUrls = API_URLS;
      }
    } else if (isLocalAccess) {
      // 本地訪問：優先使用本地 API
      console.log('🏠 檢測到本地訪問，優先使用本地 API');
      const localUrls = API_URLS.filter(url => 
        url.includes('localhost') || url.includes('127.0.0.1')
      );
      const remoteUrls = API_URLS.filter(url => 
        !url.includes('localhost') && !url.includes('127.0.0.1')
      );
      prioritizedUrls = [...localUrls, ...remoteUrls];
    }
    
    for (const baseUrl of prioritizedUrls) {
      try {
        const normalizedUrl = baseUrl.replace(/\/+$/, '');
        const apiUrl = normalizedUrl.endsWith('/api') ? normalizedUrl : `${normalizedUrl}/api`;
        
        // 根據是否為 DevTunnels 設定不同的超時時間
        const isRemoteUrl = !baseUrl.includes('localhost') && !baseUrl.includes('127.0.0.1');
        const timeout = isRemoteUrl ? 15000 : 5000; // DevTunnels 使用 15 秒，本地使用 5 秒
        
        // 測試連接
        const testApi = axios.create({
          baseURL: apiUrl,
          timeout: timeout,
          headers: { 'Content-Type': 'application/json' }
        });

        // 嘗試訪問健康檢查端點
        const healthUrl = `${normalizedUrl}/health`;
        await axios.get(healthUrl, { timeout: timeout });
        
        console.log(`✅ API 端點可用: ${apiUrl}`);
        this.currentApiUrl = apiUrl;
        this.api = testApi;
        return;
      } catch (error) {
        console.log(`❌ API 端點不可用: ${baseUrl}`, error.message);
      }
    }
    
    // 如果所有端點都失敗，使用第一個作為默認值
    const fallbackUrl = API_URLS[0].replace(/\/+$/, '');
    const fallbackApiUrl = fallbackUrl.endsWith('/api') ? fallbackUrl : `${fallbackUrl}/api`;
    
    console.warn(`⚠️ 所有 API 端點都不可用，使用默認端點: ${fallbackApiUrl}`);
    this.currentApiUrl = fallbackApiUrl;
    this.api = axios.create({
      baseURL: fallbackApiUrl,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  async getApi() {
    if (!this.isInitialized) {
      await this.initialize();
    }
    return this.api;
  }

  getCurrentUrl() {
    return this.currentApiUrl;
  }
}

const apiManager = new ApiManager();

// 導出一個函數來獲取初始化後的 API 實例
export const getApi = () => apiManager.getApi();

// No auth interceptors - auth has been removed from the backend.

export const chatService = {
  async sendMessage(content, conversationId = null, model_name = null) {
    const api = await getApi();
    const response = await api.post('/chat/send', { 
      content, 
      conversation_id: conversationId,
      model_name
    });
    return response.data;
  },

  async getConversations() {
    const api = await getApi();
    const response = await api.get('/chat/conversations');
    return response.data;
  },

  async getConversation(conversationId) {
    const api = await getApi();
    const response = await api.get(`/chat/conversations/${conversationId}`);
    return response.data;
  },

  async deleteConversation(conversationId) {
    const api = await getApi();
    const response = await api.delete(`/chat/conversations/${conversationId}`);
    return response.data;
  }
};

export const documentService = {
  async uploadDocument(file) {
    const api = await getApi();
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
    const api = await getApi();
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
    const api = await getApi();
    const response = await api.get('/documents');
    return response.data;
  },

  async deleteDocument(documentId) {
    const api = await getApi();
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  }
};

export const adminService = {
  async getUsers() {
    const api = await getApi();
    const response = await api.get('/admin/users');
    return response.data;
  },

  async getStatistics() {
    const api = await getApi();
    const response = await api.get('/admin/statistics');
    return response.data;
  },

  async updateUser(userId, userData) {
    const api = await getApi();
    const response = await api.put(`/admin/users/${userId}`, userData);
    return response.data;
  },

  async deleteUser(userId) {
    const api = await getApi();
    const response = await api.delete(`/admin/users/${userId}`);
    return response.data;
  }
};

// 導出 API 管理器供其他服務使用
export { apiManager };
export default getApi;
