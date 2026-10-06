# Contributing

## Setup

See the root [README](./README.md#installation) for local setup
(Docker or manual). For backend-only or frontend-only work, see
`backend/README.md` equivalent instructions inline in the root README,
and [`frontend/README.md`](./frontend/README.md).

## Workflow

1. Fork and branch from `main`: `git checkout -b feat/short-description`
2. Make your change.
3. Run the checks that match what you touched:
   ```bash
   # backend
   cd backend && pytest -v && ruff check .

   # frontend
   cd frontend && npm run lint && npm run build
   ```
4. Commit with a clear message (see below).
5. Open a PR against `main` — the template will prompt for what's needed.
6. CI (`.github/workflows/ci.yml`) runs lint + tests + build + Docker
   verification automatically on every PR.

## Commit messages

This repo follows a loose [Conventional Commits](https://www.conventionalcommits.org/)
style — `type: short description`, e.g.:

```
feat: add refresh-token rotation to /auth/refresh
fix: correct token bucket refill math for sub-second windows
docs: add deployment guide for Render/Vercel/Upstash
test: cover unhandled-exception path in error handler
chore: bump fastapi to 0.115.0
```

Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.

## Code style

- **Backend:** PEP 8, type hints on function signatures, `ruff check .`
  before committing (config in `backend/ruff.toml`).
- **Frontend:** TypeScript strict mode is on — fix type errors rather
  than reaching for `any`. `npm run lint` before committing.
- Comments explain *why*, not *what* — the code should already say what it does.

## Adding a migration

Model change in `backend/app/models/` → generate + review + commit the migration:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
# review the generated file in alembic/versions/ before committing —
# autogenerate doesn't always get it exactly right
```
