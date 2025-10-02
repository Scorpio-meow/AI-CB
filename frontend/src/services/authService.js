/**
 * JWT 認證服務
 * 處理用戶註冊、登入、登出和 Token 管理
 */

import api from './api';

const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user_info';

// 超時控制輔助函數
const withTimeout = async (promise, timeoutMs = 45000) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const result = await promise(controller.signal);
    clearTimeout(timeoutId);
    return result;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError' || error.name === 'CanceledError') {
      const timeoutError = new Error('請求超時，請稍後再試');
      timeoutError.isTimeout = true;
      throw timeoutError;
    }
    throw error;
  }
};

class AuthService {
  /**
   * 用戶註冊
   */
  async register(username, email, password) {
    try {
      const response = await withTimeout(
        (signal) => api.post('/auth/register', {
          username,
          email,
          password
        }, { signal }),
        45000 // 45 秒超時，給 DevTunnels 更多時間
      );
      
      const { user, tokens } = response.data;
      this.saveTokens(tokens);
      this.saveUser(user);
      
      return { success: true, user, tokens };
    } catch (error) {
      console.error('註冊失敗:', error);
      
      // 處理錯誤消息
      let errorMessage = error.isTimeout ? error.message : '註冊失敗';
      
      if (!error.isTimeout && error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        // 如果 detail 是數組（Pydantic 驗證錯誤）
        if (Array.isArray(detail)) {
          errorMessage = detail.map(err => err.msg || err).join(', ');
        } 
        // 如果 detail 是字符串
        else if (typeof detail === 'string') {
          errorMessage = detail;
        }
        // 如果 detail 是對象
        else if (typeof detail === 'object') {
          errorMessage = detail.msg || JSON.stringify(detail);
        }
      }
      
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  /**
   * 用戶登入
   */
  async login(username, password) {
    try {
      const response = await withTimeout(
        (signal) => api.post('/auth/login', {
          username,
          password
        }, { signal }),
        45000 // 45 秒超時
      );
      
      const { user, tokens } = response.data;
      this.saveTokens(tokens);
      this.saveUser(user);
      
      return { success: true, user, tokens };
    } catch (error) {
      console.error('登入失敗:', error);
      
      // 處理錯誤消息
      let errorMessage = error.isTimeout ? error.message : '登入失敗';
      
      if (!error.isTimeout && error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        // 如果 detail 是數組（Pydantic 驗證錯誤）
        if (Array.isArray(detail)) {
          errorMessage = detail.map(err => err.msg || err).join(', ');
        } 
        // 如果 detail 是字符串
        else if (typeof detail === 'string') {
          errorMessage = detail;
        }
        // 如果 detail 是對象
        else if (typeof detail === 'object') {
          errorMessage = detail.msg || JSON.stringify(detail);
        }
      }
      
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  /**
   * 用戶登出
   */
  async logout() {
    try {
      // 通知後端 (記錄日誌) - 使用超時控制
      await withTimeout(
        (signal) => api.post('/auth/logout', {}, { signal }),
        10000 // 登出只需 10 秒超時
      );
    } catch (error) {
      console.error('登出請求失敗:', error);
    } finally {
      // 無論後端請求是否成功,都清除本地 Token
      this.clearAuth();
    }
  }

  /**
   * 刷新 Access Token
   */
  async refreshAccessToken() {
    try {
      const refreshToken = this.getRefreshToken();
      
      if (!refreshToken) {
        throw new Error('無刷新令牌');
      }

      const response = await withTimeout(
        (signal) => api.post('/auth/refresh', {
          refresh_token: refreshToken
        }, { signal }),
        45000 // 45 秒超時
      );
      
      const { access_token, refresh_token } = response.data;
      
      // 更新 Token
      this.saveTokens({
        access_token,
        refresh_token,
        token_type: 'bearer'
      });
      
      return access_token;
    } catch (error) {
      console.error('刷新令牌失敗:', error);
      // 刷新失敗,清除認證信息
      this.clearAuth();
      throw error;
    }
  }

  /**
   * 獲取當前用戶資料
   */
  async getCurrentUser() {
    try {
      const response = await withTimeout(
        (signal) => api.get('/auth/me', { signal }),
        45000 // 45 秒超時
      );
      const user = response.data;
      this.saveUser(user);
      return user;
    } catch (error) {
      console.error('獲取用戶資料失敗:', error);
      throw error;
    }
  }

  /**
   * 更新用戶資料
   */
  async updateProfile(data) {
    try {
      const response = await withTimeout(
        (signal) => api.put('/auth/me', data, { signal }),
        45000 // 45 秒超時
      );
      const user = response.data;
      this.saveUser(user);
      return { success: true, user };
    } catch (error) {
      console.error('更新用戶資料失敗:', error);
      const errorMsg = error.isTimeout ? error.message : (error.response?.data?.detail || '更新失敗');
      return {
        success: false,
        error: errorMsg
      };
    }
  }

  /**
   * 修改密碼
   */
  async changePassword(currentPassword, newPassword, confirmPassword) {
    try {
      const response = await withTimeout(
        (signal) => api.post('/auth/change-password', {
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        }, { signal }),
        45000 // 45 秒超時
      );
      
      return { success: true, message: response.data.message };
    } catch (error) {
      console.error('修改密碼失敗:', error);
      const errorMsg = error.isTimeout ? error.message : (error.response?.data?.detail || '修改密碼失敗');
      return {
        success: false,
        error: errorMsg
      };
    }
  }

  /**
   * 驗證 Token 是否有效
   */
  async validateToken() {
    try {
      const response = await withTimeout(
        (signal) => api.get('/auth/validate', { signal }),
        10000 // 驗證只需 10 秒超時
      );
      return response.data.success;
    } catch (error) {
      return false;
    }
  }

  // ==================== Token 管理 ====================

  /**
   * 保存 Tokens
   */
  saveTokens(tokens) {
    if (tokens.access_token) {
      localStorage.setItem(TOKEN_KEY, tokens.access_token);
    }
    if (tokens.refresh_token) {
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    }
  }

  /**
   * 保存用戶信息
   */
  saveUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  /**
   * 獲取 Access Token
   */
  getAccessToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  /**
   * 獲取 Refresh Token
   */
  getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  /**
   * 獲取用戶信息
   */
  getUser() {
    const userStr = localStorage.getItem(USER_KEY);
    try {
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  }

  /**
   * 檢查是否已登入
   */
  isAuthenticated() {
    return !!this.getAccessToken();
  }

  /**
   * 檢查是否為管理員
   */
  isAdmin() {
    const user = this.getUser();
    return user?.is_admin === true;
  }

  /**
   * 清除所有認證信息
   */
  clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

// 創建單例
const authService = new AuthService();

export default authService;
