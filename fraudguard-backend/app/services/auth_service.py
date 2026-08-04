"""Business logic for registration, login, token refresh, logout, and password reset."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictException, CredentialsException, PermissionDeniedException
from app.core.logging import logger
from app.core.redis_client import blacklist_token
from app.core.security import (
    TokenType,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenResponse, UserLogin, UserOut, UserRegister

settings = get_settings()


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #
    def register(self, payload: UserRegister) -> User:
        if self.users.get_by_email(payload.email):
            raise ConflictException(f"An account with email {payload.email} already exists.")

        # Bootstrap: the very first user in an empty system becomes Admin
        # automatically, regardless of the role they requested. After that,
        # self-registration as Admin is blocked — an existing Admin must
        # promote accounts manually (no such endpoint yet; direct DB update
        # or a future /users/{id}/role endpoint).
        is_first_user = self.users.count_all() == 0
        if is_first_user:
            role = UserRole.ADMIN
        elif payload.role == UserRole.ADMIN:
            raise PermissionDeniedException(
                "Self-registration as Admin is not permitted. Ask an existing Admin to promote your account."
            )
        else:
            role = payload.role

        user = User(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=role,
            is_active=True,
            is_verified=False,
        )
        user = self.users.create(user)
        logger.info(
            "User registered | id={} email={} role={} bootstrap_admin={}",
            user.id, user.email, user.role.value, is_first_user,
        )
        return user

    # ------------------------------------------------------------------ #
    # Login / tokens
    # ------------------------------------------------------------------ #
    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise CredentialsException("Incorrect email or password.")
        if not user.is_active:
            raise CredentialsException("This account has been deactivated.")
        return user

    def _issue_tokens(self, user: User) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id),
            user=UserOut.model_validate(user),
        )

    def login(self, payload: UserLogin) -> TokenResponse:
        user = self.authenticate(payload.email, payload.password)
        user.last_login_at = datetime.now(timezone.utc)
        self.users.save(user)
        logger.info("User logged in | id={} email={}", user.id, user.email)
        return self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, settings.JWT_REFRESH_SECRET_KEY, TokenType.REFRESH)
        user = self._user_from_subject(payload)

        # Rotate: blacklist the refresh token just used, so it can't be replayed.
        self._blacklist_from_payload(payload)

        logger.info("Access token refreshed | user_id={}", user.id)
        return self._issue_tokens(user)

    def logout(self, access_token: str, refresh_token: Optional[str] = None) -> None:
        """
        Blacklists whatever valid tokens are provided. Already-expired or
        malformed tokens are silently skipped — there's nothing to revoke.
        """
        candidates = [(access_token, settings.SECRET_KEY)]
        if refresh_token:
            candidates.append((refresh_token, settings.JWT_REFRESH_SECRET_KEY))

        for token, secret in candidates:
            try:
                payload = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])
                self._blacklist_from_payload(payload)
            except JWTError:
                continue

        logger.info("User logged out")

    # ------------------------------------------------------------------ #
    # Password reset
    # ------------------------------------------------------------------ #
    def forgot_password(self, email: str) -> Optional[str]:
        """
        Returns the raw reset token ONLY outside production (no email
        provider is wired up yet — see TODO below). In production this
        always returns None; the API layer must not leak whether an
        account exists for a given email either way.
        """
        user = self.users.get_by_email(email)
        if user is None:
            logger.info("Password reset requested for unknown email (no-op)")
            return None

        token = create_password_reset_token(user.id)

        if settings.ENVIRONMENT != "production":
            logger.info("[DEV ONLY] Password reset token for {}: {}", user.email, token)
            return token

        logger.info("Password reset token generated | user_id={}", user.id)
        # TODO: integrate a real email provider (Step 9+) and stop returning
        # the token from this method entirely once one exists.
        return None

    def reset_password(self, token: str, new_password: str) -> None:
        payload = decode_token(token, settings.SECRET_KEY, TokenType.PASSWORD_RESET)
        user = self._user_from_subject(payload)

        user.hashed_password = hash_password(new_password)
        self.users.save(user)
        self._blacklist_from_payload(payload)  # the reset token itself is now spent

        logger.info("Password reset completed | user_id={}", user.id)

    # ------------------------------------------------------------------ #
    # Shared helpers
    # ------------------------------------------------------------------ #
    def _user_from_subject(self, payload: dict) -> User:
        try:
            user_id = uuid.UUID(payload["sub"])
        except (KeyError, ValueError):
            raise CredentialsException("Malformed token subject.")
        user = self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise CredentialsException("User no longer exists or is inactive.")
        return user

    @staticmethod
    def _blacklist_from_payload(payload: dict) -> None:
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            ttl = int(exp - datetime.now(timezone.utc).timestamp())
            blacklist_token(jti, ttl)

    # ------------------------------------------------------------------ #
    # Profile / self-service (Settings page)
    # ------------------------------------------------------------------ #
    def update_profile(self, user: User, full_name: str) -> User:
        user.full_name = full_name
        user = self.users.save(user)
        logger.info("Profile updated | user_id={}", user.id)
        return user

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise CredentialsException("Current password is incorrect.")
        user.hashed_password = hash_password(new_password)
        self.users.save(user)
        logger.info("Password changed via Settings | user_id={}", user.id)

    def get_notification_preferences(self, user: User) -> dict:
        return user.notification_preferences or {}

    def update_notification_preferences(self, user: User, preferences: dict) -> dict:
        # Merge rather than overwrite — a client sending only the keys it
        # actually changed shouldn't silently wipe out preferences it never
        # touched (e.g. a future settings tab that only exposes 2 of 5 toggles).
        merged = {**(user.notification_preferences or {}), **preferences}
        user.notification_preferences = merged
        self.users.save(user)
        logger.info("Notification preferences updated | user_id={}", user.id)
        return merged
