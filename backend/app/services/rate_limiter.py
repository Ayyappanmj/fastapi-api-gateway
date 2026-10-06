"""
Token Bucket rate limiter, backed by Redis.

--------------------------------------------------------------------------
ALGORITHM
--------------------------------------------------------------------------
Each (user, endpoint) pair gets a "bucket" that holds up to `capacity`
tokens. Every request costs 1 token. Tokens refill continuously at
`refill_rate` tokens per second (not in discrete steps) — so instead of
a hard reset every N seconds (like a fixed window counter), the bucket
smoothly regains capacity over time. This is what makes token bucket
better than a naive fixed-window counter: it absorbs short bursts (a
user can spend a full bucket of saved-up tokens all at once) while
still enforcing a steady long-run rate, and it doesn't have the
"double burst at the window boundary" flaw of fixed windows.

We don't store a timer that ticks in the background. Instead, on each
request we compute how many tokens *would* have accumulated since the
bucket's `last_refill` timestamp, add them (capped at `capacity`), and
then check if there's enough to pay this request's cost:

    elapsed          = now - last_refill
    tokens           = min(capacity, tokens + elapsed * refill_rate)
    if tokens >= cost:
        tokens -= cost          # request allowed
    else:
        retry_after = (cost - tokens) / refill_rate   # request denied

--------------------------------------------------------------------------
WHY A LUA SCRIPT
--------------------------------------------------------------------------
"Read current tokens, compute new tokens, write back" is a
read-modify-write. If we did that as separate Redis calls (GET then
SET) from Python, two concurrent requests from the same user could
both read the same starting token count and both be allowed through,
double-spending the bucket. Redis executes a Lua script as a single
atomic operation — no other command can run on that key in the middle
of it — so this race is closed without needing a separate distributed
lock.
--------------------------------------------------------------------------
"""
import time
from dataclasses import dataclass

import redis

_TOKEN_BUCKET_SCRIPT = """
-- KEYS[1] = bucket key
-- ARGV[1] = capacity          (max tokens the bucket can hold)
-- ARGV[2] = refill_rate       (tokens added per second)
-- ARGV[3] = now                (current unix time, seconds, float)
-- ARGV[4] = cost               (tokens this request consumes)

local key          = KEYS[1]
local capacity      = tonumber(ARGV[1])
local refill_rate   = tonumber(ARGV[2])
local now           = tonumber(ARGV[3])
local cost          = tonumber(ARGV[4])

local bucket        = redis.call("HMGET", key, "tokens", "last_refill")
local tokens        = tonumber(bucket[1])
local last_refill    = tonumber(bucket[2])

-- First request ever for this key: start with a full bucket.
if tokens == nil then
    tokens = capacity
    last_refill = now
end

local elapsed = now - last_refill
if elapsed < 0 then elapsed = 0 end        -- clock skew guard

tokens = tokens + (elapsed * refill_rate)
if tokens > capacity then tokens = capacity end

local allowed = 0
local retry_after = 0

if tokens >= cost then
    tokens = tokens - cost
    allowed = 1
else
    local deficit = cost - tokens
    retry_after = deficit / refill_rate
end

redis.call("HMSET", key, "tokens", tostring(tokens), "last_refill", tostring(now))
redis.call("EXPIRE", key, 3600)  -- idle buckets expire instead of living forever

return {allowed, tostring(tokens), tostring(retry_after)}
"""


@dataclass
class RateLimitResult:
    allowed: bool
    tokens_remaining: float
    retry_after_seconds: float


class TokenBucketRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def check(
        self, key: str, capacity: int, refill_rate: float, cost: float = 1.0
    ) -> RateLimitResult:
        now = time.time()
        allowed, tokens_remaining, retry_after = self.redis.eval(
            _TOKEN_BUCKET_SCRIPT, 1, key, capacity, refill_rate, now, cost
        )
        return RateLimitResult(
            allowed=bool(int(allowed)),
            tokens_remaining=float(tokens_remaining),
            retry_after_seconds=float(retry_after),
        )
