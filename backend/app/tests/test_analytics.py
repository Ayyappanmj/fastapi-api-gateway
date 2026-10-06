"""
Phase 8 tests: analytics aggregation reflects actual request_logs data,
and every /analytics/* route is admin-only.
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

    # Re-login so the fresh access token's embedded role claim is "admin",
    # not the "user" role baked into the token issued before the promotion.
    tokens = client.post("/auth/login", json={"email": email, "password": "Password123"}).json()
    return tokens, {"Authorization": f"Bearer {tokens['access_token']}"}


# --- RBAC --------------------------------------------------------------

def test_overview_requires_authentication(client):
    assert client.get("/analytics/overview").status_code == 401


def test_overview_rejects_non_admin(client):
    _, headers = register_and_login(client, "user@example.com")
    response = client.get("/analytics/overview", headers=headers)
    assert response.status_code == 403


def test_overview_allows_admin(client, db_session):
    _, headers = make_admin(client, db_session)
    response = client.get("/analytics/overview", headers=headers)
    assert response.status_code == 200


def test_admin_logs_requires_admin(client):
    _, headers = register_and_login(client, "plain@example.com")
    response = client.get("/admin/logs", headers=headers)
    assert response.status_code == 403


# --- overview aggregation ----------------------------------------------

def test_overview_counts_requests_in_window(client, db_session):
    _, admin_headers = make_admin(client, db_session)
    _, user_headers = register_and_login(client, "traffic@example.com")

    # Generate some traffic: 3 gateway requests (success), 1 bad request (422->fail)
    for _ in range(3):
        client.post("/gateway/request", json={"target_service": "echo"}, headers=user_headers)
    client.post("/gateway/request", json={"target_service": "nonexistent"}, headers=user_headers)  # 404

    response = client.get("/analytics/overview?hours=24", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()

    assert body["total_requests"] >= 4
    assert body["failed_requests"] >= 1
    assert body["successful_requests"] >= 3
    assert body["active_users"] >= 1
    assert body["error_rate_percent"] >= 0


def test_overview_window_excludes_old_requests(client, db_session):
    from datetime import datetime, timedelta, timezone

    from app.models.request_log import RequestLog

    _, admin_headers = make_admin(client, db_session)

    # Insert a request_log row timestamped 3 days ago directly, bypassing
    # the middleware (which always stamps "now") so we can control it.
    db_session.add(
        RequestLog(
            user_id=None,
            endpoint="/gateway/request",
            method="GET",
            status_code=200,
            response_time_ms=10,
            ip_address="127.0.0.1",
            timestamp=datetime.now(timezone.utc) - timedelta(days=3),
        )
    )
    db_session.commit()

    total_rows_all_time = db_session.query(RequestLog).count()
    response = client.get("/analytics/overview?hours=1", headers=admin_headers)
    body = response.json()

    assert body["window_hours"] == 1
    # The 3-day-old row inflates the all-time count but must not be
    # counted in a 1-hour window.
    assert body["total_requests"] < total_rows_all_time


# --- traffic buckets ------------------------------------------------------

def test_traffic_hourly_has_requested_bucket_count(client, db_session):
    _, admin_headers = make_admin(client, db_session)
    response = client.get("/analytics/traffic?granularity=hourly&hours=6", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["granularity"] == "hourly"
    assert len(body["points"]) == 6


def test_traffic_daily_has_requested_bucket_count(client, db_session):
    _, admin_headers = make_admin(client, db_session)
    response = client.get("/analytics/traffic?granularity=daily&days=5", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["granularity"] == "daily"
    assert len(body["points"]) == 5


def test_traffic_rejects_bad_granularity(client, db_session):
    _, admin_headers = make_admin(client, db_session)
    response = client.get("/analytics/traffic?granularity=weekly", headers=admin_headers)
    assert response.status_code == 422  # caught by Query's pattern constraint


# --- endpoint breakdown -----------------------------------------------

def test_endpoints_breakdown_reports_known_endpoint(client, db_session):
    _, admin_headers = make_admin(client, db_session)
    _, user_headers = register_and_login(client, "breakdown@example.com")

    client.post("/gateway/request", json={"target_service": "echo"}, headers=user_headers)
    client.post("/gateway/request", json={"target_service": "echo"}, headers=user_headers)

    response = client.get("/analytics/endpoints", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()

    endpoints_seen = {row["endpoint"] for row in body["top_endpoints"]}
    assert "/gateway/request" in endpoints_seen

    gateway_row = next(r for r in body["top_endpoints"] if r["endpoint"] == "/gateway/request")
    assert gateway_row["total_requests"] >= 2


def test_endpoints_breakdown_lists_active_user(client, db_session):
    _, admin_headers = make_admin(client, db_session)
    _, user_headers = register_and_login(client, "activeuser@example.com")

    client.post("/gateway/request", json={"target_service": "echo"}, headers=user_headers)

    response = client.get("/analytics/endpoints", headers=admin_headers)
    body = response.json()
    emails = {u["email"] for u in body["most_active_users"]}
    assert "activeuser@example.com" in emails
