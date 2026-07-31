"""
SQLAlchemy ORM models.

Importing this package (rather than individual model modules directly)
guarantees every table is registered on `Base.metadata` — required both for
Alembic autogenerate and for `Base.metadata.create_all()` in tests. Import
order matters where relationships reference each other by string name, but
SQLAlchemy resolves those lazily, so the order below (roughly: independent
tables first, dependent tables after) is for readability, not correctness.
"""

from app.models.user import User, UserRole
from app.models.transaction import Transaction
from app.models.model_registry import ModelRegistry, ModelStatus
from app.models.fraud_prediction import Decision, FraudPrediction
from app.models.fraud_log import FraudLog, LogStatus, PipelineStage
from app.models.review import AnalystDecision, ReviewQueue, ReviewStatus
from app.models.notification import Notification, NotificationType
from app.models.audit_log import AuditLog
from app.models.model_metrics import ModelMetrics

__all__ = [
    "User",
    "UserRole",
    "Transaction",
    "ModelRegistry",
    "ModelStatus",
    "FraudPrediction",
    "Decision",
    "FraudLog",
    "PipelineStage",
    "LogStatus",
    "ReviewQueue",
    "ReviewStatus",
    "AnalystDecision",
    "Notification",
    "NotificationType",
    "AuditLog",
    "ModelMetrics",
]
