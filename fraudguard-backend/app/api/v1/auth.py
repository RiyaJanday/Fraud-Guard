"""
Authentication endpoints.

Thin routes only — every handler does request/response translation and
delegates all logic to AuthService. Consistent with clean architecture:
API layer -> Service layer -> Repository layer -> Database.
"""

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.security import bearer_scheme, get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    description=(
        "Creates a new user. The very first account ever registered becomes "
        "Admin automatically; every account after that gets the requested "
        "role (Analyst or Auditor) — self-registering as Admin is rejected."
    ),
)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> User:
    return AuthService(db).register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with email and password",
)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    return AuthService(db).login(payload)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new access/refresh token pair",
    description="The refresh token used in this call is immediately revoked (single-use / rotation).",
)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return AuthService(db).refresh(payload.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out and revoke the current tokens",
    description=(
        "Revokes the access token used to authenticate this request, and the "
        "refresh token too if provided in the body. Revocation is enforced via "
        "a Redis blacklist; if Redis is unreachable, revocation fails open and "
        "the tokens simply expire naturally instead (see app/core/redis_client.py)."
    ),
)
def logout(
    payload: RefreshTokenRequest | None = None,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    AuthService(db).logout(
        access_token=credentials.credentials,
        refresh_token=payload.refresh_token if payload else None,
    )
    logger.info("Logout endpoint called | user_id={}", current_user.id)
    return MessageResponse(message="Logged out successfully.")


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get the currently authenticated user",
)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request a password reset token",
    description=(
        "Always returns the same generic message whether or not the email "
        "exists, to avoid leaking account existence. Outside production, "
        "the response also includes the raw reset token directly (no email "
        "provider is wired up yet) so this flow can be tested end-to-end."
    ),
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    token = AuthService(db).forgot_password(payload.email)
    return ForgotPasswordResponse(dev_reset_token=token)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset a password using a reset token",
)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    AuthService(db).reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Password has been reset successfully. Please log in with your new password.")
