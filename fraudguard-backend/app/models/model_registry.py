"""
Registry of every trained model version and its headline evaluation metrics.

Exactly one row should have status=ACTIVE at any time — that's the model
`ml_engine/predictor.py` loads for live inference. Enforced with a partial
unique index (Postgres-specific) rather than only in application code, so
it's impossible to end up with two "active" models even under a race
condition.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.fraud_prediction import FraudPrediction
    from app.models.model_metrics import ModelMetrics


class ModelStatus(str, enum.Enum):
    TRAINING = "training"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class ModelRegistry(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "model_registry"

    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False, default="XGBoost")
    status: Mapped[ModelStatus] = mapped_column(
        Enum(ModelStatus, name="model_status", values_callable=lambda obj: [e.value for e in obj]),
        default=ModelStatus.TRAINING,
        nullable=False,
        index=True,
    )

    # Headline metrics (also recorded in more detail/over time in ModelMetrics)
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    roc_auc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pr_auc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    training_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dataset_name: Mapped[str] = mapped_column(String(255), default="creditcard.csv (ULB)", nullable=False)
    dataset_row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    model_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    scaler_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    shap_explainer_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    hyperparameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    predictions: Mapped[List["FraudPrediction"]] = relationship(back_populates="model")
    metrics: Mapped[List["ModelMetrics"]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Table args — defined at the END of the class body, deliberately.
    # `status` must already exist as a class attribute here, since the
    # partial index expression (status == ModelStatus.ACTIVE) references
    # the column object itself.
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index(
            "ix_model_registry_single_active",
            "status",
            unique=True,
            postgresql_where=(status == ModelStatus.ACTIVE),
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ModelRegistry version={self.version} status={self.status.value}>"
