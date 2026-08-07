"""
FraudGuard backend entry point.

Builds the FastAPI application via a factory function (`create_app`) rather
than a bare module-level `app = FastAPI()`, so tests can spin up isolated
instances with different settings/overrides later (Step 10).

Run locally with:
    uvicorn app.main:app --reload
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, logger
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.websocket import manager as ws_manager

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan handler.

    Startup and shutdown logic is centralized here (the modern replacement
    for the deprecated `@app.on_event` decorators). Database engine
    disposal, ML model loading, and Redis connection warm-up will be added
    to this function in their respective steps — for now it only wires up
    logging so every request from boot onward is captured.
    """
    configure_logging()
    logger.info(
        "Starting {} v{} [{}]",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )
    logger.info("Dataset path configured as: {}", settings.DATASET_PATH)
    logger.info("Model artifact directory: {}", settings.MODEL_DIR)

    # Step 8: bind the WebSocket connection manager to THIS event loop (the
    # one FastAPI actually serves requests on). Sync services running in the
    # threadpool (transaction_service.py) need this reference to schedule a
    # broadcast via asyncio.run_coroutine_threadsafe — see core/websocket.py.
    ws_manager.bind_loop(asyncio.get_running_loop())
    logger.info("WebSocket connection manager bound to event loop.")

    yield  # ---- application runs here ----

    logger.info("Shutting down {}", settings.PROJECT_NAME)


def create_app() -> FastAPI:
    """Application factory. Assembles middleware, routers, and error handlers."""

    # ---------------------------------------------------------------- #
    # /docs, /redoc, and the raw OpenAPI schema are only served outside
    # production. They don't gate any actual access (every route behind
    # them still requires the same JWT + RBAC either way), but there's no
    # reason to publish the full API surface — including admin-only route
    # shapes — to anyone who finds the live URL. Set ENVIRONMENT=production
    # in Render's env vars to disable these; see .env.example.
    # ---------------------------------------------------------------- #
    is_production = settings.ENVIRONMENT == "production"
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
        lifespan=lifespan,
    )

    # ---------------------------------------------------------------- #
    # Security headers (see app/core/security_headers.py) — applied first
    # (outermost) so they land on every response, including error responses
    # from the exception handlers registered below.
    # ---------------------------------------------------------------- #
    app.add_middleware(SecurityHeadersMiddleware)

    # ---------------------------------------------------------------- #
    # Rate limiting (SlowAPI) — in-memory, per-client-IP. Individual routes
    # opt in via @limiter.limit(...) (see api/v1/auth.py, api/v1/prediction.py);
    # this just wires the shared Limiter instance + its request-state hook
    # into the app. The actual 429 response shape is handled by
    # register_exception_handlers below, not SlowAPI's own default handler.
    # ---------------------------------------------------------------- #
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    # ---------------------------------------------------------------- #
    # CORS — allows the React (Vite) frontend to call this API directly.
    # ---------------------------------------------------------------- #
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------------- #
    # Centralized error handling (see app/core/exceptions.py)
    # ---------------------------------------------------------------- #
    register_exception_handlers(app)

    # ---------------------------------------------------------------- #
    # Routers
    # ---------------------------------------------------------------- #
    app.include_router(api_router)

    @app.get("/", tags=["Root"])
    async def root() -> dict:
        """Basic liveness/info endpoint — not the full health check (see Step 8)."""
        return {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": None if is_production else "/docs",
        }

    return app


app = create_app()
