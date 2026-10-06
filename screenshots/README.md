# Screenshots

This folder is where real, captured screenshots of the running app go
once you've deployed it (or run it locally) — login page, dashboard,
analytics, logs, etc.

None are committed yet: this project was built without being able to
actually run the frontend/backend together (no network access in the
environment it was generated in — see the root README's "What's been
verified" section for the full list of what could and couldn't be
tested). A hand-drawn mockup is at
[`docs/assets/dashboard-mockup.svg`](../docs/assets/dashboard-mockup.svg)
and linked from the main README in the meantime.

## Suggested shots

Once you have it running (`docker compose up --build`, see the root
README), capture:

- `login.png` — the login page
- `dashboard-admin.png` — admin overview with real traffic data
- `dashboard-user.png` — the gateway playground (non-admin view)
- `analytics.png` — the traffic chart + endpoint breakdown
- `logs.png` — the request logs table, ideally with the endpoint filter in use

Then update the README's Screenshots section to reference them with
standard Markdown image syntax: `![Dashboard](screenshots/dashboard-admin.png)`.
