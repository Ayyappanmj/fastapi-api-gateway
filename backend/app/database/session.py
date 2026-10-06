"""
Database engine and session management.

- Uses a connection pool (QueuePool, the SQLAlchemy default for non-SQLite
  URLs) so we don't open a fresh TCP connection to Postgres per request.
- `get_db` is a FastAPI dependency: it yields one session per request and
  guarantees it's closed afterward, even if the request raises.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_size=10,          # baseline connections kept open
    max_overflow=20,       # extra connections allowed under burst load
    pool_pre_ping=True,    # check connection liveness before using it
    pool_recycle=300,      # recycle connections every 5 min (avoids stale conns)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
