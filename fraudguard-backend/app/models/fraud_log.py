"""
Structured event log for each stage of the fraud-detection pipeline.

Distinct from AuditLog: AuditLog records *who called what API endpoint*;
FraudLog records *what the ML pipeline did to a specific transaction*
(Validation → Preprocessing → Prediction → Decision → Persistence →
Notification). Lets an engineer reconstruct exactly what happened to a
single transaction without grepping application logs.
"""

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class PipelineStage(str, enum.Enum):
    VALIDATION = "validation"
    PREPROCESSING = "preprocessing"
    PREDICTION = "prediction"
    DECISION = "decision"
    PERSISTENCE = "persistence"
    NOTIFICATION = "notification"


class LogStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class FraudLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "fraud_logs"
    __table_args__ = (
        Index("ix_fraud_logs_transaction_stage", "transaction_id", "stage"),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage, name="pipeline_stage", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    status: Mapped[LogStatus] = mapped_column(
        Enum(LogStatus, name="log_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Stage-specific structured detail, e.g. feature values or error traces"
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    transaction: Mapped["Transaction"] = relationship(back_populates="logs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FraudLog stage={self.stage.value} status={self.status.value} txn={self.transaction_id}>"
