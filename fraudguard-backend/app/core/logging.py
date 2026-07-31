"""
Application-wide logging configuration, built on Loguru.

Responsibilities:
  * Configure Loguru sinks (console + rotating file) from Settings.
  * Redirect the standard library `logging` module (used internally by
    Uvicorn, SQLAlchemy, etc.) into Loguru so every log line — ours and
    third-party — ends up in one consistent, structured stream.

Nothing else in the codebase should call `logging.getLogger(...)` directly;
import `logger` from this module instead:

    from app.core.logging import logger
    logger.info("Prediction completed", transaction_id=str(txn.id))
"""

import logging
import sys
from pathlib import Path

from loguru import logger as loguru_logger

from app.core.config import get_settings

settings = get_settings()

# The single logger instance the rest of the app imports.
logger = loguru_logger


class InterceptHandler(logging.Handler):
    """
    Routes standard-library `logging` records into Loguru.

    Uvicorn, SQLAlchemy, and other third-party libraries log via the stdlib
    `logging` module. Without this handler, their output would bypass
    Loguru's formatting/sinks entirely and show up in a different style
    (or not at all once we disable stdlib's default handlers).
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Map the stdlib level to the matching Loguru level name.
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find the caller so Loguru reports the *original* call site,
        # not this interceptor.
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging() -> None:
    """
    Initialize Loguru sinks and intercept stdlib logging.

    Called once at application startup (see app/main.py's lifespan handler).
    """
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    loguru_logger.remove()  # drop Loguru's default stderr sink so we control formatting

    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    loguru_logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format=console_format,
        colorize=True,
        backtrace=settings.ENVIRONMENT != "production",
        diagnose=settings.ENVIRONMENT != "production",
    )

    # Rotating file sink — plain text for local dev, still useful in prod
    # until a centralized log shipper (e.g. ELK, Loki) is wired up.
    loguru_logger.add(
        Path(settings.LOG_DIR) / "fraudguard.log",
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        enqueue=True,  # process-safe, non-blocking writes
        backtrace=False,
        diagnose=False,
    )

    # Separate sink exclusively for errors/exceptions — makes incident
    # triage fast without grepping through INFO-level noise.
    loguru_logger.add(
        Path(settings.LOG_DIR) / "errors.log",
        level="ERROR",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        enqueue=True,
    )

    # Redirect stdlib logging (uvicorn, sqlalchemy, fastapi, ...) into Loguru.
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for noisy_logger in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy_logger).handlers = [InterceptHandler()]
        logging.getLogger(noisy_logger).propagate = False

    loguru_logger.info(
        "Logging configured | environment={} | level={}",
        settings.ENVIRONMENT,
        settings.LOG_LEVEL,
    )
