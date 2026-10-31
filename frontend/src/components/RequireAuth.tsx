import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { Spinner } from "./ui";

export function RequireAuth({ children }: { children?: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="boot-screen">
        <Spinner label="Opening the library…" />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children ? <>{children}</> : <Outlet />;
}
