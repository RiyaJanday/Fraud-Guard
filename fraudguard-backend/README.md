# FraudGuard Backend

AI-powered real-time credit card fraud detection system — production backend.

Built with clean architecture (API → Service → Repository → Database) on
FastAPI, PostgreSQL, and an XGBoost + SHAP inference pipeline trained on the
ULB Credit Card Fraud Detection dataset.

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI (async), Uvicorn |
| Database | PostgreSQL, SQLAlchemy 2.0, Alembic migrations |
| Auth | JWT (python-jose), Passlib/bcrypt, RBAC (Admin / Analyst / Auditor) |
| ML | XGBoost, scikit-learn, SHAP, imbalanced-learn (SMOTE), joblib |
| Real-time | WebSockets, Redis |
| Reporting | ReportLab (PDF), Python `csv` module (CSV export) |
| Ops | Loguru, SlowAPI rate limiting, Docker |
| Testing | Pytest, httpx |

## Project Structure

```
fraudguard-backend/
├── alembic.ini              # Alembic config (DB URL pulled from Settings, not hardcoded)
├── app/
│   ├── api/v1/            # Route handlers only — no business logic
│   ├── core/               # config, security, logging, exceptions, websocket
│   ├── database/
│   │   ├── base.py           # Declarative Base + UUIDMixin + TimestampMixin
│   │   ├── session.py         # engine, SessionLocal, get_db dependency
│   │   └── migrations/         # Alembic env.py, script.py.mako, versions/
│   ├── models/              # SQLAlchemy ORM models (9 tables)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── repositories/        # Raw DB queries
│   ├── services/             # Business logic
│   ├── ml_engine/
│   │   ├── models/           # Saved model.joblib, scaler.joblib, etc. (gitignored)
│   │   ├── preprocessing.py
│   │   ├── predictor.py
│   │   ├── training.py
│   │   ├── evaluation.py
│   │   ├── shap_service.py
│   │   └── drift_detector.py   # Step 7 remainder — not yet built
│   └── main.py               # FastAPI app factory
├── tests/
├── train_model.py            # Standalone training pipeline entry point
├── requirements.txt
├── Dockerfile                 # Backend container build (Step 10 — see project-root docker-compose.yml)
├── .env                       # Local config (gitignored)
└── .env.example                # Template for the above
```

A `docker-compose.yml`, `DEPLOYMENT.md`, and `LOCAL_RUN.md` also exist one
level up, at the project root (`FraudGuard/`) — they orchestrate this backend
together with Postgres, Redis, and the frontend. See those for the actual
recommended way to run the full stack locally or deploy it; the manual venv
setup below is still useful for running the backend in isolation (e.g. for
`train_model.py`, which needs a local Python environment regardless).

## Setup

### 0. Python version

**Use Python 3.11.** This project pins to 3.11 (see `.python-version`) rather
than newer releases like 3.13, because several ML dependencies (`numpy`,
`scipy`-based packages) either lack prebuilt Windows wheels on brand-new
Python versions or require a modern C compiler to build from source. 3.11 has
mature prebuilt wheels for the entire stack and avoids that class of install
failure entirely.

If you have multiple Python versions installed on Windows, force 3.11
explicitly when creating the venv (see step 1) rather than relying on
whatever plain `python` resolves to on your PATH.

### 1. Create a virtual environment

