"""
Result of running a transaction through the ML inference pipeline.

One-to-one with Transaction (a transaction is scored once; re-scoring, if
ever needed, creates a new Transaction rather than mutating history — this
keeps the audit trail immutable). Denormalizes `model_version` alongside the
`model_registry_id` FK so this row remains meaningful/readable even if the
referenced ModelRegistry entry is later archived.
"""

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.model_registry import ModelRegistry
    from app.models.review import ReviewQueue
    from app.models.transaction import Transaction


class Decision(str, enum.Enum):
    """Decision engine output. Thresholds live in Settings, applied in the service layer."""

    APPROVE = "approve"
    MFA_REQUIRED = "mfa_required"
    BLOCKED = "blocked"


class FraudPrediction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "fraud_predictions"
    __table_args__ = (
        Index("ix_fraud_predictions_decision_created_at", "decision", "created_at"),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    model_registry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_registry.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    is_fraud: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    fraud_probability: Mapped[float] = mapped_column(Float, nullable=False, comment="Raw model output, 0.0-1.0")
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, index=True, comment="fraud_probability scaled 0-100")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, comment="Model's confidence in this prediction, 0.0-1.0")
    decision: Mapped[Decision] = mapped_column(
        Enum(Decision, name="decision", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, comment="Inference wall-clock time")

    top_shap_features: Mapped[list] = mapped_column(
        JSONB, nullable=False,
        comment='[{"feature": "V17", "impact": 0.31, "value": -3.2}, ...] ordered by |impact| desc',
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False, comment="Natural-language SHAP explanation")

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    transaction: Mapped["Transaction"] = relationship(back_populates="prediction")
    model: Mapped[Optional["ModelRegistry"]] = relationship(back_populates="predictions")
    review: Mapped[Optional["ReviewQueue"]] = relationship(
        back_populates="fraud_prediction", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FraudPrediction id={self.id} decision={self.decision.value} risk_score={self.risk_score}>"
