# FraudGuard

Real-time credit card fraud detection and monitoring platform. FastAPI + XGBoost backend, React (Vite) dashboard, with SHAP-based explainability, drift detection, and live transaction monitoring over WebSockets.

## Features

- **Fraud prediction** — XGBoost model trained on transaction data, with SHAP explanations for every flagged transaction
- **Live monitoring** — real-time transaction feed over WebSockets
- **Dashboard & analytics** — fraud stats, risk trends, merchant/decision breakdowns, activity heatmap by day/hour
- **Explainability** — per-transaction SHAP feature importance
- **Drift detection** — compares live traffic against a reference distribution to flag data drift
- **Auth & RBAC** — JWT auth, role-based access (Admin / Analyst), password reset flow
- **Reports** — CSV/PDF export
- **Audit log** — tracks review actions and case resolutions

## Tech Stack

**Backend:** FastAPI, SQLAlchemy + Alembic, PostgreSQL, Redis, XGBoost, scikit-learn, SHAP, WebSockets, JWT auth
**Frontend:** React 19, Vite, Tailwind CSS, Chart.js, React Hook Form + Zod, Axios

## Quick Start (Local)

**Prerequisite:** Docker Desktop installed and running. That's it — Postgres and Redis run as containers, so nothing else needs to be installed locally besides Node.js for the frontend.

### 1. Backend, database, and cache

```bash
git clone https://github.com/<you>/fraudguard.git
cd fraudguard
docker compose up --build
```

Wait for `Application startup complete` in the logs — this also runs the Alembic migrations automatically. Verify it's up at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

The first account you register becomes Admin automatically:

1. In the Swagger UI, expand `POST /api/v1/auth/register`, click "Try it out"
2. Register with any email + a password (8+ characters, containing a letter and a digit)
3. Optionally register 1–2 more accounts as `analyst` role to demo RBAC

### 2. Frontend

In a second terminal:

```bash
cd fraudguard-frontend
npm install
npm run dev
```

Open the URL Vite prints (usually [http://localhost:5173](http://localhost:5173)) and log in with the account you just created.

More detail — including a note on why you should seed some demo data a day ahead of a live demo rather than right before — is in [`LOCAL_RUN.md`](./LOCAL_RUN.md).

## Deployment

FraudGuard deploys as: **Render** (backend API + Postgres + Redis) + **Vercel** (frontend). Full step-by-step instructions, including how to ship the trained model artifacts and drift-detection reference cache alongside your code, are in [`DEPLOYMENT.md`](./DEPLOYMENT.md).

## Project Structure

```
FraudGuard/
├── fraudguard-backend/     # FastAPI app, ML pipeline, Alembic migrations
│   └── app/
│       ├── api/v1/         # Route handlers (auth, transactions, analytics, drift, ...)
│       ├── core/           # Config, security, logging, rate limiting
│       ├── ml_engine/      # Model training, SHAP explainer, drift detector
│       ├── models/         # SQLAlchemy models
│       ├── repositories/   # Data access layer
│       ├── schemas/        # Pydantic request/response schemas
│       └── services/       # Business logic
├── fraudguard-frontend/    # React + Vite dashboard
│   └── src/
│       ├── components/     # Charts, layout, transactions, UI primitives
│       ├── context/        # Auth context
│       ├── lib/            # API client, data transforms
│       └── pages/          # Dashboard, Transactions, Analytics, Settings, ...
├── docker-compose.yml      # One-command local stack (Postgres + Redis + backend)
├── seed_transactions.py    # Seed script for demo data
└── creditcard.csv          # Reference dataset (used to build the drift baseline)
```

## Status

Every page in the dashboard is wired to the real backend — there is no mock data in the running app. See [`LOCAL_RUN.md`](./LOCAL_RUN.md#what-is-actually-connected-today) for the full page-by-page breakdown.

## License

GPL-3.0 — see [`LICENSE`](./LICENSE).
