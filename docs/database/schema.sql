-- ============================================================================
-- API Gateway & Rate Limiting Platform — Database Schema (PostgreSQL 15+)
-- ============================================================================
-- This script is the raw-SQL equivalent of backend/app/models/*.py.
-- Run manually with: psql -U gateway_user -d gateway_db -f schema.sql
-- (Normally you'd let Alembic apply backend/alembic/versions/0001_initial_schema.py
-- instead of running this by hand — this file exists so the schema is reviewable
-- without reading Python, and as a fallback for quick local setup.)
-- ============================================================================

-- Required for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE user_role AS ENUM ('admin', 'user');

-- ----------------------------------------------------------------------------
-- users
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    role            user_role NOT NULL DEFAULT 'user',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_users_email ON users (email);

-- ----------------------------------------------------------------------------
-- api_keys
-- ----------------------------------------------------------------------------
CREATE TABLE api_keys (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name          VARCHAR(100) NOT NULL,
    key_hash      VARCHAR(255) NOT NULL UNIQUE,
    key_prefix    VARCHAR(12) NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at  TIMESTAMPTZ
);
CREATE INDEX ix_api_keys_user_id ON api_keys (user_id);
CREATE INDEX ix_api_keys_key_hash ON api_keys (key_hash);

-- ----------------------------------------------------------------------------
-- sessions  (refresh tokens)
-- ----------------------------------------------------------------------------
CREATE TABLE sessions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    refresh_token_hash   VARCHAR(255) NOT NULL UNIQUE,
    user_agent           VARCHAR(255),
    ip_address           VARCHAR(45),
    is_revoked           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at           TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_sessions_user_id ON sessions (user_id);
CREATE INDEX ix_sessions_refresh_token_hash ON sessions (refresh_token_hash);

-- ----------------------------------------------------------------------------
-- rate_limits  (token bucket configuration per user / endpoint)
-- ----------------------------------------------------------------------------
CREATE TABLE rate_limits (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    endpoint             VARCHAR(255),                 -- NULL = account-wide default
    bucket_capacity      INTEGER NOT NULL DEFAULT 100,
    refill_rate_per_sec  DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_rate_limit_user_endpoint UNIQUE (user_id, endpoint)
);
CREATE INDEX ix_rate_limits_user_id ON rate_limits (user_id);

-- ----------------------------------------------------------------------------
-- request_logs  (one row per gateway request)
-- ----------------------------------------------------------------------------
CREATE TABLE request_logs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID REFERENCES users (id) ON DELETE SET NULL,
    endpoint          VARCHAR(255) NOT NULL,
    method            VARCHAR(10) NOT NULL,
    status_code       INTEGER NOT NULL,
    response_time_ms  INTEGER NOT NULL,
    ip_address        VARCHAR(45) NOT NULL,
    "timestamp"       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_request_logs_user_id ON request_logs (user_id);
CREATE INDEX ix_request_logs_endpoint ON request_logs (endpoint);
CREATE INDEX ix_request_logs_timestamp ON request_logs ("timestamp");
CREATE INDEX ix_request_logs_endpoint_timestamp ON request_logs (endpoint, "timestamp");

-- ----------------------------------------------------------------------------
-- blocked_requests  (429 rejections)
-- ----------------------------------------------------------------------------
CREATE TABLE blocked_requests (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users (id) ON DELETE SET NULL,
    endpoint     VARCHAR(255) NOT NULL,
    ip_address   VARCHAR(45) NOT NULL,
    reason       VARCHAR(255) NOT NULL DEFAULT 'rate_limit_exceeded',
    "timestamp"  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_blocked_requests_user_id ON blocked_requests (user_id);
CREATE INDEX ix_blocked_requests_endpoint ON blocked_requests (endpoint);
CREATE INDEX ix_blocked_requests_timestamp ON blocked_requests ("timestamp");

-- ----------------------------------------------------------------------------
-- endpoint_stats  (daily pre-aggregated rollups)
-- ----------------------------------------------------------------------------
CREATE TABLE endpoint_stats (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint               VARCHAR(255) NOT NULL,
    method                 VARCHAR(10) NOT NULL,
    date                   DATE NOT NULL,
    total_requests         INTEGER NOT NULL DEFAULT 0,
    total_errors           INTEGER NOT NULL DEFAULT 0,
    avg_response_time_ms   DOUBLE PRECISION NOT NULL DEFAULT 0,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_endpoint_stats_endpoint_method_date UNIQUE (endpoint, method, date)
);
CREATE INDEX ix_endpoint_stats_endpoint ON endpoint_stats (endpoint);
CREATE INDEX ix_endpoint_stats_date ON endpoint_stats (date);
