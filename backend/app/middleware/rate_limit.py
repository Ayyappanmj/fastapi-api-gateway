"""
Rate-limit enforcement as a FastAPI dependency.

Wraps get_current_user, so any route using this instead of
get_current_user gets authentication AND rate limiting for free. On
429 it also writes a row to `blocked_requests` (Phase 3 model) so the
admin dashboard (Phase 8) can show blocked-request counts without
re-deriving them from Redis.
"""
from fastapi import Depends, HTTPException, Request, status  # type: ignore[import-not-found]
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

import app.services.redis_client as redis_client_module
from app.config import get_settings
from app.database.session import get_db
from app.models.blocked_request import BlockedRequest
from app.models.user import User
from app.services.rate_limit_config import resolve_bucket_config
from app.services.rate_limiter import TokenBucketRateLimiter
from app.services.redis_client import get_redis
from app.utils.dependencies import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

_FIXED_WINDOW_SCRIPT = """
local count = redis.call("INCR", KEYS[1])
if count == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end
return count
"""


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "127.0.0.1"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 5, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path.lower()
        if not any(target in path for target in ("login", "register", "gateway")):
            return await call_next(request)

        client_ip = get_client_ip(request)
        redis_key = f"rate_limit:{path}:{client_ip}"
        try:
            current_count = await run_in_threadpool(
                redis_client_module.get_redis().eval,
                _FIXED_WINDOW_SCRIPT,
                1,
                redis_key,
                self.window_seconds,
            )
        except Exception:
            logger.exception("Redis IP rate-limit check failed for %s; allowing request", path)
            return await call_next(request)

        logger.info("[RATE_LIMIT] Path: %s | IP: %s | Count: %s", path, client_ip, current_count)
        if current_count > self.max_requests:
            logger.warning("[RATE_LIMIT BLOCKED] %s exceeded limit on %s", client_ip, path)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Too many requests to this endpoint."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        return await call_next(request)


def rate_limited(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis),
) -> User:
    settings = get_settings()
    if not settings.rate_limit_enabled and settings.environment == "development":
        return current_user

    endpoint = request.url.path
    capacity, refill_rate = resolve_bucket_config(db, current_user.id, endpoint)

    client_ip = get_client_ip(request)
    bucket_key = f"rate_limit:{current_user.id}:{client_ip}:{endpoint}"
    limiter = TokenBucketRateLimiter(redis_client)
    try:
        result = limiter.check(bucket_key, capacity, refill_rate)
    except Exception:
        logger.exception("Redis rate-limit check failed for %s; allowing request", endpoint)
        return current_user

    if not result.allowed:
        db.add(
            BlockedRequest(
                user_id=current_user.id,
                endpoint=endpoint,
                ip_address=client_ip,
                reason="rate_limit_exceeded",
            )
        )
        db.commit()

        retry_after = max(1, int(result.retry_after_seconds) + 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for '{endpoint}'. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    return current_user
