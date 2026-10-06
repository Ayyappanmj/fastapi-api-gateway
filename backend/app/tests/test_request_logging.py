"""
Phase 7 tests: the logging middleware persists a request_logs row for
every request, with user id, endpoint, method, status code, response
time, and IP address — and excludes docs/openapi noise.
"""
import pytest

from app.models.request_log import RequestLog

pytestmark = pytest.mark.integration


def register_and_login(client, email="logging@example.com"):
    client.post(
        "/auth/register",
        json={"email": email, "password": "Password123", "full_name": "Log User"},
    )
    tokens = client.post("/auth/login", json={"email": email, "password": "Password123"}).json()
    return tokens, {"Authorization": f"Bearer {tokens['access_token']}"}


def test_unauthenticated_request_is_logged_with_null_user(client, fresh_session):
    client.get("/health")

    logs = fresh_session.query(RequestLog).filter(RequestLog.endpoint == "/health").all()
    assert len(logs) == 1
    assert logs[0].user_id is None
    assert logs[0].method == "GET"
    assert logs[0].status_code == 200
    assert logs[0].response_time_ms >= 0
    assert logs[0].ip_address  # not empty


def test_authenticated_request_is_logged_with_user_id(client, fresh_session):
    tokens, headers = register_and_login(client)
    client.get("/auth/me", headers=headers)

    logs = fresh_session.query(RequestLog).filter(RequestLog.endpoint == "/auth/me").all()
    assert len(logs) == 1
    assert logs[0].user_id == tokens["user"]["id"]


def test_gateway_request_is_logged(client, fresh_session):
    _, headers = register_and_login(client, email="gatewaylog@example.com")
    client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)

    logs = fresh_session.query(RequestLog).filter(RequestLog.endpoint == "/gateway/request").all()
    assert len(logs) == 1
    assert logs[0].method == "POST"
    assert logs[0].status_code == 200


def test_failed_request_is_logged_with_error_status(client, fresh_session):
    client.get("/auth/me")  # no auth header -> 401

    logs = fresh_session.query(RequestLog).filter(RequestLog.endpoint == "/auth/me").all()
    assert len(logs) == 1
    assert logs[0].status_code == 401


def test_each_request_gets_its_own_log_row(client, fresh_session):
    client.get("/health")
    client.get("/health")
    client.get("/health")

    logs = fresh_session.query(RequestLog).filter(RequestLog.endpoint == "/health").all()
    assert len(logs) == 3


def test_docs_routes_are_not_logged(client, fresh_session):
    client.get("/openapi.json")

    logs = fresh_session.query(RequestLog).filter(RequestLog.endpoint == "/openapi.json").all()
    assert len(logs) == 0
