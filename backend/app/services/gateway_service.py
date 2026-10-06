"""
API Gateway core logic.

This is a deliberately simple "routing table" — a dict of service name
-> handler function — standing in for what would, in a real deployment,
be reverse-proxied HTTP calls to independent downstream microservices
(user-service, orders-service, etc. each on their own host:port). The
registry pattern is what matters for the portfolio piece: it's the same
shape you'd use to swap a mock handler for an httpx call to a real
service without touching the route layer at all.

Responsibilities demonstrated here (the four gateway jobs not already
covered elsewhere): routing, request validation, response-time
tracking. Authentication is enforced by the route layer via
get_current_user; global error handling is app.middleware.error_handler.
"""
import time
from collections.abc import Callable
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx

from app.config import get_settings
from app.schemas.gateway import ALLOWED_METHODS


class GatewayError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _echo_service(body: dict) -> dict:
    """Returns whatever body it was sent — useful for testing the pipeline end-to-end."""
    return {"echoed": body}


def _time_service(body: dict) -> dict:
    return {"server_time_utc": datetime.now(timezone.utc).isoformat()}


def _users_service(body: dict) -> dict:
    # Stand-in for a real user-management microservice.
    return {"message": "users-service reached", "received": body}


def _orders_service(body: dict) -> dict:
    # Stand-in for a real order-management microservice.
    return {"message": "orders-service reached", "received": body}


SERVICE_REGISTRY: dict[str, Callable[[dict], dict]] = {
    "echo": _echo_service,
    "time": _time_service,
    "users": _users_service,
    "orders": _orders_service,
}


def list_registered_services() -> list[str]:
    return sorted(SERVICE_REGISTRY.keys())


def route_request(target_service: str, method: str, path: str, body: dict | None) -> dict:
    """
    Validates and routes a single gateway request, returning a dict with
    response_time_ms and the downstream data. Raises GatewayError (with
    an appropriate status_code) for any validation or routing failure.
    """
    if method not in ALLOWED_METHODS:
        raise GatewayError(f"Unsupported HTTP method '{method}'", status_code=400)

    handler = SERVICE_REGISTRY.get(target_service)
    if handler is None:
        raise GatewayError(
            f"Unknown service '{target_service}'. Registered services: {list_registered_services()}",
            status_code=404,
        )

    start = time.perf_counter()
    service_url = get_settings().service_url_map.get(target_service)
    try:
        if service_url:
            target_url = urljoin(f"{service_url.rstrip('/')}/", path.lstrip("/"))
            response = httpx.request(method, target_url, json=body, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        else:
            data = handler(body or {})
    except httpx.RequestError as exc:
        raise GatewayError(
            f"Downstream service '{target_service}' is offline or unreachable",
            status_code=502,
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise GatewayError(
            f"Downstream service '{target_service}' returned HTTP {exc.response.status_code}",
            status_code=502,
        ) from exc
    except Exception as exc:  # downstream handler or response processing failed
        raise GatewayError(f"Downstream service '{target_service}' failed: {exc}", status_code=502) from exc
    response_time_ms = (time.perf_counter() - start) * 1000

    return {
        "service": target_service,
        "path": path,
        "method": method,
        "data": data,
        "response_time_ms": round(response_time_ms, 3),
    }
