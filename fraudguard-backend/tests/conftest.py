"""
Shared pytest fixtures.

Tests run against a REAL Postgres database, not SQLite — several models use
Postgres-specific types (JSONB, native UUID; see e.g. Transaction.v_features)
that don't exist in SQLite, so an in-memory SQLite DB would silently test a
different schema than production runs on.

Defaults to a database named `fraudguard_test`, distinct from the `fraudguard`
dev database docker-compose creates, so running the suite never touches (or
wipes) your real demo data. Uses the SAME Postgres server as docker-compose's
`db` service — just a different logical database, created automatically on
first run if it doesn't exist yet. Override with the TEST_DATABASE_URL env
var to point somewhere else.
"""

import os
import uuid
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 — registers every table on Base.metadata; see app/models/__init__.py
from app.core.config import get_settings
from app.database.base import Base
from app.database.session import get_db
from app.main import app

settings = get_settings()


def _default_test_database_url() -> str:
    """Swaps the configured DATABASE_URL's database name for `fraudguard_test`,
    keeping the same host/credentials — works unmodified against either the
    docker-compose Postgres or a local install."""
    base_url = str(settings.DATABASE_URL)
    root, _, _ = base_url.rpartition("/")
    return f"{root}/fraudguard_test"


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", _default_test_database_url())


def _ensure_test_database_exists() -> None:
    """Connects to Postgres's `postgres` maintenance database and creates
    `fraudguard_test` if missing — mirrors what a human would do once by
    hand, automated so `pytest` works with zero manual setup."""
    admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    db_name = TEST_DATABASE_URL.rsplit("/", 1)[1]
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """
    SlowAPI's rate limiter (see core/rate_limit.py) uses in-memory storage
    shared across the whole pytest process — the same `app` instance (and
    therefore the same `app.state.limiter`) is imported once and reused by
    every test. Without a reset, admin_auth_headers alone calls the
    RATE_LIMIT_AUTH-limited /auth/register and /auth/login endpoints twice
    per test; nearly every test in this suite uses that fixture, so a full
    run would trip the limit and start failing unrelated tests with 429s
    well before all 23 finish. Reset before every test instead, same spirit
    as db_session wiping tables before every test.
    """
    app.state.limiter.reset()


@pytest.fixture(scope="session")
def test_engine():
    _ensure_test_database_exists()
    engine = create_engine(TEST_DATABASE_URL, connect_args={"options": "-c timezone=utc"})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine) -> Iterator[Session]:
    """
    Function-scoped session with every table wiped before each test.

    Deliberately a full wipe rather than the more common "wrap the test in a
    transaction and roll it back" pattern: every repository in this codebase
    calls `db.commit()` directly (see e.g. NotificationRepository.create),
    which would end the outer transaction a rollback-based strategy depends
    on staying open. A wipe-before-each-test is slightly slower but works
    correctly regardless of how deep a test's call stack commits.
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):  # FK-safe delete order
        session.execute(table.delete())
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    """A TestClient wired to use `db_session` instead of a real request-scoped
    session — every request in a test hits the same wiped-clean test DB."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_auth_headers(client: TestClient) -> dict:
    """
    Registers a fresh user, logs in, and returns `Authorization` headers for it.

    Uses a random email so tests never collide with each other, and relies
    on AuthService's documented bootstrap behavior — the very first user
    registered against an empty `users` table becomes admin automatically
    (see auth_service.py) — which is guaranteed here since db_session wipes
    the table before every test.
    """
    email = f"test-{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass123"

    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test Admin"},
    )
    assert register_response.status_code == 201, register_response.text

    login_response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
