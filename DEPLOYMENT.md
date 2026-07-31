# Deploying FraudGuard Online (public URL for faculty)

Stack: **Render** (backend API + Postgres + Redis) + **Vercel** (frontend).
Both have free tiers sufficient for a class demo. Total time: ~30-45 min.

---

## 0. Push to GitHub

Render and Vercel both deploy from a git repo.

```bash
cd C:\Drishti\FraudGuard
git init                      # if not already a repo
git add .
git commit -m "Ready for deployment"
```

**Important — the trained model must travel with the code.** It's currently
gitignored (`app/ml_engine/models/*.joblib`), which is correct for normal
dev (regenerate via `train_model.py`), but the deployed API can't train on
startup, so force-add the already-trained artifacts just for this repo:

```bash
cd fraudguard-backend
git add -f app/ml_engine/models/model.joblib app/ml_engine/models/scaler.joblib app/ml_engine/models/shap_explainer.joblib app/ml_engine/models/metrics.json
git commit -m "Include trained model artifacts for deployment"
cd ..
```

**Same problem, one more file — the drift-detection reference cache.**
`GET /api/v1/drift` (Step 7) needs a reference sample from `creditcard.csv`
to compare live traffic against. Locally that file is mounted straight into
the Docker container (see `docker-compose.yml`), but Render has no access to
your local filesystem — there's nowhere for it to read `creditcard.csv`
from at all. Generate the cache file once locally (it's small — a JSON
sample, not the raw dataset) before you deploy, then force-add and ship
*that* instead of the ~150MB CSV:

```bash
cd fraudguard-backend
# With the local stack running (docker compose up, or your venv), hit the
# endpoint once — this triggers _load_or_build_reference() to write the
# cache file to disk:
curl -H "Authorization: Bearer <your access_token>" "http://127.0.0.1:8000/api/v1/drift?sample_size=30"

git add -f app/ml_engine/models/drift_reference.json
git commit -m "Include drift-detection reference cache for deployment"
cd ..
```

If you skip this, `/drift` will simply return a clean `DATASET_NOT_FOUND`
error on Render (the same honest 503 behavior `train_model.py` already has
locally) rather than crashing anything else — the rest of the app is
unaffected either way.

Push to a new GitHub repo (create one on github.com first, then):
```bash
git remote add origin https://github.com/<you>/fraudguard.git
git branch -M main
git push -u origin main
```

---

## 1. Backend — Render

1. Go to https://render.com → New → **Blueprint**, or do it manually:
2. **New → PostgreSQL** — name it `fraudguard-db`, free tier. Copy the
   **Internal Database URL** once created.
3. **New → Redis** — name it `fraudguard-redis`, free tier. Copy its
   **Internal Redis URL**.
4. **New → Web Service** → connect your GitHub repo → set:
   - **Root Directory**: `fraudguard-backend`
   - **Runtime**: Docker (Render detects the `Dockerfile` automatically)
   - **Instance type**: Free
5. Add environment variables on the Web Service (Environment tab):
   ```
   ENVIRONMENT=production
   DEBUG=False
   SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
   JWT_REFRESH_SECRET_KEY=<a different one, same command>
   DATABASE_URL=<the postgresql+psycopg2:// Internal Database URL from step 2 — note: Render gives you postgresql://, change the scheme to postgresql+psycopg2://>
   REDIS_URL=<the Internal Redis URL from step 3>
   CORS_ORIGINS=http://localhost:5173,https://<your-vercel-app>.vercel.app
   ```
   (You'll fill in the real Vercel URL after step 2 below, then redeploy.)
6. Deploy. Render builds the Docker image, runs `alembic upgrade head`, then
   starts uvicorn (both wired into the `Dockerfile` CMD already).
7. Once live, note your backend URL, e.g. `https://fraudguard-api.onrender.com`.
   Verify: visit `https://fraudguard-api.onrender.com/docs`.
8. Register your first (Admin) account via that Swagger UI, same as local.

**Free-tier note:** Render's free web services spin down after 15 min of
inactivity and take ~30-50s to wake on the next request. Hit the backend URL
a minute before the faculty demo starts to warm it up, or upgrade to a paid
instance for the day.

---

## 2. Frontend — Vercel

1. Go to https://vercel.com → **Add New → Project** → import the same
   GitHub repo.
2. **Root Directory**: `fraudguard-frontend`
3. Framework preset: Vite (auto-detected).
4. Environment variable:
   ```
   VITE_API_BASE_URL=https://fraudguard-api.onrender.com/api/v1
   ```
   (your real Render URL from step 1.7, with `/api/v1` on the end)
5. Deploy. Vercel gives you a URL like `https://fraudguard.vercel.app`.
6. Go back to Render → update `CORS_ORIGINS` to include this real Vercel URL
   (step 1.5) → the service redeploys automatically on env var change.

---

## 3. Verify end-to-end

Open the Vercel URL → Register/Login → Dashboard should load real stats from
the Render backend → Transactions page should list real data.

---

## Rollback / troubleshooting

- **CORS errors in browser console** → `CORS_ORIGINS` on Render doesn't
  exactly match the Vercel URL (must include `https://`, no trailing slash).
- **502 / cold start on first click** → free-tier Render service waking up;
  wait ~30s and retry.
- **500 on `/predict`** → model artifacts weren't force-added to git (see
  step 0) or didn't survive the Docker build — check Render's build logs for
  `app/ml_engine/models/model.joblib` being copied.
- **Migration errors on deploy** → check Render's Postgres is truly empty on
  first deploy; the `Dockerfile` CMD runs `alembic upgrade head` on every
  boot, which is safe to re-run.
