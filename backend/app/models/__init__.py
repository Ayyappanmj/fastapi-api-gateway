"""
Importing this package registers every model on Base.metadata, which
Alembic's env.py and the test fixtures rely on for
`Base.metadata.create_all()` / autogenerate to see all seven tables.
"""
from app.models.user import User, UserRole
from app.models.api_key import APIKey
from app.models.session import UserSession
from app.models.rate_limit import RateLimit
from app.models.request_log import RequestLog
from app.models.blocked_request import BlockedRequest
from app.models.endpoint_stat import EndpointStat

__all__ = [
    "User",
    "UserRole",
    "APIKey",
    "UserSession",
    "RateLimit",
    "RequestLog",
    "BlockedRequest",
    "EndpointStat",
]
