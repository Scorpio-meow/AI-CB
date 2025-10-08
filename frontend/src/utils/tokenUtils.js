/**
 * Token 管理工具
 * 處理 Token 過期檢測和自動刷新
 */

import { jwtDecode } from 'jwt-decode';

/**
 * 解碼 JWT Token
 */
export const decodeToken = (token) => {
  try {
    return jwtDecode(token);
  } catch (error) {
    console.error('Token 解碼失敗:', error);
    return null;
  }
};

/**
 * 檢查 Token 是否過期
 * @param {string} token - JWT Token
 * @param {number} bufferTime - 提前刷新時間（秒），預設 5 分鐘
 */
export const isTokenExpired = (token, bufferTime = 300) => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) {
    return true;
  }

  const currentTime = Date.now() / 1000;
  return decoded.exp - currentTime < bufferTime;
};

/**
 * 獲取 Token 剩餘時間（秒）
 */
export const getTokenRemainingTime = (token) => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) {
    return 0;
  }

  const currentTime = Date.now() / 1000;
  return Math.max(0, decoded.exp - currentTime);
};

/**
 * 檢查 Token 是否需要刷新
 * @param {string} token - JWT Token
 * @param {number} threshold - 刷新閾值（秒），預設 5 分鐘
 */
export const shouldRefreshToken = (token, threshold = 300) => {
  if (!token) return false;
  
  const remainingTime = getTokenRemainingTime(token);
  // 只有在 token 還未過期但接近過期時才刷新
  // 如果已經過期（remainingTime <= 0），不要嘗試刷新，直接讓它失敗
  return remainingTime > 0 && remainingTime < threshold;
};

/**
 * 檢查是否有有效的登錄狀態
 */
export const hasValidAuth = () => {
  const token = localStorage.getItem('access_token');
  if (!token) return false;
  
  // 檢查 token 是否完全過期
  const remainingTime = getTokenRemainingTime(token);
  return remainingTime > 0;
};

/**
 * 清除所有認證信息
 */
export const clearAuth = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_info');
  console.log('[Auth] 已清除認證信息');
};

/**
 * 格式化剩餘時間為可讀字符串
 */
export const formatRemainingTime = (seconds) => {
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days} 天`;
  if (hours > 0) return `${hours} 小時`;
  if (minutes > 0) return `${minutes} 分鐘`;
  return `${Math.floor(seconds)} 秒`;
};
