import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/shared/hooks/useAuth";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";

export function ProtectedRoute() {
  const { is_authenticated, is_loading } = useAuth();
  const location = useLocation();

  // While restoring session, show a full-page spinner
  if (is_loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <LoadingSpinner size="h-10 w-10" />
          <p className="text-sm text-gray-500">Restaurando sesión…</p>
        </div>
      </div>
    );
  }

  if (!is_authenticated) {
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }

  return <Outlet />;
}

