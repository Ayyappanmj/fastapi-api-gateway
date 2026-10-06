import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  BarChart3,
  Users,
  FileClock,
  Settings as SettingsIcon,
  Sun,
  Moon,
  LogOut,
  Menu,
  X,
  Network,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, adminOnly: false },
  { to: "/analytics", label: "Analytics", icon: BarChart3, adminOnly: true },
  { to: "/users", label: "Users", icon: Users, adminOnly: true },
  { to: "/logs", label: "Logs", icon: FileClock, adminOnly: true },
  { to: "/settings", label: "Settings", icon: SettingsIcon, adminOnly: false },
];

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  const visibleItems = NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === "admin");

  return (
    <div className="flex min-h-screen bg-base text-text-primary">
      {/* Sidebar — desktop */}
      <aside className="hidden w-60 shrink-0 border-r border-border bg-surface md:flex md:flex-col">
        <SidebarContent visibleItems={visibleItems} onNavigate={() => {}} />
      </aside>

      {/* Sidebar — mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 border-r border-border bg-surface">
            <div className="flex justify-end p-3">
              <button onClick={() => setMobileOpen(false)} aria-label="Close menu">
                <X size={20} className="text-text-secondary" />
              </button>
            </div>
            <SidebarContent visibleItems={visibleItems} onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-4">
          <div className="flex items-center gap-3">
            <button
              className="text-text-secondary md:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu size={22} />
            </button>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-success/30 bg-success/10 px-2.5 py-1 text-xs text-success">
              <span className="h-1.5 w-1.5 rounded-full bg-success" />
              operational
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              aria-label="Toggle theme"
              className="rounded-md border border-border p-1.5 text-text-secondary transition-colors hover:border-accent hover:text-accent"
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <div className="hidden text-right sm:block">
              <div className="text-sm leading-tight">{user?.full_name || user?.email}</div>
              <div className="font-mono text-xs leading-tight text-text-secondary">{user?.role}</div>
            </div>
            <button
              onClick={logout}
              aria-label="Log out"
              className="rounded-md border border-border p-1.5 text-text-secondary transition-colors hover:border-danger hover:text-danger"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}

function SidebarContent({
  visibleItems,
  onNavigate,
}: {
  visibleItems: typeof NAV_ITEMS;
  onNavigate: () => void;
}) {
  return (
    <>
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <Network size={18} className="text-accent" />
        <span className="font-semibold tracking-tight">Gateway Console</span>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {visibleItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "bg-accent/10 text-accent"
                  : "text-text-secondary hover:bg-surface-raised hover:text-text-primary"
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
