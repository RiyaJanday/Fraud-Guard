"""Admin-only endpoints for team/user management (Settings > Team tab)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import AdminCreateUserRequest, AdminCreateUserResponse, UserListItemOut, UserListResponse
from app.services.user_management_service import UserManagementService

router = APIRouter()


@router.get("", response_model=UserListResponse, summary="List all users (admin only)")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserListResponse:
    return UserManagementService(db).list_users(page=page, page_size=page_size)


@router.post(
    "",
    response_model=AdminCreateUserResponse,
    summary="Create a new user directly (admin only)",
    description=(
        "No email provider is wired up, so the generated temporary password is "
        "returned directly in this response — visible exactly once. Relay it to "
        "the new user out-of-band; it cannot be retrieved again afterward."
    ),
)
def create_user(
    payload: AdminCreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> AdminCreateUserResponse:
    return UserManagementService(db).create_user(payload)


@router.patch("/{user_id}/deactivate", response_model=UserListItemOut, summary="Deactivate a user (admin only)")
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserListItemOut:
    user = UserManagementService(db).set_active(user_id, is_active=False)
    return UserListItemOut.model_validate(user)


@router.patch("/{user_id}/activate", response_model=UserListItemOut, summary="Reactivate a user (admin only)")
def activate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserListItemOut:
    user = UserManagementService(db).set_active(user_id, is_active=True)
    return UserListItemOut.model_validate(user)
