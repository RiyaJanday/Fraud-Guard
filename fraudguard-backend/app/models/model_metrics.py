"""
Point-in-time evaluation snapshots for a model version — confusion matrix,
ROC/PR curve points, latency, and prediction volume. Distinct from the
headline metrics on ModelRegistry: this table lets `GET /metrics` show
trends over time (e.g. accuracy drifting week over week) rather than a
single fixed number per model version.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.model_registry import ModelRegistry


class ModelMetrics(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "model_metrics"
    __table_args__ = (
        Index("ix_model_metrics_model_recorded_at", "model_registry_id", "recorded_at"),
    )

    model_registry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_registry.id", ondelete="CASCADE"), nullable=False, index=True
    )

    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    precision: Mapped[float] = mapped_column(Float, nullable=False)
    recall: Mapped[float] = mapped_column(Float, nullable=False)
    f1_score: Mapped[float] = mapped_column(Float, nullable=False)

    confusion_matrix: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment='{"tp": 0, "fp": 0, "tn": 0, "fn": 0}'
    )
    roc_curve: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment='{"fpr": [...], "tpr": [...], "thresholds": [...]}'
    )
    pr_curve: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment='{"precision": [...], "recall": [...], "thresholds": [...]}'
    )

    avg_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prediction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        comment="When this snapshot was computed — may differ from created_at if backfilled",
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    model: Mapped["ModelRegistry"] = relationship(back_populates="metrics")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ModelMetrics model={self.model_registry_id} f1={self.f1_score}>"
