"""
Database layer — SQLAlchemy engine, session management, declarative base.

Re-exports the pieces other modules need most often, so e.g. a route handler
can do `from app.database import get_db` instead of reaching into
`app.database.session` directly.
"""

from app.database.base import Base, TimestampMixin, UUIDMixin
from app.database.session import SessionLocal, check_database_connection, engine, get_db

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "SessionLocal",
    "engine",
    "get_db",
    "check_database_connection",
]
