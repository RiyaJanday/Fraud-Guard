"""
Admin-only user management: list all accounts, create a new one directly
(no self-registration flow, no email provider exists to send an invite —
see AuthService.forgot_password for the same limitation elsewhere), and
activate/deactivate accounts.
"""

import secrets
import string
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.core.logging import logger
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import AdminCreateUserRequest, AdminCreateUserResponse, UserListItemOut, UserListResponse


def _generate_temp_password() -> str:
    """
    12 random characters guaranteed to satisfy the same password_strength
    rule every other password on this system follows (>=1 letter, >=1
    digit) — built explicitly rather than trusting secrets.token_urlsafe()
    to happen to include a digit, which it doesn't always.
    """
    alphabet = string.ascii_letters + string.digits
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(12))
        if any(c.isdigit() for c in candidate) and any(c.isalpha() for c in candidate):
            return candidate


class UserManagementService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def list_users(self, page: int = 1, page_size: int = 50) -> UserListResponse:
        items, total = self.users.list_all(page=page, page_size=page_size)
        return UserListResponse(items=[UserListItemOut.model_validate(u) for u in items], total=total)

    def create_user(self, payload: AdminCreateUserRequest) -> AdminCreateUserResponse:
        if self.users.get_by_email(payload.email):
            raise ConflictException(f"An account with email {payload.email} already exists.")

        temp_password = _generate_temp_password()
        user = User(
            email=payload.email.lower(),
            hashed_password=hash_password(temp_password),
            full_name=payload.full_name,
            role=payload.role,
            is_active=True,
            is_verified=False,
        )
        user = self.users.create(user)
        logger.info("User created by admin | id={} email={} role={}", user.id, user.email, user.role.value)
        return AdminCreateUserResponse(user=UserListItemOut.model_validate(user), temporary_password=temp_password)

    def set_active(self, user_id: uuid.UUID, is_active: bool) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundException(f"User {user_id} was not found.")
        user.is_active = is_active
        user = self.users.save(user)
        logger.info("User {} | id={}", "activated" if is_active else "deactivated", user.id)
        return user
