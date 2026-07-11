import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const brand = (
    <Link to="/" className="display text-lg">
      Person<span className="text-signal">Trace</span>
    </Link>
  );

  const navigation = (
    <>
      <Link
        to="/new"
        className="rounded-md bg-signal text-void text-center font-semibold py-2"
      >
        New trace
      </Link>
      <nav className="flex flex-col gap-1 text-sm">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `rounded px-3 py-2 ${isActive ? "bg-panel2 text-text" : "text-dim hover:text-text"}`
          }
        >
          Traces
        </NavLink>
      </nav>
      <div className="mt-auto text-xs text-dim space-y-2">
        <p className="truncate" title={user?.email}>{user?.email}</p>
        <button
          onClick={async () => {
            await logout.mutateAsync().catch(() => {});
            navigate("/login");
          }}
          className="hover:text-text"
        >
          Sign out
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <aside className="hidden md:flex w-56 shrink-0 border-r border-line flex-col p-4 gap-6">
        {brand}
        {navigation}
      </aside>
      <header className="md:hidden border-b border-line">
        <div className="flex items-center justify-between p-4">
          {brand}
          <button
            onClick={() => setMenuOpen((open) => !open)}
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            className="text-sm text-dim hover:text-text"
          >
            {menuOpen ? "Close" : "Menu"}
          </button>
        </div>
        {menuOpen && (
          <div
            id="mobile-nav"
            className="flex flex-col gap-6 border-t border-line p-4"
          >
            {navigation}
          </div>
        )}
      </header>
      <main className="flex-1 min-w-0 p-4 md:p-8">
        <Outlet />
      </main>
    </div>
  );
}
