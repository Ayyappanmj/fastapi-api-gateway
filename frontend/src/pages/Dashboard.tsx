import { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  Users as UsersIcon,
  Timer,
  Gauge,
  AlertTriangle,
} from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useAuth } from "../context/AuthContext";
import { getOverview, getTraffic } from "../api/analytics";
import { StatCard } from "../components/StatCard";
import type { OverviewStats, TrafficPoint } from "../types";
import { GatewayPlayground } from "../components/GatewayPlayground";

export default function Dashboard() {
  const { user } = useAuth();

  if (user?.role === "admin") return <AdminOverview />;
  return <GatewayPlayground />;
}

function AdminOverview() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [traffic, setTraffic] = useState<TrafficPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getOverview(24), getTraffic("hourly", 24)])
      .then(([overview, trafficResp]) => {
        setStats(overview);
        setTraffic(trafficResp.points);
      })
      .catch(() => setError("Could not load analytics data."))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <p className="text-text-secondary">Loading dashboard…</p>;
  if (error) return <p className="text-danger">{error}</p>;
  if (!stats) return null;

  return (
    <div>
      <h1 className="mb-1 text-lg font-semibold text-text-primary">Overview</h1>
      <p className="mb-6 text-sm text-text-secondary">Last {stats.window_hours} hours of gateway traffic.</p>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <StatCard label="Total requests" value={stats.total_requests} icon={Activity} category="volume" />
        <StatCard
          label="Successful"
          value={stats.successful_requests}
          icon={CheckCircle2}
          category="success"
        />
        <StatCard label="Failed" value={stats.failed_requests} icon={XCircle} category="danger" />
        <StatCard label="Blocked" value={stats.blocked_requests} icon={ShieldAlert} category="warning" />
        <StatCard label="Active users" value={stats.active_users} icon={UsersIcon} category="volume" />
        <StatCard
          label="Avg response time"
          value={stats.avg_response_time_ms}
          suffix="ms"
          icon={Timer}
          category="neutral"
        />
        <StatCard
          label="Requests / min"
          value={stats.requests_per_minute}
          icon={Gauge}
          category="volume"
        />
        <StatCard
          label="Error rate"
          value={stats.error_rate_percent}
          suffix="%"
          icon={AlertTriangle}
          category={stats.error_rate_percent > 5 ? "danger" : "neutral"}
        />
      </div>

      <div className="mt-6 rounded-sm border border-border bg-surface p-4">
        <h2 className="mb-4 text-sm font-medium text-text-primary">Hourly traffic</h2>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={traffic}>
            <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
            <XAxis
              dataKey="bucket"
              tick={{ fill: "var(--color-text-secondary)", fontSize: 11 }}
              tickFormatter={(value: string) => value.slice(11)}
            />
            <YAxis tick={{ fill: "var(--color-text-secondary)", fontSize: 11 }} allowDecimals={false} />
            <Tooltip
              contentStyle={{
                background: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                fontSize: 12,
              }}
            />
            <Line type="monotone" dataKey="request_count" stroke="var(--color-accent)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
