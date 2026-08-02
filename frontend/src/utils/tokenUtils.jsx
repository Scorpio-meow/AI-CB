
import { jwtDecode } from 'jwt-decode';
export const decodeToken = (token) => {
  try {
    return jwtDecode(token);
  } catch (error) {
    console.error('Token 解碼失敗:', error);
    return null;
  }
};
export const isTokenExpired = (token, bufferTime = 300) => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) {
    return true;
  }
  const currentTime = Date.now() / 1000;
  return decoded.exp - currentTime < bufferTime;
};
export const getTokenRemainingTime = (token) => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) {
    return 0;
  }
  const currentTime = Date.now() / 1000;
  return Math.max(0, decoded.exp - currentTime);
};
export const shouldRefreshToken = (token, threshold = 300) => {
  if (!token) return false;
  const remainingTime = getTokenRemainingTime(token);
  return remainingTime > 0 && remainingTime < threshold;
};
export const hasValidAuth = () => {
  const token = localStorage.getItem('access_token');
  if (!token) return false;
  const remainingTime = getTokenRemainingTime(token);
  return remainingTime > 0;
};
export const clearAuth = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_info');
  console.log('[Auth] 已清除認證信息');
};
export const formatRemainingTime = (seconds) => {
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days} 天`;
  if (hours > 0) return `${hours} 小時`;
  if (minutes > 0) return `${minutes} 分鐘`;
  return `${Math.floor(seconds)} 秒`;
};