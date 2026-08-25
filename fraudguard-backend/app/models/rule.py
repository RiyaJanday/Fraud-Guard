"""
Business-logic rules that run alongside the ML model, not instead of it.

The XGBoost model is a statistical judgment; some fraud policy is not
statistical at all — "always block a first-ever transaction over 50,000"
is a compliance decision, not something you want silently dependent on
model confidence drifting over time. Rules give admins/analysts a way to
express that kind of hard business logic without retraining anything.

Evaluated by app/services/rule_engine.py against the raw Transaction fields
(available at submission time, before the ML pipeline even runs) — not
against the model's output — so a rule match is never contingent on the
model being right.
"""

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class RuleField(str, enum.Enum):
    """Transaction fields a rule can target. Deliberately limited to fields
    present on the raw submission payload (see TransactionCreate) — a rule
    should be evaluable the instant a transaction arrives, without waiting
    on the ML pipeline."""

    AMOUNT = "amount"
    CURRENCY = "currency"
    MERCHANT = "merchant"
    CUSTOMER_REFERENCE = "customer_reference"
    CARD_LAST4 = "card_last4"
    DEVICE_INFO = "device_info"
    IP_ADDRESS = "ip_address"
    LOCATION = "location"
    TIME_FEATURE = "time_feature"


class RuleOperator(str, enum.Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"
    CONTAINS = "contains"


class RuleAction(str, enum.Enum):
    """
    What happens to the transaction's decision when this rule matches.
    Severity order (weakest to strongest): NOTIFY < FLAG < BLOCK. Multiple
    matched rules combine by taking the strongest action across all matches
    — see rule_engine.py.

    NOTIFY — no decision change, just an extra notification for visibility.
    FLAG   — pushes the transaction into the manual review queue if the
             model's own decision wouldn't have (upgrades APPROVE ->
             MFA_REQUIRED); never downgrades an existing BLOCKED.
    BLOCK  — hard override to BLOCKED regardless of what the model decided.
    """

    NOTIFY = "notify"
    FLAG = "flag"
    BLOCK = "block"


class Rule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "rules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    field: Mapped[RuleField] = mapped_column(
        Enum(RuleField, name="rule_field", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    operator: Mapped[RuleOperator] = mapped_column(
        Enum(RuleOperator, name="rule_operator", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Stored as text regardless of field type; rule_engine.py casts to float for numeric fields.",
    )
    action: Mapped[RuleAction] = mapped_column(
        Enum(RuleAction, name="rule_action", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    created_by: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Rule id={self.id} name={self.name!r} {self.field.value} {self.operator.value} {self.value!r} -> {self.action.value}>"
