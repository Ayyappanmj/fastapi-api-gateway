"""
Redis connection.

Exposed as `get_redis()` — a plain function, not a global-only singleton
— so it can be used with FastAPI's Depends() and overridden in tests
with an in-memory fake (see app/tests/conftest.py), the same pattern
used for get_db().
"""
import redis

from app.config import get_settings

settings = get_settings()

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client
