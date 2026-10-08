"""
Phase 6 tests: the token bucket algorithm itself (unit-level, against
FakeRedis), and the full rate-limited /gateway/request flow
(integration-level, through the FastAPI TestClient).
"""
from starlette.requests import Request

from app.middleware.rate_limit import get_client_ip
from app.models.blocked_request import BlockedRequest
from app.services.rate_limiter import TokenBucketRateLimiter
from app.tests.fake_redis import FakeRedis


def make_request(headers=None, client=("127.0.0.1", 1234)):
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers or [],
            "client": client,
            "server": ("testserver", 80),
        }
    )


def test_get_client_ip_prefers_first_forwarded_address():
    request = make_request(headers=[(b"x-forwarded-for", b"203.0.113.5, 10.0.0.1")])

    assert get_client_ip(request) == "203.0.113.5"


def test_get_client_ip_falls_back_to_socket_address():
    assert get_client_ip(make_request()) == "127.0.0.1"
    assert get_client_ip(make_request(client=None)) == "127.0.0.1"


def test_fixed_window_counter_expires_after_window(monkeypatch):
    import app.tests.fake_redis as fake_redis_module

    current_time = {"now": 1000.0}
    monkeypatch.setattr(fake_redis_module.time, "time", lambda: current_time["now"])
    client = FakeRedis()

    assert client.eval("fixed-window", 1, "counter", 60) == 1
    assert client.eval("fixed-window", 1, "counter", 60) == 2
    current_time["now"] += 60
    assert client.eval("fixed-window", 1, "counter", 60) == 1


def register_and_login(client, email="ratelimit@example.com"):
    client.post(
        "/auth/register",
        json={"email": email, "password": "Password123", "full_name": "RL User"},
    )
    tokens = client.post("/auth/login", json={"email": email, "password": "Password123"}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# --- token bucket algorithm (unit-level) ------------------------------------

def test_bucket_starts_full_and_allows_up_to_capacity(fake_redis):
    limiter = TokenBucketRateLimiter(fake_redis)
    for _ in range(5):
        result = limiter.check("bucket:a", capacity=5, refill_rate=1.0)
        assert result.allowed is True

    # 6th request with an empty bucket and no time elapsed must be denied.
    result = limiter.check("bucket:a", capacity=5, refill_rate=1.0)
    assert result.allowed is False
    assert result.retry_after_seconds > 0


def test_bucket_refills_over_time(fake_redis, monkeypatch):
    import app.services.rate_limiter as rate_limiter_module

    current_time = {"now": 1_000_000.0}
    monkeypatch.setattr(rate_limiter_module.time, "time", lambda: current_time["now"])

    limiter = TokenBucketRateLimiter(fake_redis)
    # Drain the bucket (capacity 2).
    assert limiter.check("bucket:b", capacity=2, refill_rate=1.0).allowed is True
    assert limiter.check("bucket:b", capacity=2, refill_rate=1.0).allowed is True
    assert limiter.check("bucket:b", capacity=2, refill_rate=1.0).allowed is False

    # Advance the clock by 1.5s at refill_rate=1/s -> 1 token available.
    current_time["now"] += 1.5
    result = limiter.check("bucket:b", capacity=2, refill_rate=1.0)
    assert result.allowed is True


def test_bucket_never_exceeds_capacity(fake_redis, monkeypatch):
    import app.services.rate_limiter as rate_limiter_module

    current_time = {"now": 1_000_000.0}
    monkeypatch.setattr(rate_limiter_module.time, "time", lambda: current_time["now"])

    limiter = TokenBucketRateLimiter(fake_redis)
    limiter.check("bucket:c", capacity=3, refill_rate=10.0)  # consumes 1, leaves 2

    # Advance the clock by a huge amount — refill should cap at capacity, not overflow.
    current_time["now"] += 1000
    result = limiter.check("bucket:c", capacity=3, refill_rate=10.0)
    assert result.allowed is True
    assert result.tokens_remaining <= 3


def test_different_buckets_are_independent(fake_redis):
    limiter = TokenBucketRateLimiter(fake_redis)
    limiter.check("bucket:user1", capacity=1, refill_rate=1.0)
    result = limiter.check("bucket:user1", capacity=1, refill_rate=1.0)
    assert result.allowed is False

    # A different key must have its own full bucket, unaffected by user1's.
    other = limiter.check("bucket:user2", capacity=1, refill_rate=1.0)
    assert other.allowed is True


# --- integration: /gateway/request enforcement ------------------------------

def test_gateway_request_allowed_within_limit(client, db_session):
    from app.models.rate_limit import RateLimit
    from app.models.user import User

    headers = register_and_login(client)
    user = db_session.query(User).filter(User.email == "ratelimit@example.com").first()
    db_session.add(RateLimit(user_id=user.id, endpoint="/gateway/request", bucket_capacity=3, refill_rate_per_sec=0.001))
    db_session.commit()

    response = client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)
    assert response.status_code == 200


