"""
Application entrypoint.

Wires together CORS, request logging, global error handling, and the
routers as each phase adds them: Phase 4 /auth, Phase 5 /gateway,
Phase 8 /analytics and /admin.
"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_db
from app.middleware.error_handler import register_error_handlers
from app.middleware.request_logger import RequestLoggingMiddleware
from app.routes import admin, analytics, auth, gateway
from app.services.redis_client import get_redis
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

app = FastAPI(
    title="API Gateway & Rate Limiting Platform",
    version="0.1.0",
    description="A scalable API gateway with JWT auth, Redis-backed rate limiting, and analytics.",
)

# Order matters: CORS outermost, then request logging/timing.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

register_error_handlers(app)

app.include_router(auth.router)
app.include_router(gateway.router)
app.include_router(analytics.router)
app.include_router(admin.router)


@app.get("/", tags=["health"])
async def root() -> dict:
    return {"service": "api-gateway-platform", "status": "ok"}


@app.get("/health", tags=["health"])
async def health(db: Session = Depends(get_db), redis_client=Depends(get_redis)) -> dict:
    """Liveness + DB + Redis connectivity check."""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - depends on live DB
        logger.warning("DB health check failed: %s", exc)
        db_status = "unreachable"

    redis_status = "ok"
    try:
        redis_client.ping()
    except Exception as exc:  # pragma: no cover - depends on live Redis
        logger.warning("Redis health check failed: %s", exc)
        redis_status = "unreachable"

    return {
        "status": "healthy",
        "environment": settings.environment,
        "database": db_status,
        "redis": redis_status,
    }
