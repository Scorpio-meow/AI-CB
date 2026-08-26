import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { shouldRefreshToken, hasValidAuth, clearAuth } from '../utils/tokenUtils.ts';
import { devLog, devWarn } from '../utils/secureLogger.ts';
export interface ChatAttachment {
  id?: string;
  filename: string;
  file_type: string;
  file_size?: number;
  data_url?: string;
  content?: string;
  file?: File;
}

export interface Message {
  id?: number;
  content: string;
  is_user: boolean;
  created_at?: string;
  context_used?: string | null | string[];
  model_name?: string | null;
  reasoning_effort?: string | null;
  attachments?: ChatAttachment[];
  sources?: string[];
  sources_detail?: Array<{
    source: string;
    chunk?: number;
    score?: number | null;
    snippet?: string;
    url?: string;
  }>;
  research_trace?: Array<{
    step: number;
    tool: string;
    arguments?: Record<string, any>;
    output_preview?: string;
    duration_seconds?: number;
    status?: string;
  }>;
  think?: string | null;
  role?: string;
  isUser?: boolean;
}
export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}
export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  role: string;
}
export interface ChatResponse {
  message: Message;
  conversation_id: number;
}
const RAW_API_URL = (import.meta.env.VITE_API_BASE as string) || (import.meta.env.VITE_API_URL as string) || '/api';
const ensureTrailingApi = (urlString: string): string => {
  const trimmed = urlString.replace(/\/+$/, '');
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`;
};
const normalizeAbsoluteUrl = (rawUrl: string): string => {
  try {
    const parsed = new URL(rawUrl);
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
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];
const onAccessTokenRefreshed = (accessToken: string) => {
  refreshSubscribers.forEach((callback) => callback(accessToken));
  refreshSubscribers = [];
};
const addRefreshSubscriber = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback);
};
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      if (shouldRefreshToken(token, 300) && !isRefreshing) {
        devLog('[Token] Token 即將過期，觸發靜默刷新...');
        try {
          isRefreshing = true;
          const response = await axios.post<{ access_token: string }>(
            `${API_BASE_URL}/auth/refresh`,
            {},
            { withCredentials: true }
          );
          const { access_token } = response.data;
          localStorage.setItem('access_token', access_token);
          onAccessTokenRefreshed(access_token);
          config.headers.Authorization = `Bearer ${access_token}`;
          devLog('[Token] 靜默刷新成功');
        } catch (error: any) {
          devWarn('[Token] 靜默刷新失敗，清除無效 Token:', error.response?.status);
          if (error.response?.status === 401) {
            clearAuth();
          } else {
            config.headers.Authorization = `Bearer ${token}`;
          }
        } finally {
          isRefreshing = false;
        }
      } else if (!hasValidAuth() && token) {
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
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
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
        const response = await axios.post<{ access_token: string }>(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        const { access_token } = response.data;
        localStorage.setItem('access_token', access_token);
        isRefreshing = false;
        onAccessTokenRefreshed(access_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError: any) {
        isRefreshing = false;
        refreshSubscribers = [];
        console.warn('[Token] Token 刷新失敗，清除認證信息:', refreshError.response?.status);
        clearAuth();
        const currentPath = window.location.pathname;
        if (currentPath !== '/login' && currentPath !== '/register') {
          console.log('[Token] 跳轉到登錄頁面');
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
export interface StreamEvent {
  event: 'start' | 'step_start' | 'step_end' | 'token' | 'think' | 'sources' | 'done' | 'error';
  data: any;
}

export const chatService = {
  async sendMessageStream(
    content: string,
    conversationId: number | null = null,
    model_name: string | null = null,
    reasoning_effort: string = 'medium',
    onEvent: (event: StreamEvent) => void,
    signal?: AbortSignal,
    attachments?: ChatAttachment[]
  ): Promise<void> {
    const token = localStorage.getItem('access_token');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const payloadAttachments = attachments?.map(a => ({
      filename: a.filename,
      file_type: a.file_type,
      file_size: a.file_size,
      data_url: a.data_url,
      content: a.content
    })) || [];

    const response = await fetch(`${API_BASE_URL}/chat/send`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        content,
        conversation_id: conversationId,
        model_name,
        reasoning_effort,
        attachments: payloadAttachments
      }),
      signal
    });

    if (!response.ok) {
      const errText = await response.text();
      let detail = errText;
      try {
        const parsed = JSON.parse(errText);
        detail = parsed.detail || errText;
      } catch (e) {
        // ignore parse error
      }
      throw new Error(detail || `HTTP Error ${response.status}`);
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported by browser');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent: string = 'message';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        if (trimmed.startsWith('event:')) {
          currentEvent = trimmed.slice(6).trim();
        } else if (trimmed.startsWith('data:')) {
          const rawData = trimmed.slice(5).trim();
          try {
            const parsedData = JSON.parse(rawData);
            onEvent({ event: currentEvent as any, data: parsedData });
          } catch (e) {
            console.warn('Failed to parse SSE data:', rawData, e);
          }
        }
      }
    }
  },
  async sendMessage(
    content: string,
    conversationId: number | null = null,
    model_name: string | null = null,
    reasoning_effort: string = 'medium',
    attachments?: ChatAttachment[]
  ): Promise<ChatResponse> {
    const payloadAttachments = attachments?.map(a => ({
      filename: a.filename,
      file_type: a.file_type,
      file_size: a.file_size,
      data_url: a.data_url,
      content: a.content
    })) || [];

    const response = await api.post<ChatResponse>('/chat/send', {
      content,
      conversation_id: conversationId,
      model_name,
      reasoning_effort,
      attachments: payloadAttachments
    });
    return response.data;
  },
  async getConversations(): Promise<Conversation[]> {
    const response = await api.get<Conversation[]>('/chat/conversations');
    return response.data;
  },
  async getConversation(conversationId: number): Promise<Conversation> {
    const response = await api.get<Conversation>(`/chat/conversations/${conversationId}`);
    return response.data;
  },
  async deleteConversation(conversationId: number): Promise<{ message: string }> {
    const response = await api.delete<{ message: string }>(`/chat/conversations/${conversationId}`);
    return response.data;
  }
};
export const documentService = {
  async uploadDocument(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<any>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  async uploadDocuments(files: File[]): Promise<any> {
    const formData = new FormData();
    files.forEach((f) => formData.append('file', f));
    const response = await api.post<any>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  async getDocuments(): Promise<any[]> {
    const response = await api.get<any[]>('/documents/');
    return response.data;
  },
  async deleteDocument(documentId: number): Promise<any> {
    const response = await api.delete<any>(`/documents/${documentId}`);
    return response.data;
  }
};
export const adminService = {
  async getUsers(): Promise<User[]> {
    const response = await api.get<User[]>('/admin/users');
    return response.data;
  },
  async getStatistics(): Promise<any> {
    const response = await api.get<any>('/admin/statistics');
    return response.data;
  },
  async updateUser(userId: number, userData: Partial<User>): Promise<User> {
    const response = await api.put<User>(`/admin/users/${userId}`, userData);
    return response.data;
  },
  async deleteUser(userId: number): Promise<any> {
    const response = await api.delete<any>(`/admin/users/${userId}`);
    return response.data;
  }
};
export default api;
