import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useSchoolSlug } from "../hooks/useSchoolNav";
import { hasRole } from "../utils/roles";

export default function ProtectedRoute({ allowedRoles }) {
  const { user, loading, isAuthenticated } = useAuth();
  const schoolSlug = useSchoolSlug();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground font-mono text-sm uppercase tracking-widest">
        Loading…
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={`/${schoolSlug}/login`} replace />;
  }

  if (allowedRoles && !hasRole(user, allowedRoles)) {
    return <Navigate to={`/${schoolSlug}/dashboard`} replace />;
  }

  return <Outlet />;
}
