"""
Manual review workflow for high-risk predictions.

Prediction --(high risk)--> ReviewQueue --(analyst decision)--> ground truth
stored for future model retraining. One row per FraudPrediction that needed
human eyes — not every prediction gets one (low-risk approvals never enter
this table at all).
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.fraud_prediction import FraudPrediction
    from app.models.user import User


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"


class AnalystDecision(str, enum.Enum):
    FRAUD = "fraud"
    LEGITIMATE = "legitimate"


class ReviewQueue(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "review_queue"
    __table_args__ = (
        Index("ix_review_queue_status_created_at", "status", "created_at"),
    )

    fraud_prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fraud_predictions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    assigned_analyst_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status", values_callable=lambda obj: [e.value for e in obj]),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    analyst_decision: Mapped[Optional[AnalystDecision]] = mapped_column(
        Enum(AnalystDecision, name="analyst_decision", values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
        comment="Ground truth captured for future model retraining",
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    fraud_prediction: Mapped["FraudPrediction"] = relationship(back_populates="review")
    analyst: Mapped[Optional["User"]] = relationship(
        back_populates="assigned_reviews", foreign_keys=[assigned_analyst_id]
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ReviewQueue id={self.id} status={self.status.value}>"
