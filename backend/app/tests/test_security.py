"""
Phase 11 tests: unit-level coverage of app/services/security.py that the
auth integration tests (Phase 4) only exercise indirectly. These don't
touch the DB or a running app — pure functions in, assertions out.
"""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.config import get_settings
from app.services import security

settings = get_settings()
pytestmark = pytest.mark.unit


# --- password hashing ---------------------------------------------------

def test_hash_password_produces_different_hash_each_time():
    # bcrypt salts automatically — hashing the same password twice must
    # never produce the same stored value.
    hash_one = security.hash_password("Password123")
    hash_two = security.hash_password("Password123")
    assert hash_one != hash_two
    assert security.verify_password("Password123", hash_one)
    assert security.verify_password("Password123", hash_two)


def test_verify_password_rejects_empty_string():
    hashed = security.hash_password("RealPassword1")
    assert security.verify_password("", hashed) is False


# --- access tokens ---------------------------------------------------

def test_access_token_round_trip():
    token, expires_in = security.create_access_token(subject="user-123", role="admin")
    assert expires_in == settings.access_token_expire_minutes * 60

    payload = security.decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_decode_access_token_rejects_garbage():
    assert security.decode_access_token("not.a.valid.token") is None


def test_decode_access_token_rejects_expired_token():
    # Build a token that expired 1 second ago, bypassing create_access_token's
    # settings-driven expiry so this test doesn't depend on sleeping for real.
    expired_payload = {
        "sub": "user-123",
        "role": "user",
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    assert security.decode_access_token(expired_token) is None


def test_decode_access_token_rejects_wrong_token_type():
    # A refresh-flavored JWT (if someone ever encoded one) must not be
    # accepted where an access token is expected.
    payload = {
        "sub": "user-123",
        "role": "user",
        "type": "refresh",  # wrong type
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    assert security.decode_access_token(token) is None


def test_decode_access_token_rejects_wrong_signing_key():
    payload = {
        "sub": "user-123",
        "role": "user",
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, "a-totally-different-secret", algorithm=settings.jwt_algorithm)
    assert security.decode_access_token(token) is None


# --- refresh tokens ---------------------------------------------------

def test_generate_refresh_token_is_unique_and_high_entropy():
    tokens = {security.generate_refresh_token() for _ in range(50)}
    assert len(tokens) == 50  # no collisions in 50 draws
    assert all(len(t) > 40 for t in tokens)


def test_hash_refresh_token_is_deterministic_and_one_way():
    raw = security.generate_refresh_token()
    hash_a = security.hash_refresh_token(raw)
    hash_b = security.hash_refresh_token(raw)
    assert hash_a == hash_b  # same input -> same hash, so DB lookup by hash works
    assert hash_a != raw  # never store the raw token itself


@pytest.mark.parametrize("raw_a,raw_b", [("token-one", "token-two")])
def test_hash_refresh_token_differs_for_different_input(raw_a, raw_b):
    assert security.hash_refresh_token(raw_a) != security.hash_refresh_token(raw_b)
