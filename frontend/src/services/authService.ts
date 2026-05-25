import api, { User } from './api';

const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user_info';

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterLoginResult {
  success: boolean;
  user?: User;
  tokens?: Tokens;
  error?: string;
}

const withTimeout = async <T>(
  promiseCreator: (signal: AbortSignal) => Promise<T>,
  timeoutMs: number = 45000
): Promise<T> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const result = await promiseCreator(controller.signal);
    clearTimeout(timeoutId);
    return result;
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError' || error.name === 'CanceledError') {
      const timeoutError = new Error('請求超時，請稍後再試') as any;
      timeoutError.isTimeout = true;
      throw timeoutError;
    }
    throw error;
  }
};

class AuthService {
  async register(username: string, email: string, password: string): Promise<RegisterLoginResult> {
    try {
      const response = await withTimeout(
        (signal) => api.post<{ user: User; tokens: Tokens }>('/auth/register', {
          username,
          email,
          password
        }, { signal }),
        45000
      );

      const { user, tokens } = response.data;
      this.saveTokens(tokens);
      this.saveUser(user);

      return { success: true, user, tokens };
    } catch (error: any) {
      console.error('註冊失敗:', error);

      let errorMessage = error.isTimeout ? error.message : '註冊失敗';

      if (!error.isTimeout && error.response?.data?.detail) {
        const detail = error.response.data.detail;

        if (Array.isArray(detail)) {
          errorMessage = detail.map((err: any) => err.msg || err).join(', ');
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (typeof detail === 'object') {
          errorMessage = detail.msg || JSON.stringify(detail);
        }
      }

      return {
        success: false,
        error: errorMessage
      };
    }
  }

  async login(username: string, password: string): Promise<RegisterLoginResult> {
    try {
      const response = await withTimeout(
        (signal) => api.post<{ user: User; tokens: Tokens }>('/auth/login', {
          username,
          password
        }, { signal }),
        45000
      );

      const { user, tokens } = response.data;
      this.saveTokens(tokens);
      this.saveUser(user);

      return { success: true, user, tokens };
    } catch (error: any) {
      console.error('登入失敗:', error);

      let errorMessage = error.isTimeout ? error.message : '登入失敗';

      if (!error.isTimeout && error.response?.data?.detail) {
        const detail = error.response.data.detail;

        if (Array.isArray(detail)) {
          errorMessage = detail.map((err: any) => err.msg || err).join(', ');
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (typeof detail === 'object') {
          errorMessage = detail.msg || JSON.stringify(detail);
        }
      }

      return {
        success: false,
        error: errorMessage
      };
    }
  }

  async logout(): Promise<void> {
    try {
      await withTimeout(
        (signal) => api.post('/auth/logout', {}, { signal }),
        10000
      );
    } catch (error) {
      console.error('登出請求失敗:', error);
    } finally {
      this.clearAuth();
    }
  }

  async refreshAccessToken(): Promise<string> {
    try {
      const refreshToken = this.getRefreshToken();

      if (!refreshToken) {
        throw new Error('無刷新令牌');
      }

      const response = await withTimeout(
        (signal) => api.post<{ access_token: string; refresh_token: string }>('/auth/refresh', {
          refresh_token: refreshToken
        }, { signal }),
        45000
      );

      const { access_token, refresh_token } = response.data;

      this.saveTokens({
        access_token,
        refresh_token,
        token_type: 'bearer'
      });

      return access_token;
    } catch (error) {
      console.error('刷新令牌失敗:', error);
      this.clearAuth();
      throw error;
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      const response = await withTimeout(
        (signal) => api.get<User>('/auth/me', { signal }),
        90000
      );
      const user = response.data;
      this.saveUser(user);
      return user;
    } catch (error: any) {
      if (error.isTimeout && import.meta.env.DEV) {
        console.debug('getCurrentUser timeout (DevTunnels may be slow)');
      }
      throw error;
    }
  }

  async updateProfile(data: Partial<User>): Promise<{ success: boolean; user?: User; error?: string }> {
    try {
      const response = await withTimeout(
        (signal) => api.put<User>('/auth/me', data, { signal }),
        45000
      );
      const user = response.data;
      this.saveUser(user);
      return { success: true, user };
    } catch (error: any) {
      console.error('更新用戶資料失敗:', error);
      const errorMsg = error.isTimeout ? error.message : (error.response?.data?.detail || '更新失敗');
      return {
        success: false,
        error: errorMsg
      };
    }
  }

  async changePassword(currentPassword: string, newPassword: string, confirmPassword: string): Promise<{ success: boolean; message?: string; error?: string }> {
    try {
      const response = await withTimeout(
        (signal) => api.post<{ message: string }>('/auth/change-password', {
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        }, { signal }),
        45000
      );

      return { success: true, message: response.data.message };
    } catch (error: any) {
      console.error('修改密碼失敗:', error);
      const errorMsg = error.isTimeout ? error.message : (error.response?.data?.detail || '修改密碼失敗');
      return {
        success: false,
        error: errorMsg
      };
    }
  }

  async validateToken(): Promise<boolean> {
    try {
      const response = await withTimeout(
        (signal) => api.get<{ success: boolean }>('/auth/validate', { signal }),
        10000
      );
      return response.data.success;
    } catch {
      return false;
    }
  }

  saveTokens(tokens: Tokens) {
    if (tokens.access_token) {
      localStorage.setItem(TOKEN_KEY, tokens.access_token);
    }
    if (tokens.refresh_token) {
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    }
  }

  saveUser(user: User) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  getAccessToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  getUser(): User | null {
    const userStr = localStorage.getItem(USER_KEY);
    try {
      return userStr ? JSON.parse(userStr) as User : null;
    } catch {
      return null;
    }
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }

  isAdmin(): boolean {
    const user = this.getUser();
    return user?.is_admin === true;
  }

  clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

const authService = new AuthService();
export default authService;
