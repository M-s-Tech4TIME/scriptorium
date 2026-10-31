import { IconBook2, IconLogout2 } from "@tabler/icons-react";
import { Link, Outlet } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { Button } from "./ui";

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="app-brand" aria-label="Scriptorium home">
          <IconBook2 size={22} stroke={1.8} aria-hidden="true" />
          <span>Scriptorium</span>
        </Link>
        <div className="app-header-right">
          {user ? (
            <>
              <span className="user-chip" title={user.email}>
                {user.display}
              </span>
              <Button variant="ghost" onClick={() => void logout()}>
                <IconLogout2 size={16} aria-hidden="true" />
                Sign out
              </Button>
            </>
          ) : null}
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
