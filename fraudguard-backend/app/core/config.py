"""
Centralized application configuration.

All environment-dependent values are declared here as a single Pydantic
Settings object, loaded once and cached. Nothing else in the codebase should
call `os.getenv` directly — every module imports `get_settings()` instead so
configuration stays in one auditable place.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = two levels up from this file (app/core/config.py -> app/ -> root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings, populated from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # General
    # ------------------------------------------------------------------ #
    PROJECT_NAME: str = "FraudGuard"
    PROJECT_DESCRIPTION: str = (
        "AI-Powered Real-Time Credit Card Fraud Detection System — "
        "production backend for real-time transaction risk scoring, "
        "explainability, and fraud analytics."
    )
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # ------------------------------------------------------------------ #
    # Security / JWT
    # ------------------------------------------------------------------ #
    SECRET_KEY: str = Field(..., description="Signing key for JWT access tokens")
    JWT_REFRESH_SECRET_KEY: str = Field(..., description="Signing key for JWT refresh tokens")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # ------------------------------------------------------------------ #
    # Database (PostgreSQL)
    # ------------------------------------------------------------------ #
    DATABASE_URL: PostgresDsn = Field(
        ..., description="postgresql+psycopg2://user:password@host:port/dbname"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # ------------------------------------------------------------------ #
    # Redis (caching, rate limiting, websocket pub/sub — later steps)
    # ------------------------------------------------------------------ #
    REDIS_URL: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------------ #
    # CORS
    #
    # Stored as a plain string (NOT List[str]) deliberately: pydantic-settings
    # attempts to JSON-decode any complex-typed (list/dict/set) field read
    # from a .env value *before* validators run, so a human-friendly
    # comma-separated string like "http://a,http://b" fails to parse as JSON
    # and blows up at startup. Keeping this a str and exposing a computed
    # `cors_origins_list` property sidesteps that entirely.
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS_ORIGINS split into a clean list, e.g. for CORSMiddleware(allow_origins=...)."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # ------------------------------------------------------------------ #
    # Rate limiting (SlowAPI) — wired up in a later step
    # ------------------------------------------------------------------ #
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_PREDICT: str = "30/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    # ------------------------------------------------------------------ #
    # ML / Dataset / Model artifacts
    # ------------------------------------------------------------------ #
    # The dataset lives in the project ROOT (one level above fraudguard-backend/),
    # per the project layout: C:\Drishti\FraudGuard\creditcard.csv
    DATASET_PATH: Path = BASE_DIR.parent / "creditcard.csv"
    MODEL_DIR: Path = BASE_DIR / "app" / "ml_engine" / "models"
    MODEL_FILE: str = "model.joblib"
    SCALER_FILE: str = "scaler.joblib"
    LABEL_ENCODER_FILE: str = "label_encoder.joblib"
    SHAP_EXPLAINER_FILE: str = "shap_explainer.joblib"
    METRICS_FILE: str = "metrics.json"
    MODEL_VERSION: str = "v1"

    # Decision engine thresholds (risk score is a 0.0–1.0 probability)
    RISK_THRESHOLD_APPROVE: float = 0.30
    RISK_THRESHOLD_BLOCK: float = 0.80

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = BASE_DIR / "logs"
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "14 days"

    # ------------------------------------------------------------------ #
    # WebSocket
    # ------------------------------------------------------------------ #
    WS_PATH: str = "/ws/dashboard"


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    lru_cache ensures the .env file and environment are only parsed once per
    process, and every module gets the exact same Settings object.
    """
    return Settings()
