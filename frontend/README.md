# Gateway Console (Frontend)

React + TypeScript + Vite dashboard for the API Gateway & Rate Limiting Platform.

## Stack

- React 18, TypeScript, Vite
- Tailwind CSS (custom dark/light design tokens — see `src/index.css`)
- React Router for client-side routing
- Axios, with a refresh-token interceptor that transparently retries
  requests that 401 due to an expired access token
- Recharts for the traffic charts
- lucide-react for icons

## Setup

```bash
npm install
cp .env.example .env    # point VITE_API_BASE_URL at your backend
npm run dev              # http://localhost:5173
```

The backend (see `../backend`) must be running for login/data to work.

## Pages

| Route | Access | Purpose |
|---|---|---|
| `/login`, `/register` | public | auth |
| `/dashboard` | any authenticated user | admins see the overview + traffic chart; everyone else sees an interactive gateway playground |
| `/analytics` | admin only | traffic chart (hourly/daily), top/slowest endpoints, most active users |
| `/users` | admin only | paginated user list |
| `/logs` | admin only | paginated request logs (filterable by endpoint) + blocked requests tab |
| `/settings` | any authenticated user | account info (read-only), theme toggle, logout |

## Auth flow

Tokens are stored in `localStorage` (see the trade-off note in
`src/api/client.ts` — an httpOnly cookie would be more secure against
XSS, but needs a server-side cookie-setting step this project doesn't
have). The Axios response interceptor catches a 401, calls
`/auth/refresh` once, and retries the original request; concurrent
401s share a single in-flight refresh instead of each triggering their
own (which would race against the backend's refresh-token rotation
from Phase 4).

## Build

```bash
npm run build      # outputs to dist/
npm run preview    # serve the production build locally
```
