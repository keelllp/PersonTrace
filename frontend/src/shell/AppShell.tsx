import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 shrink-0 border-r border-line flex flex-col p-4 gap-6">
        <Link to="/" className="display text-lg">
          Person<span className="text-signal">Trace</span>
        </Link>
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
              await logout.mutateAsync();
              navigate("/login");
            }}
            className="hover:text-text"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 p-8">
        <Outlet />
      </main>
    </div>
  );
}
