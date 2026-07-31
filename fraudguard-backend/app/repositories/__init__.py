"""Repository layer — all raw database queries live here, nowhere else."""

from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.fraud_log_repository import FraudLogRepository
from app.repositories.fraud_prediction_repository import FraudPredictionRepository
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "UserRepository",
    "TransactionRepository",
    "FraudPredictionRepository",
    "FraudLogRepository",
    "ModelRegistryRepository",
    "ReviewRepository",
    "AnalyticsRepository",
]
