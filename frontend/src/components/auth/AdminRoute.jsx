import { Navigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";

/**
 * Wraps /admin. Requires both a signed-in user (like ProtectedRoute) AND
 * user.is_admin — a non-admin who navigates here directly is sent back
 * to their own dashboard rather than the login page, since they are
 * authenticated, just not authorized for this page.
 */
export default function AdminRoute({ children }) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!user?.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