def test_gateway_request_fails_open_when_redis_check_fails(client, monkeypatch):
    headers = register_and_login(client, email="redis-error@example.com")

    def fail_check(self, key, capacity, refill_rate, cost=1.0):
        raise ConnectionError("Redis unavailable")

    monkeypatch.setattr(TokenBucketRateLimiter, "check", fail_check)

    response = client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)

    assert response.status_code == 200


def test_ip_fixed_window_limiter_returns_429_after_five_requests(client):
    headers = {
        "X-Forwarded-For": "203.0.113.10",
        "Origin": "https://fastapi-gateway-frontend.onrender.com",
        **register_and_login(client, email="fixed-window@example.com"),
    }
    responses = [
        client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)
        for _ in range(6)
    ]

    assert [response.status_code for response in responses] == [200, 200, 200, 200, 200, 429]
    assert responses[-1].headers["retry-after"] == "60"
    assert responses[-1].headers["access-control-allow-origin"] == "https://fastapi-gateway-frontend.onrender.com"


def test_options_preflight_does_not_increment_ip_counter(client, fake_redis):
    response = client.options(
        "/gateway/request",
        headers={
            "Origin": "https://fastapi-gateway-frontend.onrender.com",
            "Access-Control-Request-Method": "POST",
            "X-Forwarded-For": "203.0.113.20",
        },
    )

    assert response.status_code == 200
    assert fake_redis._counters == {}


def test_fixed_window_matches_prefixed_case_insensitive_paths(client, fake_redis):
    response = client.post(
        "/API/Login",
        headers={"X-Forwarded-For": "203.0.113.30"},
    )

    assert response.status_code == 404
    assert fake_redis._counters["rate_limit:/api/login:203.0.113.30"][0] == 1


def test_gateway_request_returns_429_when_exhausted(client, db_session):
    from app.models.rate_limit import RateLimit
    from app.models.user import User

    headers = register_and_login(client)
    user = db_session.query(User).filter(User.email == "ratelimit@example.com").first()
    # Tiny bucket, effectively no refill, so the 3rd request in quick succession is denied.
    db_session.add(RateLimit(user_id=user.id, endpoint="/gateway/request", bucket_capacity=2, refill_rate_per_sec=0.0001))
    db_session.commit()

    r1 = client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)
    r2 = client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)
    r3 = client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert "Retry-After" in r3.headers


def test_development_bypass_skips_rate_limit(client, db_session, monkeypatch):
    from app.config import Settings
    from app.middleware import rate_limit as rate_limit_module
    from app.models.rate_limit import RateLimit
    from app.models.user import User

    headers = register_and_login(client)
    user = db_session.query(User).filter(User.email == "ratelimit@example.com").first()
    db_session.add(RateLimit(user_id=user.id, endpoint="/gateway/request", bucket_capacity=1, refill_rate_per_sec=0.0001))
    db_session.commit()
    monkeypatch.setattr(
        rate_limit_module,
        "get_settings",
        lambda: Settings(environment="development", rate_limit_enabled=False),
    )

    responses = [
        client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)
        for _ in range(3)
    ]

    assert all(response.status_code == 200 for response in responses)


def test_blocked_request_is_persisted(client, db_session):
    from app.models.rate_limit import RateLimit
    from app.models.user import User

    headers = register_and_login(client)
    user = db_session.query(User).filter(User.email == "ratelimit@example.com").first()
    db_session.add(RateLimit(user_id=user.id, endpoint="/gateway/request", bucket_capacity=1, refill_rate_per_sec=0.0001))
    db_session.commit()

    client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)  # consumes the 1 token
    client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)  # should be blocked

    blocked = db_session.query(BlockedRequest).filter(BlockedRequest.user_id == user.id).all()
    assert len(blocked) == 1
    assert blocked[0].endpoint == "/gateway/request"
    assert blocked[0].reason == "rate_limit_exceeded"


def test_different_users_have_independent_limits(client, db_session):
    from app.models.rate_limit import RateLimit
    from app.models.user import User

    headers_a = register_and_login(client, email="userA@example.com")
    headers_b = register_and_login(client, email="userB@example.com")

    user_a = db_session.query(User).filter(User.email == "userA@example.com").first()
    db_session.add(RateLimit(user_id=user_a.id, endpoint="/gateway/request", bucket_capacity=1, refill_rate_per_sec=0.0001))
    db_session.commit()

    # Exhaust user A's bucket.
    client.post("/gateway/request", json={"target_service": "echo"}, headers=headers_a)
    blocked_a = client.post("/gateway/request", json={"target_service": "echo"}, headers=headers_a)
    assert blocked_a.status_code == 429

    # User B (default global limits, much higher) is unaffected.
    allowed_b = client.post("/gateway/request", json={"target_service": "echo"}, headers=headers_b)
    assert allowed_b.status_code == 200


def test_default_limits_apply_when_no_override_configured(client):
    headers = register_and_login(client, email="defaultlimits@example.com")
    # No RateLimit row inserted -> falls back to settings.default_rate_limit_tokens (100),
    # so a handful of requests should all succeed.
    for _ in range(5):
        response = client.post("/gateway/request", json={"target_service": "echo"}, headers=headers)
        assert response.status_code == 200
