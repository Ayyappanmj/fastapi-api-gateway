# Database ER Diagram

```mermaid
erDiagram
    USERS ||--o{ API_KEYS : owns
    USERS ||--o{ SESSIONS : has
    USERS ||--o{ RATE_LIMITS : configured_for
    USERS ||--o{ REQUEST_LOGS : makes
    USERS ||--o{ BLOCKED_REQUESTS : triggers

    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        enum role
        bool is_active
        timestamptz created_at
        timestamptz updated_at
    }

    API_KEYS {
        uuid id PK
        uuid user_id FK
        string name
        string key_hash UK
        string key_prefix
        bool is_active
        timestamptz created_at
        timestamptz last_used_at
    }

    SESSIONS {
        uuid id PK
        uuid user_id FK
        string refresh_token_hash UK
        string user_agent
        string ip_address
        bool is_revoked
        timestamptz created_at
        timestamptz expires_at
    }

    RATE_LIMITS {
        uuid id PK
        uuid user_id FK
        string endpoint "nullable = account default"
        int bucket_capacity
        float refill_rate_per_sec
        timestamptz created_at
        timestamptz updated_at
    }

    REQUEST_LOGS {
        uuid id PK
        uuid user_id FK "nullable"
        string endpoint
        string method
        int status_code
        int response_time_ms
        string ip_address
        timestamptz timestamp
    }

    BLOCKED_REQUESTS {
        uuid id PK
        uuid user_id FK "nullable"
        string endpoint
        string ip_address
        string reason
        timestamptz timestamp
    }

    ENDPOINT_STATS {
        uuid id PK
        string endpoint
        string method
        date date
        int total_requests
        int total_errors
        float avg_response_time_ms
        timestamptz updated_at
    }
```

## Normalization notes

- **3NF throughout.** No repeating groups; every non-key column depends only on its table's primary key.
- `RATE_LIMITS.endpoint` is nullable by design (not a separate "default limits" table) — a NULL row is the account-wide default, an override row targets one endpoint. The unique constraint `(user_id, endpoint)` still holds because Postgres treats each NULL as distinct, so a user can have at most one override per named endpoint plus one default.
- `REQUEST_LOGS` and `BLOCKED_REQUESTS` are kept separate rather than one table with a status flag, because they're queried independently at high volume (all requests vs. only rejections) and have different retention/aggregation needs.
- `ENDPOINT_STATS` is a derived/denormalized rollup of `REQUEST_LOGS`, intentionally — it exists purely so the analytics dashboard doesn't scan the full log table on every page load.
- Foreign keys use `ON DELETE CASCADE` for owned child rows (api_keys, sessions, rate_limits — deleting a user removes their own config) and `ON DELETE SET NULL` for historical logs (request_logs, blocked_requests — deleting a user preserves the audit trail).