```bash
cd fraudguard-backend
py -3.11 -m venv .venv         # Windows — forces Python 3.11 specifically
.venv\Scripts\activate
# python3.11 -m venv .venv     # macOS/Linux
# source .venv/bin/activate

python --version                # sanity check — should print 3.11.x
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Using `python -m pip` (rather than a bare `pip`) guarantees you're installing
into the active venv even if another `pip` is earlier on your PATH.

### 3. Configure environment variables

`.env` is already populated with working local defaults (including generated
JWT secrets). At minimum, update `DATABASE_URL` to match your local
PostgreSQL credentials:

```
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@localhost:5432/fraudguard
```

Create the database itself (once PostgreSQL is installed):

```sql
CREATE DATABASE fraudguard;
```

### 4. Run the API

```bash
python -m uvicorn app.main:app --reload
```

Using `python -m uvicorn` (rather than a bare `uvicorn`) guarantees the venv's
own uvicorn runs, rather than a different `uvicorn.exe` earlier on your
system PATH.

- API root: http://127.0.0.1:8000/
- Swagger docs: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### 5. Database migrations (Alembic)

Make sure the `fraudguard` database exists (step 3), then generate and apply
the initial migration, which creates all 9 tables (`users`, `transactions`,
`fraud_predictions`, `fraud_logs`, `audit_logs`, `review_queue`,
`notifications`, `model_registry`, `model_metrics`):

```bash
alembic revision --autogenerate -m "initial schema - 9 core tables"
alembic upgrade head
```

`alembic revision --autogenerate` connects to `DATABASE_URL`, compares it
against every model in `app/models/`, and writes a migration file into
`app/database/migrations/versions/`. **Open that generated file and read it**
before applying — autogenerate is reliable for a first migration like this
one, but it's still worth a sanity check (e.g. confirm all 9 `CREATE TABLE`
statements and the enum types are present) before running `upgrade head`
against a real database.

To verify afterwards:

```bash
psql -U postgres -d fraudguard -c "\dt"
```

should list all 9 tables.

### 6. Create your first account & test the API

Start the server (step 4), then open Swagger UI at http://127.0.0.1:8000/docs.

1. Expand **POST /api/v1/auth/register** → "Try it out" → register with any
   email/password (8+ chars, at least one letter and one digit). **The very
   first account ever registered automatically becomes Admin** — no seed
   script needed.
2. Expand **POST /api/v1/auth/login** → log in with those same credentials.
   Copy the `access_token` from the response.
3. Click the green **Authorize** button (top right) and paste just the raw
   token value (no `Bearer ` prefix needed — Swagger adds that itself).
4. Now **GET /api/v1/auth/me** should return your account.

Redis is optional for local development: if it isn't running, login/logout
still work, but logout won't be able to instantly revoke tokens (they'll
just expire naturally after `ACCESS_TOKEN_EXPIRE_MINUTES`). Install it later
via Docker (Step 10) if you want full logout revocation.

### 7. Train the fraud detection model

With your `.venv` active and `creditcard.csv` present at the project root, first pick up the XGBoost version fix (see Step 4 notes below):

```bash
python -m pip install -r requirements.txt
```

Then run the training pipeline from `fraudguard-backend/`:

```bash
python train_model.py --quick    # fast sanity-check run first — a few minutes
python train_model.py            # full hyperparameter search — see timing notes below
```

`--quick` skips hyperparameter search (fixed, reasonable defaults) and is
worth running first just to confirm everything works end-to-end against your
real data before committing to the longer full search. Expect it to finish
in low single-digit minutes even on the full 284K-row dataset.

The full search (no `--quick`) runs `RandomizedSearchCV` across all 3
candidate models. **Random Forest is the slow one** — on a small 20K-row
synthetic test it alone took ~2 minutes; scaled up to 284K real rows (plus
SMOTE bringing the training set to roughly 200K+ rows), budget substantially
longer — quite possibly 30-90+ minutes depending on your CPU. Logistic
Regression and XGBoost are much faster. If the full run is impractical on
your machine, `--quick` results are entirely legitimate to use — the
difference is search-optimized hyperparameters vs. reasonable fixed ones,
not a difference in correctness.

When it finishes, you'll have:
- `app/ml_engine/models/model.joblib`, `scaler.joblib`, `shap_explainer.joblib`, `metrics.json`
- A new row in the `model_registry` table with `status=ACTIVE` (any previous active model is automatically deactivated)

**Paste the console output back** (especially the "Model comparison" and
"Selected model" lines) — I'll review the real metrics on your actual data.

## Dataset

This project uses the real ULB Credit Card Fraud Detection dataset
(`creditcard.csv`: `Time`, `V1`–`V28`, `Amount`, `Class`), expected at the
**project root** — one level above this `fraudguard-backend/` folder
(`C:\Drishti\FraudGuard\creditcard.csv`). The training pipeline auto-detects
it from there; no synthetic data is ever generated as a fallback.

## Build Progress

This backend is being built incrementally, one feature at a time, per the
project's clean-architecture requirements.

- [x] **Step 1 — Project structure & configuration**
  - Folder skeleton for every planned module
  - `app/core/config.py` — centralized Pydantic Settings
  - `app/core/logging.py` — Loguru logging (console + rotating file + error sinks)
  - `app/core/exceptions.py` — exception hierarchy + consistent JSON error envelope
  - `app/main.py` — FastAPI app factory, CORS, lifespan startup/shutdown
  - `requirements.txt`, `.env` / `.env.example`, `.gitignore`, `.python-version`
- [x] **Step 2 — Database models + Alembic migrations** (this commit)
  - `app/database/base.py` — `Base`, `UUIDMixin`, `TimestampMixin`
  - `app/database/session.py` — engine, `SessionLocal`, `get_db` dependency, `check_database_connection`
  - 9 SQLAlchemy models: `User`, `Transaction`, `FraudPrediction`, `FraudLog`,
    `AuditLog`, `ReviewQueue`, `Notification`, `ModelRegistry`, `ModelMetrics`
    — each with UUID PK, timestamps, indexes, FKs, and relationships
  - Partial unique index guaranteeing only one `ModelRegistry` row can be `ACTIVE`
  - Alembic scaffolding (`alembic.ini`, `env.py`, `script.py.mako`) wired to
    read `DATABASE_URL` from Settings rather than duplicating it
  - Verified: full model layer imports cleanly, DDL compiles against the
    Postgres dialect, and every `relationship()`/`back_populates` pair
    resolves via `configure_mappers()` with no errors
  - **Migration applied to a real local Postgres database** — all 9 tables
    + `alembic_version` confirmed live via `psql \dt`
- [x] **Step 3 — Authentication (JWT + RBAC)**
  - `app/core/security.py` — password hashing (bcrypt), JWT access/refresh/
    password-reset token issuance (each with its own `type` claim and, for
    refresh tokens, a separate signing secret), `get_current_user` and
    `require_role(...)` RBAC dependencies
  - `app/core/redis_client.py` — logout token-blacklist, deliberately
    fail-open if Redis is unreachable so it never blocks local development
  - `HTTPBearer` (not `OAuth2PasswordBearer`) used for token extraction —
    matches our JSON-based `/login` and gives a simple "paste your token"
    field in Swagger's Authorize dialog
  - `AuthService` — register (with first-user-becomes-Admin bootstrap),
    login, refresh (single-use/rotating), logout (blacklists both tokens),
    forgot-password (no email-enumeration leak), reset-password (single-use)
  - 7 endpoints: `POST /register`, `/login`, `/refresh`, `/logout`,
    `/forgot-password`, `/reset-password`, `GET /me`
  - Verified end-to-end against a real local Postgres + Redis: registration
    bootstrap, RBAC allow/deny on both single- and multi-role routes, refresh
    token rotation (old token rejected after use), logout blacklisting
    (confirmed both access AND refresh tokens rejected afterward), full
    password-reset round trip (old password stops working, reset token is
    single-use), Redis-down fail-open behavior, and OpenAPI schema generation
  - **Bug caught and fixed during testing**: a weak-password validation
    error crashed with a 500 instead of returning a clean 422 — Pydantic
    embeds the raw `ValueError` from a custom `@field_validator` inside the
    error payload, which plain `json.dumps` can't serialize. Fixed globally
    in `app/core/exceptions.py` via `jsonable_encoder` plus explicit
    stringification of that field, so any future validator is safe too, not
    just this one field.
- [x] **Step 4 — ML inference service** (this commit)
  - `app/ml_engine/preprocessing.py` — dataset load/validate/analyze,
    defensive missing-value handling, feature engineering (`Hour` from
    `Time`, `Amount_log`), stratified 70/15/15 train/val/test split,
    `StandardScaler` fit on train only, SMOTE (`sampling_strategy=0.1` —
    deliberately not a full 1:1 balance; reasoning documented in the module)
  - `app/ml_engine/training.py` — trains Logistic Regression, Random Forest,
    and XGBoost, each with `RandomizedSearchCV` (or `--quick` fixed defaults)
  - `app/ml_engine/evaluation.py` — Accuracy/Precision/Recall/F1/ROC-AUC/
    PR-AUC/confusion matrix per model; `select_best_model` enforces the
    Recall > F1 > Precision > ROC-AUC > Accuracy priority explicitly
  - `app/ml_engine/shap_service.py` — unified `shap.Explainer` (auto-adapts
    to whichever model wins), top-5 feature attribution, natural-language
    explanation generation. Deliberately honest about V1-V28 being
    anonymized PCA components with no disclosed business meaning — never
    fabricates a false semantic label for them
  - `app/ml_engine/predictor.py` — loads saved artifacts once (never
    retrains during inference), single-transaction prediction with risk
    score, confidence, decision (approve/MFA/block via `Settings`
    thresholds), latency, SHAP explanation
  - `train_model.py` — end-to-end pipeline entry point (`--quick` flag for a
    fast fixed-hyperparameter run); registers the winning model in
    `model_registry` as `ACTIVE`, deactivating any previous active model
  - Verified end-to-end in a sandbox against a synthetic dataset with the
    exact real schema: full pipeline (both quick and full hyperparameter
    search modes), live inference + SHAP explanation on both a legit and a
    fraud example, and both error paths (missing dataset, missing model
    artifacts) fail cleanly with actionable messages instead of crashing
  - **Bug caught and fixed during testing**: `scikit-learn==1.6.1` introduced
    a new `__sklearn_tags__` protocol that `xgboost==2.1.3`'s `XGBClassifier`
    doesn't implement, crashing `RandomizedSearchCV` (and any sklearn
    meta-estimator) wrapping an XGBoost model with
    `AttributeError: 'super' object has no attribute '__sklearn_tags__'`.
    Reproduced it, found `xgboost==2.1.4` fixes it, verified the fix with a
    real `RandomizedSearchCV` run, and re-ran the entire pipeline
    successfully. **Run `pip install -r requirements.txt` again to pick up
    this version bump before training.**
  - **Second bug, caught from the real training run's actual output** — more
    serious than the first: `select_best_model`'s literal "Recall > F1"
    priority chose **Logistic Regression** (recall 0.89) over **Random
    Forest** (recall 0.80), because 0.89 > 0.80, full stop. On the real test
    set, Logistic Regression only reached that recall by flagging ~1,200 of
    ~42,700 transactions as fraud — a **94.5% false-positive rate** among
    everything it blocks. Random Forest catches nearly as much real fraud
    (59 vs 66 of 74 cases) while flagging only ~66 transactions total (10.6%
    false positives) — the model any real fraud team would actually ship.
    Fixed by switching the primary sort key to **F1 first, Recall as
    tiebreaker** (F1 already balances recall and precision; that's its whole
    purpose). Verified the fix against your actual real numbers — it now
    selects Random Forest. **Re-run `python train_model.py` to replace the
    currently-registered Logistic Regression model** (version
    `v20260719091942`) with a correctly-selected one; the old row will be
    auto-deactivated.
  - **Performance bug, also from the real run**: Random Forest's full search
    took **19.6 minutes** (vs. Logistic Regression's 17.6s and XGBoost's
    93.8s) — caused by `n_jobs=-1` set on both `RandomizedSearchCV` *and*
    the `RandomForestClassifier`/`XGBClassifier` it wraps, which causes CPU
    oversubscription (the search tries to run parallel fits across all
    cores while each fit also tries to use all cores to build its own
    trees), compounded by an unbounded `max_depth: None` option in the
    search space. Fixed: inner estimators now use `n_jobs=1` when wrapped in
    the search (letting only the outer search parallelize), and `max_depth`
    is capped at 20 instead of allowing `None`.
- [x] **Step 5 — Transaction APIs** (this commit)
  - `app/schemas/transaction.py` — `TransactionCreate` (validates all 28
    V-features are present), `TransactionDetailOut`/`TransactionOut`,
    `FraudPredictionOut`, `FraudLogOut` (decision history), `ShapFeatureOut`
  - `TransactionRepository` (filtered/paginated listing with eager-loaded
    predictions via `contains_eager` — no N+1 queries), `FraudPredictionRepository`,
    `FraudLogRepository`, `ModelRegistryRepository`
  - `TransactionService.submit_transaction` — the full pipeline from the
    spec (Validation → Preprocessing → Prediction → Risk Score → SHAP →
    Decision → Save Database), calling Step 4's `FraudPredictor` once and
    recording every stage as a queryable `FraudLog` row rather than just a
    log line. "Notify Dashboard" is deliberately NOT logged as a fake
    success — WebSockets don't exist until Step 8, and logging a stage
    that doesn't do anything yet would be dishonest.
  - `POST /predict` (Admin/Analyst only) — returns prediction, fraud
    probability, risk score, confidence, decision (suggested action), SHAP
    features, explanation, and full decision history in one response
  - `GET /transactions` (all 3 roles — read-only) — pagination, filter by
    decision/risk-score-range/merchant/date-range
  - `GET /transactions/{id}` (all 3 roles) — full detail incl. decision history
  - Verified end-to-end in a sandbox against a real Postgres + a freshly
    trained model: RBAC (Auditor blocked from submitting but allowed to
    view, unauthenticated requests rejected), full 5-stage pipeline on both
    a legit and fraud transaction (SHAP correctly attributing the
    engineered fraud signal), validation errors (missing V-feature,
    negative amount) rejected with clean 422s, listing/filtering/pagination
    all correct, 404 on a nonexistent transaction, and the
    `ModelNotLoadedException` path — confirmed the transaction row still
    persists (audit trail preserved) even when scoring fails with a 503
- [x] **Step 6 — Manual review workflow** (this commit)
  - `app/schemas/review.py` — `ReviewQueueOut`/`ReviewQueueDetailOut` (with
    denormalized transaction/prediction summary so the frontend queue view
    doesn't need a second round trip), `ReviewResolveRequest`
  - `ReviewRepository` — eager-loads the `FraudPrediction -> Transaction`
    chain and the assigned analyst on every read path
  - `ReviewService.create_review_if_needed` — called by `TransactionService`
    right after a prediction is persisted; auto-queues only `BLOCKED`
    decisions ("high risk" per the spec — `MFA_REQUIRED` already has its own
    automated mitigation and doesn't need a human review to also fire)
  - `claim_review` (optional team-visibility step) / `resolve_review`
    (records fraud/legitimate as ground truth, auto-claims if nobody did) —
    both guard against double-processing with `ConflictException`
  - 4 endpoints under `/review-queue`: `GET` (list, filterable by status),
    `GET /{id}` (detail incl. SHAP features), `POST /{id}/claim`,
    `POST /{id}/resolve` — Auditor can view but not act, matching the RBAC
    pattern from Step 3
  - Verified end-to-end in a sandbox: a blocked prediction auto-creates
    exactly one pending review (a paired legit transaction correctly does
    NOT); RBAC blocks Auditor from claim/resolve; a second analyst trying to
    claim an already-claimed review gets a 409, as does trying to resolve
    one claimed by someone else, and trying to resolve an already-resolved
    review; the ground-truth decision, notes, and resolver identity all
    persist correctly; and the "resolve without claiming first" auto-claim
    path works as designed
- [x] **Step 7 — Analytics + metrics + drift detection** (dashboard/analytics
  portion from an earlier commit; drift detection added this commit)
  - `app/schemas/dashboard.py` — `DashboardStatsOut` (with real week-over-week
    deltas, not decorative ones), `DashboardChartsOut` (volume, decision
    distribution, risk trend, model performance radar, heatmap), `AnalyticsOut`
    (adds top-merchants-by-risk). Where the frontend's mock data assumed
    named fraud "types" (card-testing/account-takeover/etc.) this dataset has
    no way to actually distinguish, the shape was honestly adapted to a
    decision breakdown (Approved/MFA Required/Blocked) instead of inventing
    fake categories.
  - `AnalyticsRepository` — real aggregate SQL (Postgres `date_trunc`/
    `extract`) for every chart; every series zero-fills its full label range
    (all 24 hours, all 14 days, all 7 weekdays) rather than only returning
    buckets that happen to have data, so a demo with a handful of
    transactions still renders a properly-shaped chart
  - `AnalyticsService` — assembles repository output into response schemas;
    pulls `detection_accuracy` and the model-performance radar directly from
    the active `ModelRegistry` row (real trained-model metrics, not guesses)
  - 5 endpoints: `GET /dashboard/stats`, `GET /dashboard/charts`,
    `GET /dashboard/alerts` (bonus — recent non-approved predictions),
    `GET /analytics` — all read-only, all 3 roles
  - Verified end-to-end in a sandbox: submitted 8 legit + 5 fraud
    transactions across several merchants, confirmed `/dashboard/stats`
    matches exactly, confirmed the doughnut/heatmap/alerts/top-merchants all
    reflect the real submitted data (e.g. "Suspicious Store"/"Sketchy Shop"
    correctly surfaced as the highest-risk merchants), and confirmed RBAC
    requires auth on all 4 endpoints
  - **Bug caught and fixed during testing**: both `volume_by_hour` (24
    hourly buckets) and `risk_trend_by_day` (14 daily buckets) had an
    off-by-one error — bucket labels were generated counting *forward* from
    `now - N`, which only reaches `now - 1` and never includes the current
    hour/day's own bucket. In practice this meant a transaction submitted
    "just now" would silently vanish from every chart — the exact scenario
    a live demo hits immediately. Fixed by computing the label range
    *backward* from the current (truncated) hour/day instead; verified the
    fix by confirming the current-hour bucket now correctly captures
    freshly-submitted transactions.
  - `app/ml_engine/drift_detector.py` — two-sample Kolmogorov-Smirnov test
    per feature (V1-V28, Amount), comparing recently-scored live
    transactions against a cached reference sample of the real training
    dataset. Chose KS over a simpler mean-comparison because a feature can
    keep the same mean while its shape changes entirely — exactly the kind
    of drift that matters in a PCA-transformed feature space. A single
    feature flagged alone is expected noise (running 29 independent tests
    at alpha=0.05 flags ~1-2 by chance even with zero real drift); overall
    `drift_detected` only fires when more than 30% of features are flagged
    together.
  - Reference distribution is built once from `creditcard.csv` and cached
    to `app/ml_engine/models/drift_reference.json` (gitignored like the
    model artifacts, same `git add -f` pattern for deployment — see
    `DEPLOYMENT.md`) rather than re-reading the 284K-row CSV on every check
  - `GET /drift` (all 3 roles, read-only) — returns `insufficient_data`
    instead of a verdict below 30 live transactions, since a KS test's
    p-value is too noisy to report responsibly on a handful of points
  - **Deployment gap caught and fixed while building this**: `creditcard.csv`
    was never actually reachable from inside the backend's Docker container
    (not `COPY`'d into the image — correctly so, to avoid a ~150MB image —
    and not mounted either, since nothing needed it there until now). Fixed
    by adding a read-only volume mount in the project-root `docker-compose.yml`
    (`./creditcard.csv:/creditcard.csv:ro`), matching where `Settings.DATASET_PATH`
    already expected to find it. Also documented the equivalent gap for a
    Render deployment (no local filesystem at all there) in `DEPLOYMENT.md`.
  - Depends on `scipy` (`scipy.stats.ks_2samp`) — not separately pinned in
    `requirements.txt`, since it's already an installed transitive
    dependency of `scikit-learn==1.6.1`. Flagged here rather than silently
    assumed: if a future `scikit-learn` upgrade ever drops that transitive
    dependency, this is the first place to check.
  - Verified against the real deployed stack: `GET /drift?sample_size=30`
    returned `"status": "insufficient_data"` with `sample_size: 1` —
    correctly recognizing there's only 1 real scored transaction so far and
    refusing to compute a misleading verdict from it, exactly as designed
- [x] **Step 8 — WebSockets + notifications + health check** (this commit)
  - `app/core/websocket.py` — `ConnectionManager`, an in-memory registry of
    live WebSocket connections. The whole app runs synchronously
    (SQLAlchemy `Session`, `def` route handlers run in FastAPI's threadpool
    — see `prediction.py`), so a plain `await manager.broadcast(...)` from
    inside a service is unreachable from a worker thread. Solved by binding
    the manager to the *main* event loop once at startup (`app.main`'s
    lifespan) and using `asyncio.run_coroutine_threadsafe` from
    `broadcast_sync` to hand the coroutine across threads correctly.
  - `app/api/v1/ws.py` — `GET /ws/notifications`, authenticated via a
    `?token=` query parameter (not a header) — the browser WebSocket API
    can't attach `Authorization`, so it's the same `decode_token` +
    `UserRepository` check as `get_current_user`, just fed from a different
    place in the handshake.
  - `app/models/notification.py` already existed from Step 2 — this step
    added the repository/service/schema/REST layer around it:
    `NotificationRepository`, `NotificationService.notify_for_prediction`
    (BLOCKED/MFA_REQUIRED decisions only — a silent APPROVE doesn't page
    anyone), `GET /notifications`, `PATCH /notifications/{id}/read`,
    `PATCH /notifications/read-all`
  - `GET /health` — checks the database, Redis (best-effort — Redis is
    documented to fail-open elsewhere, so a Redis outage alone doesn't flip
    the overall status to unhealthy), and that trained model artifacts
    exist on disk
  - `TransactionService.submit_transaction`'s "Notify Dashboard" stage
    (Step 5's spec pipeline) is now real — it persists a `Notification` and
    broadcasts it live, and finally earns a genuine `FraudLog` entry
    instead of being omitted as dishonest placeholder success
  - Verified against the real deployed stack (Docker Compose): browser
    console WebSocket client connected and authenticated successfully via
    query-param token; a real `POST /predict` call scoring a transaction as
    `blocked` (risk score 91.59) produced a genuine `notification` FraudLog
    stage in the response (`"Dashboard notified (id=...)"`), replacing the
    Step 5 placeholder
- [x] **Step 9 — Reports (CSV/PDF)** (this commit)
  - `app/services/report_service.py` — builds on the *same* repositories
    the dashboard/analytics endpoints already query (`TransactionRepository`,
    `AnalyticsRepository`), not parallel raw SQL, so a report can never show
    different numbers than the live dashboard for the same period
  - `GET /reports/transactions.csv` — filterable by decision/date range,
    capped at 10,000 rows per export (protects against an unbounded
    response if the table grows large; callers needing more should page
    through `/transactions` instead)
  - `GET /reports/summary.pdf` — headline stats, decision distribution, and
    top-flagged-merchants, rendered with ReportLab in FraudGuard's brand
    color (`#7C3AED`), filterable by date range
  - Both endpoints stream the file directly in the response body via a
    `Content-Disposition` header rather than writing to disk — there's no
    durable file storage configured in this deployment, and generate-on-
    request means the content is always live, with no stale-file cleanup
    to manage
  - Verified against the real deployed stack: `GET /reports/summary.pdf`
    downloaded a correctly rendered PDF — headline stats (1 transaction, 1
    fraud, 1 blocked, avg risk 91.59), the decision-distribution table, and
    the top-merchants table all matched the real data exactly, with
    FraudGuard's brand purple header styling intact
