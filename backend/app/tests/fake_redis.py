"""
Minimal in-memory stand-in for redis.Redis, used only in tests.

We don't run a real Redis server in this environment, so instead of
parsing the actual Lua script, this fake mirrors the exact same token
bucket math in Python for the one method (`eval`) our rate limiter
calls. Keeping the math here byte-for-byte identical to
app/services/rate_limiter.py's Lua script is what makes this a
faithful stand-in rather than a shortcut — every branch (first
request, partial refill, cap at capacity, insufficient tokens) matches.

For a real project you'd point tests at a real Redis instance (or the
`fakeredis` package, which embeds an actual Lua interpreter) instead;
this hand-rolled version avoids adding a dependency just for CI.
"""


import time


class FakeRedis:
    def __init__(self):
        self._buckets: dict[str, dict[str, float]] = {}
        self._counters: dict[str, tuple[int, float]] = {}

    def eval(self, script, numkeys, *args):
        if len(args) == 2:
            key, window_seconds = args
            now = time.time()
            count, expires_at = self._counters.get(key, (0, now + window_seconds))
            if now >= expires_at:
                count = 0
            count += 1
            if count == 1:
                expires_at = now + window_seconds
            self._counters[key] = (count, expires_at)
            return count

        key, capacity, refill_rate, now, cost = args
        capacity = float(capacity)
        refill_rate = float(refill_rate)
        now = float(now)
        cost = float(cost)

        bucket = self._buckets.get(key)
        if bucket is None:
            tokens = capacity
            last_refill = now
        else:
            tokens = bucket["tokens"]
            last_refill = bucket["last_refill"]

        elapsed = max(0.0, now - last_refill)
        tokens = min(capacity, tokens + elapsed * refill_rate)

        if tokens >= cost:
            tokens -= cost
            allowed = 1
            retry_after = 0.0
        else:
            allowed = 0
            retry_after = (cost - tokens) / refill_rate

        self._buckets[key] = {"tokens": tokens, "last_refill": now}
        return [allowed, str(tokens), str(retry_after)]

    def flushall(self):
        self._buckets.clear()
        self._counters.clear()

    def ping(self) -> bool:
        return True
