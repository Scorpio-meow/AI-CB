/**
 * 受保護路由組件
 * 檢查用戶是否已登入,未登入則跳轉到登入頁
 */

import { Navigate, useLocation } from 'react-router-dom';
import authService from '../services/authService';

/**
 * 私有路由 - 需要登入才能訪問
 */
export const PrivateRoute = ({ element }) => {
  const location = useLocation();
  const isAuthenticated = authService.isAuthenticated();

  if (!isAuthenticated) {
    // 未登入,跳轉到登入頁,並保存原始路徑
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 已登入,顯示內容
  return element;
};/**
 * 管理員路由 - 需要管理員權限才能訪問
 */
export const AdminRoute = ({ element }) => {
  const location = useLocation();
  const isAuthenticated = authService.isAuthenticated();
  const isAdmin = authService.isAdmin();

  if (!isAuthenticated) {
    // 未登入,跳轉到登入頁
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!isAdmin) {
    // 已登入但不是管理員,跳轉到首頁並提示
    alert('您沒有管理員權限');
    return <Navigate to="/" replace />;
  }

  // 是管理員,顯示內容
  return element;
};/**
 * 公開路由 - 已登入用戶不能訪問 (如登入頁)
 */
export const PublicRoute = ({ element }) => {
  const isAuthenticated = authService.isAuthenticated();

  if (isAuthenticated) {
    // 已登入,跳轉到首頁
    return <Navigate to="/" replace />;
  }

  // 未登入,顯示內容 (登入頁)
  return element;
}; export default PrivateRoute;