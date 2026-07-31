"""
Persisted notifications shown in the dashboard's notification panel.

`user_id = NULL` means a broadcast notification (visible to every
analyst/admin), matching how dashboard-wide alerts like "High Risk Alert"
work in the frontend rather than being addressed to one person.
"""

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.user import User


class NotificationType(str, enum.Enum):
    HIGH_RISK_ALERT = "high_risk_alert"
    BLOCKED_TRANSACTION = "blocked_transaction"
    REVIEW_REQUIRED = "review_required"
    MODEL_UPDATE = "model_update"
    SYSTEM = "system"


class Notification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_is_read", "user_id", "is_read"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True,
        comment="NULL = broadcast to all users",
    )
    related_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    user: Mapped[Optional["User"]] = relationship(back_populates="notifications")
    related_transaction: Mapped[Optional["Transaction"]] = relationship(back_populates="notifications")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Notification id={self.id} type={self.type.value} is_read={self.is_read}>"
