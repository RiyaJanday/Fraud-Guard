"""
Raw database access for User records. No business logic here — that's
AuthService's job. Every method takes/returns ORM objects or primitives,
never Pydantic schemas (those belong to the API/service boundary).
"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return self.db.execute(stmt).scalar_one_or_none()

    def count_all(self) -> int:
        """Used to detect a fresh install (0 users) for the first-admin bootstrap."""
        stmt = select(func.count()).select_from(User)
        return self.db.execute(stmt).scalar_one()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def save(self, user: User) -> User:
        """Persist changes to an already-tracked User instance (e.g. after mutating fields)."""
        self.db.commit()
        self.db.refresh(user)
        return user
