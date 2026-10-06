import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { listBlocked, listLogs } from "../api/admin";
import type { BlockedRequestEntry, RequestLogEntry } from "../types";

const PAGE_SIZE = 15;

function statusColor(status: number): string {
  if (status >= 500) return "text-danger";
  if (status >= 400) return "text-warning";
  return "text-success";
}

export default function Logs() {
  const [tab, setTab] = useState<"logs" | "blocked">("logs");
  const [page, setPage] = useState(1);
  const [endpointFilter, setEndpointFilter] = useState("");

  const [logs, setLogs] = useState<RequestLogEntry[]>([]);
  const [blocked, setBlocked] = useState<BlockedRequestEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setPage(1);
  }, [tab, endpointFilter]);

  useEffect(() => {
    setIsLoading(true);
    if (tab === "logs") {
      listLogs(page, PAGE_SIZE, endpointFilter || undefined)
        .then((resp) => {
          setLogs(resp.items);
          setTotal(resp.total);
        })
        .finally(() => setIsLoading(false));
    } else {
      listBlocked(page, PAGE_SIZE)
        .then((resp) => {
          setBlocked(resp.items);
          setTotal(resp.total);
        })
        .finally(() => setIsLoading(false));
    }
  }, [tab, page, endpointFilter]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Logs</h1>
          <p className="text-sm text-text-secondary">{total} entries.</p>
        </div>
        <div className="flex rounded-sm border border-border text-xs">
          <button
            onClick={() => setTab("logs")}
            className={`px-3 py-1.5 ${tab === "logs" ? "bg-accent text-base" : "text-text-secondary hover:text-text-primary"}`}
          >
            Request logs
          </button>
          <button
            onClick={() => setTab("blocked")}
            className={`px-3 py-1.5 ${tab === "blocked" ? "bg-accent text-base" : "text-text-secondary hover:text-text-primary"}`}
          >
            Blocked
          </button>
        </div>
      </div>

      {tab === "logs" && (
        <div className="mb-4 flex items-center gap-2 rounded-sm border border-border bg-surface px-3 py-2">
          <Search size={14} className="text-text-secondary" />
          <input
            value={endpointFilter}
            onChange={(e) => setEndpointFilter(e.target.value)}
            placeholder="Filter by exact endpoint, e.g. /gateway/request"
            className="w-full bg-transparent font-mono text-xs text-text-primary outline-none placeholder:text-text-secondary"
          />
        </div>
      )}

      <div className="overflow-x-auto rounded-sm border border-border bg-surface">
        {tab === "logs" ? (
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border text-text-secondary">
                <th className="px-4 py-3 font-normal">Timestamp</th>
                <th className="px-4 py-3 font-normal">Method</th>
                <th className="px-4 py-3 font-normal">Endpoint</th>
                <th className="px-4 py-3 font-normal">Status</th>
                <th className="px-4 py-3 font-normal">Time</th>
                <th className="px-4 py-3 font-normal">IP</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-b border-border font-mono last:border-0">
                  <td className="px-4 py-2.5 text-text-secondary">{l.timestamp.slice(0, 19).replace("T", " ")}</td>
                  <td className="px-4 py-2.5 text-text-primary">{l.method}</td>
                  <td className="px-4 py-2.5 text-text-primary">{l.endpoint}</td>
                  <td className={`px-4 py-2.5 ${statusColor(l.status_code)}`}>{l.status_code}</td>
                  <td className="px-4 py-2.5 tabular text-text-secondary">{l.response_time_ms}ms</td>
                  <td className="px-4 py-2.5 text-text-secondary">{l.ip_address}</td>
                </tr>
              ))}
              {!isLoading && logs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-text-secondary">
                    No log entries match.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        ) : (
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border text-text-secondary">
                <th className="px-4 py-3 font-normal">Timestamp</th>
                <th className="px-4 py-3 font-normal">Endpoint</th>
                <th className="px-4 py-3 font-normal">Reason</th>
                <th className="px-4 py-3 font-normal">IP</th>
              </tr>
            </thead>
            <tbody>
              {blocked.map((b) => (
                <tr key={b.id} className="border-b border-border font-mono last:border-0">
                  <td className="px-4 py-2.5 text-text-secondary">{b.timestamp.slice(0, 19).replace("T", " ")}</td>
                  <td className="px-4 py-2.5 text-text-primary">{b.endpoint}</td>
                  <td className="px-4 py-2.5 text-warning">{b.reason}</td>
                  <td className="px-4 py-2.5 text-text-secondary">{b.ip_address}</td>
                </tr>
              ))}
              {!isLoading && blocked.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-text-secondary">
                    No blocked requests.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-text-secondary">
        <span>
          Page {page} of {totalPages}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-sm border border-border p-1.5 disabled:opacity-40"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-sm border border-border p-1.5 disabled:opacity-40"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
