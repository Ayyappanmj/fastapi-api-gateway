"""
Resolves which token-bucket settings apply to a given (user, endpoint)
pair: an endpoint-specific override in the `rate_limits` table wins,
then the user's account-wide default row (endpoint IS NULL), then the
application-wide defaults from settings. This is what makes "different
limits per user" possible — an admin can insert a row giving one user
a bigger bucket without touching code.
"""
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.rate_limit import RateLimit

settings = get_settings()


def resolve_bucket_config(db: Session, user_id: str, endpoint: str) -> tuple[int, float]:
    """Returns (capacity, refill_rate_per_sec) for this user + endpoint."""
    override = (
        db.query(RateLimit)
        .filter(RateLimit.user_id == user_id, RateLimit.endpoint == endpoint)
        .first()
    )
    if override:
        return override.bucket_capacity, override.refill_rate_per_sec

    account_default = (
        db.query(RateLimit)
        .filter(RateLimit.user_id == user_id, RateLimit.endpoint.is_(None))
        .first()
    )
    if account_default:
        return account_default.bucket_capacity, account_default.refill_rate_per_sec

    return settings.default_rate_limit_tokens, settings.default_rate_limit_refill_per_sec
