"""
App-level smoke tests: the app object builds, root route responds, and
(using the full `client` fixture, which overrides get_db/get_redis)
/health reports both dependencies as reachable.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.integration

_bare_client = TestClient(app)


def test_root_returns_ok():
    response = _bare_client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_app_has_expected_routes():
    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/health" in paths
    assert "/auth/login" in paths
    assert "/gateway/request" in paths
    assert "/analytics/overview" in paths
    assert "/admin/users" in paths


def test_health_reports_db_and_redis_ok_with_test_overrides(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database"] == "ok"
    assert body["redis"] == "ok"
