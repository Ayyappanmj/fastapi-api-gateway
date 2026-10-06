"""
Phase 4 tests: registration, login, password hashing, protected routes,
refresh-token rotation, and role-based access control.
"""
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.models.session import UserSession
from app.models.user import User, UserRole
from app.services.security import hash_password, hash_refresh_token, verify_password

pytestmark = pytest.mark.integration


def register(client, email="test@example.com", password="Password123", full_name="Test User"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )


def login(client, email="test@example.com", password="Password123"):
    return client.post("/auth/login", json={"email": email, "password": password})


# --- password hashing -------------------------------------------------------

def test_password_hash_and_verify_roundtrip():
    hashed = hash_password("Password123")
    assert hashed != "Password123"
    assert verify_password("Password123", hashed) is True
    assert verify_password("WrongPassword", hashed) is False


# --- register ----------------------------------------------------------------

def test_register_creates_user(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "test@example.com"
    assert body["role"] == "user"
    assert "hashed_password" not in body  # never leak the hash


def test_register_rejects_duplicate_email(client):
    register(client)
    response = register(client)
    assert response.status_code == 409


def test_register_rejects_weak_password(client):
    response = client.post(
        "/auth/register",
        json={"email": "weak@example.com", "password": "short", "full_name": "X"},
    )
    assert response.status_code == 422


# --- login ---------------------------------------------------------------

def test_login_returns_tokens(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "test@example.com"


def test_login_rejects_wrong_password(client):
    register(client)
    response = login(client, password="WrongPassword1")
    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = login(client, email="nobody@example.com")
    assert response.status_code == 401


def test_login_rejects_inactive_user(client, db_session):
    register(client)
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    user.is_active = False
    db_session.commit()

    response = login(client)
    assert response.status_code == 401


# --- protected routes ---------------------------------------------------

def test_me_requires_authentication(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token(client):
    register(client)
    tokens = login(client).json()

    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_me_rejects_garbage_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


# --- refresh flow --------------------------------------------------------

def test_refresh_issues_new_access_token(client):
    register(client)
    tokens = login(client).json()

    time.sleep(1)
    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


def test_refresh_token_cannot_be_reused_after_rotation(client):
    register(client)
    tokens = login(client).json()

    first = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200

    # Same (now-revoked) refresh token used again must fail.
    second = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert second.status_code == 401


def test_refresh_rejects_expired_naive_database_timestamp(client, db_session):
    register(client)
    tokens = login(client).json()
    session = db_session.query(UserSession).filter(
        UserSession.refresh_token_hash == hash_refresh_token(tokens["refresh_token"])
    ).first()
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    db_session.expire(session, ["expires_at"])

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401
    assert response.json()["error"] == "Refresh token has expired"


def test_refresh_rejects_garbage_token(client):
    response = client.post("/auth/refresh", json={"refresh_token": "not-a-real-refresh-token"})
    assert response.status_code == 401


# --- RBAC ------------------------------------------------------------------

def test_require_role_blocks_non_admin(client, db_session):
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from app.utils.dependencies import require_role

    # Small isolated app just to exercise the dependency in unit-test
    # fashion; real admin routes land in Phase 8 and reuse this same
    # require_role() dependency directly on their router.
    probe_app = FastAPI()

    @probe_app.get("/admin-only")
    def admin_only(user=Depends(require_role(UserRole.ADMIN))):
        return {"ok": True}

    from app.database.session import get_db

    probe_app.dependency_overrides[get_db] = lambda: db_session
    probe_client = TestClient(probe_app)

    register(client)
    tokens = login(client).json()

    response = probe_client.get(
        "/admin-only", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 403


def test_require_role_allows_admin(client, db_session):
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from app.utils.dependencies import require_role

    probe_app = FastAPI()

    @probe_app.get("/admin-only")
    def admin_only(user=Depends(require_role(UserRole.ADMIN))):
        return {"ok": True}

    from app.database.session import get_db

    probe_app.dependency_overrides[get_db] = lambda: db_session
    probe_client = TestClient(probe_app)

    register(client, email="boss@example.com")
    user = db_session.query(User).filter(User.email == "boss@example.com").first()
    user.role = UserRole.ADMIN
    db_session.commit()

    tokens = login(client, email="boss@example.com").json()
    response = probe_client.get(
        "/admin-only", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
