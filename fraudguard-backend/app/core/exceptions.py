"""
Application exception hierarchy and centralized FastAPI exception handlers.

Every error path in the codebase should raise one of the exceptions defined
here (never a bare `HTTPException` scattered through route handlers). This
keeps error semantics consistent and lets us guarantee a single JSON error
shape across the entire API:

    {
        "success": false,
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Transaction 3f2e... was not found.",
            "details": null
        },
        "path": "/api/v1/transactions/3f2e...",
        "timestamp": "2026-07-15T10:32:00.123Z"
    }
"""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger


class AppException(Exception):
    """Base class for all application-raised (as opposed to framework) errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_SERVER_ERROR"

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


# --------------------------------------------------------------------------- #
# 4xx — client errors
# --------------------------------------------------------------------------- #
class BadRequestException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"


class CredentialsException(AppException):
    """Invalid/expired/missing JWT, or bad login credentials."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "INVALID_CREDENTIALS"


class PermissionDeniedException(AppException):
    """Authenticated, but the user's role does not permit this action (RBAC)."""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"


class ConflictException(AppException):
    """E.g. registering an email that already exists."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "RESOURCE_CONFLICT"


class ValidationException(AppException):
    """Domain-level validation failure that isn't a plain Pydantic schema error."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


class RateLimitExceededException(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"


# --------------------------------------------------------------------------- #
# 5xx / domain infrastructure errors
# --------------------------------------------------------------------------- #
class DatasetNotFoundException(AppException):
    """
    Raised when creditcard.csv is missing from the project root at training
    time. Deliberately NOT a generic 500 — the message tells the operator
    exactly what to do, since we never fabricate synthetic data as a fallback.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "DATASET_NOT_FOUND"


class ModelNotLoadedException(AppException):
    """Raised when a prediction is requested but no trained model artifacts exist yet."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "MODEL_NOT_LOADED"


class DatabaseException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "DATABASE_ERROR"


# --------------------------------------------------------------------------- #
# Response envelope helper
# --------------------------------------------------------------------------- #
def _error_response(
    request: Request, status_code: int, error_code: str, message: str, details: Any = None
) -> JSONResponse:
    # jsonable_encoder (rather than a raw dict passed straight to JSONResponse)
    # is essential here: Pydantic's exc.errors() can embed raw exception
    # objects (e.g. a ValueError raised inside a @field_validator ends up at
    # details[i]["ctx"]["error"]), and plain json.dumps() crashes on those
    # with a 500 instead of returning the intended 422. jsonable_encoder
    # safely serializes exceptions, UUIDs, datetimes, enums, etc. wherever
    # they show up in `details`.
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "success": False,
                "error": {"code": error_code, "message": message, "details": details},
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
    )


def _sanitize_validation_errors(errors: list) -> list:
    """
    jsonable_encoder alone would silently collapse ctx.error (a raw
    exception instance) down to an uninformative `{}`. Stringify it instead
    so a custom validator's message (e.g. "Password must contain at least
    one digit.") survives all the way into the JSON response, not just the
    top-level `msg` field.
    """
    sanitized = []
    for err in errors:
        err = dict(err)
        ctx = err.get("ctx")
        if isinstance(ctx, dict) and "error" in ctx:
            ctx = dict(ctx)
            ctx["error"] = str(ctx["error"])
            err["ctx"] = ctx
        sanitized.append(err)
    return sanitized


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every exception handler to the FastAPI app. Called once in main.py."""

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        # SlowAPI's own default handler returns a differently-shaped plain-text
        # response — routed through _error_response instead so a 429 looks like
        # every other error in this API, not a one-off exception to the frontend.
        logger.warning(
            "Rate limit exceeded | path={} | limit={}", request.url.path, exc.detail
        )
        return _error_response(
            request,
            status.HTTP_429_TOO_MANY_REQUESTS,
            "RATE_LIMIT_EXCEEDED",
            f"Too many requests. Limit: {exc.detail}. Please wait before trying again.",
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Handled application exception | code={} | path={} | message={}",
            exc.error_code,
            request.url.path,
            exc.message,
        )
        return _error_response(request, exc.status_code, exc.error_code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info("Request validation failed | path={} | errors={}", request.url.path, exc.errors())
        return _error_response(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "One or more fields failed validation.",
            details=_sanitize_validation_errors(exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return _error_response(request, exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Anything that reaches here is a genuine bug — log the full traceback.
        logger.exception("Unhandled exception | path={}", request.url.path)
        return _error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred. It has been logged for investigation.",
        )
