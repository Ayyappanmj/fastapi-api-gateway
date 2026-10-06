import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Network } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../api/errors";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(extractErrorMessage(err, "Invalid email or password."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-base px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2">
          <Network size={22} className="text-accent" />
          <span className="text-lg font-semibold tracking-tight text-text-primary">
            Gateway Console
          </span>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-sm border border-border bg-surface p-6"
        >
          <h1 className="mb-1 text-base font-semibold text-text-primary">Sign in</h1>
          <p className="mb-5 text-sm text-text-secondary">Access the API gateway dashboard.</p>

          {error && (
            <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </div>
          )}

          <label className="mb-1 block text-xs text-text-secondary">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mb-4 w-full rounded-sm border border-border bg-base px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
            placeholder="you@company.com"
          />

          <label className="mb-1 block text-xs text-text-secondary">Password</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mb-5 w-full rounded-sm border border-border bg-base px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
            placeholder="••••••••"
          />

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-sm bg-accent py-2 text-sm font-medium text-base transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-text-secondary">
          No account?{" "}
          <Link to="/register" className="text-accent hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
