import { Moon, Sun, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export default function Settings() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  if (!user) return null;

  return (
    <div className="max-w-lg">
      <h1 className="mb-1 text-lg font-semibold text-text-primary">Settings</h1>
      <p className="mb-6 text-sm text-text-secondary">Account and appearance.</p>

      <section className="mb-4 rounded-sm border border-border bg-surface p-4">
        <h2 className="mb-3 text-sm font-medium text-text-primary">Account</h2>
        <dl className="space-y-2 text-sm">
          <Row label="Name" value={user.full_name || "—"} />
          <Row label="Email" value={user.email} mono />
          <Row label="Role" value={user.role} mono />
          <Row label="Status" value={user.is_active ? "active" : "disabled"} />
        </dl>
        <p className="mt-3 text-xs text-text-secondary">
          Profile editing isn't available yet — this view is read-only.
        </p>
      </section>

      <section className="mb-4 rounded-sm border border-border bg-surface p-4">
        <h2 className="mb-3 text-sm font-medium text-text-primary">Appearance</h2>
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">Theme</span>
          <button
            onClick={toggleTheme}
            className="flex items-center gap-2 rounded-sm border border-border px-3 py-1.5 text-sm text-text-primary transition-colors hover:border-accent"
          >
            {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            {theme === "dark" ? "Switch to light" : "Switch to dark"}
          </button>
        </div>
      </section>

      <button
        onClick={logout}
        className="flex items-center gap-2 rounded-sm border border-danger/30 px-3 py-2 text-sm text-danger transition-colors hover:bg-danger/10"
      >
        <LogOut size={15} />
        Log out
      </button>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between border-t border-border pt-2 first:border-0 first:pt-0">
      <dt className="text-text-secondary">{label}</dt>
      <dd className={`text-text-primary ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}
