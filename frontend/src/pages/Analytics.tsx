import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { getEndpointBreakdown, getTraffic } from "../api/analytics";
import type { EndpointBreakdown, TrafficPoint, UserActivity } from "../types";

export default function Analytics() {
  const [granularity, setGranularity] = useState<"hourly" | "daily">("hourly");
  const [traffic, setTraffic] = useState<TrafficPoint[]>([]);
  const [topEndpoints, setTopEndpoints] = useState<EndpointBreakdown[]>([]);
  const [slowEndpoints, setSlowEndpoints] = useState<EndpointBreakdown[]>([]);
  const [activeUsers, setActiveUsers] = useState<UserActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    Promise.all([
      getTraffic(granularity, 24, 14),
      getEndpointBreakdown(24 * 7, 8),
    ])
      .then(([trafficResp, endpointsResp]) => {
        setTraffic(trafficResp.points);
        setTopEndpoints(endpointsResp.top_endpoints);
        setSlowEndpoints(endpointsResp.slow_endpoints);
        setActiveUsers(endpointsResp.most_active_users);
      })
      .finally(() => setIsLoading(false));
  }, [granularity]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Analytics</h1>
          <p className="text-sm text-text-secondary">Endpoint and traffic breakdown, last 7 days.</p>
        </div>
        <div className="flex rounded-sm border border-border text-xs">
          {(["hourly", "daily"] as const).map((g) => (
            <button
              key={g}
              onClick={() => setGranularity(g)}
              className={`px-3 py-1.5 capitalize ${
                granularity === g ? "bg-accent text-base" : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-6 rounded-sm border border-border bg-surface p-4">
        <h2 className="mb-4 text-sm font-medium text-text-primary">Traffic ({granularity})</h2>
        {isLoading ? (
          <p className="text-sm text-text-secondary">Loading…</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={traffic}>
              <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
              <XAxis
                dataKey="bucket"
                tick={{ fill: "var(--color-text-secondary)", fontSize: 11 }}
                tickFormatter={(v: string) => (granularity === "hourly" ? v.slice(11) : v.slice(5))}
              />
              <YAxis tick={{ fill: "var(--color-text-secondary)", fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: "var(--color-surface-raised)",
                  border: "1px solid var(--color-border)",
                  fontSize: 12,
                }}
              />
              <Bar dataKey="request_count" fill="var(--color-accent)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <EndpointTable title="Top endpoints" rows={topEndpoints} valueKey="total_requests" valueLabel="requests" />
        <EndpointTable
          title="Slowest endpoints"
          rows={slowEndpoints}
          valueKey="avg_response_time_ms"
          valueLabel="ms"
        />
        <div className="rounded-sm border border-border bg-surface p-4">
          <h2 className="mb-3 text-sm font-medium text-text-primary">Most active users</h2>
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-text-secondary">
                <th className="pb-2 font-normal">Email</th>
                <th className="pb-2 text-right font-normal">Requests</th>
              </tr>
            </thead>
            <tbody>
              {activeUsers.map((u) => (
                <tr key={u.user_id} className="border-t border-border">
                  <td className="py-2 text-text-primary">{u.email}</td>
                  <td className="py-2 text-right font-mono tabular text-text-primary">{u.request_count}</td>
                </tr>
              ))}
              {activeUsers.length === 0 && (
                <tr>
                  <td colSpan={2} className="py-3 text-text-secondary">
                    No activity yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function EndpointTable({
  title,
  rows,
  valueKey,
  valueLabel,
}: {
  title: string;
  rows: EndpointBreakdown[];
  valueKey: "total_requests" | "avg_response_time_ms";
  valueLabel: string;
}) {
  return (
    <div className="rounded-sm border border-border bg-surface p-4">
      <h2 className="mb-3 text-sm font-medium text-text-primary">{title}</h2>
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="text-text-secondary">
            <th className="pb-2 font-normal">Endpoint</th>
            <th className="pb-2 text-right font-normal">{valueLabel}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.method}-${r.endpoint}`} className="border-t border-border">
              <td className="py-2 font-mono text-text-primary">
                {r.method} {r.endpoint}
              </td>
              <td className="py-2 text-right font-mono tabular text-text-primary">{r[valueKey]}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={2} className="py-3 text-text-secondary">
                No data yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
