import { useState, useCallback } from 'react';
import authService, { Tokens, RegisterLoginResult } from '../services/authService';
import { User } from '../services/api';
export function useAuth() {
  const [user, setUser] = useState<User | null>(() => authService.getUser());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const login = useCallback(async (username: string, password: string): Promise<RegisterLoginResult> => {
    setLoading(true);
    setError(null);
    try {
      const result = await authService.login(username, password);
      if (result.success && result.user) {
        setUser(result.user);
      } else {
        setError(result.error || '登入失敗');
      }
      return result;
    } catch (err: any) {
      const errorMsg = err.message || '登入時發生錯誤';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  }, []);
  const register = useCallback(async (username: string, email: string, password: string): Promise<RegisterLoginResult> => {
    setLoading(true);
    setError(null);
    try {
      const result = await authService.register(username, email, password);
      if (result.success && result.user) {
        setUser(result.user);
      } else {
        setError(result.error || '註冊失敗');
      }
      return result;
    } catch (err: any) {
      const errorMsg = err.message || '註冊時發生錯誤';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  }, []);
  const logout = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      await authService.logout();
      setUser(null);
    } catch (err) {
      console.error('Logout failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);
  const getCurrentUser = useCallback(async (): Promise<User | null> => {
    setLoading(true);
    setError(null);
    try {
      const userData = await authService.getCurrentUser();
      setUser(userData);
      return userData;
    } catch (err: any) {
      setError(err.message || '獲取使用者資料失敗');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);
  const updateProfile = useCallback(async (data: Partial<User>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await authService.updateProfile(data);
      if (result.success && result.user) {
        setUser(result.user);
      } else {
        setError(result.error || '更新設定失敗');
      }
      return result;
    } catch (err: any) {
      const errorMsg = err.message || '更新時發生錯誤';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  }, []);
  const changePassword = useCallback(async (currentPassword: string, newPassword: string, confirmPassword: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await authService.changePassword(currentPassword, newPassword, confirmPassword);
      if (!result.success) {
        setError(result.error || '修改密碼失敗');
      }
      return result;
    } catch (err: any) {
      const errorMsg = err.message || '修改密碼時發生錯誤';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  }, []);
  return {
    user,
    loading,
    error,
    login,
    register,
    logout,
    getCurrentUser,
    updateProfile,
    changePassword,
    isAuthenticated: authService.isAuthenticated(),
    isAdmin: authService.isAdmin(),
  };
}
export default useAuth;