- [x] **Step 10 — Docker, testing, deployment** (Docker/deployment done ahead
  of sequence, driven by an early need to get the app runnable for a faculty
  demo; test suite added this commit)
  - `tests/conftest.py` — runs against a REAL Postgres database, not
    SQLite: several models use Postgres-specific types (JSONB, native UUID)
    that don't exist in SQLite, so an in-memory DB would silently test a
    different schema than production runs on. Defaults to a database named
    `fraudguard_test` (auto-created on first run), distinct from the `fraudguard`
    dev database — running the suite never touches or wipes real demo data.
    Wipes all tables before each test (rather than a transaction-rollback
    strategy) since every repository in this codebase calls `db.commit()`
    directly, which would end the outer transaction a rollback-based
    approach depends on staying open.
  - `tests/test_health.py`, `test_auth.py`, `test_prediction.py`,
    `test_drift.py`, `test_reports.py` — integration tests hitting the real
    FastAPI app via `TestClient`, covering: registration/bootstrap-admin/
    login/auth guards, the full `/predict` pipeline against the REAL trained
    model (deliberately not mocked — mocking it would only prove the
    plumbing works, not that scoring still functions after a change to
    preprocessing or thresholds), the blocked-transaction → real-notification
    path (Step 8), `/drift`'s honest `insufficient_data` behavior on an empty
    DB (Step 7), and `/reports`' PDF/CSV generation (Step 9)
  - No new dependencies needed — `pytest`, `pytest-asyncio`, `httpx` were
    already pinned in `requirements.txt` from the start, unused until now
  - **Run it**: `docker compose exec backend pytest -v` (with the stack
    already up via `docker compose up`) — running inside the container
    sidesteps any local-vs-containerized Postgres credential mismatch
    between your `.env` (local venv, own Postgres instance) and
    `docker-compose.yml` (containerized Postgres, different credentials)
  - **Verified against the real deployed stack**: `docker compose exec backend
    pytest -v` — **23/23 passed** (one round-trip fix needed first: a wrong
    `Decision` enum string in the test itself — `"approved"` instead of the
    actual `"approve"`). Also caught and fixed two real packaging bugs along
    the way: `tests/` and `pytest.ini` were never `COPY`'d into the Docker
    image (missing from the `Dockerfile`), and `.dockerignore` was
    separately excluding `tests/` from the build context entirely — both
    needed fixing before the suite could even be collected inside the
    container.
  - `Dockerfile` — multi-stage build, runs `alembic upgrade head` then
    `uvicorn` on container start, ships the already-trained model artifacts
  - Project-root `docker-compose.yml` — Postgres + Redis + backend in one
    command (`docker compose up --build`); frontend intentionally left
    outside the compose file, run via `npm run dev` separately to keep
    Vite's hot-reload
  - Project-root `DEPLOYMENT.md` — full Render (backend + Postgres + Redis)
    + Vercel (frontend) walkthrough, including the model-artifact
    git-ignore gotcha and the free-tier cold-start warning
  - Project-root `LOCAL_RUN.md` — step-by-step for the offline/local demo
  - Verified live: `docker compose up --build` boots Postgres → runs
    Alembic migrations → starts Uvicorn cleanly; registration, login, and
    `POST /predict` all confirmed working end-to-end against the
    containerized stack (see Steps 8/9 verification notes above, run
    against this same Docker setup)
  - **Still pending**: `tests/` currently has no test suite — `pytest` and
    `httpx` are in `requirements.txt` but unused so far. Also pending: an
    actual live deployment to Render + Vercel (the guide is written and
    ready, but hasn't yet been executed against real Render/Vercel accounts)
