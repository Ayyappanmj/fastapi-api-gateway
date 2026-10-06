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

from app.config import get_settings
from app.database.session import get_db
from app.models.blocked_request import BlockedRequest
from app.models.user import User
from app.services.rate_limit_config import resolve_bucket_config
from app.services.rate_limiter import TokenBucketRateLimiter
from app.services.redis_client import get_redis
from app.utils.dependencies import get_current_user


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

    bucket_key = f"rate_limit:{current_user.id}:{endpoint}"
    limiter = TokenBucketRateLimiter(redis_client)
    result = limiter.check(bucket_key, capacity, refill_rate)

    if not result.allowed:
        ip_address = request.client.host if request.client else "unknown"
        db.add(
            BlockedRequest(
                user_id=current_user.id,
                endpoint=endpoint,
                ip_address=ip_address,
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
