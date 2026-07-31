# Running FraudGuard Locally (for the faculty demo, no internet needed)

Two things need to run at once: the **backend API** (port 8000) and the
**frontend** (port 5173). Open two terminals.

## One-time setup

**Docker Desktop must be installed and running.** That's the only
prerequisite now — Postgres and Redis run as containers, so you don't need
to install either on your laptop.

## Terminal 1 — Backend + Database + Redis

```bash
cd C:\Drishti\FraudGuard
docker compose up --build
```

Wait until you see `Application startup complete` in the logs. This also
runs the Alembic migrations automatically, so the database schema is ready.

Leave this terminal running. Verify it's alive: open
http://127.0.0.1:8000/docs in a browser — you should see the Swagger UI.

**First run only** — create your demo account (the very first account
registered becomes Admin automatically):
1. In Swagger, expand `POST /api/v1/auth/register`, "Try it out", register
   with any email + an 8+ character password containing a letter and digit.
2. Optionally register 1-2 more accounts as `analyst` role to show RBAC.

**First run only** — the model is already trained (`model.joblib` etc. ship
in the repo), so no training step is needed before the demo.

## Terminal 2 — Frontend

```bash
cd C:\Drishti\FraudGuard\fraudguard-frontend
npm install        # first time only
npm run dev
```

Open the URL Vite prints — usually http://localhost:5173. Log in with the
account you registered above.

## Before the actual demo

- Run through the flow once end-to-end the night before: login → Dashboard
  loads real stats → Transactions page → submit a test prediction via
  Swagger's `POST /api/v1/predict` (or wire a page to it) → confirm it shows
  up.
- Known limitation to be upfront about if asked: **Live Monitoring, Fraud
  Analytics, Explainability, Reports, Settings, and Profile pages still
  display placeholder/mock data** — only Dashboard, Transactions, and Auth
  are wired to the real backend so far (see the "What's Actually Connected"
  section below).
- If Docker isn't available on the demo machine, fall back to the manual
  Postgres+Redis install path in `fraudguard-backend/README.md`.

## What's Actually Connected Today

| Page | Status |
|---|---|
| Login / Register | Real backend (JWT auth) |
| Dashboard | Real backend (stats, charts, alerts, recent transactions) |
| Transactions | Real backend (search, filter, pagination) |
| Live Monitoring | Mock data (needs backend WebSockets — not built yet) |
| Fraud Analytics | Mock data |
| Explainability | Mock data (backend SHAP endpoint exists via `/predict`, just not wired here) |
| Reports | Static list (backend PDF/CSV export not built yet) |
| Settings / Profile | Mostly static/cosmetic |
