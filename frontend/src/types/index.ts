// Mirrors app/schemas/*.py field-for-field so the frontend and backend
// never drift silently out of sync.

export type UserRole = "admin" | "user";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// --- gateway ---------------------------------------------------------

export interface GatewayResponseMeta {
  service: string;
  path: string;
  method: string;
  status_code: number;
  response_time_ms: number;
}

export interface GatewayResponse {
  success: boolean;
  meta: GatewayResponseMeta;
  data: Record<string, unknown>;
}

export interface GatewayStatus {
  gateway: string;
  registered_services: string[];
  requested_by: string;
}

// --- analytics ---------------------------------------------------------

export interface OverviewStats {
  window_hours: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  blocked_requests: number;
  active_users: number;
  avg_response_time_ms: number;
  requests_per_minute: number;
  error_rate_percent: number;
}

export interface TrafficPoint {
  bucket: string;
  request_count: number;
}

export interface TrafficResponse {
  granularity: "hourly" | "daily";
  points: TrafficPoint[];
}

export interface EndpointBreakdown {
  endpoint: string;
  method: string;
  total_requests: number;
  total_errors: number;
  avg_response_time_ms: number;
  error_rate_percent: number;
}

export interface UserActivity {
  user_id: string;
  email: string;
  request_count: number;
}

export interface EndpointsResponse {
  top_endpoints: EndpointBreakdown[];
  slow_endpoints: EndpointBreakdown[];
  most_active_users: UserActivity[];
}

// --- admin ---------------------------------------------------------

export interface RequestLogEntry {
  id: string;
  user_id: string | null;
  endpoint: string;
  method: string;
  status_code: number;
  response_time_ms: number;
  ip_address: string;
  timestamp: string;
}

export interface BlockedRequestEntry {
  id: string;
  user_id: string | null;
  endpoint: string;
  ip_address: string;
  reason: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  page: number;
  page_size: number;
  total: number;
  items: T[];
}

export interface ApiErrorBody {
  success: false;
  error: string;
  detail?: string;
}
