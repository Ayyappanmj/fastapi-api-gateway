"""
Phase 5 tests: the gateway routes incoming requests, validates them,
requires authentication, and reports response time.
"""
import pytest

pytestmark = pytest.mark.integration


def register_and_login(client, email="gateway@example.com"):
    client.post(
        "/auth/register",
        json={"email": email, "password": "Password123", "full_name": "Gateway User"},
    )
    tokens = client.post("/auth/login", json={"email": email, "password": "Password123"}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# --- authentication enforcement ---------------------------------------------

def test_gateway_request_requires_auth(client):
    response = client.post("/gateway/request", json={"target_service": "echo"})
    assert response.status_code == 401


def test_gateway_status_requires_auth(client):
    response = client.get("/gateway/status")
    assert response.status_code == 401


# --- routing -----------------------------------------------------------------

def test_gateway_routes_to_echo_service(client):
    headers = register_and_login(client)
    response = client.post(
        "/gateway/request",
        json={"target_service": "echo", "method": "POST", "path": "/anything", "body": {"hello": "world"}},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["service"] == "echo"
    assert body["meta"]["method"] == "POST"
    assert body["data"]["echoed"] == {"hello": "world"}


def test_gateway_routes_to_users_service(client):
    headers = register_and_login(client)
    response = client.post(
        "/gateway/request",
        json={"target_service": "users", "method": "GET"},
        headers=headers,
    )
    assert response.status_code == 200
    assert "users-service" in response.json()["data"]["message"]


def test_gateway_returns_502_when_configured_service_is_unreachable(monkeypatch):
    import httpx
    import pytest

    from app.config import Settings
    from app.services import gateway_service
    from app.services.gateway_service import GatewayError

    monkeypatch.setattr(
        gateway_service,
        "get_settings",
        lambda: Settings(echo_service_url="http://echo.invalid"),
    )

    def raise_connect_error(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(gateway_service.httpx, "request", raise_connect_error)

    with pytest.raises(GatewayError) as error:
        gateway_service.route_request("echo", "POST", "/anything", {"ping": True})

    assert error.value.status_code == 502
    assert "echo" in error.value.message
    assert "unreachable" in error.value.message


def test_gateway_status_lists_registered_services(client):
    headers = register_and_login(client)
    response = client.get("/gateway/status", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["gateway"] == "operational"
    assert "echo" in body["registered_services"]
    assert "users" in body["registered_services"]
    assert body["requested_by"] == "gateway@example.com"


# --- validation ----------------------------------------------------------

def test_gateway_rejects_unknown_service(client):
    headers = register_and_login(client)
    response = client.post(
        "/gateway/request", json={"target_service": "nonexistent"}, headers=headers
    )
    assert response.status_code == 404


def test_gateway_rejects_unsupported_method(client):
    headers = register_and_login(client)
    response = client.post(
        "/gateway/request",
        json={"target_service": "echo", "method": "TRACE"},
        headers=headers,
    )
    # Pydantic's field_validator rejects this before it ever reaches routing logic.
    assert response.status_code == 422


def test_gateway_rejects_path_without_leading_slash(client):
    headers = register_and_login(client)
    response = client.post(
        "/gateway/request",
        json={"target_service": "echo", "path": "no-leading-slash"},
        headers=headers,
    )
    assert response.status_code == 422


# --- response time tracking ------------------------------------------------

def test_gateway_response_includes_response_time(client):
    headers = register_and_login(client)
    response = client.post("/gateway/request", json={"target_service": "time"}, headers=headers)
    assert response.status_code == 200
    meta = response.json()["meta"]
    assert meta["response_time_ms"] >= 0
    assert "server_time_utc" in response.json()["data"]
