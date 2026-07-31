"""
Liveness/readiness health check.

Distinct from the root `/` endpoint in main.py (static info, no I/O) — this
one actively probes the database, Redis, and trained-model availability, so
uptime monitors / Render's health check / a quick `curl` before a demo can
tell at a glance whether the service is actually ready to serve traffic, not
just that the process is alive.

Deliberately returns HTTP 200 even when a non-critical dependency (Redis) is
down, since the app is documented to fail-open on Redis (see
app/core/redis_client.py) — a monitor treating "Redis down" as "service
down" would trigger false-positive pages for a degraded-but-working API.
Only a missing database or missing model artifacts bring the overall
`status` to "unhealthy", since those two are hard requirements for the app
to do its actual job (serve predictions backed by real data).
"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.redis_client import get_redis_client
from app.database.session import check_database_connection

router = APIRouter()
settings = get_settings()


@router.get("/health", tags=["Health"])
async def health_check() -> dict:
    db_ok = check_database_connection()

    redis_client = get_redis_client()
    redis_ok = redis_client is not None

    model_path = settings.MODEL_DIR / settings.MODEL_FILE
    scaler_path = settings.MODEL_DIR / settings.SCALER_FILE
    model_ok = model_path.exists() and scaler_path.exists()

    overall_ok = db_ok and model_ok  # Redis is best-effort, not a hard dependency

    return {
        "status": "healthy" if overall_ok else "unhealthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": "up" if db_ok else "down",
            "redis": "up" if redis_ok else "down (fail-open — logout revocation degraded only)",
            "model": "loaded" if model_ok else "missing — run train_model.py",
        },
    }
