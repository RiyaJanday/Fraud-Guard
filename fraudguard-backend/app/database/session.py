"""
SQLAlchemy engine, session factory, and the `get_db` FastAPI dependency.

Every repository/service takes a `Session` injected via `Depends(get_db)` —
nothing outside this module ever calls `SessionLocal()` directly, so
connection handling stays in exactly one place.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

engine = create_engine(
    str(settings.DATABASE_URL),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # transparently recycles dropped connections
    echo=settings.DB_ECHO,
    # Forces every connection's Postgres session to UTC, regardless of the
    # server's own configured timezone (which defaults to the OS locale on
    # many local installs — e.g. IST on a machine set to an Indian locale).
    # Without this, date_trunc('hour'/'day', a_timestamptz_column) in the
    # analytics queries truncates using the SESSION's timezone, not UTC. For
    # any timezone with a non-whole-hour UTC offset (IST is UTC+5:30), that
    # produces hour/day boundaries that don't line up with the UTC-aligned
    # boundaries this code computes in Python — so every bucket lookup
    # silently misses and every chart comes back all zeros, even with real
    # data in the table. Confirmed via real testing and reproduced/fixed
    # deliberately (see analytics_repository.py for the affected queries).
    connect_args={"options": "-c timezone=utc"},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a request-scoped DB session and guarantees
    it is closed afterwards, even if the request raises.

        @router.get("/transactions")
        def list_transactions(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Lightweight connectivity probe used by the `/health` endpoint (Step 8).
    Does not raise — returns False on any failure so health checks degrade
    gracefully instead of crashing the endpoint that reports the outage.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 — deliberately broad for a health probe
        logger.error("Database connectivity check failed: {}", exc)
        return False
