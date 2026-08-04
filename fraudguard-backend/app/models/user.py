"""User accounts, authentication, and RBAC roles."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.notification import Notification
    from app.models.review import ReviewQueue
    from app.models.transaction import Transaction


class UserRole(str, enum.Enum):
    """
    RBAC roles.

    ADMIN    — full access, manages users and model registry.
    ANALYST  — reviews flagged transactions, resolves the manual review queue.
    AUDITOR  — read-only access to audit logs, reports, and analytics.
    """

    ADMIN = "admin"
    ANALYST = "analyst"
    AUDITOR = "auditor"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda obj: [e.value for e in obj]),
        default=UserRole.ANALYST,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notification_preferences: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment='e.g. {"blocked_transaction": true, "high_risk_alert": true, "review_required": false}. '
        "Missing keys are treated as enabled by default (see NotificationService).",
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    submitted_transactions: Mapped[List["Transaction"]] = relationship(
        back_populates="submitted_by", foreign_keys="Transaction.submitted_by_id"
    )
    assigned_reviews: Mapped[List["ReviewQueue"]] = relationship(
        back_populates="analyst", foreign_keys="ReviewQueue.assigned_analyst_id"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"
