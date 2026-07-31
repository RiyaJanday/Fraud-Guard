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
