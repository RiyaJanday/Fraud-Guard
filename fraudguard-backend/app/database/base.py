"""
Declarative base and shared model mixins.

Every SQLAlchemy model inherits from `Base` plus the two mixins below, which
together satisfy the project-wide requirement that *every* table has a UUID
primary key and created_at / updated_at timestamps — without repeating that
boilerplate in each of the 9 model files.

Deliberately contains NO imports of app.models.* — models import Base from
here, so if this module imported them back we'd have a circular import. The
model registry (making sure every table actually lands on Base.metadata for
Alembic autogenerate) lives in app/models/__init__.py instead, which Alembic's
env.py imports explicitly.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in the application."""


class UUIDMixin:
    """UUID primary key, generated client-side (no reliance on a Postgres extension)."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """created_at / updated_at, both timezone-aware and maintained automatically."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
