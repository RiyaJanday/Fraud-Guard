# ============================================================================
# FraudGuard Backend — production image
# Python 3.11 (matches .python-version — ML deps need mature prebuilt wheels)
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# psycopg2-binary needs libpq at runtime; build-essential covers anything
# without a prebuilt wheel for this base image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# App code, including the already-trained model artifacts in
# app/ml_engine/models/*.joblib (deliberately NOT excluded below — the
# deployed API can't train on startup, so the trained model has to travel
# with the image).
COPY app ./app
COPY alembic.ini .

# tests/ + pytest.ini: not needed to SERVE the API, but included so
# `docker compose exec backend pytest` (Step 10) works without a separate
# test-only image variant. Negligible size cost — no large fixtures/data
# files live under tests/, unlike app/ml_engine/models/.
COPY tests ./tests
COPY pytest.ini .

RUN mkdir -p /app/logs

# Render/Railway/most PaaS inject $PORT at runtime; default to 8000 for
# plain `docker run` / docker-compose use.
ENV PORT=8000
EXPOSE 8000

# Run migrations, then start the API. Using sh -c so $PORT expands.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
