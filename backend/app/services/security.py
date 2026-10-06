"""
Low-level security primitives — password hashing and JWT encode/decode.

Kept separate from auth_service.py (which holds the business logic:
looking users up, creating sessions) so these pure functions are easy
to unit test and reuse anywhere a token or hash is needed.
"""
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# bcrypt: industry-standard, adaptive (tunable) cost factor, salts automatically.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: str) -> tuple[str, int]:
    """Returns (jwt_string, expires_in_seconds)."""
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire_at = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": expire_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict | None:
    """Returns the decoded payload, or None if the token is invalid/expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def generate_refresh_token() -> str:
    """
    Refresh tokens are opaque random strings, NOT JWTs. We store only a
    hash of this value in the `sessions` table (see auth_service.py), so
    a stolen DB dump doesn't hand out usable refresh tokens, and a
    single row can be revoked (logout on one device) without needing a
    JWT blocklist.
    """
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    # Refresh tokens are already 48 bytes of high-entropy randomness, so a
    # fast, non-adaptive hash (not bcrypt) is fine here and avoids the
    # unnecessary CPU cost of bcrypt on every /auth/refresh call.
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()
