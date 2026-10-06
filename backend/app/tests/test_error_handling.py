"""
Phase 11 tests: app/middleware/error_handler.py's handlers are each hit
somewhere in the existing suite indirectly (422 via bad request bodies,
401/403/404/429 via auth/gateway/rate-limiter tests) except the
catch-all Exception handler — nothing in the app deliberately raises a
bare Exception, so it's never been exercised. This file forces that
path with a throwaway route on a fresh FastAPI app that shares the
real app's exception handlers.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.error_handler import register_error_handlers


def _make_probe_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise RuntimeError("something went genuinely wrong")

    return app


def test_unhandled_exception_returns_generic_500_without_leaking_details():
    client = TestClient(_make_probe_app(), raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "Internal server error"
    # The real exception message/type/traceback must never reach the client.
    assert "RuntimeError" not in response.text
    assert "something went genuinely wrong" not in response.text


def test_validation_error_response_shape(client):
    # Reuses the real app (via the `client` fixture) for a request that
    # trips Pydantic validation, to confirm the envelope shape end-to-end.
    response = client.post("/auth/register", json={"email": "not-an-email", "password": "short"})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "Validation failed"
    assert "detail" in body


def test_404_on_unknown_route_still_uses_error_envelope(client):
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
