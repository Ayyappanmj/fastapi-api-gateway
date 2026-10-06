"""
Phase 8 tests: /admin/users, /admin/logs, /admin/blocked — pagination,
filtering, and admin-only access.
"""
import pytest

from app.models.user import User, UserRole

pytestmark = pytest.mark.integration


def register_and_login(client, email, password="Password123"):
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "X"})
    tokens = client.post("/auth/login", json={"email": email, "password": password}).json()
    return tokens, {"Authorization": f"Bearer {tokens['access_token']}"}


def make_admin(client, db_session, email="admin@example.com"):
    register_and_login(client, email)
    user = db_session.query(User).filter(User.email == email).first()
    user.role = UserRole.ADMIN
    db_session.commit()
    tokens = client.post("/auth/login", json={"email": email, "password": "Password123"}).json()
    return tokens, {"Authorization": f"Bearer {tokens['access_token']}"}


# --- RBAC --------------------------------------------------------------

def test_admin_users_requires_admin(client):
    _, headers = register_and_login(client, "notadmin@example.com")
    assert client.get("/admin/users", headers=headers).status_code == 403


def test_admin_blocked_requires_admin(client):
    _, headers = register_and_login(client, "notadmin2@example.com")
    assert client.get("/admin/blocked", headers=headers).status_code == 403


# --- /admin/users --------------------------------------------------------

def test_admin_users_lists_all_users_paginated(client, db_session):
    _, admin_headers = make_admin(client, db_session)
    register_and_login(client, "userA@example.com")
    register_and_login(client, "userB@example.com")

    response = client.get("/admin/users?page=1&page_size=2", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    assert body["total"] >= 3  # admin + userA + userB

    for item in body["items"]:
        assert "hashed_password" not in item


# --- /admin/logs ------------------------------------------------------

def test_admin_logs_returns_entries(client, db_session):
    _, admin_headers = make_admin(client, db_session)
    _, user_headers = register_and_login(client, "loggeduser@example.com")
    client.post("/gateway/request", json={"target_service": "echo"}, headers=user_headers)

    response = client.get("/admin/logs?page=1&page_size=50", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["endpoint"] == "/gateway/request" for item in body["items"])


def test_admin_logs_filters_by_endpoint(client, db_session):
    _, admin_headers = make_admin(client, db_session)
    _, user_headers = register_and_login(client, "filtereduser@example.com")
    client.post("/gateway/request", json={"target_service": "echo"}, headers=user_headers)
    client.get("/gateway/status", headers=user_headers)

    response = client.get("/admin/logs?endpoint=/gateway/status", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert all(item["endpoint"] == "/gateway/status" for item in body["items"])
    assert body["total"] >= 1


# --- /admin/blocked -----------------------------------------------------

def test_admin_blocked_returns_rate_limited_entries(client, db_session):
    from app.models.rate_limit import RateLimit

    _, admin_headers = make_admin(client, db_session)
    _, user_headers = register_and_login(client, "blockeduser@example.com")

    user = db_session.query(User).filter(User.email == "blockeduser@example.com").first()
    db_session.add(
        RateLimit(user_id=user.id, endpoint="/gateway/request", bucket_capacity=1, refill_rate_per_sec=0.0001)
    )
    db_session.commit()

    client.post("/gateway/request", json={"target_service": "echo"}, headers=user_headers)
    client.post("/gateway/request", json={"target_service": "echo"}, headers=user_headers)  # blocked

    response = client.get("/admin/blocked", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["items"][0]["reason"] == "rate_limit_exceeded"
