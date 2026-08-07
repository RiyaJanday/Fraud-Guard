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

- Run through the flow once end-to-end the night before: register/log in →
  Dashboard loads real stats → Transactions page → submit a test prediction
  via Swagger's `POST /api/v1/predict` → confirm it shows up on Dashboard,
  Live Monitoring, and Transactions.
- Consider running `seed_demo_data.py` a day or two beforehand rather than
  right before the demo — charts that bucket by hour/day (Transaction
  Volume, Risk Trend) look flat if every transaction was submitted in one
  short burst, since there's no real time spread to show. A demo run the
  night before is enough to avoid this.
- If Docker isn't available on the demo machine, fall back to the manual
  Postgres+Redis install path in `fraudguard-backend/README.md`.

## What's Actually Connected Today

Every page in the dashboard is wired to the real backend — there is no mock
data left in the running app.

| Page | Status |
|---|---|
| Login / Register | Real backend (JWT auth, bootstrap-admin-on-first-account) |
| Dashboard | Real backend (stats, charts, alerts, recent transactions, live model metrics) |
| Transactions | Real backend (search, filter, pagination) |
| Live Monitoring | Real backend (WebSocket transaction feed) |
| Fraud Analytics | Real backend (merchant/decision aggregates) |
| Explainability | Real backend (SHAP feature importance + per-transaction explanations) |
| Reports | Real backend (PDF/CSV export, generated on request) |
| Settings | Real backend (password change, notification preferences, team management) |
| Profile | Real backend (review stats, resolved-case activity) |
