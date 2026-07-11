import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./useAuth";

export function RequireAuth() {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return <div className="min-h-screen grid place-items-center text-dim">Loading…</div>;
  }
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
