"""
Incoming transactions submitted for fraud scoring.

Stores both the raw model-input features (the same shape as the ULB dataset:
Time, V1–V28, Amount) and business-facing metadata that a real payment
gateway would provide but the anonymized training dataset does not (merchant,
card, device, location). The V1–V28 PCA components are stored as a single
JSONB column rather than 28 near-identical Float columns — same data,
dramatically less boilerplate, and still fully queryable in Postgres
(`v_features ->> 'V17'`).
"""

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.fraud_log import FraudLog
    from app.models.fraud_prediction import FraudPrediction
    from app.models.notification import Notification
    from app.models.user import User


class Transaction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_merchant_created_at", "merchant", "created_at"),
    )

    # ------------------------------------------------------------------ #
    # ML model input — mirrors the ULB dataset schema exactly
    # ------------------------------------------------------------------ #
    time_feature: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Seconds elapsed, same semantics as the dataset's Time column"
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    v_features: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment='PCA components V1..V28, e.g. {"V1": -1.359, ..., "V28": -0.021}'
    )

    # ------------------------------------------------------------------ #
    # Business metadata — not present in the training dataset, but part of
    # any real transaction submitted through the API.
    # ------------------------------------------------------------------ #
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    merchant: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    customer_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    card_last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    device_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    submitted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    submitted_by: Mapped[Optional["User"]] = relationship(
        back_populates="submitted_transactions", foreign_keys=[submitted_by_id]
    )
    prediction: Mapped[Optional["FraudPrediction"]] = relationship(
        back_populates="transaction", uselist=False, cascade="all, delete-orphan"
    )
    logs: Mapped[List["FraudLog"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(back_populates="related_transaction")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Transaction id={self.id} amount={self.amount} merchant={self.merchant!r}>"
