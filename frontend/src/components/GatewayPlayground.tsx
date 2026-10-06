import { useState, type FormEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { sendGatewayRequest } from "../api/gateway";
import { extractErrorMessage } from "../api/errors";
import type { GatewayResponse } from "../types";

const SERVICES = ["echo", "time", "users", "orders"];
const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];

export function GatewayPlayground() {
  const [targetService, setTargetService] = useState("echo");
  const [method, setMethod] = useState("POST");
  const [path, setPath] = useState("/");
  const [body, setBody] = useState('{\n  "hello": "world"\n}');
  const [result, setResult] = useState<GatewayResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setIsSubmitting(true);
    try {
      let parsedBody: Record<string, unknown> | null = null;
      if (body.trim()) {
        parsedBody = JSON.parse(body);
      }
      const response = await sendGatewayRequest(targetService, method, path, parsedBody);
      setResult(response);
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError("Body must be valid JSON.");
      } else {
        setError(extractErrorMessage(err, "The gateway rejected that request."));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-lg font-semibold text-text-primary">Gateway playground</h1>
      <p className="mb-6 text-sm text-text-secondary">
        Send an authenticated, rate-limited request through the gateway to a registered service.
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        <form onSubmit={handleSubmit} className="rounded-sm border border-border bg-surface p-4">
          <div className="mb-4 grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-text-secondary">Target service</label>
              <select
                value={targetService}
                onChange={(e) => setTargetService(e.target.value)}
                className="w-full rounded-sm border border-border bg-base px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
              >
                {SERVICES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-text-secondary">Method</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="w-full rounded-sm border border-border bg-base px-3 py-2 text-sm text-text-primary outline-none focus:border-accent"
              >
                {METHODS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <label className="mb-1 block text-xs text-text-secondary">Path</label>
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            className="mb-4 w-full rounded-sm border border-border bg-base px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-accent"
          />

          <label className="mb-1 block text-xs text-text-secondary">Body (JSON)</label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={6}
            className="mb-4 w-full rounded-sm border border-border bg-base px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-accent"
          />

          {error && (
            <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center justify-center gap-2 rounded-sm bg-accent px-4 py-2 text-sm font-medium text-base transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            Send request
          </button>
        </form>

        <div className="rounded-sm border border-border bg-surface p-4">
          <h2 className="mb-3 text-sm font-medium text-text-primary">Response</h2>
          {!result ? (
            <p className="text-sm text-text-secondary">Nothing sent yet.</p>
          ) : (
            <div>
              <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-text-secondary">
                <span>
                  status <span className="text-success">{result.meta.status_code}</span>
                </span>
                <span>
                  service <span className="text-text-primary">{result.meta.service}</span>
                </span>
                <span>
                  time <span className="text-text-primary">{result.meta.response_time_ms}ms</span>
                </span>
              </div>
              <pre className="overflow-x-auto rounded-sm bg-base p-3 font-mono text-xs text-text-primary">
                {JSON.stringify(result.data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
