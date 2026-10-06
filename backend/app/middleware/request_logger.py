"""
Request timing + access logging + persistence middleware.

Phase 2 added stdout logging and the X-Process-Time-Ms header. Phase 7
adds the other half: writing a row into `request_logs` (Phase 3's
model) for every request, so the analytics dashboard (Phase 8) has
real data to aggregate — user id, endpoint, method, status code,
response time, IP, and timestamp, exactly as the spec's Logging
section lists.

This stays Starlette ASGI middleware (not a FastAPI dependency) because
it needs to run around *every* request, including ones that 404 or
raise before any route's dependencies execute. That means it sits
outside FastAPI's Depends() graph, so it can't take get_db as a
parameter — instead it opens its own short-lived session via
app.database.session.SessionLocal(), referenced through the module
(not imported by name) specifically so tests can monkeypatch
`app.database.session.SessionLocal` to point at the test engine (see
app/tests/conftest.py).
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.database import session as db_session_module
from app.models.request_log import RequestLog
from app.services.security import decode_access_token
from app.utils.logger import get_logger

logger = get_logger("access")

# Framework/docs routes aren't meaningful "gateway traffic" — excluding them
# keeps request_logs focused on what the analytics dashboard actually cares about.
_EXCLUDED_PREFIXES = ("/docs", "/redoc", "/openapi.json")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            "%s %s status=%s duration_ms=%.2f ip=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            client_ip,
        )

        if not request.url.path.startswith(_EXCLUDED_PREFIXES):
            self._persist(request, response, duration_ms, client_ip)

        return response

    @staticmethod
    def _extract_user_id(request: Request) -> str | None:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return None
        token = auth_header.split(" ", 1)[1]
        payload = decode_access_token(token)
        return payload.get("sub") if payload else None

    def _persist(
        self, request: Request, response: Response, duration_ms: float, client_ip: str
    ) -> None:
        # Synchronous DB call inside an async middleware: acceptable at this
        # project's scale (one small insert per request). A high-throughput
        # production gateway would offload this to a background task queue
        # or an async session instead of blocking the event loop here.
        db = db_session_module.SessionLocal()
        try:
            db.add(
                RequestLog(
                    user_id=self._extract_user_id(request),
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=int(duration_ms),
                    ip_address=client_ip,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to persist request log for %s %s", request.method, request.url.path)
        finally:
            db.close()
