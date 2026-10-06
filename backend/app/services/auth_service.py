"""
Auth business logic: registration, login, and the refresh-token flow.

Route handlers (app/routes/auth.py) stay thin and just call these
functions, so the logic here is unit-testable without spinning up
FastAPI's request/response cycle.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.session import UserSession
from app.models.user import User
from app.services.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

settings = get_settings()


class AuthError(Exception):
    """Raised for any auth failure the route layer should turn into a 4xx."""


def register_user(db: Session, email: str, password: str, full_name: str | None) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise AuthError("An account with this email already exists")

    user = User(email=email, hashed_password=hash_password(password), full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _issue_session_and_tokens(
    db: Session, user: User, ip_address: str | None, user_agent: str | None
) -> dict:
    access_token, expires_in = create_access_token(subject=user.id, role=user.role.value)

    raw_refresh_token = generate_refresh_token()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(raw_refresh_token),
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh_token,
        "expires_in": expires_in,
        "user": user,
    }


def authenticate_user(
    db: Session, email: str, password: str, ip_address: str | None = None, user_agent: str | None = None
) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password")
    if not user.is_active:
        raise AuthError("This account has been deactivated")

    return _issue_session_and_tokens(db, user, ip_address, user_agent)


def refresh_access_token(db: Session, raw_refresh_token: str) -> dict:
    token_hash = hash_refresh_token(raw_refresh_token)
    session = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()

    if not session or session.is_revoked:
        raise AuthError("Invalid or revoked refresh token")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise AuthError("Refresh token has expired")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        raise AuthError("Account is no longer active")

    # Rotate: revoke the used refresh token and issue a brand-new pair.
    # Rotation limits the damage if a refresh token is ever intercepted,
    # since a stolen token only works once before the legitimate client's
    # next refresh call would reveal the reuse (out of scope here, but the
    # rotation itself is the important half).
    session.is_revoked = True
    db.add(session)
    db.commit()

    return _issue_session_and_tokens(db, user, session.ip_address, session.user_agent)
