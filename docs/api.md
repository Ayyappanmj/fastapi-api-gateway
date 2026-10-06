# API Reference

Interactive docs (Swagger UI) are always available at `/docs` on a
running backend, generated directly from the Pydantic schemas — this
page is a hand-written companion with example requests/responses for
each endpoint. Default local base URL: `http://localhost:8000`.

All authenticated requests need `Authorization: Bearer <access_token>`.

## Auth

### `POST /auth/register`

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@example.com","password":"Password123","full_name":"Jane Doe"}'
```

```json
// 201 Created
{
  "id": "6c2f...",
  "email": "jane@example.com",
  "full_name": "Jane Doe",
  "role": "user",
  "is_active": true
}
```

`409 Conflict` if the email is already registered. `422` if the
password is under 8 characters or missing letters/numbers.

### `POST /auth/login`

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@example.com","password":"Password123"}'
```

```json
// 200 OK
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "AbCdEf123...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { "id": "6c2f...", "email": "jane@example.com", "full_name": "Jane Doe", "role": "user", "is_active": true }
}
```

`401 Unauthorized` on wrong credentials or a deactivated account.

### `POST /auth/refresh`

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"AbCdEf123..."}'
```

Returns the same shape as `/auth/login` — both tokens are **rotated**:
the old refresh token stops working as soon as you use it once.
`401` if the refresh token is invalid, expired, or already used.

### `GET /auth/me`

```bash
curl http://localhost:8000/auth/me -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
// 200 OK
{ "id": "6c2f...", "email": "jane@example.com", "full_name": "Jane Doe", "role": "user", "is_active": true }
```

## Gateway

### `POST /gateway/request`

Authenticated **and** rate-limited (token bucket — see [`docs/diagrams.md`](./diagrams.md) for the full flow).

```bash
curl -X POST http://localhost:8000/gateway/request \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_service":"echo","method":"POST","path":"/anything","body":{"hello":"world"}}'
```

```json
// 200 OK
{
  "success": true,
  "meta": { "service": "echo", "path": "/anything", "method": "POST", "status_code": 200, "response_time_ms": 0.42 },
  "data": { "echoed": { "hello": "world" } }
}
```

Registered `target_service` values: `echo`, `time`, `users`, `orders`.
To proxy a target to an external HTTP service, set its optional URL in the backend environment: `ECHO_SERVICE_URL`, `TIME_SERVICE_URL`, `USERS_SERVICE_URL`, or `ORDERS_SERVICE_URL`. Each maps to the corresponding lowercase `target_service`; unset URLs use the in-process demo handlers. An unreachable configured target returns `502 Bad Gateway` with a target-specific error.

```json
// 429 Too Many Requests (bucket exhausted)
{ "success": false, "error": "Rate limit exceeded for '/gateway/request'. Try again in 4s." }
```
Response also includes a `Retry-After` header (seconds).

```json
// 404 Not Found (unknown service)
{ "success": false, "error": "Unknown service 'nonexistent'. Registered services: ['echo', 'orders', 'time', 'users']" }
```

### `GET /gateway/status`

```bash
curl http://localhost:8000/gateway/status -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
{ "gateway": "operational", "registered_services": ["echo", "orders", "time", "users"], "requested_by": "jane@example.com" }
```

## Analytics *(admin only — all return 403 for a non-admin token)*

### `GET /analytics/overview?hours=24`

```json
{
  "window_hours": 24,
  "total_requests": 4820,
  "successful_requests": 4713,
  "failed_requests": 107,
  "blocked_requests": 19,
  "active_users": 34,
  "avg_response_time_ms": 42.3,
  "requests_per_minute": 3.35,
  "error_rate_percent": 2.22
}
```

### `GET /analytics/traffic?granularity=hourly&hours=24`

`granularity` is `hourly` (uses `hours`) or `daily` (uses `days`).

```json
{
  "granularity": "hourly",
  "points": [
    { "bucket": "2026-10-04 09:00", "request_count": 112 },
    { "bucket": "2026-10-04 10:00", "request_count": 98 }
  ]
}
```

### `GET /analytics/endpoints?hours=168&limit=10`

```json
{
  "top_endpoints": [
    { "endpoint": "/gateway/request", "method": "POST", "total_requests": 3120, "total_errors": 41, "avg_response_time_ms": 38.1, "error_rate_percent": 1.31 }
  ],
  "slow_endpoints": [ /* same shape, sorted by avg_response_time_ms desc */ ],
  "most_active_users": [
    { "user_id": "6c2f...", "email": "jane@example.com", "request_count": 812 }
  ]
}
```

## Admin *(admin only)*

All three support `?page=1&page_size=20`.

### `GET /admin/users`

```json
{
  "success": true, "page": 1, "page_size": 20, "total": 3,
  "items": [ { "id": "6c2f...", "email": "jane@example.com", "full_name": "Jane Doe", "role": "user", "is_active": true } ]
}
```

### `GET /admin/logs?endpoint=/gateway/request`

`endpoint` is an optional exact-match filter.

```json
{
  "success": true, "page": 1, "page_size": 20, "total": 3120,
  "items": [
    {
      "id": "a1b2...", "user_id": "6c2f...", "endpoint": "/gateway/request", "method": "POST",
      "status_code": 200, "response_time_ms": 41, "ip_address": "172.18.0.1", "timestamp": "2026-10-04T09:12:03Z"
    }
  ]
}
```

### `GET /admin/blocked`

```json
{
  "success": true, "page": 1, "page_size": 20, "total": 19,
  "items": [
    { "id": "c3d4...", "user_id": "6c2f...", "endpoint": "/gateway/request", "ip_address": "172.18.0.1", "reason": "rate_limit_exceeded", "timestamp": "2026-10-04T09:14:21Z" }
  ]
}
```

## Error envelope

Every non-2xx response (except FastAPI's own 404 for a truly unmatched
route, which still gets converted to this shape by the global handler)
follows the same shape:

```json
{ "success": false, "error": "short message", "detail": "optional longer detail, e.g. field-level validation errors" }
```

## Health

### `GET /health`

No auth required.

```json
{ "status": "healthy", "environment": "development", "database": "ok", "redis": "ok" }
```
