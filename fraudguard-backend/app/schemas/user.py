"""Pydantic schemas for authentication and user representation."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserRegister(BaseModel):
    """POST /register request body."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    # Public registration may request analyst/auditor; ADMIN is rejected here
    # unless this is the very first user in the system (see AuthService.register).
    role: UserRole = UserRole.ANALYST

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in value):
            raise ValueError("Password must contain at least one letter.")
        return value


class UserLogin(BaseModel):
    """POST /login request body."""

    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Public-facing user representation — never includes hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class TokenResponse(BaseModel):
    """Returned by /login and /refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in value):
            raise ValueError("Password must contain at least one letter.")
        return value


class MessageResponse(BaseModel):
    """Generic success wrapper for endpoints with no meaningful payload to return."""

    message: str


class ForgotPasswordResponse(BaseModel):
    """
    Returned by POST /forgot-password.

    `dev_reset_token` is populated ONLY when ENVIRONMENT != "production" (no
    email provider is wired up yet — see AuthService.forgot_password). The
    `message` is deliberately identical whether or not the email exists, to
    avoid leaking account existence to an attacker.
    """

    message: str = "If an account with that email exists, a password reset link has been sent."
    dev_reset_token: Optional[str] = None


class UserUpdateRequest(BaseModel):
    """PATCH /auth/me — deliberately just full_name. Email is intentionally
    NOT editable here: it's the login identifier and changing it without any
    re-verification flow would be a real security footgun, not just a UX nicety
    to skip."""

    full_name: str = Field(..., min_length=2, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in value):
            raise ValueError("Password must contain at least one letter.")
        return value


class NotificationPreferencesOut(BaseModel):
    preferences: dict


class NotificationPreferencesUpdateRequest(BaseModel):
    preferences: dict


class ProfileStatsOut(BaseModel):
    """
    Real, computed-from-the-review-queue stats — deliberately NOT an
    "accuracy rate", which would need ground truth this system doesn't
    independently have. Confirmed/marked-legitimate counts and average
    response time are honestly computable from ReviewQueue instead.
    """

    cases_reviewed: int
    fraud_confirmed: int
    marked_legitimate: int
    avg_response_minutes: Optional[float] = None


class ProfileActivityItemOut(BaseModel):
    transaction_id: uuid.UUID
    merchant: Optional[str] = None
    analyst_decision: Optional[str] = None
    resolved_at: datetime


class UserListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class UserListResponse(BaseModel):
    items: list[UserListItemOut]
    total: int


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = UserRole.ANALYST


class AdminCreateUserResponse(BaseModel):
    """
    Includes the generated temporary password exactly ONCE, in this response
    only — it is never retrievable again afterward (only its bcrypt hash is
    stored). No email provider exists to deliver it any other way (same
    limitation as AuthService.forgot_password); the admin is expected to
    relay it to the new user out-of-band.
    """

    user: UserListItemOut
    temporary_password: str
