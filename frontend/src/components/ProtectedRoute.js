import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="rounded-3xl bg-white/90 px-8 py-6 text-sm text-ink shadow-soft ring-1 ring-borderSoft">
          Checking your session...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace state={{ from: location }} />;
  }

  return children;
}

export default ProtectedRoute;
