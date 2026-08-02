
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
export const PrivateRoute = ({ element }) => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return element;
};
export const AdminRoute = ({ element }) => {
  const location = useLocation();
  const { isAuthenticated, isAdmin } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (!isAdmin) {
    alert('您沒有管理員權限');
    return <Navigate to="/" replace />;
  }
  return element;
};
export const PublicRoute = ({ element }) => {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return element;
}; export default PrivateRoute;