# Deployment

Target stack: **Render** (backend + Postgres), **Upstash** (Redis),
**Vercel** (frontend). All four have a free tier sufficient for a
portfolio deployment.

Deploy in this order — each step needs a URL or credential from the
one before it:

1. Upstash Redis
2. Render Postgres + backend
3. Vercel frontend
4. Go back and fix CORS on the backend (its only dependency on step 3)

## 1. Redis — Upstash

1. Create an account at [upstash.com](https://upstash.com) and verify
   your email.
2. **Create database** → give it a name (e.g. `gateway-redis`) → pick
   a region close to where you'll deploy the backend (Render's
   `oregon` region, to match `render.yaml`, pick an Upstash region on
   the US west coast) → **Create**.
3. On the database's detail page, under **REST API** / **Connect**,
   copy the **Redis URL** (starts with `rediss://` — note the extra
   `s`, meaning TLS; our `redis.Redis.from_url()` call in
   `app/services/redis_client.py` handles this transparently).
4. Keep this tab open — you'll paste this URL into Render in the next step.

## 2. Backend + Postgres — Render

### Option A: Blueprint (recommended — one step creates both)

1. Push this repo to GitHub if you haven't already.
2. In the Render dashboard: **New +** → **Blueprint**.
3. Connect the repo. Render detects `render.yaml` at the repo root and
   shows a preview: one web service (`api-gateway-backend`) and one
   Postgres database (`api-gateway-db`).
4. Click **Apply**. Render provisions the database first, then builds
   and deploys the backend with `DATABASE_URL` already wired in
   (`render.yaml`'s `fromDatabase` link) and `JWT_SECRET_KEY`
   auto-generated.
5. Once it's live, open the service → **Environment** and set the two
   variables `render.yaml` deliberately left blank:
   - `REDIS_URL` → the `rediss://...` URL from step 1
   - `CORS_ORIGINS` → leave as `http://localhost:5173` for now; you'll
     update this in step 4 once you have the real Vercel URL
6. Saving env var changes triggers an automatic redeploy.

### Option B: Manual (if you'd rather not use the blueprint)

1. **New +** → **PostgreSQL**. Name it, pick the free plan, create it.
   Copy its **Internal Database URL**.
2. **New +** → **Web Service**, connect the repo.
   - **Root directory**: `backend`
   - **Runtime**: Python 3
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health check path**: `/health`
3. Under **Environment**, add every variable listed in
   `backend/.env.example`, using:
   - `DATABASE_URL` → the Internal Database URL from step 1
   - `REDIS_URL` → the Upstash URL from section 1
   - `JWT_SECRET_KEY` → generate one yourself, e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`
   - `CORS_ORIGINS` → `http://localhost:5173` for now
4. **Create Web Service**.

### Verify

Once deployed, Render gives you a URL like
`https://api-gateway-backend.onrender.com`. Confirm:

```bash
curl https://api-gateway-backend.onrender.com/health
# {"status":"healthy","environment":"production","database":"ok","redis":"ok"}
```

If `database` or `redis` show `"unreachable"`, double-check the
corresponding env var and redeploy.

> **Free-tier note:** Render's free web services spin down after 15
> minutes of inactivity and take ~30–60s to wake on the next request —
> expect a slow first load after idle periods. Free Postgres databases
> also expire after 90 days unless upgraded.

## 3. Frontend — Vercel

1. Create an account at [vercel.com](https://vercel.com) and connect
   your GitHub account.
2. **Add New** → **Project** → import this repo.
3. Vercel auto-detects Vite, but since the frontend lives in a
   subdirectory, set:
   - **Root directory**: `frontend`
   - **Framework preset**: Vite (should auto-fill)
   - **Build command**: `npm run build` (default)
   - **Output directory**: `dist` (default)
4. Under **Environment Variables**, add:
   - `VITE_API_BASE_URL` → your Render backend URL from step 2
     (e.g. `https://api-gateway-backend.onrender.com`), **no trailing slash**
5. **Deploy**. Vercel gives you a URL like
   `https://api-gateway-platform.vercel.app`.

`frontend/vercel.json` (already in the repo) adds the rewrite rule
that makes client-side routes like `/analytics` survive a hard
refresh or direct link — without it, Vercel would 404 on anything
that isn't a real static file.

## 4. Close the loop: fix CORS

The backend was deployed with a placeholder `CORS_ORIGINS`. Now that
you have the real Vercel URL:

1. Back in Render → your backend service → **Environment**.
2. Set `CORS_ORIGINS` to your Vercel URL (comma-separated if you also
   want to keep `http://localhost:5173` for local testing):
   ```
   https://api-gateway-platform.vercel.app,http://localhost:5173
   ```
3. Save — Render redeploys automatically.

## Verification checklist

- [ ] `GET {backend_url}/health` returns `"database": "ok"` and `"redis": "ok"`
- [ ] `GET {backend_url}/docs` loads the Swagger UI
- [ ] Opening the Vercel URL loads the login page with no console CORS errors
- [ ] Registering + logging in works end-to-end
- [ ] A logged-in admin can see `/dashboard` → `/analytics` → `/users` → `/logs` with real data
- [ ] Sending a request through the Gateway Playground (non-admin dashboard view) returns a response

## Updating a deployment

- **Backend**: push to the connected branch — Render auto-deploys and
  re-runs `alembic upgrade head`, so new migrations apply automatically.
- **Frontend**: push to the connected branch — Vercel auto-deploys.
  Remember `VITE_API_BASE_URL` is baked in at build time; changing it
  requires a new deploy (Vercel's dashboard → **Redeploy**), not just
  an env var save.
