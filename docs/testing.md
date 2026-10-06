# Testing

## Running the suite

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

No real Postgres or Redis needed — see "Test infrastructure" below.

## Coverage

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html
```

Reads config from `backend/.coveragerc`. The HTML report lands in
`backend/htmlcov/index.html`. I can't run this myself in the
environment I built this project in (no network access to install
the dependencies), so I'm not going to quote a coverage percentage I
haven't actually measured — run the command above and you'll have the
real number.

## What's covered

85 tests across 11 files, as of Phase 11:

| File | Tests | Covers |
|---|---|---|
| `test_models.py` | 7 | All 7 tables: constraints, FK behavior (`CASCADE` vs `SET NULL`), relationships |
| `test_auth.py` | 16 | Register, login, password strength, protected routes, refresh rotation, RBAC |
| `test_security.py` | 10 | JWT expiry/tampering/wrong-key rejection, password hash uniqueness, refresh token hashing |
| `test_gateway.py` | 9 | Routing, validation, auth enforcement, response-time tracking |
| `test_rate_limiter.py` | 9 | Token bucket math (refill, capacity cap, isolation), 429s, per-user limits, blocked-request persistence |
| `test_request_logging.py` | 6 | Every request persisted with correct fields, docs routes excluded |
| `test_analytics.py` | 11 | Aggregation correctness, time-window filtering, RBAC |
| `test_admin.py` | 6 | Pagination, endpoint filtering, RBAC |
| `test_error_handling.py` | 3 | The unhandled-exception 500 path specifically (everything else is hit indirectly elsewhere), validation/404 envelope shape |
| `test_config.py` | 5 | Settings defaults, CORS origin list parsing |
| `test_health.py` | 3 | App boots, all routers registered, `/health` reports DB+Redis |

## Test infrastructure

- **Database:** a temp-file SQLite DB per test (not Postgres) — see
  `app/tests/conftest.py`. File-based rather than `:memory:` because
  Phase 7's logging middleware opens its own DB session independently
  of the request-scoped one, and two independent sessions can't safely
  share a single in-memory SQLite connection.
- **Redis:** `app/tests/fake_redis.py`, a small in-memory stand-in
  implementing just the `.eval()` contract the rate limiter needs — no
  real Redis server required.
- **Auth:** tests register/log in real users through the actual
  `/auth` endpoints rather than inserting rows directly, so the auth
  flow itself stays exercised by every other test file that needs an
  authenticated user.

## Markers

```bash
pytest -m unit          # fast, no I/O
pytest -m integration    # through TestClient + test DB
```

`test_security.py` and `test_config.py` are `unit`. Everything that
uses the `client` or `db_session` fixtures is `integration`.
`test_rate_limiter.py` and `test_error_handling.py` genuinely mix both
styles within one file (documented in each file's module docstring),
so they're left unmarked rather than mislabeled — run them with a bare
`pytest`, which still picks up everything regardless of marker.
