import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { Loading } from './components/ui';

// Wrap a page: <RequireRole roles={['admin']}><AdminPage/></RequireRole>
export default function RequireRole({ roles, children }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}
