# Diagrams

All diagrams here are Mermaid, so they render natively in GitHub's
Markdown viewer — no image files to keep in sync with the architecture.
The database ER diagram lives separately at
[`docs/database/er-diagram.md`](./database/er-diagram.md).

## System architecture

```mermaid
flowchart TD
    Client["Client\n(React SPA)"]

    subgraph Gateway["API Gateway — FastAPI"]
        direction TB
        Auth["Authentication\nJWT + RBAC"]
        RateLimit["Rate Limiter\nToken bucket, Redis-backed"]
        Logging["Logging Middleware\nevery request → request_logs"]
        Routing["Routing & Validation\nservice registry"]
    end

    Services["Downstream Services\n(echo / time / users / orders)"]
    Analytics["Analytics & Admin\naggregation over request_logs"]

    Postgres[("PostgreSQL\nusers, sessions, rate_limits,\nrequest_logs, blocked_requests,\nendpoint_stats, api_keys")]
    Redis[("Redis\ntoken bucket state")]

    Client -->|HTTPS + JWT| Auth
    Auth --> RateLimit
    RateLimit --> Logging
    Logging --> Routing
    Routing --> Services

    RateLimit <-->|GET/SET bucket state| Redis
    Logging -->|INSERT| Postgres
    Auth <-->|read/write users, sessions| Postgres
    RateLimit -->|read config, write blocked_requests| Postgres

    Client -->|admin only| Analytics
    Analytics -->|aggregate queries| Postgres
```

## Request flow (a single gateway call)

What actually happens, in order, for `POST /gateway/request`:

```mermaid
sequenceDiagram
    participant C as Client
    participant MW as Logging Middleware
    participant A as Auth Dependency
    participant RL as Rate Limiter
    participant G as Gateway Service
    participant R as Redis
    participant DB as PostgreSQL

    C->>MW: POST /gateway/request (Bearer token)
    MW->>A: decode JWT, load user
    alt invalid/missing token
        A-->>C: 401 Unauthorized
    else valid token
        A->>RL: check token bucket
        RL->>R: EVAL token_bucket.lua
        alt bucket empty
            R-->>RL: allowed=0, retry_after
            RL->>DB: INSERT blocked_requests
            RL-->>C: 429 Too Many Requests
        else tokens available
            R-->>RL: allowed=1, tokens_remaining
            RL->>G: route_request(service, method, path, body)
            G-->>RL: response data + timing
            RL-->>C: 200 OK
        end
    end
    MW->>DB: INSERT request_logs (always, regardless of outcome)
```

## Auth flow (login + refresh rotation)

```mermaid
sequenceDiagram
    participant C as Client
    participant API as /auth routes
    participant DB as PostgreSQL

    C->>API: POST /auth/login {email, password}
    API->>DB: SELECT user WHERE email=?
    API->>API: verify_password (bcrypt)
    API->>DB: INSERT sessions (hashed refresh token)
    API-->>C: access_token (30min) + refresh_token

    Note over C,API: ...time passes, access token expires...

    C->>API: POST /auth/refresh {refresh_token}
    API->>DB: SELECT session WHERE refresh_token_hash=?
    alt expired or already revoked
        API-->>C: 401 Unauthorized
    else valid
        API->>DB: UPDATE sessions SET is_revoked=true
        API->>DB: INSERT new sessions row
        API-->>C: new access_token + new refresh_token
    end
```

## Frontend auth interceptor (why a 401 doesn't just fail)

```mermaid
sequenceDiagram
    participant UI as React component
    participant AX as Axios interceptor
    participant API as Backend

    UI->>AX: GET /admin/users
    AX->>API: request + Bearer access_token
    API-->>AX: 401 (access token expired)
    AX->>API: POST /auth/refresh (stored refresh_token)
    API-->>AX: new token pair
    AX->>AX: store new tokens
    AX->>API: retry GET /admin/users + new access_token
    API-->>AX: 200 OK
    AX-->>UI: resolved data
```
