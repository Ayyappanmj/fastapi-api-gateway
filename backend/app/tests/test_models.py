"""
Phase 3 tests: verify each model can be created, relationships resolve,
and the constraints declared in Phase 3 (unique, FK) are actually
enforced by the DB — not just present in the Python class.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration

from app.models import (
    APIKey,
    BlockedRequest,
    EndpointStat,
    RateLimit,
    RequestLog,
    User,
    UserRole,
    UserSession,
)


def make_user(db_session, email="jane@example.com", role=UserRole.USER) -> User:
    user = User(email=email, hashed_password="bcrypt$fakehash", role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_user_defaults(db_session):
    user = make_user(db_session)
    assert user.id is not None
    assert user.is_active is True
    assert user.role == UserRole.USER


def test_user_email_must_be_unique(db_session):
    make_user(db_session, email="dupe@example.com")
    db_session.add(User(email="dupe@example.com", hashed_password="x"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_api_key_relationship(db_session):
    user = make_user(db_session, email="apikey@example.com")
    key = APIKey(user_id=user.id, name="CI key", key_hash="hash123", key_prefix="gw_live_a1b2")
    db_session.add(key)
    db_session.commit()
    db_session.refresh(user)

    assert len(user.api_keys) == 1
    assert user.api_keys[0].key_prefix == "gw_live_a1b2"


def test_session_requires_valid_user_fk(db_session):
    session = UserSession(
        user_id="nonexistent-id",
        refresh_token_hash="hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(session)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_rate_limit_unique_per_user_and_endpoint(db_session):
    user = make_user(db_session, email="limits@example.com")
    db_session.add(RateLimit(user_id=user.id, endpoint="/gateway/request", bucket_capacity=50))
    db_session.commit()

    db_session.add(RateLimit(user_id=user.id, endpoint="/gateway/request", bucket_capacity=999))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_request_log_survives_user_deletion(db_session):
    user = make_user(db_session, email="deleteme@example.com")
    log = RequestLog(
        user_id=user.id,
        endpoint="/gateway/request",
        method="POST",
        status_code=200,
        response_time_ms=42,
        ip_address="127.0.0.1",
    )
    db_session.add(log)
    db_session.commit()

    db_session.delete(user)
    db_session.commit()
    db_session.refresh(log)

    assert log.user_id is None  # ON DELETE SET NULL, not a cascade delete


def test_blocked_request_and_endpoint_stats_creation(db_session):
    blocked = BlockedRequest(endpoint="/gateway/request", ip_address="10.0.0.5")
    stat = EndpointStat(endpoint="/gateway/request", method="POST", date=datetime.now(timezone.utc).date())
    db_session.add_all([blocked, stat])
    db_session.commit()

    assert blocked.reason == "rate_limit_exceeded"
    assert stat.total_requests == 0
