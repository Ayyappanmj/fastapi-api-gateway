"""
Shared pytest fixtures.

Uses a temp-file SQLite DB for tests instead of Postgres so the test
suite runs anywhere with zero external services — CI included.
File-based (not :memory:+StaticPool) specifically because Phase 7's
logging middleware opens its own DB session independently of the
`get_db`-overridden one the route code uses; two independent SQLAlchemy
sessions need two independently-functioning connections, which a
single shared in-memory connection can't safely give them. A real
file on disk lets SQLite's normal connection pooling handle that.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base import Base


@pytest.fixture()
def db_engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    # SQLite ignores FK constraints unless explicitly told to enforce them;
    # Postgres (used in real environments) enforces them by default.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def fake_redis():
    from app.tests.fake_redis import FakeRedis

    return FakeRedis()


@pytest.fixture()
def client(db_engine, db_session, fake_redis, monkeypatch):
    """
    TestClient wired to test infrastructure everywhere the app touches
    the outside world:
    - `get_db` dependency -> the same session used by db_session
    - `get_redis` dependency -> a fresh FakeRedis
    - app.database.session.SessionLocal -> a sessionmaker bound to the
      same test engine, so the request-logging middleware (which opens
      its own session directly, outside FastAPI's Depends system,
      since Starlette middleware isn't part of that DI graph) persists
      into the same database the test can assert against.
    """
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.database.session import get_db
    from app.main import app
    from app.services.redis_client import get_redis

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    monkeypatch.setattr("app.database.session.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(
        "app.middleware.rate_limit.get_settings",
        lambda: Settings(environment="test", rate_limit_enabled=True),
    )

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    monkeypatch.setattr("app.services.redis_client.get_redis", lambda: fake_redis)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def fresh_session(db_engine):
    """
    A brand-new session bound to the same test engine, independent of
    db_session's open transaction/identity map. Use this in tests that
    need to see what the logging middleware (a separate session) wrote,
    to avoid stale-identity-map surprises from querying through
    db_session right after the app wrote via a different session.
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
